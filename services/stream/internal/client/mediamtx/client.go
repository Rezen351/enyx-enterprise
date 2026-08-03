package mediamtx

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"image/jpeg"
	"io"
	"log"
	"math"
	"net/http"
	"os/exec"
	"strings"
	"time"
)

// Client wraps the MediaMTX Control API (v3). It registers/removes path
// configurations (config/paths) and reads runtime path status (paths).
//
// Endpoints used (MediaMTX v3):
//   - POST   /v3/config/paths/add/{name}    — persist a path config (source pull)
//   - DELETE /v3/config/paths/delete/{name} — remove a path config
//   - GET    /v3/paths/get/{name}           — runtime state (idle/waiting/running/ready)
//   - PATCH  /v3/config/paths/patch/{name}  — update a path (e.g. record on/off)
//
// The HTTP/HLS server (separate port) serves single-frame snapshots at
// /live/{name}/snapshot, used for snapshot capture.
type Client struct {
	baseURL string // Control API (v3), e.g. http://mediamtx:9997
	httpURL string // HTTP/HLS server, e.g. http://mediamtx:8888 (snapshot source)
	rtspURL string // RTSP server, e.g. rtsp://mediamtx:8554 (legacy/compat only)
	httpCl  *http.Client
}

func New(baseURL string) *Client {
	return &Client{
		baseURL: baseURL,
		rtspURL: "rtsp://mediamtx:8554",
		httpCl:  &http.Client{Timeout: 15 * time.Second},
	}
}

// WithHTTPURL sets the MediaMTX HTTP/HLS server base URL.
func (c *Client) WithHTTPURL(u string) *Client {
	c.httpURL = u
	return c
}

// WithRTSPURL sets the MediaMTX RTSP base URL (legacy/compat only; snapshots
// use the HTTP snapshot endpoint).
func (c *Client) WithRTSPURL(u string) *Client {
	if u != "" {
		c.rtspURL = u
	}
	return c
}

// addPathConf is the request body for config/paths/add. Only the fields we set.
type addPathConf struct {
	Source                     string `json:"source"`
	SourceOnDemand             bool   `json:"sourceOnDemand"`
	SourceOnDemandStartTimeout string `json:"sourceOnDemandStartTimeout"`
	SourceOnDemandCloseAfter   string `json:"sourceOnDemandCloseAfter"`
	Record                     bool   `json:"record"`
}

// pathGetResponse is a subset of the runtime Path object returned by /v3/paths/get.
// MediaMTX v3 does not expose a single "state" field; the runtime state is
// derived from online/ready/available, so all three are captured here.
// NOTE: `source` is a JSON object, so it is intentionally omitted here to
// avoid an unmarshal error on the whole response.
type pathGetResponse struct {
	Name      string `json:"name"`
	State     string `json:"state"`
	Ready     bool   `json:"ready"`
	Available bool   `json:"available"`
	Online    bool   `json:"online"`
	Tracks    []any  `json:"tracks"`
}

// AddPath registers a path config that pulls `source` on demand.
func (c *Client) AddPath(ctx context.Context, name, source string) error {
	body, _ := json.Marshal(addPathConf{
		Source:                     source,
		SourceOnDemand:             true,
		SourceOnDemandStartTimeout: "5s",
		SourceOnDemandCloseAfter:   "15s",
		Record:                     false,
	})
	url := fmt.Sprintf("%s/v3/config/paths/add/%s", c.baseURL, name)
	if err := c.do(ctx, http.MethodPost, url, body); err != nil {
		return fmt.Errorf("mediamtx add path %q: %w", name, err)
	}
	return nil
}

// RemovePath deletes a previously registered path config.
func (c *Client) RemovePath(ctx context.Context, name string) error {
	url := fmt.Sprintf("%s/v3/config/paths/delete/%s", c.baseURL, name)
	// 404 is acceptable (already gone) — treat as success.
	if err := c.do(ctx, http.MethodDelete, url, nil); err != nil {
		if IsNotFound(err) {
			return nil
		}
		return fmt.Errorf("mediamtx remove path %q: %w", name, err)
	}
	return nil
}

// PathExists reports whether a path config is currently registered in
// MediaMTX (true on 200, false on 404 or any other outcome).
func (c *Client) PathExists(ctx context.Context, name string) bool {
	url := fmt.Sprintf("%s/v3/config/paths/get/%s", c.baseURL, name)
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
	if err != nil {
		return false
	}
	resp, err := c.httpCl.Do(req)
	if err != nil {
		return false
	}
	defer resp.Body.Close()
	return resp.StatusCode == http.StatusOK
}

// GetPathStatus returns the runtime state string for a path ("unknown" on miss/error).
func (c *Client) GetPathStatus(ctx context.Context, name string) string {
	url := fmt.Sprintf("%s/v3/paths/get/%s", c.baseURL, name)
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
	if err != nil {
		return "unknown"
	}
	resp, err := c.httpCl.Do(req)
	if err != nil {
		return "unknown"
	}
	defer resp.Body.Close()
	if resp.StatusCode == http.StatusNotFound {
		return "idle"
	}
	if resp.StatusCode != http.StatusOK {
		return "unknown"
	}
	data, _ := io.ReadAll(resp.Body)
	var p pathGetResponse
	if err := json.Unmarshal(data, &p); err != nil {
		return "unknown"
	}

	// Derive a state string from MediaMTX v3 fields.
	// State is only present on older builds; otherwise infer it.
	if p.State != "" {
		return p.State
	}
	switch {
	case p.Ready:
		return "ready"
	case p.Available || p.Online:
		return "waiting"
	default:
		return "idle"
	}
}

// apiError carries the HTTP status for NotFound detection.
type apiError struct {
	status int
	msg    string
}

func (e *apiError) Error() string { return e.msg }

func IsNotFound(err error) bool {
	if e, ok := err.(*apiError); ok {
		return e.status == http.StatusNotFound
	}
	return false
}

func (c *Client) do(ctx context.Context, method, url string, body []byte) error {
	var rdr io.Reader
	if body != nil {
		rdr = bytes.NewReader(body)
	}
	req, err := http.NewRequestWithContext(ctx, method, url, rdr)
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", "application/json")
	resp, err := c.httpCl.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 200 && resp.StatusCode < 300 {
		return nil
	}
	b, _ := io.ReadAll(resp.Body)
	msg := string(bytes.TrimSpace(b))
	if msg == "" {
		msg = fmt.Sprintf("status %d", resp.StatusCode)
	}
	log.Printf("[mediamtx] %s %s -> %d: %s", method, url, resp.StatusCode, msg)
	return &apiError{status: resp.StatusCode, msg: msg}
}

// SetRecord toggles MediaMTX recording for a path via the v3 config patch API.
func (c *Client) SetRecord(ctx context.Context, name string, enabled bool) error {
	body, _ := json.Marshal(map[string]any{"record": enabled})
	url := fmt.Sprintf("%s/v3/config/paths/patch/%s", c.baseURL, name)
	return c.do(ctx, http.MethodPatch, url, body)
}

// snapshotAttempts is how many times we retry a snapshot before giving up.
// Paths are registered with sourceOnDemand, so the first frame may not be ready
// immediately; reading the RTSP relay triggers source startup, so retrying with
// backoff waits for the stream to become live.
//
// The total worst-case budget (attempts × ffmpegTimeout + backoff) stays well
// below the stream server's http WriteTimeout (see main.go) so the response is
// never aborted mid-write (which would surface as a Kong 504).
const snapshotAttempts = 4

// ffmpegTimeout bounds a single ffmpeg capture attempt.
const ffmpegTimeout = 12 * time.Second

// minSnapshotBytes rejects tiny/partial frames. A real 1080p JPEG frame is tens
// of KB; a garbled first-GOP frame is a few KB. Below this we retry, but accept
// any non-empty frame on the final attempt so a legitimately simple/dark scene
// is still captured.
const minSnapshotBytes = 20 * 1024

// CaptureSnapshot grabs a single frame from the MediaMTX RTSP relay
// (rtsp://mediamtx:8554/{name}) using ffmpeg and encodes it as JPEG.
//
// MediaMTX has no built-in HTTP snapshot endpoint, so we pull one frame from the
// RTSP output — this also triggers the on-demand source. Returns the JPEG bytes
// plus content type, retrying with backoff to tolerate an idle source, and
// rejecting uniform gray/placeholder frames (source "ready" but no real video).
func (c *Client) CaptureSnapshot(ctx context.Context, name string) ([]byte, string, error) {
	if c.rtspURL == "" {
		return nil, "", fmt.Errorf("mediamtx RTSP URL not configured")
	}
	src := fmt.Sprintf("%s/%s", strings.TrimRight(c.rtspURL, "/"), name)

	backoff := 1 * time.Second
	var lastErr error
	for attempt := 0; attempt < snapshotAttempts; attempt++ {
		if attempt > 0 {
			select {
			case <-ctx.Done():
				return nil, "", fmt.Errorf("mediamtx snapshot cancelled: %w", ctx.Err())
			case <-time.After(backoff):
			}
			backoff *= 2
			if backoff > 2*time.Second {
				backoff = 2 * time.Second
			}
		}

		data, err := c.ffmpegFrame(ctx, src)
		if err != nil {
			lastErr = err
			continue
		}
		// Reject tiny frames — the source is likely not live yet. A real frame
		// on the final attempt is still accepted.
		if len(data) < minSnapshotBytes && attempt != snapshotAttempts-1 {
			lastErr = fmt.Errorf("mediamtx snapshot produced incomplete frame (%d bytes) — stream may not be live", len(data))
			continue
		}
		// Reject uniform gray/placeholder frames (source ready but no real video).
		if isBlankFrame(data) && attempt != snapshotAttempts-1 {
			lastErr = fmt.Errorf("mediamtx snapshot is blank/grey (no real video)")
			continue
		}
		return data, "image/jpeg", nil
	}
	return nil, "", lastErr
}

// ffmpegFrame runs ffmpeg to read one frame from an RTSP source and returns the
// JPEG bytes written to stdout.
func (c *Client) ffmpegFrame(ctx context.Context, src string) ([]byte, error) {
	runCtx, cancel := context.WithTimeout(ctx, ffmpegTimeout)
	defer cancel()

	args := []string{
		"-hide_banner", "-loglevel", "error",
		"-analyzeduration", "2000000", "-probesize", "32M",
		"-rtsp_transport", "tcp",
		"-i", src,
		// Output seek (AFTER -i) re-decodes from the start of the
		// stream, so the HEVC VPS/SPS/PPS at the IDR are seen
		// before we jump to ~1s. An input seek (-ss before -i)
		// skips straight to the middle of the GOP and fails on
		// "VPS 0 does not exist" for H265 sources.
		"-ss", "1",
		"-frames:v", "1",
		"-q:v", "2",
		"-an",
		"-f", "image2",
		"-c:v", "mjpeg",
		"pipe:1",
	}
	cmd := exec.CommandContext(runCtx, "ffmpeg", args...)
	var out, stderr bytes.Buffer
	cmd.Stdout = &out
	cmd.Stderr = &stderr
	if err := cmd.Run(); err != nil {
		msg := bytes.TrimSpace(stderr.Bytes())
		// ffmpeg may emit decode warnings (e.g. "Could not find ref with
		// POC ..." / missing reference frames) for H.264/H.265 streams even
		// when a valid frame was still written to stdout. Treat such
		// non-fatal warnings as success as long as we got a real frame.
		if out.Len() >= minSnapshotBytes && !isFatalFFmpegError(msg) {
			log.Printf("[mediamtx] ffmpeg snapshot %q warning (frame still captured): %s", src, msg)
			return out.Bytes(), nil
		}
		log.Printf("[mediamtx] ffmpeg snapshot %q failed: %v: %s", src, err, msg)
		return nil, fmt.Errorf("ffmpeg snapshot failed (stream may not be live): %s", msg)
	}
	return out.Bytes(), nil
}

// isFatalFFmpegError reports whether an ffmpeg stderr message is fatal (as
// opposed to a recoverable decode warning). Decode warnings like "Could not
// find ref with POC" or "Missing reference" still yield a usable frame, so
// callers should not abort the snapshot on them.
func isFatalFFmpegError(msg []byte) bool {
	s := string(msg)
	if s == "" {
		return true
	}
	nonFatal := []string{
		"Could not find ref with POC",
		"Missing reference picture",
		"error while decoding MB",
		"concealing",
		"number of reference frames",
		"decode_slice_header error",
	}
	for _, nf := range nonFatal {
		if strings.Contains(s, nf) {
			return false
		}
	}
	// Hard failures (no input, cannot open, timeout, no frames produced).
	fatal := []string{
		"Invalid data found",
		"Cannot open",
		"No such file",
		"Connection refused",
		"Immediate exit requested",
		"Operation timed out",
	}
	for _, f := range fatal {
		if strings.Contains(s, f) {
			return true
		}
	}
	// Default: treat any other error as fatal to be safe.
	return true
}

// isBlankFrame reports whether the JPEG is effectively a uniform gray/color
// placeholder (e.g. MediaMTX serving a no-signal frame). It samples the image
// at a coarse grid and checks per-channel variance plus unique-color count.
func isBlankFrame(data []byte) bool {
	img, err := jpeg.Decode(bytes.NewReader(data))
	if err != nil {
		// Cannot decode — treat as blank to avoid storing garbage.
		return true
	}
	b := img.Bounds()
	const step = 16
	var sum, sumSq [3]float64
	var n int
	seen := map[[3]uint8]struct{}{}
	for y := b.Min.Y; y < b.Max.Y; y += step {
		for x := b.Min.X; x < b.Max.X; x += step {
			r, g, bl, _ := img.At(x, y).RGBA()
			pr := uint8(r >> 8)
			pg := uint8(g >> 8)
			pb := uint8(bl >> 8)
			sum[0] += float64(pr)
			sum[1] += float64(pg)
			sum[2] += float64(pb)
			sumSq[0] += float64(pr) * float64(pr)
			sumSq[1] += float64(pg) * float64(pg)
			sumSq[2] += float64(pb) * float64(pb)
			n++
			seen[[3]uint8{pr, pg, pb}] = struct{}{}
		}
	}
	if n == 0 {
		return true
	}
	var variance float64
	for c := 0; c < 3; c++ {
		mean := sum[c] / float64(n)
		variance += sumSq[c]/float64(n) - mean*mean
	}
	stddev := math.Sqrt(variance / 3)
	return stddev < 12.0 || len(seen) < 60
}
