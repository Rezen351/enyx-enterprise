package model

import "time"

// Stream is the persisted stream metadata (GORM single source of truth).
type Stream struct {
	ID          string    `gorm:"column:id;type:char(36);primaryKey"`
	Name        string    `gorm:"column:name;type:varchar(64);uniqueIndex;not null"` // MediaMTX path name
	DeviceLabel string    `gorm:"column:device_label;type:varchar(128)"`
	Location    string    `gorm:"column:location;type:varchar(128)"`
	SourceRTSP  string    `gorm:"column:source_rtsp;type:varchar(512);not null"` // includes CCTV credentials
	NodeID      string    `gorm:"column:node_id;type:char(36);index"`            // owning node (CCTV device)
	ModuleID    string    `gorm:"column:module_id;type:char(36);index"`          // owning module (denormalized for filtering)
	Enabled     bool      `gorm:"column:enabled;not null;default:true"`
	CreatedAt   time.Time `gorm:"column:created_at;autoCreateTime"`
	UpdatedAt   time.Time `gorm:"column:updated_at;autoUpdateTime"`
}

func (Stream) TableName() string { return "streams" }

// Snapshot is a captured frame (or recording cover) stored in MinIO.
// kind is "snapshot" (single frame), "recording" (recording session cover), or
// "detection" (a snapshot that was also run through the AI vision model; the
// URL points at the original frame and the detection metadata is stored inline
// so the dashboard can overlay bounding boxes without depending on the ML
// bucket's public URL).
type Snapshot struct {
	ID          string `gorm:"column:id;type:char(36);primaryKey"`
	StreamID    string `gorm:"column:stream_id;type:char(36);index"`
	StreamName  string `gorm:"column:stream_name;type:varchar(64)"`
	ModuleID    string `gorm:"column:module_id;type:char(36);index"` // owning module (denormalized from stream)
	ObjectKey   string `gorm:"column:object_key;type:varchar(512);not null"`
	URL         string `gorm:"column:url;type:varchar(1024);not null"`
	ContentType string `gorm:"column:content_type;type:varchar(64)"`
	Size        int64  `gorm:"column:size"`
	Kind        string `gorm:"column:kind;type:varchar(16);default:snapshot"`

	// AI vision detection metadata (kind="detection" only).
	ModelID       string   `gorm:"column:model_id;type:varchar(64)"`
	ModelName     string   `gorm:"column:model_name;type:varchar(255)"`
	NumDetections int      `gorm:"column:num_detections"`
	Classes       string   `gorm:"column:classes;type:text"`          // JSON array string
	Detections    string   `gorm:"column:detections;type:mediumtext"` // JSON array string
	ConfidenceAvg float64  `gorm:"column:confidence_avg"`
	RootLengthCM  *float64 `gorm:"column:root_length_cm"` // vision measurement in cm
	TuberSizeCM   *float64 `gorm:"column:tuber_size_cm"`  // vision measurement in cm
	Condition     *float64 `gorm:"column:condition"`      // vision condition score
	Duration      float64  `gorm:"column:duration"`       // recorded clip length in seconds (kind="recording")

	CreatedAt time.Time `gorm:"column:created_at;autoCreateTime"`
}

func (Snapshot) TableName() string { return "snapshots" }

// SnapshotView is returned to the dashboard.
type SnapshotView struct {
	ID         string    `json:"id"`
	StreamID   string    `json:"stream_id"`
	StreamName string    `json:"stream_name"`
	ModuleID   string    `json:"module_id,omitempty"`
	URL        string    `json:"url"`
	Kind       string    `json:"kind"`
	Size       int64     `json:"size"`
	CreatedAt  time.Time `json:"created_at"`

	// AI vision detection metadata (present when kind="detection").
	ModelID       string   `json:"model_id,omitempty"`
	ModelName     string   `json:"model_name,omitempty"`
	NumDetections int      `json:"num_detections,omitempty"`
	Classes       string   `json:"classes,omitempty"`    // JSON array string
	Detections    string   `json:"detections,omitempty"` // JSON array string
	ConfidenceAvg float64  `json:"confidence_avg,omitempty"`
	RootLengthCM  *float64 `json:"root_length_cm,omitempty"` // vision measurement in cm
	TuberSizeCM   *float64 `json:"tuber_size_cm,omitempty"`  // vision measurement in cm
	Condition     *float64 `json:"condition,omitempty"`      // vision condition score
	Duration      float64  `json:"duration,omitempty"`       // recorded clip length in seconds
}

// ─── Request DTOs ─────────────────────────────────────────────────────────────

// CreateStreamRequest is the body for POST /streams.
// source_rtsp is optional; when empty the configured CCTV_RTSP_URL is used.
// node_id / module_id optionally bind the stream to a node (and its module) so
// the dashboard can scope Live/Gallery to a selected module.
type CreateStreamRequest struct {
	Name        string `json:"name"`
	DeviceLabel string `json:"device_label"`
	Location    string `json:"location"`
	SourceRTSP  string `json:"source_rtsp"`
	NodeID      string `json:"node_id"`
	ModuleID    string `json:"module_id"`
}

// UpdateStreamRequest is the body for PUT /streams/{id}.
// Name and SourceRTSP are optional; when provided they re-register the
// MediaMTX path (the path is keyed by name and pulls from SourceRTSP, so
// changing either requires removing the old path and adding a new one).
type UpdateStreamRequest struct {
	Name        *string `json:"name"`
	DeviceLabel *string `json:"device_label"`
	Location    *string `json:"location"`
	SourceRTSP  *string `json:"source_rtsp"`
	Enabled     *bool   `json:"enabled"`
	NodeID      *string `json:"node_id"`
	ModuleID    *string `json:"module_id"`
}

// ─── Response DTOs ────────────────────────────────────────────────────────────

// StreamView is what the dashboard receives: metadata + live status + playback URLs.
type StreamView struct {
	ID             string    `json:"id"`
	Name           string    `json:"name"`
	DeviceLabel    string    `json:"device_label"`
	Location       string    `json:"location"`
	SourceRTSP     string    `json:"source_rtsp"`
	NodeID         string    `json:"node_id,omitempty"`
	ModuleID       string    `json:"module_id,omitempty"`
	Enabled        bool      `json:"enabled"`
	Status         string    `json:"status"` // MediaMTX source state: idle|waiting|running|ready|unknown
	HlsURL         string    `json:"hls_url"`
	WebRTCURL      string    `json:"webrtc_url"` // playback (WHEP) endpoint, host-direct
	Recording      bool      `json:"recording"`
	RecordingStart int64     `json:"recording_start,omitempty"` // Unix timestamp in milliseconds
	CreatedAt      time.Time `json:"created_at"`
	UpdatedAt      time.Time `json:"updated_at"`
}
