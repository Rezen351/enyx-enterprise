package tsdb

import (
	"context"
	"errors"
	"log"
	"strings"
	"time"

	"github.com/almuzky/iot/services/analytics/internal/model"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

// Store reads/writes aggregated telemetry into the Analytics TimescaleDB.
type Store struct {
	pool *pgxpool.Pool
}

// New connects to TimescaleDB using a libpq DSN.
func New(dsn string) (*Store, error) {
	pool, err := pgxpool.New(context.Background(), dsn)
	if err != nil {
		return nil, err
	}
	return &Store{pool: pool}, nil
}

// Close releases the connection pool.
func (s *Store) Close() { s.pool.Close() }

// UpsertRollup writes one batch row into metrics_rollup. The time bucket is
// aligned to the minute using the batch's last_ts, and the write is idempotent
// (ON CONFLICT) so redelivered NATS batches do not duplicate data.
func (s *Store) UpsertRollup(ctx context.Context, row model.BatchRow) error {
	// Align the rollup timestamp to the start of the batch minute (UTC).
	now := time.Now().UTC()
	bucket := now.Truncate(time.Minute)
	if row.LastTS != 0 {
		bucket = time.UnixMilli(row.LastTS).UTC().Truncate(time.Minute)
		// Clamp future-skewed device clocks so a fast node clock cannot push
		// the rollup outside the dashboard's "now" query window (which would
		// hide recent telemetry in short timeframes like 1 HOUR).
		if bucket.After(now.Add(5 * time.Minute)) {
			bucket = now.Truncate(time.Minute)
		}
	}
	var moduleID *string
	if row.ModuleID != "" {
		m := row.ModuleID
		moduleID = &m
	}

	_, err := s.pool.Exec(ctx,
		`INSERT INTO metrics_rollup
		   (time, node_id, module_id, metric, count, sum, min, max, avg, last, first_ts, last_ts)
		 VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
		 ON CONFLICT (time, node_id, metric) DO UPDATE SET
		   module_id = EXCLUDED.module_id,
		   count     = EXCLUDED.count,
		   sum       = EXCLUDED.sum,
		   min       = EXCLUDED.min,
		   max       = EXCLUDED.max,
		   avg       = EXCLUDED.avg,
		   last      = EXCLUDED.last,
		   first_ts  = EXCLUDED.first_ts,
		   last_ts   = EXCLUDED.last_ts`,
		bucket, row.NodeID, moduleID, row.Metric, row.Count,
		row.Sum, row.Min, row.Max, row.Avg, row.Last, row.FirstTS, row.LastTS,
	)
	if err != nil {
		log.Printf("[tsdb] upsert rollup failed node=%s metric=%s: %v", row.NodeID, row.Metric, err)
	}
	return err
}

// sourceForDuration picks the materialized view (or raw hypertable) that best
// matches the requested resolution window to keep payloads small. The chosen
// source always carries count/sum/min/max/last so the query can derive a
// representative `last` plus a min–max envelope for analog metrics.
func sourceForDuration(d time.Duration) string {
	switch {
	case d <= time.Hour:
		return "metrics_rollup"
	case d <= 24*time.Hour:
		return "metrics_hourly"
	default:
		return "metrics_daily"
	}
}

// QuerySeriesMulti returns aggregated time-series for a set of nodes and metrics
// over a window, in one round-trip. Result is keyed series[node_id][metric].
// If a (node, metric) has no data in the requested window, the window is
// progressively widened (x6, x24, x7d, x30d) so the dashboard always renders
// the most recent available telemetry instead of a blank chart.
func (s *Store) QuerySeriesMulti(ctx context.Context, nodeIDs, metrics []string, from, to time.Time, interval string, discreteSet map[string]bool) (map[string]map[string][]model.SeriesPoint, error) {
	out := make(map[string]map[string][]model.SeriesPoint, len(nodeIDs))
	base := parseInterval(interval)
	if base <= 0 {
		base = time.Hour
	}
	for _, n := range nodeIDs {
		perNode := make(map[string][]model.SeriesPoint, len(metrics))
		for _, m := range metrics {
			discrete := discreteSet[m]
			pts, err := s.queryRange(ctx, n, m, from, to, base, discrete)
			if err != nil {
				return nil, err
			}
			if len(pts) == 0 {
				for _, mult := range []time.Duration{6, 24, 24 * 7, 24 * 30} {
					wFrom := to.Add(-base * mult)
					wPts, wErr := s.queryRange(ctx, n, m, wFrom, to, base*mult, discrete)
					if wErr != nil {
						return nil, wErr
					}
					if len(wPts) > 0 {
						pts = wPts
						break
					}
				}
			}
			// Final fallback: even if no data falls inside any widened window
			// (the node went inactive long ago), return the most recent available
			// buckets so the dashboard always renders the last known telemetry
			// instead of a blank chart — inactive nodes must keep showing their
			// last data, not disappear.
			if len(pts) == 0 {
				if latest, lErr := s.queryLatest(ctx, n, m, discrete, 120); lErr == nil {
					pts = latest
				}
			}
			perNode[m] = pts
		}
		out[n] = perNode
	}
	return out, nil
}

// queryRange executes the series query for a fixed [from,to] window using the
// given effective duration to pick the source view / bucket size.
func (s *Store) queryRange(ctx context.Context, nodeID, metric string, from, to time.Time, d time.Duration, discrete bool) ([]model.SeriesPoint, error) {
	if discrete {
		step := discreteStep(d)
		q := `SELECT time_bucket(CAST($5 AS interval), time) AS t, last(last, time) AS v
		      FROM metrics_rollup
		      WHERE node_id = $1 AND metric = $2 AND time BETWEEN $3 AND $4
		      GROUP BY t
		      ORDER BY t`
		rows, err := s.pool.Query(ctx, q, nodeID, metric, from, to, step)
		if err != nil {
			return nil, err
		}
		defer rows.Close()
		return scanSeries(rows)
	}

	table := sourceForDuration(d)
	timeCol := "time"
	if table != "metrics_rollup" {
		timeCol = "bucket"
	}

	// V carries `last` (keeps digital-state detection stable and matches the
	// legacy single-value client), while avg/min/max are derived so the
	// dashboard can draw a min–max envelope and never lose the bucket's range.
	// avg is recomputed as sum/NULLIF(count,0) because the hourly/daily
	// continuous aggregates do not store avg.
	q := `SELECT ` + timeCol + `, last, COALESCE(sum / NULLIF(count, 0), 0), COALESCE(min, 0), COALESCE(max, 0)
	      FROM ` + table + `
	      WHERE node_id = $1 AND metric = $2 AND ` + timeCol + ` BETWEEN $3 AND $4
	      ORDER BY ` + timeCol
	rows, err := s.pool.Query(ctx, q, nodeID, metric, from, to)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	return scanSeriesRange(rows)
}

// queryLatest returns the most recent `limit` buckets for a node/metric
// regardless of how old they are. It is the last-resort fallback used by
// QuerySeriesMulti so an inactive node (no data in any widened window) still
// shows its last known telemetry instead of a blank chart.
func (s *Store) queryLatest(ctx context.Context, nodeID, metric string, discrete bool, limit int) ([]model.SeriesPoint, error) {
	if limit <= 0 {
		limit = 120
	}
	if discrete {
		q := `SELECT t, v FROM (
		          SELECT time_bucket('1 minute', time) AS t, last(last, time) AS v, time
		          FROM metrics_rollup
		          WHERE node_id = $1 AND metric = $2
		          ORDER BY time DESC
		          LIMIT $3
		      ) sub
		      GROUP BY t, v
		      ORDER BY t`
		rows, err := s.pool.Query(ctx, q, nodeID, metric, limit)
		if err != nil {
			return nil, err
		}
		defer rows.Close()
		return scanSeries(rows)
	}

	q := `SELECT ` + "time" + `, last, COALESCE(sum / NULLIF(count, 0), 0), COALESCE(min, 0), COALESCE(max, 0)
	      FROM (
	        SELECT * FROM metrics_rollup
	        WHERE node_id = $1 AND metric = $2
	        ORDER BY time DESC
	        LIMIT $3
	      ) sub
	      ORDER BY time`
	rows, err := s.pool.Query(ctx, q, nodeID, metric, limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	return scanSeriesRange(rows)
}

// scanSeries reads (time, value) rows into SeriesPoints.
func scanSeries(rows pgx.Rows) ([]model.SeriesPoint, error) {
	pts := make([]model.SeriesPoint, 0)
	for rows.Next() {
		var t time.Time
		var v float64
		if err := rows.Scan(&t, &v); err != nil {
			return nil, err
		}
		pts = append(pts, model.SeriesPoint{T: t.UTC().Format(time.RFC3339), V: v})
	}
	if err := rows.Err(); err != nil {
		return nil, err
	}
	return pts, nil
}

// scanSeriesRange reads (time, last, avg, min, max) rows into SeriesPoints,
// carrying the bucket statistics so the dashboard can draw a min–max envelope
// while keeping `last` as V for digital-state detection.
func scanSeriesRange(rows pgx.Rows) ([]model.SeriesPoint, error) {
	pts := make([]model.SeriesPoint, 0)
	for rows.Next() {
		var t time.Time
		var v, a, mn, mx float64
		if err := rows.Scan(&t, &v, &a, &mn, &mx); err != nil {
			return nil, err
		}
		pts = append(pts, model.SeriesPoint{
			T:   t.UTC().Format(time.RFC3339),
			V:   v,
			Min: &mn,
			Max: &mx,
			Avg: &a,
		})
	}
	if err := rows.Err(); err != nil {
		return nil, err
	}
	return pts, nil
}

// discreteStep picks a transition-preserving bucket for digital metrics so they
// stay at raw 1-minute resolution within a day (up to ~1440 points) and only
// coarsen for multi-day windows. The bucket always carries `last`, so values
// stay 0/1 and on/off transitions remain visible instead of being averaged.
func discreteStep(d time.Duration) string {
	switch {
	case d <= 24*time.Hour:
		return "1 minute"
	case d <= 7*24*time.Hour:
		return "15 minutes"
	case d <= 30*24*time.Hour:
		return "1 hour"
	default:
		return "3 hours"
	}
}

// QuerySummary returns the statistical summary for a node/metric over a window.
func (s *Store) QuerySummary(ctx context.Context, nodeID, metric string, from, to time.Time) (*model.SummaryResponse, error) {
	var countSum, firstTS, lastTS int64
	var sumSum, mn, mx, lastV float64
	err := s.pool.QueryRow(ctx,
		`SELECT COALESCE(sum(count),0), COALESCE(sum(sum),0),
		        COALESCE(min(min),0), COALESCE(max(max),0),
		        COALESCE(last(last,time),0),
		        COALESCE(min(first_ts),0), COALESCE(max(last_ts),0)
		 FROM metrics_rollup
		 WHERE node_id = $1 AND metric = $2 AND time BETWEEN $3 AND $4`,
		nodeID, metric, from, to,
	).Scan(&countSum, &sumSum, &mn, &mx, &lastV, &firstTS, &lastTS)
	if err != nil {
		// No telemetry for this node/metric in the window is not an error:
		// return an empty summary instead of a 500 so the dashboard chart
		// renders cleanly (the chart series endpoint already returns []).
		if errors.Is(err, pgx.ErrNoRows) {
			return &model.SummaryResponse{
				NodeID: nodeID,
				Metric: metric,
			}, nil
		}
		return nil, err
	}
	avg := 0.0
	if countSum > 0 {
		avg = float64(sumSum) / float64(countSum)
	}
	return &model.SummaryResponse{
		NodeID:  nodeID,
		Metric:  metric,
		Count:   int(countSum),
		Min:     float64(mn),
		Max:     float64(mx),
		Avg:     avg,
		Last:    float64(lastV),
		FirstTS: firstTS,
		LastTS:  lastTS,
	}, nil
}

// resolutionSource maps a requested export resolution to its source table and
// time column (raw 1-min rollup, hourly, or daily continuous aggregate).
func resolutionSource(resolution string) (table, timeCol string) {
	switch strings.ToLower(resolution) {
	case "raw":
		return "metrics_rollup", "time"
	case "hour":
		return "metrics_hourly", "bucket"
	default: // "day" and anything unrecognized falls back to daily history
		return "metrics_daily", "bucket"
	}
}

// ExportSeries returns the full aggregated rows (count/sum/min/max/avg/last)
// for a node/metric over a window at the requested resolution. It is intended
// for bulk research export (CSV): avg is recomputed as sum/NULLIF(count,0) so
// it is consistent across the raw hypertable and the continuous aggregates
// (which do not store avg).
func (s *Store) ExportSeries(ctx context.Context, nodeID, metric string, from, to time.Time, resolution string) ([]model.ExportRow, error) {
	table, timeCol := resolutionSource(resolution)
	q := `SELECT ` + timeCol + `, node_id, metric, count, sum, min, max,
	             (sum / NULLIF(count, 0)), last
	      FROM ` + table + `
	      WHERE node_id = $1 AND metric = $2 AND ` + timeCol + ` BETWEEN $3 AND $4
	      ORDER BY ` + timeCol
	rows, err := s.pool.Query(ctx, q, nodeID, metric, from, to)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	out := make([]model.ExportRow, 0)
	for rows.Next() {
		var r model.ExportRow
		var cnt int64
		var sm, mn, mx, av, ls float64
		if err := rows.Scan(&r.Bucket, &r.NodeID, &r.Metric, &cnt, &sm, &mn, &mx, &av, &ls); err != nil {
			return nil, err
		}
		r.Count = int(cnt)
		r.Sum = sm
		r.Min = mn
		r.Max = mx
		r.Avg = av
		r.Last = ls
		out = append(out, r)
	}
	if err := rows.Err(); err != nil {
		return nil, err
	}
	return out, nil
}

// ListNodes returns every node that has telemetry and the metrics available.
func (s *Store) ListNodes(ctx context.Context) ([]model.NodeMetric, error) {
	rows, err := s.pool.Query(ctx,
		`SELECT node_id, COALESCE(module_id,''),
		        string_agg(DISTINCT metric, ',' ORDER BY metric)
		 FROM metrics_rollup
		 GROUP BY node_id, module_id
		 ORDER BY node_id`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	out := make([]model.NodeMetric, 0)
	for rows.Next() {
		var nodeID, moduleID, metricsCSV string
		if err := rows.Scan(&nodeID, &moduleID, &metricsCSV); err != nil {
			return nil, err
		}
		var metrics []string
		if metricsCSV != "" {
			for _, m := range strings.Split(metricsCSV, ",") {
				if m != "" {
					metrics = append(metrics, m)
				}
			}
		}
		out = append(out, model.NodeMetric{NodeID: nodeID, ModuleID: moduleID, Metrics: metrics})
	}
	if err := rows.Err(); err != nil {
		return nil, err
	}
	return out, nil
}

// WindowForInterval returns the duration covered by an interval label
// (used by the API to default the query window when from/to are omitted).
func WindowForInterval(interval string) time.Duration { return parseInterval(interval) }
func parseInterval(interval string) time.Duration {
	switch strings.ToLower(interval) {
	case "15m", "30m":
		return 30 * time.Minute
	case "1h":
		return time.Hour
	case "6h":
		return 6 * time.Hour
	case "12h":
		return 12 * time.Hour
	case "24h", "1d":
		return 24 * time.Hour
	case "7d":
		return 7 * 24 * time.Hour
	case "30d":
		return 30 * 24 * time.Hour
	case "90d":
		return 90 * 24 * time.Hour
	default:
		if d, err := time.ParseDuration(interval); err == nil {
			return d
		}
		return time.Hour
	}
}
