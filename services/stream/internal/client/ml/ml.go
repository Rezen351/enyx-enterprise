package ml

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"mime/multipart"
	"net/http"
	"strings"
	"time"

	"github.com/golang-jwt/jwt/v5"
)

// Client calls the ML / Vision inference API to run object detection on a
// captured frame. It mints a short-lived service JWT using the shared JWT
// secret (same secret the Auth Service issues tokens with) so it can satisfy
// the ML Service's require_write RBAC without contacting Auth at runtime.
type Client struct {
	baseURL   string
	modelID   string
	jwtSecret string
	httpCl    *http.Client
}

// New builds an ML client. baseURL is the ML Service root (e.g. http://ml:8080),
// modelID selects the vision model in the registry, and jwtSecret is the shared
// JWT secret used to sign the service token.
func New(baseURL, modelID, jwtSecret string) *Client {
	return &Client{
		baseURL:   strings.TrimRight(baseURL, "/"),
		modelID:   modelID,
		jwtSecret: jwtSecret,
		httpCl:    &http.Client{Timeout: 60 * time.Second},
	}
}

// BBox is a pixel-space bounding box returned by the model.
type BBox struct {
	X1 int `json:"x1"`
	Y1 int `json:"y1"`
	X2 int `json:"x2"`
	Y2 int `json:"y2"`
}

// Detection is a single detected object.
type Detection struct {
	ClassID    int     `json:"class_id"`
	ClassName  string  `json:"class_name"`
	Confidence float64 `json:"confidence"`
	BBox       BBox    `json:"bbox"`
}

// DetectResult mirrors the relevant subset of the ML /detect response.
type DetectResult struct {
	DetectionUID  string      `json:"detection_uid"`
	ModelID       string      `json:"model_id"`
	ModelName     string      `json:"model_name"`
	NumDetections int         `json:"num_detections"`
	Classes       []string    `json:"classes"`
	Detections    []Detection `json:"detections"`
	ConfidenceAvg float64     `json:"confidence_avg"`
	RootLengthCM  *float64    `json:"root_length_cm"`
	TuberSizeCM   *float64    `json:"tuber_size_cm"`
	Condition     *float64    `json:"condition"`
	OriginalURL   string      `json:"original_url"`
	AnnotatedURL  string      `json:"annotated_url"`
}

// mlDetectResponse is the envelope returned by POST /ml/detect.
type mlDetectResponse struct {
	Count   int            `json:"count"`
	Results []DetectResult `json:"results"`
}

// mintToken issues a service JWT with admin/operator roles (required by the ML
// Service's write RBAC). It never leaves the process.
func (c *Client) mintToken() (string, error) {
	now := time.Now()
	claims := jwt.MapClaims{
		"uid":      "stream-svc",
		"username": "stream-svc",
		"roles":    []string{"admin", "operator"},
		"iat":      now.Unix(),
		"exp":      now.Add(15 * time.Minute).Unix(),
	}
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	return token.SignedString([]byte(c.jwtSecret))
}

// Detect runs inference on a single JPEG frame and returns the first result.
// It returns (nil, error) when the client is not configured or the request
// fails, so callers can surface a clear error instead of silently skipping.
func (c *Client) Detect(ctx context.Context, imageBytes []byte, filename string) (*DetectResult, error) {
	if c.baseURL == "" || c.jwtSecret == "" {
		return nil, fmt.Errorf("ml client not configured: baseURL=%q jwtSecret=%q", c.baseURL, c.jwtSecret)
	}
	token, err := c.mintToken()
	if err != nil {
		return nil, fmt.Errorf("ml token: %w", err)
	}

	var buf bytes.Buffer
	writer := multipart.NewWriter(&buf)
	part, err := writer.CreateFormFile("files", filename)
	if err != nil {
		return nil, fmt.Errorf("ml form: %w", err)
	}
	if _, err := part.Write(imageBytes); err != nil {
		return nil, fmt.Errorf("ml form: %w", err)
	}
	if c.modelID != "" {
		if err := writer.WriteField("model_id", c.modelID); err != nil {
			return nil, fmt.Errorf("ml form: %w", err)
		}
	}
	if err := writer.Close(); err != nil {
		return nil, fmt.Errorf("ml form: %w", err)
	}

	url := c.baseURL + "/ml/detect"
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, url, &buf)
	if err != nil {
		return nil, fmt.Errorf("ml request: %w", err)
	}
	req.Header.Set("Content-Type", writer.FormDataContentType())
	req.Header.Set("Authorization", "Bearer "+token)

	resp, err := c.httpCl.Do(req)
	if err != nil {
		return nil, fmt.Errorf("ml http: %w", err)
	}
	defer resp.Body.Close()

	data, _ := io.ReadAll(resp.Body)
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return nil, fmt.Errorf("ml detect failed (%d): %s", resp.StatusCode, strings.TrimSpace(string(data)))
	}

	// The ML Service returns the standardized wrapper
	// {"success":true,"data":{...}}. Unwrap the "data" envelope; if the
	// envelope is absent, fall back to parsing the body directly so the
	// client keeps working against older/raw responses.
	var envelope struct {
		Success bool            `json:"success"`
		Data    json.RawMessage `json:"data"`
	}
	if err := json.Unmarshal(data, &envelope); err != nil {
		return nil, fmt.Errorf("ml decode: %w", err)
	}
	if !envelope.Success {
		var errEnvelope struct {
			Error struct {
				Code    string `json:"code"`
				Message string `json:"message"`
			} `json:"error"`
		}
		if err := json.Unmarshal(data, &errEnvelope); err == nil && errEnvelope.Error.Message != "" {
			return nil, fmt.Errorf("ml error %s: %s", errEnvelope.Error.Code, errEnvelope.Error.Message)
		}
		return nil, fmt.Errorf("ml detect failed: %s", strings.TrimSpace(string(data)))
	}

	payload := envelope.Data
	if len(payload) == 0 {
		payload = data
	}

	var parsed mlDetectResponse
	if err := json.Unmarshal(payload, &parsed); err != nil {
		return nil, fmt.Errorf("ml decode: %w", err)
	}
	if len(parsed.Results) == 0 {
		return nil, nil
	}
	return &parsed.Results[0], nil
}
