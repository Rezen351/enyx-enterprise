package module

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"
)

// Tag is the telemetry tag-mapping entry managed by the Module Service. It is
// the single source of truth for which telemetry keys (sensors AND actuator
// outputs) are meaningful on a node — the same schema the Sensor/Analytics
// pages use. The Control Service reuses it so output control follows the exact
// same "attach a tag" flow as sensor monitoring.
type Tag struct {
	ID          string `json:"id"`
	NodeID      string `json:"node_id"`
	SourceKey   string `json:"source_key"` // telemetry dot-path, e.g. outputs.pump
	TagName     string `json:"tag_name"`   // friendly DB tag, e.g. mist_pump
	DisplayName string `json:"display_name"`
	Unit        string `json:"unit"`
	DataType    string `json:"data_type"` // float | int | bool
	Enabled     bool   `json:"enabled"`
}

// Client talks to the Module Service tags endpoint to discover controllable
// outputs (actuator tags) for a node.
type Client struct {
	baseURL string
	token   string
	http    *http.Client
}

// NewClient builds a Module Service client. token may be empty (dev mode where
// the Module Service does not enforce auth); callers pass the incoming request
// bearer token so the same identity is reused.
func NewClient(baseURL, token string) *Client {
	return &Client{
		baseURL: baseURL,
		token:   token,
		http:    &http.Client{Timeout: 10 * time.Second},
	}
}

func (c *Client) ListTags(nodeID string) ([]Tag, error) {
	if c.baseURL == "" {
		return nil, fmt.Errorf("module service url not configured")
	}
	url := fmt.Sprintf("%s/nodes/%s/tags", c.baseURL, nodeID)
	req, err := http.NewRequest(http.MethodGet, url, nil)
	if err != nil {
		return nil, err
	}
	if c.token != "" {
		req.Header.Set("Authorization", "Bearer "+c.token)
	}
	resp, err := c.http.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	body, _ := io.ReadAll(resp.Body)
	if resp.StatusCode >= 400 {
		return nil, fmt.Errorf("module service returned %d: %s", resp.StatusCode, string(body))
	}
	var out struct {
		Tags []Tag `json:"tags"`
	}
	// The Module Service returns the standard envelope { success, data }.
	// Unwrap the `data` wrapper (and tolerate a bare { tags } shape too).
	if err := unmarshalTags(body, &out); err != nil {
		return nil, err
	}
	return out.Tags, nil
}

// ListActuatorTags returns the actuator (kind="actuator") tags for a node — the
// controllable outputs the user explicitly mapped via the dashboard.
func (c *Client) ListActuatorTags(nodeID string) ([]Tag, error) {
	if c.baseURL == "" {
		return nil, fmt.Errorf("module service url not configured")
	}
	url := fmt.Sprintf("%s/nodes/%s/actuators", c.baseURL, nodeID)
	req, err := http.NewRequest(http.MethodGet, url, nil)
	if err != nil {
		return nil, err
	}
	if c.token != "" {
		req.Header.Set("Authorization", "Bearer "+c.token)
	}
	resp, err := c.http.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	body, _ := io.ReadAll(resp.Body)
	if resp.StatusCode >= 400 {
		return nil, fmt.Errorf("module service returned %d: %s", resp.StatusCode, string(body))
	}
	var out struct {
		Tags []Tag `json:"tags"`
	}
	if err := unmarshalTags(body, &out); err != nil {
		return nil, err
	}
	return out.Tags, nil
}

// unmarshalTags decodes a tag list, accepting both the standard envelope
// { success, data: { tags } } and a bare { tags } payload.
func unmarshalTags(body []byte, out *struct {
	Tags []Tag `json:"tags"`
}) error {
	var env struct {
		Data struct {
			Tags []Tag `json:"tags"`
		} `json:"data"`
	}
	if err := json.Unmarshal(body, &env); err == nil && env.Data.Tags != nil {
		out.Tags = env.Data.Tags
		return nil
	}
	// Fall back to bare { tags } shape.
	return json.Unmarshal(body, out)
}

// IsNodePaired reports whether a node_id is registered AND paired to a module
// in the Module Service. Used by the Control Service to reject control
// commands/schedules targeted at unpaired or unregistered nodes.
func (c *Client) IsNodePaired(ctx context.Context, nodeID string) (bool, error) {
	if c.baseURL == "" {
		return false, fmt.Errorf("module service url not configured")
	}
	url := fmt.Sprintf("%s/nodes/%s", c.baseURL, nodeID)
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
	if err != nil {
		return false, err
	}
	if c.token != "" {
		req.Header.Set("Authorization", "Bearer "+c.token)
	}
	resp, err := c.http.Do(req)
	if err != nil {
		return false, err
	}
	defer resp.Body.Close()

	if resp.StatusCode == http.StatusNotFound {
		return false, nil
	}
	if resp.StatusCode >= 400 {
		body, _ := io.ReadAll(resp.Body)
		return false, fmt.Errorf("module service returned %d: %s", resp.StatusCode, string(body))
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return false, err
	}

	var env struct {
		Data struct {
			Paired   bool    `json:"paired"`
			ModuleID *string `json:"module_id"`
		} `json:"data"`
		Paired   bool    `json:"paired"`
		ModuleID *string `json:"module_id"`
	}
	if err := json.Unmarshal(body, &env); err != nil {
		return false, err
	}

	isPaired := env.Data.Paired || env.Paired
	modID := env.Data.ModuleID
	if modID == nil {
		modID = env.ModuleID
	}

	if !isPaired || modID == nil || *modID == "" {
		return false, nil
	}

	return true, nil
}

// IsNodeRegistered reports whether a node_id is known to the Module Service.
// Used by the Control Service to reject commands/schedules targeted at
// unregistered nodes (prevents node-id spoofing).
func (c *Client) IsNodeRegistered(ctx context.Context, nodeID string) (bool, error) {
	return c.IsNodePaired(ctx, nodeID)
}
