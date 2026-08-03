#!/bin/bash
set -eo pipefail

MC="/usr/local/bin/mc"
ALIAS="m"

: "${MINIO_ACCESS_KEY:=minioadmin}"
: "${MINIO_SECRET_KEY:=minioadmin}"
: "${MINIO_STREAM_ACCESS_KEY:=stream-svc}"
: "${MINIO_STREAM_SECRET_KEY:=change-me-stream}"
: "${MINIO_ML_ACCESS_KEY:=ml-svc}"
: "${MINIO_ML_SECRET_KEY:=change-me-ml}"

echo "[init] waiting for minio:9000..."
for i in $(seq 1 60); do
  if wget -qO- http://minio:9000/minio/health/live >/dev/null 2>&1; then
    echo "[init] minio is healthy"
    break
  fi
  sleep 1
done

echo "[init] configuring mc alias..."
"$MC" alias set "$ALIAS" http://minio:9000 "${MINIO_ACCESS_KEY}" "${MINIO_SECRET_KEY}"

echo "[init] creating buckets..."
"$MC" mb -p "$ALIAS/stream" >/dev/null 2>&1 || true
"$MC" mb -p "$ALIAS/mlbucket" >/dev/null 2>&1 || true

echo "[init] setting bucket privacy..."
"$MC" anonymous set private "$ALIAS/stream" >/dev/null 2>&1 || true
"$MC" anonymous set private "$ALIAS/mlbucket" >/dev/null 2>&1 || true

echo "[init] creating policies..."
cat > /tmp/stream-svc-policy.json <<'JSON'
{"Version":"2012-10-17","Statement":[
  {"Effect":"Allow","Action":["s3:GetBucketLocation","s3:HeadBucket","s3:ListBucket"],"Resource":["arn:aws:s3:::stream","arn:aws:s3:::mlbucket"]},
  {"Effect":"Allow","Action":["s3:DeleteObject","s3:GetObject","s3:PutObject"],"Resource":["arn:aws:s3:::stream/*","arn:aws:s3:::mlbucket/*"]}
]}
JSON

cat > /tmp/ml-svc-policy.json <<'JSON'
{"Version":"2012-10-17","Statement":[
  {"Effect":"Allow","Action":["s3:GetBucketLocation","s3:HeadBucket","s3:ListBucket"],"Resource":["arn:aws:s3:::mlbucket"]},
  {"Effect":"Allow","Action":["s3:DeleteObject","s3:GetObject","s3:ListBucket","s3:PutObject"],"Resource":["arn:aws:s3:::mlbucket/*"]}
]}
JSON

"$MC" admin policy create "$ALIAS" stream-svc-policy-v2 /tmp/stream-svc-policy.json >/dev/null 2>&1 || true
"$MC" admin policy create "$ALIAS" ml-svc-policy-full /tmp/ml-svc-policy.json >/dev/null 2>&1 || true

echo "[init] creating users..."
"$MC" admin user add "$ALIAS" "${MINIO_STREAM_ACCESS_KEY}" "${MINIO_STREAM_SECRET_KEY}" >/dev/null 2>&1 || true
"$MC" admin user add "$ALIAS" "${MINIO_ML_ACCESS_KEY}" "${MINIO_ML_SECRET_KEY}" >/dev/null 2>&1 || true

echo "[init] attaching policies..."
"$MC" admin policy attach "$ALIAS" stream-svc-policy-v2 --user "${MINIO_STREAM_ACCESS_KEY}" >/dev/null 2>&1 || true
"$MC" admin policy attach "$ALIAS" ml-svc-policy-full --user "${MINIO_ML_ACCESS_KEY}" >/dev/null 2>&1 || true

echo "[init] minio provisioning complete."
