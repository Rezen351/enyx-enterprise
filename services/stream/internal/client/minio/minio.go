package minio

import (
	"bytes"
	"context"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"strconv"
	"strings"
	"time"

	"github.com/minio/minio-go/v7"
	"github.com/minio/minio-go/v7/pkg/credentials"
)

// Client wraps the MinIO Go SDK for storing snapshots & recordings in the
// stream bucket. Objects are served to the dashboard through a same-origin
// proxy (Vite /storage → minio:9000) with a public-read policy on the
// snapshots/recordings prefixes, so no presigned URLs are required.
type Client struct {
	client *minio.Client
	bucket string
}

// New connects to MinIO and ensures the bucket exists. MinIO may not be ready
// when this service starts (see the connection-refused race in the logs), so we
// retry the bucket check/creation for up to ~90s — mirroring the DB startup
// retry — instead of giving up and leaving the client nil (which would make
// every snapshot/recording call fail with "client not configured").
func New(endpoint, accessKey, secretKey string, useSSL bool, bucket string) (*Client, error) {
	c, err := minio.New(endpoint, &minio.Options{
		Creds:  credentials.NewStaticV4(accessKey, secretKey, ""),
		Secure: useSSL,
	})
	if err != nil {
		return nil, fmt.Errorf("minio init: %w", err)
	}
	cl := &Client{client: c, bucket: bucket}

	var lastErr error
	for i := 0; i < 30; i++ {
		if err := cl.prepareBucket(bucket); err != nil {
			lastErr = err
			log.Printf("[minio] bucket %q not ready yet (%d/30): %v", bucket, i+1, err)
			time.Sleep(3 * time.Second)
			continue
		}
		lastErr = nil
		break
	}
	if lastErr != nil {
		return nil, fmt.Errorf("minio bucket prepare: %w", lastErr)
	}

	// NOTE: the bucket is intentionally NOT made public-read. Objects are
	// served to authenticated clients only, via the Stream Service's
	// /storage proxy (which uses these scoped service credentials). A
	// public-read policy would violate the "scoped credential, not public
	// bucket" requirement.

	return cl, nil
}

// prepareBucket verifies (and creates if missing) the bucket.
func (c *Client) prepareBucket(bucket string) error {
	exists, err := c.client.BucketExists(context.Background(), bucket)
	if err != nil {
		return fmt.Errorf("minio bucket check: %w", err)
	}
	if !exists {
		if err := c.client.MakeBucket(context.Background(), bucket, minio.MakeBucketOptions{}); err != nil {
			return fmt.Errorf("minio make bucket: %w", err)
		}
	}
	return nil
}

// ServeObject streams an object from the bucket to the given ResponseWriter
// using the service's scoped MinIO credentials. This is the only way the
// dashboard obtains stored snapshots/recordings: the bucket stays private
// (no public-read policy) and every read is authenticated at the Stream
// Service layer (JWT) before MinIO is touched.
func (c *Client) ServeObject(w io.Writer, bucket, key string) error {
	if bucket == "" {
		bucket = c.bucket
	}
	obj, err := c.client.GetObject(context.Background(), bucket, key, minio.GetObjectOptions{})
	if err != nil {
		return fmt.Errorf("minio get: %w", err)
	}
	defer obj.Close()
	stat, err := obj.Stat()
	if err != nil {
		return fmt.Errorf("minio stat: %w", err)
	}
	if rw, ok := w.(interface {
		Header() http.Header
	}); ok {
		rw.Header().Set("Content-Type", stat.ContentType)
		rw.Header().Set("Content-Length", strconv.FormatInt(stat.Size, 10))
		rw.Header().Set("Cache-Control", "private, max-age=300")
	}
	if _, err := io.Copy(w, obj); err != nil {
		return fmt.Errorf("minio copy: %w", err)
	}
	return nil
}

// ValidObjectPath reports whether bucket+key are safe to serve — no path
// traversal (`..`), no absolute paths, and the bucket must be one we are
// allowed to proxy (prevents reaching arbitrary MinIO buckets/objects).
func ValidObjectPath(bucket, key string) bool {
	if key == "" {
		return false
	}
	if strings.Contains(key, "..") || strings.HasPrefix(key, "/") || strings.Contains(key, "\\") {
		return false
	}
	switch bucket {
	case "stream", "mlbucket":
		return true
	}
	return false
}

// UploadFile streams a local file into the bucket (used for recordings, which
// can be large and must not be buffered entirely in memory). Returns a
// same-origin /storage URL the dashboard can render.
func (c *Client) UploadFile(key, contentType, path string) (string, error) {
	f, err := os.Open(path)
	if err != nil {
		return "", fmt.Errorf("minio open file: %w", err)
	}
	defer f.Close()
	fi, err := f.Stat()
	if err != nil {
		return "", fmt.Errorf("minio stat file: %w", err)
	}
	if err := c.EnsureBucket(c.bucket); err != nil {
		return "", err
	}
	_, err = c.client.PutObject(context.Background(), c.bucket, key, f, fi.Size(),
		minio.PutObjectOptions{ContentType: contentType})
	if err != nil {
		return "", fmt.Errorf("minio put: %w", err)
	}
	return "/storage/" + c.bucket + "/" + key, nil
}

// UploadObject stores data under key (e.g. "snapshots/cam-01/<uuid>.jpg").
// proxyBase is the dashboard-relative base used to build the public URL
// (e.g. "/storage"). Returns the same-origin URL the dashboard can render.
func (c *Client) UploadObject(key, contentType string, data []byte) (string, error) {
	return c.UploadObjectToBucket(c.bucket, key, contentType, data)
}

// UploadObjectToBucket stores data in an arbitrary bucket (e.g. the shared
// mlbucket bucket where both the cron capture job and the live "Capture
// Detect AI" button land their results). Returns a same-origin /storage URL.
func (c *Client) UploadObjectToBucket(bucket, key, contentType string, data []byte) (string, error) {
	return c.UploadObjectToBucketWithMetadata(bucket, key, contentType, data, nil)
}

// UploadObjectToBucketWithMetadata is like UploadObjectToBucket but also
// attaches user-defined metadata (e.g. vision measurements) to the object.
func (c *Client) UploadObjectToBucketWithMetadata(bucket, key, contentType string, data []byte, metadata map[string]string) (string, error) {
	if bucket == "" {
		bucket = c.bucket
	}
	if err := c.EnsureBucket(bucket); err != nil {
		return "", err
	}
	_, err := c.client.PutObject(context.Background(), bucket, key, bytes.NewReader(data), int64(len(data)),
		minio.PutObjectOptions{
			ContentType:  contentType,
			UserMetadata: metadata,
		})
	if err != nil {
		return "", fmt.Errorf("minio put: %w", err)
	}
	return "/storage/" + bucket + "/" + key, nil
}

// EnsureBucket creates the bucket if it does not exist (best-effort).
func (c *Client) EnsureBucket(bucket string) error {
	exists, err := c.client.BucketExists(context.Background(), bucket)
	if err != nil {
		return fmt.Errorf("minio bucket check: %w", err)
	}
	if exists {
		return nil
	}
	if err := c.client.MakeBucket(context.Background(), bucket, minio.MakeBucketOptions{}); err != nil {
		return fmt.Errorf("minio make bucket: %w", err)
	}
	return nil
}

// ReadObject fetches an object (used to mirror the ML service's annotated
// image from the ml bucket into the shared mlbucket bucket).
func (c *Client) ReadObject(bucket, key string) ([]byte, error) {
	obj, err := c.client.GetObject(context.Background(), bucket, key, minio.GetObjectOptions{})
	if err != nil {
		return nil, fmt.Errorf("minio get: %w", err)
	}
	defer obj.Close()
	data, err := io.ReadAll(obj)
	if err != nil {
		return nil, fmt.Errorf("minio read: %w", err)
	}
	return data, nil
}

// StatObject returns object metadata (including user-defined metadata) for
// the given bucket/key. Used to preserve metadata when mirroring annotated
// images from the ML bucket.
func (c *Client) StatObject(bucket, key string) (map[string]string, error) {
	info, err := c.client.StatObject(context.Background(), bucket, key, minio.StatObjectOptions{})
	if err != nil {
		return nil, fmt.Errorf("minio stat: %w", err)
	}
	meta := make(map[string]string, len(info.Metadata))
	for k, v := range info.Metadata {
		if len(v) > 0 {
			meta[k] = v[0]
		}
	}
	return meta, nil
}

// DeleteObject removes an object (best-effort; ignores not-found).
func (c *Client) DeleteObject(key string) error {
	err := c.client.RemoveObject(context.Background(), c.bucket, key, minio.RemoveObjectOptions{})
	if err != nil {
		// MinIO returns an error for missing objects; treat as success.
		log.Printf("[minio] remove %s: %v (ignored)", key, err)
	}
	return nil
}

// Reader opens an object for direct streaming (used if needed).
func (c *Client) Reader(key string) (io.Reader, error) {
	obj, err := c.client.GetObject(context.Background(), c.bucket, key, minio.GetObjectOptions{})
	if err != nil {
		return nil, err
	}
	return obj, nil
}
