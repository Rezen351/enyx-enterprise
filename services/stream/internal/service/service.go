package service

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"net/http"
	"net/url"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
	"sync"
	"syscall"
	"time"

	"github.com/almuzky/iot/services/stream/internal/client/mediamtx"
	miniosvc "github.com/almuzky/iot/services/stream/internal/client/minio"
	mlclient "github.com/almuzky/iot/services/stream/internal/client/ml"
	"github.com/almuzky/iot/services/stream/internal/model"
	"github.com/almuzky/iot/services/stream/internal/repository"
	"github.com/google/uuid"
)

// Errors surfaced to the handler.
var (
	ErrNotFound      = repository.ErrNotFound
	ErrMediaMTX      = errors.New("mediamtx operation failed")
	ErrMinIO         = errors.New("minio operation failed")
	ErrDuplicateName = errors.New("stream name already exists")
	ErrInvalidName   = errors.New("invalid stream name")
)

// StreamService coordinates DB metadata with MediaMTX path registration.
type StreamService struct {
	repo     *repository.Repository
	media    *mediamtx.Client
	minio    *miniosvc.Client
	ml       *mlclient.Client
	kongURL  string
	cctvRTSP string

	// Active ffmpeg recordings, keyed by stream id. The Stream Service records
	// directly via ffmpeg (not MediaMTX's disk recorder) so the resulting clip
	// is uploaded to MinIO and surfaced as a playable Gallery item.
	recMu   sync.Mutex
	recJobs map[string]*recJob
}

// recJob tracks a single in-progress ffmpeg recording.
type recJob struct {
	cmd       *exec.Cmd
	outPath   string
	name      string
	streamID  string
	moduleID  string
	done      chan struct{} // closed once ffmpeg is fully reaped by the reaper
	startTime time.Time
}

func New(repo *repository.Repository, media *mediamtx.Client, minioClient *miniosvc.Client, mlClient *mlclient.Client, kongURL, cctvRTSP string) *StreamService {
	return &StreamService{repo: repo, media: media, minio: minioClient, ml: mlClient, kongURL: kongURL, cctvRTSP: cctvRTSP, recJobs: make(map[string]*recJob)}
}

// CreateStream inserts the DB row then registers the path in MediaMTX.
// If MediaMTX registration fails, the DB row is rolled back (deleted) so the
// two systems never diverge.
func (s *StreamService) CreateStream(ctx context.Context, req model.CreateStreamRequest) (*model.StreamView, error) {
	name := strings.TrimSpace(req.Name)
	if name == "" {
		return nil, fmt.Errorf("name is required")
	}
	// Reject names that could be used for MediaMTX path traversal (e.g.
	// containing "/" or "..") or that are not safe HLS segment names.
	if !validStreamName(name) {
		return nil, ErrInvalidName
	}
	source := req.SourceRTSP
	if strings.TrimSpace(source) == "" {
		if s.cctvRTSP == "" {
			return nil, fmt.Errorf("source_rtsp is required (no default CCTV_RTSP_URL configured)")
		}
		source = s.cctvRTSP
	}

	// Best-effort duplicate guard before touching MediaMTX (race tolerated).
	if existing, _ := s.repo.GetStreamByName(ctx, name); existing != nil {
		return nil, ErrDuplicateName
	}

	st, err := s.repo.CreateStream(ctx, name, req.DeviceLabel, req.Location, source, req.NodeID, req.ModuleID)
	if err != nil {
		// Likely a duplicate-key on `name` at the DB layer.
		if isDuplicateErr(err) {
			return nil, ErrDuplicateName
		}
		return nil, err
	}

	if err := s.media.AddPath(ctx, name, source); err != nil {
		// Roll back the DB row so metadata & MediaMTX stay consistent.
		if delErr := s.repo.DeleteStream(ctx, st.ID); delErr != nil && delErr != repository.ErrNotFound {
			return nil, fmt.Errorf("mediamtx add failed and rollback failed: %v (original: %v)", delErr, err)
		}
		return nil, fmt.Errorf("%w: %v", ErrMediaMTX, err)
	}

	return s.toView(ctx, st), nil
}

// GetStream returns metadata + live status + playback URLs.
func (s *StreamService) GetStream(ctx context.Context, id string) (*model.StreamView, error) {
	st, err := s.repo.GetStream(ctx, id)
	if err != nil {
		return nil, err
	}
	// API-added MediaMTX paths are ephemeral and disappear on a MediaMTX
	// restart. Lazily re-register the path here so a single fetch (e.g. when
	// the dashboard opens the player) self-heals the "path not configured"
	// error instead of surfacing it to the user.
	s.ensurePath(ctx, st)
	return s.toView(ctx, st), nil
}

// ListStreams returns all streams with live status + playback URLs,
// optionally scoped to a single module (module_id).
func (s *StreamService) ListStreams(ctx context.Context, moduleID string) ([]model.StreamView, error) {
	streams, err := s.repo.ListStreams(ctx, moduleID)
	if err != nil {
		return nil, err
	}
	out := make([]model.StreamView, 0, len(streams))
	for i := range streams {
		out = append(out, *s.toView(ctx, &streams[i]))
	}
	return out, nil
}

// UpdateStream patches metadata. MediaMTX path is NOT re-registered (source is
// immutable after creation in Fase 5); changing the source requires delete+create.
// UpdateStream patches metadata. When the name or source changes, the
// MediaMTX path is re-registered (old path removed, new path added with the
// updated name/source) so live playback keeps working.
func (s *StreamService) UpdateStream(ctx context.Context, id string, req model.UpdateStreamRequest) (*model.StreamView, error) {
	current, err := s.repo.GetStream(ctx, id)
	if err != nil {
		return nil, err
	}
	oldName := current.Name

	// Validate the new name BEFORE persisting so an invalid name (slash, "..",
	// whitespace) can never be written to the DB — otherwise a rejected update
	// would still leave a traversal-unsafe MediaMTX path / HLS segment name
	// stored (returned as 400 but silently persisted).
	if req.Name != nil && !validStreamName(*req.Name) {
		return nil, ErrInvalidName
	}

	st, err := s.repo.UpdateStream(ctx, id, req)
	if err != nil {
		return nil, err
	}

	changed := (req.Name != nil && *req.Name != oldName) ||
		(req.SourceRTSP != nil && *req.SourceRTSP != current.SourceRTSP)
	if changed {
		// Best-effort removal of the old path; ignore "not found".
		if err := s.media.RemovePath(ctx, oldName); err != nil {
			if !mediamtx.IsNotFound(err) {
				return nil, err
			}
		}
		source := st.SourceRTSP
		if req.SourceRTSP != nil && *req.SourceRTSP != "" {
			source = *req.SourceRTSP
		}
		if req.NodeID != nil {
			current.NodeID = *req.NodeID
		}
		if req.ModuleID != nil {
			current.ModuleID = *req.ModuleID
		}
		if err := s.media.AddPath(ctx, st.Name, source); err != nil {
			return nil, fmt.Errorf("%w: %v", ErrMediaMTX, err)
		}
	}

	return s.toView(ctx, st), nil
}

// DeleteStream removes the MediaMTX path first, then the DB row — even if the
// DB delete already succeeded we still attempt the MediaMTX removal so the
// server does not keep pulling a deleted stream.
func (s *StreamService) DeleteStream(ctx context.Context, id string) error {
	st, err := s.repo.GetStream(ctx, id)
	if err != nil {
		return err
	}
	// Best-effort MediaMTX cleanup; do not block on it fatally.
	if err := s.media.RemovePath(ctx, st.Name); err != nil {
		return fmt.Errorf("%w: %v", ErrMediaMTX, err)
	}
	if err := s.repo.DeleteStream(ctx, id); err != nil {
		return err
	}
	return nil
}

// toView enriches a stream with MediaMTX status and playback URLs.
func (s *StreamService) toView(ctx context.Context, st *model.Stream) *model.StreamView {
	status := "idle"
	if st.Enabled {
		status = s.media.GetPathStatus(ctx, st.Name)
	}
	s.recMu.Lock()
	job, recording := s.recJobs[st.ID]
	var startTime int64
	if recording {
		startTime = job.startTime.UnixMilli()
	}
	s.recMu.Unlock()

	return &model.StreamView{
		ID:             st.ID,
		Name:           st.Name,
		DeviceLabel:    st.DeviceLabel,
		Location:       st.Location,
		SourceRTSP:     redactRTSPCreds(st.SourceRTSP),
		NodeID:         st.NodeID,
		ModuleID:       st.ModuleID,
		Enabled:        st.Enabled,
		Status:         status,
		HlsURL:         s.hlsURL(st.Name),
		WebRTCURL:      s.webrtcURL(st.Name),
		Recording:      recording,
		RecordingStart: startTime,
		CreatedAt:      st.CreatedAt,
		UpdatedAt:      st.UpdatedAt,
	}
}

// ensurePath re-registers a stream's MediaMTX path config if it is missing.
// API-added paths are ephemeral and lost on a MediaMTX restart, so we must
// restore them; this is idempotent (AddPath overwrites) and only fires when
// the path is actually absent, preserving any user-set runtime state (e.g.
// recording toggles).
func (s *StreamService) ensurePath(ctx context.Context, st *model.Stream) {
	if !st.Enabled {
		return
	}
	if s.media.PathExists(ctx, st.Name) {
		return
	}
	if err := s.media.AddPath(ctx, st.Name, st.SourceRTSP); err != nil {
		log.Printf("[stream] ensure path %q failed (playback may error until next reconcile): %v", st.Name, err)
		return
	}
	log.Printf("[stream] re-registered missing MediaMTX path %q", st.Name)
}

// ReconcilePaths restores every enabled stream's path config into MediaMTX.
// MediaMTX drops API-registered paths on restart, while the DB keeps the
// streams, so the two drift apart ("path 'X' is not configured"). This is run
// at startup and on a timer so a MediaMTX restart self-heals. Existing paths
// are left untouched to avoid clobbering runtime state.
func (s *StreamService) ReconcilePaths(ctx context.Context) {
	streams, err := s.repo.ListStreams(ctx, "")
	if err != nil {
		log.Printf("[stream] reconcile: list streams failed: %v", err)
		return
	}
	registered, skipped := 0, 0
	for i := range streams {
		st := streams[i]
		if !st.Enabled {
			continue
		}
		if s.media.PathExists(ctx, st.Name) {
			skipped++
			continue
		}
		if err := s.media.AddPath(ctx, st.Name, st.SourceRTSP); err != nil {
			log.Printf("[stream] reconcile: add path %q failed: %v", st.Name, err)
			continue
		}
		registered++
	}
	if registered > 0 {
		log.Printf("[stream] reconcile: re-registered %d path(s), %d already present", registered, skipped)
	}
}

func (s *StreamService) hlsURL(name string) string {
	base := strings.TrimRight(s.kongURL, "/")
	return fmt.Sprintf("%s/hls/%s/index.m3u8", base, name)
}

// webrtcURL builds the host-direct WHEP playback URL. WebRTC media/STUN cannot
// traverse Kong, so it points at the MediaMTX WebRTC port (8889) on the host
// that the browser resolves. The host is derived from KONG_PUBLIC_URL. WHEP is
// an HTTP POST of the SDP offer (not a raw ws:// connection).
func (s *StreamService) webrtcURL(name string) string {
	host := "localhost"
	if u, err := url.Parse(s.kongURL); err == nil && u.Hostname() != "" {
		host = u.Hostname()
	}
	return fmt.Sprintf("http://%s:8889/%s/whep", host, name)
}

func isDuplicateErr(err error) bool {
	if err == nil {
		return false
	}
	msg := strings.ToLower(err.Error())
	return strings.Contains(msg, "duplicate") || strings.Contains(msg, "1062") || strings.Contains(msg, "unique")
}

// validStreamName enforces a safe MediaMTX path / HLS segment name. It
// rejects anything that could enable path traversal into MediaMTX (slashes,
// "..", NUL, whitespace) so a crafted stream name can never escape the
// intended /hls/<name>/index.m3u8 namespace.
var streamNameRE = regexp.MustCompile(`^[A-Za-z0-9_.-]{1,64}$`)

func validStreamName(name string) bool {
	return streamNameRE.MatchString(name)
}

// rtspCredRE matches the embedded credentials in an RTSP URL
// (rtsp://user:pass@host/...). The source RTSP URL stores CCTV credentials
// that must never be returned to API clients, so we strip the userinfo.
var rtspCredRE = regexp.MustCompile(`^rtsp://[^/@]+@`)

func redactRTSPCreds(u string) string {
	return rtspCredRE.ReplaceAllString(u, "rtsp://")
}

// ServeObject streams a MinIO object to the client using the service's scoped
// credentials. The bucket stays private; access is gated by JWT at the
// handler and validated here (no path traversal, allowed buckets only).
func (s *StreamService) ServeObject(w http.ResponseWriter, bucket, key string) error {
	if s.minio == nil {
		return fmt.Errorf("%w: not configured", ErrMinIO)
	}
	if !miniosvc.ValidObjectPath(bucket, key) {
		return fmt.Errorf("%w: invalid object path", ErrMinIO)
	}
	return s.minio.ServeObject(w, bucket, key)
}

// ─── Snapshots & Recordings ───────────────────────────────────────────────────

// CaptureSnapshot grabs the current frame of a stream from MediaMTX.
//   - detect=false (plain snapshot): the frame is uploaded to the MinIO stream
//     bucket and a "snapshot" metadata row is stored — shown only in the
//     gallery's SNAPSHOT tab. No ML is involved.
//   - detect=true (AI Detect): the frame is sent to the AI vision model and the
//     result (frame + detection JSON + annotated image) is written to the shared
//     ml bucket — shown in the gallery's AI DETECTION tab. Nothing is
//     written to the stream bucket or the stream-DB snapshots table.
func (s *StreamService) CaptureSnapshot(ctx context.Context, id string, detect bool) (*model.SnapshotView, error) {
	if s.minio == nil {
		return nil, fmt.Errorf("%w: client not configured", ErrMinIO)
	}
	st, err := s.repo.GetStream(ctx, id)
	if err != nil {
		return nil, err
	}

	data, ct, err := s.media.CaptureSnapshot(ctx, st.Name)
	if err != nil {
		return nil, fmt.Errorf("%w: %v", ErrMediaMTX, err)
	}

	if !detect {
		// Plain snapshot: upload the original frame to the stream bucket and a
		// "snapshot" row, so it appears only in the SNAPSHOT tab.
		key := fmt.Sprintf("snapshots/%s/%s.jpg", st.Name, uuid.New().String())
		url, err := s.minio.UploadObject(key, ct, data)
		if err != nil {
			return nil, fmt.Errorf("%w: %v", ErrMinIO, err)
		}
		snap := &model.Snapshot{
			ID:          uuid.New().String(),
			StreamID:    st.ID,
			StreamName:  st.Name,
			ModuleID:    st.ModuleID,
			ObjectKey:   key,
			URL:         url,
			ContentType: ct,
			Size:        int64(len(data)),
			Kind:        "snapshot",
			CreatedAt:   time.Now(),
		}
		if _, err := s.repo.CreateSnapshot(ctx, snap); err != nil {
			return nil, err
		}
		return toSnapshotView(snap), nil
	}

	// AI Detect: run the frame through the vision model and store the result in
	// the shared ml bucket (gallery AI DETECTION tab). Nothing is written
	// to the stream bucket or the stream-DB snapshots table — the authoritative
	// copy lives in ml, same as the cron capture job.
	if s.ml == nil {
		return nil, fmt.Errorf("%w: AI vision client not configured", ErrMinIO)
	}
	result, derr := s.ml.Detect(ctx, data, fmt.Sprintf("%s_%s.jpg", st.Name, uuid.New().String()))
	if derr != nil {
		return nil, fmt.Errorf("ai vision detection failed: %w", derr)
	}
	if result == nil {
		return nil, fmt.Errorf("ai vision returned no result")
	}

	if s.minio != nil {
		s.writeToResultBucket(st.Name, data, ct, result)
	}

	// Response view built from the detection result (not persisted to the
	// stream DB; the stored copy is in ml).
	classesJSON, _ := json.Marshal(result.Classes)
	detJSON, _ := json.Marshal(result.Detections)
	view := model.SnapshotView{
		ID:            uuid.New().String(),
		StreamID:      st.ID,
		StreamName:    st.Name,
		Kind:          "detection",
		Size:          int64(len(data)),
		CreatedAt:     time.Now(),
		ModelID:       result.ModelID,
		ModelName:     result.ModelName,
		NumDetections: result.NumDetections,
		Classes:       string(classesJSON),
		Detections:    string(detJSON),
		ConfidenceAvg: result.ConfidenceAvg,
		RootLengthCM:  result.RootLengthCM,
		TuberSizeCM:   result.TuberSizeCM,
		Condition:     result.Condition,
	}
	return &view, nil
}

// knownBuckets are the buckets the gallery's ml listing can read from;
// used to parse a minio public URL (e.g. annotated_url) back into bucket+key.
var knownBuckets = []string{"mlbucket", "stream"}

// bucketAndKeyFromURL extracts (bucket, key) from a minio public URL such as
// "http://host/minio/ml/detected/foo.jpg" or "/storage/ml/...".
func bucketAndKeyFromURL(raw string) (string, string) {
	rest := raw
	if i := strings.Index(rest, "://"); i >= 0 {
		rest = rest[i+3:]
	}
	rest = strings.TrimPrefix(rest, "/")
	segs := strings.Split(rest, "/")
	for i, seg := range segs {
		for _, b := range knownBuckets {
			if seg == b {
				return b, strings.Join(segs[i+1:], "/")
			}
		}
	}
	return "", strings.Join(segs, "/")
}

// writeToResultBucket stores the captured frame, the optional annotated image
// (mirrored from the ML bucket), and a result JSON record into the shared
// mlbucket bucket. Best-effort: each upload is attempted independently and
// failures are logged so one bad write never prevents the others.
func (s *StreamService) writeToResultBucket(streamName string, data []byte, ct string, result *mlclient.DetectResult) {
	bucket := "mlbucket"
	ts := time.Now().UTC().Format("20060102_150405")

	frameKey := fmt.Sprintf("frames/%s/%s.jpg", streamName, ts)
	frameURL, err := s.minio.UploadObjectToBucket(bucket, frameKey, ct, data)
	if err != nil {
		log.Printf("[result-bucket] frame upload failed: %v", err)
	} else {
		detMap := map[string]any{
			"detection_uid":  result.DetectionUID,
			"model_id":       result.ModelID,
			"model_name":     result.ModelName,
			"num_detections": result.NumDetections,
			"classes":        result.Classes,
			"detections":     result.Detections,
			"confidence_avg": result.ConfidenceAvg,
			"root_length_cm": result.RootLengthCM,
			"tuber_size_cm":  result.TuberSizeCM,
			"condition":      result.Condition,
		}
		record := map[string]any{
			"captured_at": time.Now().UTC().Format(time.RFC3339),
			"stream":      streamName,
			"trigger":     "user",
			"source_rtsp": fmt.Sprintf("mediamtx:%s", streamName),
			"frame_key":   frameKey,
			"frame_url":   frameURL,
			"detection":   detMap,
		}
		recordBytes, merr := json.MarshalIndent(record, "", "  ")
		if merr != nil {
			log.Printf("[result-bucket] record marshal failed: %v", merr)
		} else if _, uerr := s.minio.UploadObjectToBucket(bucket, fmt.Sprintf("results/%s/%s.json", streamName, ts), "application/json", recordBytes); uerr != nil {
			log.Printf("[result-bucket] result json upload failed: %v", uerr)
		}
	}

	if result.AnnotatedURL != "" {
		srcBucket, srcKey := bucketAndKeyFromURL(result.AnnotatedURL)
		if srcBucket != "" {
			if annotated, rerr := s.minio.ReadObject(srcBucket, srcKey); rerr == nil {
				meta := map[string]string{
					"root_length_cm": floatPtrStr(result.RootLengthCM),
					"tuber_size_cm":  floatPtrStr(result.TuberSizeCM),
					"condition":      floatPtrStr(result.Condition),
					"confidence":     floatStr(result.ConfidenceAvg),
					"num_detections": strconv.Itoa(result.NumDetections),
				}
				if _, aerr := s.minio.UploadObjectToBucketWithMetadata(bucket, fmt.Sprintf("annotated/%s/%s.jpg", streamName, ts), "image/jpeg", annotated, meta); aerr != nil {
					log.Printf("[result-bucket] annotated mirror failed: %v", aerr)
				}
			} else {
				log.Printf("[result-bucket] annotated read failed: %v", rerr)
			}
		}
	}
}

// ListSnapshots returns snapshots/recordings newest-first (optional kind and
// module filters).
func (s *StreamService) ListSnapshots(ctx context.Context, kind, moduleID string) ([]model.SnapshotView, error) {
	snaps, err := s.repo.ListSnapshots(ctx, kind, moduleID)
	if err != nil {
		return nil, err
	}
	out := make([]model.SnapshotView, 0, len(snaps))
	for i := range snaps {
		out = append(out, *toSnapshotView(&snaps[i]))
	}
	return out, nil
}

// GetSnapshot returns a single snapshot view.
func (s *StreamService) GetSnapshot(ctx context.Context, id string) (*model.SnapshotView, error) {
	snap, err := s.repo.GetSnapshot(ctx, id)
	if err != nil {
		return nil, err
	}
	return toSnapshotView(snap), nil
}

// DeleteSnapshot removes the DB row and the MinIO object.
func (s *StreamService) DeleteSnapshot(ctx context.Context, id string) error {
	snap, err := s.repo.GetSnapshot(ctx, id)
	if err != nil {
		return err
	}
	if s.minio != nil {
		_ = s.minio.DeleteObject(snap.ObjectKey)
	}
	return s.repo.DeleteSnapshot(ctx, id)
}

// StartRecording begins an ffmpeg capture of the stream's RTSP relay and writes
// it to a temp .mp4. The clip is finalized and uploaded to MinIO on StopRecording.
func (s *StreamService) StartRecording(ctx context.Context, id string) error {
	st, err := s.repo.GetStream(ctx, id)
	if err != nil {
		return err
	}

	s.recMu.Lock()
	if _, ok := s.recJobs[id]; ok {
		s.recMu.Unlock()
		return fmt.Errorf("%w: recording already in progress for this stream", ErrMediaMTX)
	}
	outPath := filepath.Join(os.TempDir(), "rec-"+uuid.New().String()+".mp4")
	// Pull from the MediaMTX RTSP relay (which triggers the on-demand source).
	// Transcode to browser-playable H.264 video and AAC audio with +faststart.
	cmd := exec.Command("ffmpeg",
		"-rtsp_transport", "tcp",
		"-analyzeduration", "2000000", "-probesize", "10M",
		"-y",
		"-i", fmt.Sprintf("rtsp://mediamtx:8554/%s", st.Name),
		// ultrafast+zerolatency: minimal encoding latency so ffmpeg keeps pace
		// with the RTSP source in realtime (avoids 0-byte output on short clips).
		// NOTE: -pix_fmt yuv420p is intentionally omitted — the input H264 stream
		// is already yuv420p, so the flag creates an unnecessary libavfilter graph
		// that cannot be cleanly flushed on SIGINT ("Error marking filters as
		// finished"), resulting in a 0-byte output file.
		"-c:v", "libx264", "-preset", "ultrafast", "-tune", "zerolatency", "-crf", "28",
		"-map", "0:v?", "-map", "0:a?",
		outPath)
	if err := cmd.Start(); err != nil {
		s.recMu.Unlock()
		return fmt.Errorf("%w: failed to start recorder: %v", ErrMediaMTX, err)
	}
	job := &recJob{cmd: cmd, outPath: outPath, name: st.Name, streamID: st.ID, moduleID: st.ModuleID, done: make(chan struct{}), startTime: time.Now()}
	s.recJobs[id] = job
	s.recMu.Unlock()

	// Sole owner of cmd.Wait(): reaps the process, then (if this is still the
	// active job) cleans up the temp file and closes done so StopRecording can
	// proceed. Calling Wait() more than once on a *exec.Cmd is a race/error, so
	// no other goroutine may call it.
	go func() {
		if err := job.cmd.Wait(); err != nil {
			log.Printf("[recorder] ffmpeg for %s ended: %v", st.Name, err)
		}
		s.recMu.Lock()
		if cur, still := s.recJobs[id]; still && cur == job {
			delete(s.recJobs, id)
			os.Remove(outPath)
		}
		s.recMu.Unlock()
		close(job.done)
	}()

	// Liveness probe: if ffmpeg dies immediately (e.g. source offline) remove the
	// job so StopRecording reports a clear error. Extended to 3 s to give ffmpeg
	// enough time to negotiate the RTSP session before being falsely marked dead.
	go func() {
		time.Sleep(3000 * time.Millisecond)
		s.recMu.Lock()
		cur, still := s.recJobs[id]
		s.recMu.Unlock()
		if still && cur == job && job.cmd.Process != nil && job.cmd.Process.Signal(syscall.Signal(0)) != nil {
			s.recMu.Lock()
			delete(s.recJobs, id)
			s.recMu.Unlock()
			os.Remove(outPath)
			log.Printf("[recorder] ffmpeg for %s exited early (source unavailable)", st.Name)
		}
	}()

	return nil
}

// StopRecording ends the active ffmpeg recording, uploads the resulting MP4 to
// MinIO, and stores a "recording" snapshot (playable + downloadable in Gallery).
func (s *StreamService) StopRecording(ctx context.Context, id string) (*model.SnapshotView, error) {
	s.recMu.Lock()
	job, ok := s.recJobs[id]
	if !ok {
		s.recMu.Unlock()
		return nil, fmt.Errorf("%w: no active recording for this stream", ErrMediaMTX)
	}
	delete(s.recJobs, id)
	s.recMu.Unlock()

	// Enforce a minimum recording window: ffmpeg needs ~5–6 s to complete RTSP
	// negotiation and stream analysis before it starts encoding frames. At 5 s
	// SIGINT, 0 frames were written ("Error marking filters as finished"). 12 s
	// guarantees enough buffered data even if startup takes its maximum time.
	const minRecordingDuration = 12 * time.Second
	if elapsed := time.Since(job.startTime); elapsed < minRecordingDuration {
		time.Sleep(minRecordingDuration - elapsed)
	}

	// Take ownership of the file: it was removed from the map so the reaper
	// (which owns cmd.Wait()) will NOT delete it once ffmpeg exits. We need it
	// for the MinIO upload below.
	// Signal ffmpeg to finalize the MP4 (write the moov atom), then force-kill
	// if it does not exit promptly. The reaper goroutine owns cmd.Wait() and
	// closes job.done once the process is fully reaped.
	if job.cmd.Process != nil {
		_ = job.cmd.Process.Signal(syscall.SIGINT)
	}
	select {
	case <-job.done:
	case <-time.After(10 * time.Second):
		if job.cmd.Process != nil {
			_ = job.cmd.Process.Kill()
		}
		<-job.done
	}

	info, serr := os.Stat(job.outPath)
	if serr != nil || info.Size() == 0 {
		os.Remove(job.outPath)
		return nil, fmt.Errorf("%w: no recording produced (stream may be unavailable)", ErrMediaMTX)
	}

	if s.minio == nil {
		os.Remove(job.outPath)
		return nil, fmt.Errorf("%w: client not configured", ErrMinIO)
	}

	// Probe duration BEFORE removing the temp file so ffprobe reads the file.
	dur := probeDuration(job.outPath)

	key := fmt.Sprintf("recordings/%s/%s.mp4", job.name, uuid.New().String())
	url, uerr := s.minio.UploadFile(key, "video/mp4", job.outPath)
	os.Remove(job.outPath)
	if uerr != nil {
		return nil, fmt.Errorf("%w: %v", ErrMinIO, uerr)
	}

	snap := &model.Snapshot{
		ID:          uuid.New().String(),
		StreamID:    job.streamID,
		StreamName:  job.name,
		ModuleID:    job.moduleID,
		ObjectKey:   key,
		URL:         url,
		ContentType: "video/mp4",
		Size:        info.Size(),
		Kind:        "recording",
		Duration:    dur,
		CreatedAt:   time.Now(),
	}
	if _, err := s.repo.CreateSnapshot(ctx, snap); err != nil {
		return nil, err
	}
	return toSnapshotView(snap), nil
}

// probeDuration returns the actual length (seconds) of a media file using
// ffprobe, so the recorded clip's true duration is stored and shown to the user
// (it may differ slightly from the wall-clock recording timer due to source
// startup / finalize overhead).
func probeDuration(path string) float64 {
	out, err := exec.Command("ffprobe", "-v", "error",
		"-show_entries", "format=duration",
		"-of", "default=nokey=1:noprint_wrappers=1", path).Output()
	if err != nil {
		return 0
	}
	var d float64
	if _, err := fmt.Sscanf(strings.TrimSpace(string(out)), "%f", &d); err != nil {
		return 0
	}
	return d
}

func toSnapshotView(s *model.Snapshot) *model.SnapshotView {
	return &model.SnapshotView{
		ID:            s.ID,
		StreamID:      s.StreamID,
		StreamName:    s.StreamName,
		ModuleID:      s.ModuleID,
		URL:           s.URL,
		Kind:          s.Kind,
		Size:          s.Size,
		CreatedAt:     s.CreatedAt,
		ModelID:       s.ModelID,
		ModelName:     s.ModelName,
		NumDetections: s.NumDetections,
		Classes:       s.Classes,
		Detections:    s.Detections,
		ConfidenceAvg: s.ConfidenceAvg,
		Duration:      s.Duration,
		RootLengthCM:  s.RootLengthCM,
		TuberSizeCM:   s.TuberSizeCM,
		Condition:     s.Condition,
	}
}

func floatPtrStr(v *float64) string {
	if v == nil {
		return ""
	}
	return strconv.FormatFloat(*v, 'f', 2, 64)
}

func floatStr(v float64) string {
	return strconv.FormatFloat(v, 'f', 4, 64)
}
