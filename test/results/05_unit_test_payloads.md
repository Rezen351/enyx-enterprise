# Unit Test Payloads & Responses

Total captured requests: 129

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** POST
- **Status:** 200
- **Duration:** 0.3703s
- **Payload:**
```json
{
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1aWQiOiJjY2JlMzcwOC1lYjAzLTQ3ZGYtODNhMi1lNzBlMGQ3OTAwZTgiLCJ1c2VybmFtZSI6ImFkbWluIiwicm9sZXMiOlsiYWRtaW4iXSwiaXNzIjoiYXV0aC1zdmMiLCJzdWIiOiJjY2JlMzcwOC1lYjAzLTQ3ZGYtODNhMi1lNzBlMGQ3OTAwZTgiLCJleHAiOjE3ODU3MzAzODEsIm5iZiI6MTc4NTY4NzE4MSwiaWF0IjoxNzg1Njg3MTgxfQ.uCFObJ9DP622TbxP4IzByt7XlAhXLR5AKYE_Mb1qfhE",
    "refresh_token": "fXtD2X8p1Re9rvxQgfc0xq9xaHEJLwHkBjcLkmhSnNM=",
    "expires_in": 43200
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 200
- **Duration:** 0.0035s
- **Payload:**
```json
{
  "data": {
    "count": 2,
    "snapshots": [
      {
        "id": "815a51d7-b18e-4850-95f5-5c0053a49c67",
        "stream_id": "4a3b07e9-3616-47a1-9d5f-d6609e3bc21b",
        "stream_name": "cctv-1",
        "module_id": "05609956-3dbd-4245-9012-95e4f19b3f52",
        "url": "/storage/stream/recordings/cctv-1/863beb3a-6115-48ee-bb58-4d0d344fa272.mp4",
        "kind": "recording",
        "size": 92496,
        "created_at": "2026-08-02T15:37:18.91Z",
        "duration": 4.566667
      },
      {
        "id": "090981ff-84aa-43fa-afc2-af0428a1b18e",
        "stream_id": "4a3b07e9-3616-47a1-9d5f-d6609e3bc21b",
        "stream_name": "cctv-1",
        "module_id": "05609956-3dbd-4245-9012-95e4f19b3f52",
        "url": "/storage/stream/snapshots/cctv-1/9f675078-9f32-429f-b766-a7e7c787e217.jpg",
        "kind": "snapshot",
        "size": 49212,
        "created_at": "2026-08-02T14:20:59.434Z"
      }
    ]
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** DELETE
- **Status:** 200
- **Duration:** -0.7414s
- **Payload:**
```json
{
  "data": {
    "message": "snapshot deleted"
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** DELETE
- **Status:** 401
- **Duration:** 0.0029s
- **Payload:**
```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "invalid or expired token"
  },
  "success": false
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 200
- **Duration:** 0.0032s
- **Payload:**
```json
{
  "data": {
    "status": "ok"
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 200
- **Duration:** 0.0047s
- **Payload:**
```json
{
  "data": {
    "count": 2,
    "nodes": [
      {
        "id": "6cce0542-a53c-4cfd-9b1a-db64b4f846b3",
        "node_id": "node-00",
        "module_id": "05609956-3dbd-4245-9012-95e4f19b3f52",
        "name": "node-00",
        "mac": "61:B2:B6:31:9E:99",
        "ip": "172.31.225.221",
        "fw_version": "1.0.0",
        "status": "online",
        "paired": true,
        "last_seen_at": "2026-08-02T16:12:32.918Z",
        "discovered_at": "2026-07-31T06:12:56.177Z",
        "created_at": "2026-07-31T06:12:56.177Z",
        "updated_at": "2026-08-02T16:12:32.918Z"
      },
      {
        "id": "9047d2fc-8ca3-11f1-927f-3e7b06fa7937",
        "node_id": "node-02",
        "name": "",
        "mac": "",
        "ip": "",
        "fw_version": "",
        "status": "online",
        "paired": false,
        "discovered_at": "2026-07-31T05:46:51Z",
        "created_at": "2026-07-31T05:46:51Z",
        "updated_at": "2026-07-31T05:46:51Z"
      }
    ]
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 200
- **Duration:** 0.0026s
- **Payload:**
```json
{
  "data": {
    "count": 2,
    "nodes": [
      {
        "id": "6cce0542-a53c-4cfd-9b1a-db64b4f846b3",
        "node_id": "node-00",
        "module_id": "05609956-3dbd-4245-9012-95e4f19b3f52",
        "name": "node-00",
        "mac": "61:B2:B6:31:9E:99",
        "ip": "172.31.225.221",
        "fw_version": "1.0.0",
        "status": "online",
        "paired": true,
        "last_seen_at": "2026-08-02T16:12:32.918Z",
        "discovered_at": "2026-07-31T06:12:56.177Z",
        "created_at": "2026-07-31T06:12:56.177Z",
        "updated_at": "2026-08-02T16:12:32.918Z"
      },
      {
        "id": "9047d2fc-8ca3-11f1-927f-3e7b06fa7937",
        "node_id": "node-02",
        "name": "",
        "mac": "",
        "ip": "",
        "fw_version": "",
        "status": "online",
        "paired": false,
        "discovered_at": "2026-07-31T05:46:51Z",
        "created_at": "2026-07-31T05:46:51Z",
        "updated_at": "2026-07-31T05:46:51Z"
      }
    ]
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 200
- **Duration:** 0.0025s
- **Payload:**
```json
{
  "data": {
    "status": "ok"
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 401
- **Duration:** 0.0028s
- **Payload:**
```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "invalid or expired token"
  },
  "success": false
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** PUT
- **Status:** 401
- **Duration:** 0.0027s
- **Payload:**
```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "invalid or expired token"
  },
  "success": false
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 401
- **Duration:** 0.003s
- **Payload:**
```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "invalid or expired token"
  },
  "success": false
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 401
- **Duration:** 0.0031s
- **Payload:**
```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "invalid or expired token"
  },
  "success": false
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 401
- **Duration:** 0.0025s
- **Payload:**
```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "invalid or expired token"
  },
  "success": false
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** POST
- **Status:** 200
- **Duration:** 0.1409s
- **Payload:**
```json
{
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1aWQiOiJjY2JlMzcwOC1lYjAzLTQ3ZGYtODNhMi1lNzBlMGQ3OTAwZTgiLCJ1c2VybmFtZSI6ImFkbWluIiwicm9sZXMiOlsiYWRtaW4iXSwiaXNzIjoiYXV0aC1zdmMiLCJzdWIiOiJjY2JlMzcwOC1lYjAzLTQ3ZGYtODNhMi1lNzBlMGQ3OTAwZTgiLCJleHAiOjE3ODU3MzAzODAsIm5iZiI6MTc4NTY4NzE4MCwiaWF0IjoxNzg1Njg3MTgwfQ.In8MpBh4Ev-z3e87znedsYH-VtMYX-LqPoZemmm6Xd0",
    "refresh_token": "sakqzPJBj_0miNOy_xosLLgXAJpEVbMBOqlsxLOkG4U=",
    "expires_in": 43200
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** POST
- **Status:** 201
- **Duration:** 0.727s
- **Payload:**
```json
{
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1aWQiOiI2YTJiYzJkZi02YmMxLTQxMjAtOTNjYi04NzFiYzJmYmRhMzIiLCJ1c2VybmFtZSI6InRlc3R1c2VyXzE3ODU2ODcxODAiLCJyb2xlcyI6WyJ2aWV3ZXIiXSwiaXNzIjoiYXV0aC1zdmMiLCJzdWIiOiI2YTJiYzJkZi02YmMxLTQxMjAtOTNjYi04NzFiYzJmYmRhMzIiLCJleHAiOjE3ODU3MzAzODEsIm5iZiI6MTc4NTY4NzE4MSwiaWF0IjoxNzg1Njg3MTgxfQ.u-4cnYxBBTzisc7Dj_kFRTW58oHSca6p9M4d52XYNfA",
    "refresh_token": "HA_MKgF2OIKA2ENjdbzQ156F3gRwu281TQJ7HLaMj2I=",
    "expires_in": 43200
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** POST
- **Status:** 200
- **Duration:** 0.2016s
- **Payload:**
```json
{
  "data": {
    "message": "logged out successfully"
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** POST
- **Status:** 200
- **Duration:** 0.2016s
- **Payload:**
```json
{
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1aWQiOiI2YTJiYzJkZi02YmMxLTQxMjAtOTNjYi04NzFiYzJmYmRhMzIiLCJ1c2VybmFtZSI6InRlc3R1c2VyXzE3ODU2ODcxODAiLCJyb2xlcyI6WyJ2aWV3ZXIiXSwiaXNzIjoiYXV0aC1zdmMiLCJzdWIiOiI2YTJiYzJkZi02YmMxLTQxMjAtOTNjYi04NzFiYzJmYmRhMzIiLCJleHAiOjE3ODU3MzAzODEsIm5iZiI6MTc4NTY4NzE4MSwiaWF0IjoxNzg1Njg3MTgxfQ.u-4cnYxBBTzisc7Dj_kFRTW58oHSca6p9M4d52XYNfA",
    "refresh_token": "YBfX7wBa0xxX4ni5hcsqgjJJleRzooa6lrpt3cXyOmI=",
    "expires_in": 43200
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** DELETE
- **Status:** 200
- **Duration:** 0.4111s
- **Payload:**
```json
{
  "data": {
    "message": "account deactivated successfully"
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 200
- **Duration:** 0.0029s
- **Payload:**
```json
{
  "data": {
    "count": 1,
    "modules": [
      {
        "id": "05609956-3dbd-4245-9012-95e4f19b3f52",
        "name": "Module A",
        "description": "",
        "config": "{}",
        "created_at": "2026-07-31T06:39:07.027Z",
        "updated_at": "2026-07-31T06:39:07.027Z"
      }
    ]
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** POST
- **Status:** 201
- **Duration:** 0.3255s
- **Payload:**
```json
{
  "data": {
    "id": "d289299c-ab62-41e5-90f9-47bcdb8ffb9d",
    "name": "Test Greenhouse 1785687182",
    "description": "Automated unit test module",
    "config": "{}",
    "created_at": "2026-08-02T16:13:02.475413709Z",
    "updated_at": "2026-08-02T16:13:02.475413709Z"
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 200
- **Duration:** 0.004s
- **Payload:**
```json
{
  "data": {
    "id": "d289299c-ab62-41e5-90f9-47bcdb8ffb9d",
    "name": "Test Greenhouse 1785687182",
    "description": "Automated unit test module",
    "config": "{}",
    "created_at": "2026-08-02T16:13:02.475Z",
    "updated_at": "2026-08-02T16:13:02.475Z"
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 200
- **Duration:** 0.0026s
- **Payload:**
```json
{
  "data": {
    "count": 2,
    "nodes": [
      {
        "id": "6cce0542-a53c-4cfd-9b1a-db64b4f846b3",
        "node_id": "node-00",
        "module_id": "05609956-3dbd-4245-9012-95e4f19b3f52",
        "name": "node-00",
        "mac": "61:B2:B6:31:9E:99",
        "ip": "172.31.225.221",
        "fw_version": "1.0.0",
        "status": "online",
        "paired": true,
        "last_seen_at": "2026-08-02T16:13:01.288Z",
        "discovered_at": "2026-07-31T06:12:56.177Z",
        "created_at": "2026-07-31T06:12:56.177Z",
        "updated_at": "2026-08-02T16:13:01.288Z"
      },
      {
        "id": "9047d2fc-8ca3-11f1-927f-3e7b06fa7937",
        "node_id": "node-02",
        "name": "",
        "mac": "",
        "ip": "",
        "fw_version": "",
        "status": "online",
        "paired": false,
        "discovered_at": "2026-07-31T05:46:51Z",
        "created_at": "2026-07-31T05:46:51Z",
        "updated_at": "2026-07-31T05:46:51Z"
      }
    ]
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 200
- **Duration:** 0.0025s
- **Payload:**
```json
{
  "data": {
    "count": 1,
    "nodes": [
      {
        "id": "9047d2fc-8ca3-11f1-927f-3e7b06fa7937",
        "node_id": "node-02",
        "name": "",
        "mac": "",
        "ip": "",
        "fw_version": "",
        "status": "online",
        "paired": false,
        "discovered_at": "2026-07-31T05:46:51Z",
        "created_at": "2026-07-31T05:46:51Z",
        "updated_at": "2026-07-31T05:46:51Z"
      }
    ]
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 200
- **Duration:** 0.003s
- **Payload:**
```json
{
  "data": {
    "node_id": "node-00",
    "tags": []
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 200
- **Duration:** 0.0042s
- **Payload:**
```json
{
  "data": {
    "node_id": "node-00",
    "tags": [
      {
        "id": "11a19b58-61af-45e0-8d81-fdd69c49df0b",
        "node_id": "node-00",
        "kind": "actuator",
        "source_key": "buzzer",
        "tag_name": "buzzer",
        "display_name": "Alarm",
        "label": "",
        "unit": "",
        "data_type": "bool",
        "enabled": true,
        "created_at": "2026-07-31T07:00:11.645Z",
        "updated_at": "2026-07-31T13:35:22.54Z"
      },
      {
        "id": "dc56dd77-dcdf-4691-abbc-28ed6be564f2",
        "node_id": "node-00",
        "kind": "actuator",
        "source_key": "load1",
        "tag_name": "load1",
        "display_name": "Misting",
        "label": "",
        "unit": "",
        "data_type": "bool",
        "enabled": true,
        "created_at": "2026-07-31T07:00:12.432Z",
        "updated_at": "2026-07-31T13:35:22.585Z"
      },
      {
        "id": "dfb38ef6-8142-4254-8761-ac7cfeeea338",
        "node_id": "node-00",
        "kind": "actuator",
        "source_key": "load2",
        "tag_name": "load2",
        "display_name": "Valve",
        "label": "",
        "unit": "",
        "data_type": "bool",
        "enabled": true,
        "created_at": "2026-07-31T07:00:13.701Z",
        "updated_at": "2026-07-31T13:35:22.636Z"
      },
      {
        "id": "3b158449-f47b-499d-b8b9-23d00b67c19f",
        "node_id": "node-00",
        "kind": "actuator",
        "source_key": "load3",
        "tag_name": "load3",
        "display_name": "",
        "label": "",
        "unit": "",
        "data_type": "bool",
        "enabled": true,
        "created_at": "2026-07-31T07:00:14.59Z",
        "updated_at": "2026-07-31T13:35:22.712Z"
      },
      {
        "id": "7c8fed62-d131-4795-95cc-13f253a9e7de",
        "node_id": "node-00",
        "kind": "actuator",
        "source_key": "load4",
        "tag_name": "load4",
        "display_name": "",
        "label": "",
        "unit": "",
        "data_type": "bool",
        "enabled": true,
        "created_at": "2026-07-31T07:00:15.284Z",
        "updated_at": "2026-07-31T13:35:22.796Z"
      }
    ]
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** PUT
- **Status:** 200
- **Duration:** 0.1046s
- **Payload:**
```json
{
  "data": {
    "id": "d289299c-ab62-41e5-90f9-47bcdb8ffb9d",
    "name": "Test Greenhouse 1785687182",
    "description": "Updated by unit test",
    "config": "{}",
    "created_at": "2026-08-02T16:13:02.475Z",
    "updated_at": "2026-08-02T16:13:02.819803618Z"
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** DELETE
- **Status:** 200
- **Duration:** 0.1923s
- **Payload:**
```json
{
  "data": {
    "message": "module deleted; its nodes were unpaired"
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 200
- **Duration:** 0.0032s
- **Payload:**
```json
{
  "data": {
    "id": "6cce0542-a53c-4cfd-9b1a-db64b4f846b3",
    "node_id": "node-00",
    "module_id": "05609956-3dbd-4245-9012-95e4f19b3f52",
    "name": "node-00",
    "mac": "61:B2:B6:31:9E:99",
    "ip": "172.31.225.221",
    "fw_version": "1.0.0",
    "status": "online",
    "paired": true,
    "last_seen_at": "2026-08-02T16:13:01.288Z",
    "discovered_at": "2026-07-31T06:12:56.177Z",
    "created_at": "2026-07-31T06:12:56.177Z",
    "updated_at": "2026-08-02T16:13:01.288Z"
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** PUT
- **Status:** 200
- **Duration:** 0.0515s
- **Payload:**
```json
{
  "data": {
    "node_id": "node-00",
    "tags": [
      {
        "id": "5d0b0c81-d87e-4317-9b15-a5a915b979a8",
        "node_id": "node-00",
        "kind": "sensor",
        "source_key": "sensor_1",
        "tag_name": "temperature",
        "display_name": "Temperature",
        "label": "C",
        "unit": "°C",
        "data_type": "float",
        "enabled": true,
        "created_at": "2026-08-02T16:13:03.12Z",
        "updated_at": "2026-08-02T16:13:03.12Z"
      }
    ]
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** POST
- **Status:** 400
- **Duration:** 0.0034s
- **Payload:**
```json
{
  "error": {
    "code": "BAD_REQUEST",
    "message": "module_id is required and must reference an existing module"
  },
  "success": false
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** POST
- **Status:** 200
- **Duration:** 0.2193s
- **Payload:**
```json
{
  "data": {
    "id": "6cce0542-a53c-4cfd-9b1a-db64b4f846b3",
    "node_id": "node-00",
    "name": "node-00",
    "mac": "61:B2:B6:31:9E:99",
    "ip": "172.31.225.221",
    "fw_version": "1.0.0",
    "status": "online",
    "paired": false,
    "last_seen_at": "2026-08-02T16:13:01.288Z",
    "discovered_at": "2026-07-31T06:12:56.177Z",
    "created_at": "2026-07-31T06:12:56.177Z",
    "updated_at": "2026-08-02T16:13:03.175Z"
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 200
- **Duration:** 0.0038s
- **Payload:**
```json
{
  "data": {
    "count": 1,
    "modules": [
      {
        "id": "05609956-3dbd-4245-9012-95e4f19b3f52",
        "name": "Module A",
        "description": "",
        "config": "{}",
        "created_at": "2026-07-31T06:39:07.027Z",
        "updated_at": "2026-07-31T06:39:07.027Z"
      }
    ]
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** POST
- **Status:** 200
- **Duration:** 0.3966s
- **Payload:**
```json
{
  "data": {
    "id": "6cce0542-a53c-4cfd-9b1a-db64b4f846b3",
    "node_id": "node-00",
    "module_id": "05609956-3dbd-4245-9012-95e4f19b3f52",
    "name": "node-00",
    "mac": "61:B2:B6:31:9E:99",
    "ip": "172.31.225.221",
    "fw_version": "1.0.0",
    "status": "online",
    "paired": true,
    "last_seen_at": "2026-08-02T16:13:01.288Z",
    "discovered_at": "2026-07-31T06:12:56.177Z",
    "created_at": "2026-07-31T06:12:56.177Z",
    "updated_at": "2026-08-02T16:13:03.399Z"
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 200
- **Duration:** 0.0028s
- **Payload:**
```json
{
  "data": {
    "count": 2,
    "nodes": [
      {
        "id": "6cce0542-a53c-4cfd-9b1a-db64b4f846b3",
        "node_id": "node-00",
        "module_id": "05609956-3dbd-4245-9012-95e4f19b3f52",
        "name": "node-00",
        "mac": "61:B2:B6:31:9E:99",
        "ip": "172.31.225.221",
        "fw_version": "1.0.0",
        "status": "online",
        "paired": true,
        "last_seen_at": "2026-08-02T16:13:01.288Z",
        "discovered_at": "2026-07-31T06:12:56.177Z",
        "created_at": "2026-07-31T06:12:56.177Z",
        "updated_at": "2026-08-02T16:13:03.399Z"
      },
      {
        "id": "9047d2fc-8ca3-11f1-927f-3e7b06fa7937",
        "node_id": "node-02",
        "name": "",
        "mac": "",
        "ip": "",
        "fw_version": "",
        "status": "online",
        "paired": false,
        "discovered_at": "2026-07-31T05:46:51Z",
        "created_at": "2026-07-31T05:46:51Z",
        "updated_at": "2026-07-31T05:46:51Z"
      }
    ]
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** POST
- **Status:** 201
- **Duration:** 0.1149s
- **Payload:**
```json
{
  "data": {
    "id": "78a9853d-7308-4dc1-8d76-918ad18ac539",
    "node_id": "node-00",
    "kind": "actuator",
    "source_key": "fan",
    "tag_name": "fan",
    "display_name": "Fan",
    "label": "",
    "unit": "on/off",
    "data_type": "boolean",
    "enabled": true,
    "created_at": "2026-08-02T16:13:04.799849468Z",
    "updated_at": "2026-08-02T16:13:04.799849468Z"
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** DELETE
- **Status:** 200
- **Duration:** 0.0954s
- **Payload:**
```json
{
  "data": {
    "message": "actuator tag deleted"
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** DELETE
- **Status:** 200
- **Duration:** 0.0052s
- **Payload:**
```json
{
  "data": {
    "message": "actuator tag deleted"
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** DELETE
- **Status:** 404
- **Duration:** 0.0033s
- **Payload:**
```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "module not found"
  },
  "success": false
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 200
- **Duration:** 0.1404s
- **Payload:**
```json
{
  "data": {
    "nodes": [
      {
        "node_id": "node-00",
        "module_id": "05609956-3dbd-4245-9012-95e4f19b3f52",
        "metrics": [
          "connection_stats.mqtt_connected",
          "connection_stats.uptime_s",
          "device_info.cpu_freq_mhz",
          "device_info.flash_size_mb",
          "device_info.free_heap_kb",
          "device_info.uptime_s",
          "network.wifi_rssi",
          "telemetry.inputs.input1",
          "telemetry.inputs.input2",
          "telemetry.inputs.input3",
          "telemetry.inputs.input4",
          "telemetry.modbus.cwt1.hum",
          "telemetry.modbus.cwt1.temp",
          "telemetry.modbus.cwt2.hum",
          "telemetry.modbus.cwt2.temp",
          "telemetry.modbus.npk.ec_nutrisi",
          "telemetry.modbus.npk.ph_nutrisi",
          "telemetry.modbus.npk.temp_nutrisi",
          "telemetry.outputs.buzzer",
          "telemetry.outputs.load1",
          "telemetry.outputs.load2",
          "telemetry.outputs.load3",
          "telemetry.outputs.load4"
        ]
      }
    ]
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 200
- **Duration:** 0.0143s
- **Payload:**
```json
{
  "data": {
    "interval": "1h",
    "series": {
      "node-00": {
        "temperature": []
      }
    }
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 200
- **Duration:** 0.0057s
- **Payload:**
```json
{
  "data": {
    "node_id": "node-00",
    "metric": "temperature",
    "count": 0,
    "min": 0,
    "max": 0,
    "avg": 0,
    "last": 0,
    "first_ts": 0,
    "last_ts": 0
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 200
- **Duration:** 0.0038s
- **Payload:**
```
bucket,node_id,metric,count,sum,min,max,avg,last

```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 200
- **Duration:** 0.0058s
- **Payload:**
```json
{
  "data": {
    "interval": "1h",
    "series": {
      "node-00": {
        "temperature": []
      }
    }
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 200
- **Duration:** 0.0094s
- **Payload:**
```json
{
  "data": {
    "interval": "1h",
    "series": {
      "node-00": {
        "humidity": [],
        "temperature": []
      }
    }
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 200
- **Duration:** 0.003s
- **Payload:**
```json
{
  "data": {
    "id": "6cce0542-a53c-4cfd-9b1a-db64b4f846b3",
    "node_id": "node-00",
    "module_id": "05609956-3dbd-4245-9012-95e4f19b3f52",
    "name": "node-00",
    "mac": "61:B2:B6:31:9E:99",
    "ip": "172.31.225.221",
    "fw_version": "1.0.0",
    "status": "online",
    "paired": true,
    "last_seen_at": "2026-08-02T16:13:01.288Z",
    "discovered_at": "2026-07-31T06:12:56.177Z",
    "created_at": "2026-07-31T06:12:56.177Z",
    "updated_at": "2026-08-02T16:13:03.399Z"
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 200
- **Duration:** 0.02s
- **Payload:**
```json
{
  "data": {
    "commands": [
      {
        "id": "5ebea4f3-ff02-4fbe-a87f-ccb6dcd825c1",
        "req_id": "9341f895-f124-4450-9070-506839dcfe2d",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 0,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T16:11:18.751Z",
        "acked_at": "2026-08-02T16:11:18.859Z"
      },
      {
        "id": "42bcf788-e6d8-42b9-8cfd-f568986c6da5",
        "req_id": "c06f98e2-452d-4b0f-9746-ecad408d47b8",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 1,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T16:10:21.534Z",
        "acked_at": "2026-08-02T16:10:21.627Z"
      },
      {
        "id": "2ebec739-9d81-4d54-967b-43a5120c256f",
        "req_id": "8ee200ce-e0f3-459a-9793-2ddd602113fe",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 0,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T16:08:25.755Z",
        "acked_at": "2026-08-02T16:08:25.808Z"
      },
      {
        "id": "fcaa7c06-4935-4796-82be-cb39da2fbcfa",
        "req_id": "e86791cd-535c-4f0d-b510-41e14b42a05a",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 1,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T16:07:27.558Z",
        "acked_at": "2026-08-02T16:07:27.619Z"
      },
      {
        "id": "9c920abc-c635-4112-91a4-5d7621dd67fc",
        "req_id": "519fb478-1b17-4f4a-b8e6-4e154f0e4a04",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 0,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T16:05:33.521Z",
        "acked_at": "2026-08-02T16:05:33.779Z"
      },
      {
        "id": "1e1fd1de-bc05-4d00-adc7-2311161d6d18",
        "req_id": "816070db-d48c-40aa-8e60-47f8e629358f",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 1,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T16:04:09.364Z",
        "acked_at": "2026-08-02T16:04:10.423Z"
      },
      {
        "id": "2a92f226-333e-462e-9712-eda87e525d29",
        "req_id": "1b622dad-a742-4fa2-803c-28f849ccb591",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 0,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T16:02:13.384Z",
        "acked_at": "2026-08-02T16:02:13.782Z"
      },
      {
        "id": "fab47316-f487-45e0-a844-99fcc9f84b31",
        "req_id": "d65050b4-e644-422f-bd62-3fba2392bf11",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 1,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T16:01:16.119Z",
        "acked_at": "2026-08-02T16:01:16.286Z"
      },
      {
        "id": "08030f5b-5e33-4e1b-a422-c035bb6d5615",
        "req_id": "f65fd247-dbfe-4108-929d-fc787fbf85ed",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 0,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T15:59:21.936Z",
        "acked_at": "2026-08-02T15:59:22.003Z"
      },
      {
        "id": "7e23b311-635b-4136-899d-23acd70c6bb4",
        "req_id": "7be62a6d-c6c9-4851-9ae0-7cfb882bdcc7",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 1,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T15:58:20.883Z",
        "acked_at": "2026-08-02T15:58:23.427Z"
      },
      {
        "id": "71b05a2b-2a21-4d59-922d-5e64abef1bfd",
        "req_id": "8b6ceaee-1596-455f-a157-a2236e66d544",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 0,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T15:56:27.022Z",
        "acked_at": "2026-08-02T15:56:27.084Z"
      },
      {
        "id": "83fedb65-325d-464c-a1a4-cd5832a2bcb2",
        "req_id": "87554024-14e5-4f46-9d8a-716d504c187d",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 1,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T15:55:29.917Z",
        "acked_at": "2026-08-02T15:55:29.988Z"
      },
      {
        "id": "5a00d408-eba3-4124-84e7-5861d7f72432",
        "req_id": "7b1a6a11-9289-418a-8c18-bba94ec2d6a3",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 0,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T15:53:34.34Z",
        "acked_at": "2026-08-02T15:53:34.473Z"
      },
      {
        "id": "bc6be855-666e-40ac-b9fb-6402a4584b4e",
        "req_id": "f65cbe0a-baa3-4e30-a211-f7ac571075f2",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 1,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T15:52:37.27Z",
        "acked_at": "2026-08-02T15:52:37.337Z"
      },
      {
        "id": "ef09f666-f395-4c29-b572-94e440889e1a",
        "req_id": "453b9645-d82b-4c32-869a-cb48ab697ca3",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 0,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T15:50:43.14Z",
        "acked_at": "2026-08-02T15:50:43.205Z"
      },
      {
        "id": "d5ec8805-9269-43be-acf9-3f35eabea470",
        "req_id": "78f92eed-7ff6-4f9b-bac0-1be830cf31e7",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 1,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T15:49:45.963Z",
        "acked_at": "2026-08-02T15:49:46.023Z"
      },
      {
        "id": "3be518a5-5b2a-4108-8dbd-0ca113f8cd72",
        "req_id": "76f54bfc-e7e2-474d-a616-ae44d3d582de",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 0,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T15:47:50.446Z",
        "acked_at": "2026-08-02T15:47:50.497Z"
      },
      {
        "id": "24e97800-b0a7-4837-bdda-6568590c9f5a",
        "req_id": "3488024a-6f42-4c35-9e41-93b555ba03ba",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 1,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T15:46:53.35Z",
        "acked_at": "2026-08-02T15:46:53.397Z"
      },
      {
        "id": "1711be7b-9aa7-411e-bfca-90d0f74d1052",
        "req_id": "787fdd34-e81a-473d-9029-f286c7579154",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 0,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T15:44:58.604Z",
        "acked_at": "2026-08-02T15:44:58.677Z"
      },
      {
        "id": "34c8f7d1-f141-4edc-bfa0-c1f42206b5ff",
        "req_id": "33663a0e-b6f8-48aa-875c-0de1bb014451",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 1,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T15:44:01.285Z",
        "acked_at": "2026-08-02T15:44:01.565Z"
      },
      {
        "id": "4f48a8b3-3000-45fe-8968-83be3f8d5c02",
        "req_id": "84d7e567-074e-4eeb-89c9-d870dee595d4",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 0,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T15:42:06.178Z",
        "acked_at": "2026-08-02T15:42:06.604Z"
      },
      {
        "id": "3f013345-773c-468e-aa36-c73baf9bcdb7",
        "req_id": "e7f946f8-a6c5-4651-89b6-455a734c42c3",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 1,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T15:41:08.802Z",
        "acked_at": "2026-08-02T15:41:08.872Z"
      },
      {
        "id": "f2c29186-7acb-4ecd-a32e-a8fa2e4b89a8",
        "req_id": "2cb6aecc-c7d3-487d-a50c-de828f11623b",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 0,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T15:39:14.836Z",
        "acked_at": "2026-08-02T15:39:14.996Z"
      },
      {
        "id": "4a5d9ae1-7857-4b92-9381-8627f4769154",
        "req_id": "def5df60-b985-4721-82d8-d7a171017471",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 1,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T15:38:17.712Z",
        "acked_at": "2026-08-02T15:38:17.769Z"
      },
      {
        "id": "84abf4e0-d71d-4809-98c2-d6c5cc885bfd",
        "req_id": "86ee5f0f-0518-475b-888f-3499f7f66fd4",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 0,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T15:36:22.133Z",
        "acked_at": "2026-08-02T15:36:22.186Z"
      },
      {
        "id": "62626ff1-a2db-4a88-b9e5-ff575b76cb20",
        "req_id": "69c23746-d09e-47f7-8039-b4b31cf96219",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 1,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T15:35:25.799Z",
        "acked_at": "2026-08-02T15:35:25.843Z"
      },
      {
        "id": "fa8d76b3-7ff3-4742-8b53-ce5994ba75f6",
        "req_id": "7b2b3a70-ca4b-4c1f-a313-10bee5903f5f",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 0,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T15:33:30.363Z",
        "acked_at": "2026-08-02T15:33:30.545Z"
      },
      {
        "id": "830e99d7-3ab8-4c02-9837-9cb7af5daf7e",
        "req_id": "71fbbc9c-a9c0-4e8d-bfa2-98c55d1083b5",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 1,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T15:32:33.054Z",
        "acked_at": "2026-08-02T15:32:33.209Z"
      },
      {
        "id": "886d75b1-52d2-46b7-b6f3-ce9785dfb567",
        "req_id": "20319257-b4f4-4987-a2e1-48da2dfc2252",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 0,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T15:30:39.256Z",
        "acked_at": "2026-08-02T15:30:39.3Z"
      },
      {
        "id": "feda86a9-774c-4f10-a3f0-13574c15edce",
        "req_id": "e497ad63-0107-46de-88f3-1ffbedd80762",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 1,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T15:29:42.255Z",
        "acked_at": "2026-08-02T15:29:42.315Z"
      },
      {
        "id": "fc3c8034-8dad-4f15-98cb-3c536a65abd1",
        "req_id": "97907a6f-5677-4296-ab74-eaa6e566dc7c",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 0,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T15:27:46.153Z",
        "acked_at": "2026-08-02T15:27:46.735Z"
      },
      {
        "id": "edcd97ce-cda3-4e51-8048-05690dc04cc4",
        "req_id": "b2bf599d-a2b7-4f75-a04e-32174a25048b",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 1,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T15:26:49.174Z",
        "acked_at": "2026-08-02T15:26:49.242Z"
      },
      {
        "id": "da5965e2-c07e-4651-a5b8-5ddb313b5746",
        "req_id": "a133da7a-fc61-48fc-8a73-3bf3c99dfd2a",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 0,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T15:24:54.572Z",
        "acked_at": "2026-08-02T15:24:55.039Z"
      },
      {
        "id": "e0babc34-da25-4c33-b994-2d8b1dd054a9",
        "req_id": "e52cd963-03cb-4f0c-af87-a61c0ddfda39",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 1,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T15:23:57.003Z",
        "acked_at": "2026-08-02T15:23:57.056Z"
      },
      {
        "id": "46cef262-ac3a-4f6b-adea-3e293d48c328",
        "req_id": "7d4da6dc-26b4-4b08-9032-413bdae873eb",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 0,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T15:22:03.204Z",
        "acked_at": "2026-08-02T15:22:03.26Z"
      },
      {
        "id": "d7401d14-9d04-4943-b266-07508aeb0d48",
        "req_id": "d79607be-eefb-4a15-b6c0-0f223f24c8f6",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 1,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T15:20:44.354Z",
        "acked_at": "2026-08-02T15:20:48.422Z"
      },
      {
        "id": "e537fcb4-ac61-4f5e-ad09-3c0854fbb6df",
        "req_id": "61603f03-709e-472e-9e83-3b42ae82af67",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 0,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T15:18:50.554Z",
        "acked_at": "2026-08-02T15:18:50.601Z"
      },
      {
        "id": "aaf00d3a-0c90-4ec5-8613-4c974c65f0b0",
        "req_id": "7bbcc4b7-a559-4987-8807-33295d0ccf43",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 1,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T15:17:53.131Z",
        "acked_at": "2026-08-02T15:17:53.329Z"
      },
      {
        "id": "b4fd33ac-84e4-41f7-a9e8-0cdb2b49d810",
        "req_id": "f4ca11bb-de2b-441a-87f7-7bb9fdd20a56",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 0,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T15:15:56.471Z",
        "acked_at": "2026-08-02T15:15:56.795Z"
      },
      {
        "id": "0c42248d-ce5c-4beb-93c5-f15e9cb182a1",
        "req_id": "77bf3c66-e318-4cec-8773-50ef41295274",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 1,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T15:14:57.612Z",
        "acked_at": "2026-08-02T15:14:58.286Z"
      },
      {
        "id": "b6d6708a-ea45-432e-8ca4-2b5391d55de4",
        "req_id": "afcf8ceb-7431-49dd-b7e6-a6e520e02b49",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 0,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T15:13:03.376Z",
        "acked_at": "2026-08-02T15:13:03.53Z"
      },
      {
        "id": "cfb70d1e-49d2-4238-94df-e3b1e0f8921b",
        "req_id": "f3ee6619-4ba5-4320-b6a5-27cf0280fd21",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 1,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T15:12:05.327Z",
        "acked_at": "2026-08-02T15:12:05.535Z"
      },
      {
        "id": "af4c98bf-ac1a-4921-9b6a-551fd09c5e33",
        "req_id": "6cda2448-5871-41f2-8249-3b9a8b008de9",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 0,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T15:10:11.387Z",
        "acked_at": "2026-08-02T15:10:11.493Z"
      },
      {
        "id": "a822d072-c2f5-4132-9873-eebd9aebe927",
        "req_id": "47fcefae-156d-421d-9a25-58f2c179cb98",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 1,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T15:09:13.752Z",
        "acked_at": "2026-08-02T15:09:13.893Z"
      },
      {
        "id": "8439a192-c900-4134-a3d3-4113fdc376b1",
        "req_id": "4ce36afa-588c-4974-9daf-f08e748c390e",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 0,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T15:07:16.996Z",
        "acked_at": "2026-08-02T15:07:17.268Z"
      },
      {
        "id": "287bffb7-77ff-4624-bf66-59adbbf44cc5",
        "req_id": "9a434777-ef1c-40a3-ba5e-af521ae6be71",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 1,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T15:06:20.022Z",
        "acked_at": "2026-08-02T15:06:20.088Z"
      },
      {
        "id": "1990d1cb-997c-4cf4-a270-ca70a2de12f6",
        "req_id": "6623cbe4-ec36-4153-bfc8-340f3575ca4d",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 0,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T15:04:25.788Z",
        "acked_at": "2026-08-02T15:04:25.951Z"
      },
      {
        "id": "ebeb7c87-bab9-4594-9cf1-7558632dd0ba",
        "req_id": "54a1386c-ef70-4c14-a548-267769e61317",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 1,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T15:03:28.548Z",
        "acked_at": "2026-08-02T15:03:28.774Z"
      },
      {
        "id": "8893fd3d-a229-4193-b6dc-c6b75987c715",
        "req_id": "5c743c84-9301-47fc-a067-84fbc38ee67a",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 0,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T15:01:33.165Z",
        "acked_at": "2026-08-02T15:01:33.239Z"
      },
      {
        "id": "04339b76-e1b9-4008-b384-d1574e1dad94",
        "req_id": "0808f9f1-847f-486b-92a1-35ea39a8d305",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 1,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T15:00:35.274Z",
        "acked_at": "2026-08-02T15:00:35.782Z"
      },
      {
        "id": "06072931-384c-4b72-8cfb-4e640314eaae",
        "req_id": "a28a3990-2f16-4af3-9996-708c45fdfb2c",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 0,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T14:58:41.593Z",
        "acked_at": "2026-08-02T14:58:41.647Z"
      },
      {
        "id": "cc1f9f66-98ee-4802-90ae-144da66d68c4",
        "req_id": "904c010d-ac20-43d2-bfd9-2e5b160dcc05",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 1,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T14:57:40.454Z",
        "acked_at": "2026-08-02T14:57:40.806Z"
      },
      {
        "id": "ecbab90d-62a0-4fa0-9698-e1e5c59778fb",
        "req_id": "567c4770-dfef-47a3-8f8b-813a67840da8",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 0,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T14:55:46.221Z",
        "acked_at": "2026-08-02T14:55:46.789Z"
      },
      {
        "id": "de2d084b-a64f-4319-930a-a5c4fcf65401",
        "req_id": "208395b1-bc61-4ae9-8990-ba0ccf6a21d7",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 1,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T14:54:48.053Z",
        "acked_at": "2026-08-02T14:54:48.106Z"
      },
      {
        "id": "379eb529-9500-44bf-9b7d-fa7c26899373",
        "req_id": "d5b27bc5-e542-4c20-957d-cbe6293234d6",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 0,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T14:52:52.668Z",
        "acked_at": "2026-08-02T14:52:52.722Z"
      },
      {
        "id": "50e184d3-894e-4d0d-aac5-705d18f20da4",
        "req_id": "a9bb7148-4975-4363-ac86-2d78cbcda20b",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 1,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T14:51:55.176Z",
        "acked_at": "2026-08-02T14:51:55.22Z"
      },
      {
        "id": "0e868004-8c4b-4553-b910-877e8e961d26",
        "req_id": "9705dee9-63e7-411d-8b5e-06dba2b9d653",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 0,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T14:50:01.279Z",
        "acked_at": "2026-08-02T14:50:01.349Z"
      },
      {
        "id": "260d14b2-68ed-46da-a658-5297d664fe98",
        "req_id": "e1189ebc-a3ec-46a8-9e4f-64c445be4e27",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 1,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T14:49:04.248Z",
        "acked_at": "2026-08-02T14:49:04.28Z"
      },
      {
        "id": "576135ed-89a3-4afd-b854-88754029564a",
        "req_id": "dd8b0892-302b-457f-9f96-a5b888c28fe3",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 0,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T14:47:10.087Z",
        "acked_at": "2026-08-02T14:47:10.398Z"
      },
      {
        "id": "d0490377-a723-4034-a90f-5b067adcbe76",
        "req_id": "da6d2a30-6978-4349-8420-489d978039f2",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 1,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T14:46:11.177Z",
        "acked_at": "2026-08-02T14:46:11.219Z"
      },
      {
        "id": "1cc7fb11-e539-42df-8bb2-b9802a06f926",
        "req_id": "b2e3ad5b-7e53-4438-b3e9-67179531f8d1",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 0,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T14:44:17.467Z",
        "acked_at": "2026-08-02T14:44:17.589Z"
      },
      {
        "id": "abbd3eff-475d-49fa-b9bc-084b9f45d203",
        "req_id": "433fd9ec-2b64-4bf7-9afd-2b03710b6651",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 1,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T14:43:12.991Z",
        "acked_at": "2026-08-02T14:43:18.9Z"
      },
      {
        "id": "edd90a15-61a0-4da2-95b9-43ceb26949ed",
        "req_id": "7cdd60e2-34cc-409b-a490-18e48eb0b887",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 0,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T14:41:18.56Z",
        "acked_at": "2026-08-02T14:41:18.87Z"
      },
      {
        "id": "4afc560d-9fce-4903-b861-195e53ea37e7",
        "req_id": "24b07e21-488d-4c44-aba4-4223dff709f4",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 1,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T14:40:20.31Z",
        "acked_at": "2026-08-02T14:40:21.251Z"
      },
      {
        "id": "93a774bb-25fd-469e-97e6-671523a93693",
        "req_id": "327fdb1c-959f-4019-a594-4b3a6c3de614",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 0,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T14:38:25.077Z",
        "acked_at": "2026-08-02T14:38:25.409Z"
      },
      {
        "id": "7f3e0180-c6ba-46b3-857b-736d7ae2d703",
        "req_id": "bedec86c-1699-4cb8-aac1-8e5fcec69598",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 1,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T14:37:02.995Z",
        "acked_at": "2026-08-02T14:37:05.471Z"
      },
      {
        "id": "ebe38b6d-7829-4943-acd1-c261dabf6ea3",
        "req_id": "ce43fed2-1e83-4189-b43e-69acc46c2334",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 0,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T14:35:09.59Z",
        "acked_at": "2026-08-02T14:35:09.701Z"
      },
      {
        "id": "174e5c5f-146f-45b1-93cb-81c11b1837c0",
        "req_id": "9e459b7f-c2c7-4331-b684-03c077b24867",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 1,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T14:33:39.718Z",
        "acked_at": "2026-08-02T14:33:43.342Z"
      },
      {
        "id": "c0792db3-7258-4081-a8fa-0d6ee3418da0",
        "req_id": "0ba77e42-0045-4c7b-9da1-d485912bff4e",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 0,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T14:31:42.613Z",
        "acked_at": "2026-08-02T14:31:43.396Z"
      },
      {
        "id": "0c1f9503-aa16-4827-a542-c8de597850d3",
        "req_id": "23a604d6-7a28-457a-836c-29a542e080a6",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 1,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T14:30:44.905Z",
        "acked_at": "2026-08-02T14:30:44.959Z"
      },
      {
        "id": "261b5484-7e0f-4b6d-9fbd-85f4bbf37ed4",
        "req_id": "ddb24e60-a0a4-4a03-b21d-0205164539ee",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 0,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T14:28:50.584Z",
        "acked_at": "2026-08-02T14:28:50.729Z"
      },
      {
        "id": "dd9acb22-8f17-42b8-8d05-02c488dbf967",
        "req_id": "de274391-4ef5-41a1-af1d-6b5f9f56a04e",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 1,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T14:27:53.285Z",
        "acked_at": "2026-08-02T14:27:53.378Z"
      },
      {
        "id": "d62e5e0d-e9ed-427b-8ba1-7e44a78d447d",
        "req_id": "454e8da7-ca4e-44b1-8130-d03958903fb9",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 0,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T14:25:57.499Z",
        "acked_at": "2026-08-02T14:25:57.553Z"
      },
      {
        "id": "c3590fb5-ce7f-443e-a677-96b14e58941a",
        "req_id": "b50fa1c4-7de8-414e-8459-5fd43c9bb3f9",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 1,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T14:25:00.383Z",
        "acked_at": "2026-08-02T14:25:00.437Z"
      },
      {
        "id": "bc428239-7f38-4bd9-81c4-7ed94a241338",
        "req_id": "fb2afb7b-ac3a-4142-ba4d-900e383c4cb9",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 0,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T14:23:06.255Z",
        "acked_at": "2026-08-02T14:23:06.398Z"
      },
      {
        "id": "fa836361-babe-4ea1-a72a-40f0c9cfc3f7",
        "req_id": "b3c3d8be-9df4-461d-853c-7357735cd0b5",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 1,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T14:22:06.693Z",
        "acked_at": "2026-08-02T14:22:07.278Z"
      },
      {
        "id": "ba7f8073-a25e-4efa-9ca7-1387ee0287d8",
        "req_id": "5f09e54c-7756-4569-88e7-06419e22da6e",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 0,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T14:20:12.206Z",
        "acked_at": "2026-08-02T14:20:12.265Z"
      },
      {
        "id": "da8af5c9-d785-4d7d-b339-c797a9efbacd",
        "req_id": "36ae7700-6545-4464-935b-33f93191062c",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 1,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T14:19:13.265Z",
        "acked_at": "2026-08-02T14:19:13.316Z"
      },
      {
        "id": "abc7ef6a-2de6-4f4d-8ce3-970616840060",
        "req_id": "de8d0e44-458c-4913-b354-69987b70b4dd",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 0,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T14:17:19.386Z",
        "acked_at": "2026-08-02T14:17:19.435Z"
      },
      {
        "id": "0bb37d36-60df-421c-902f-ded7421a2aef",
        "req_id": "9ad1741e-d19f-4726-8cb9-bdbb62e09094",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 1,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T14:16:19.721Z",
        "acked_at": "2026-08-02T14:16:20.434Z"
      },
      {
        "id": "65b386f7-de94-438d-b39d-04c00d98c234",
        "req_id": "6a2796a0-1c9c-416e-9194-2791cd8a79d6",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 0,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T14:14:22.031Z",
        "acked_at": "2026-08-02T14:14:22.363Z"
      },
      {
        "id": "49e5a4e2-1968-41f7-b78e-ef05bab24e06",
        "req_id": "7438e172-3dee-4d14-a0d6-aac13f55a175",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 1,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T14:13:23.811Z",
        "acked_at": "2026-08-02T14:13:24.079Z"
      },
      {
        "id": "6a5de392-b882-4104-90e7-dac0399b1fce",
        "req_id": "ef8dc6c3-d9bf-44ac-98ad-d236d2ee76ff",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 0,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T14:11:29.478Z",
        "acked_at": "2026-08-02T14:11:29.669Z"
      },
      {
        "id": "4a572798-b4b6-407f-9e84-b75f9807baae",
        "req_id": "18328415-4eea-4295-8183-6d5c729cbfa9",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 1,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T14:10:30.343Z",
        "acked_at": "2026-08-02T14:10:30.777Z"
      },
      {
        "id": "4a22c988-c4f1-4781-bb6f-9d7e6ed9b2d0",
        "req_id": "c1abb8a6-cd0b-4260-9d1b-4d2c29e5bdbd",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 0,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T14:08:32.403Z",
        "acked_at": "2026-08-02T14:08:32.725Z"
      },
      {
        "id": "7a40c1b3-c8a3-4387-aba0-16d3e51e37fb",
        "req_id": "9ef5f7a9-5ac7-4955-94be-ad117790992f",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 1,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T14:07:34.324Z",
        "acked_at": "2026-08-02T14:07:34.731Z"
      },
      {
        "id": "335f6693-ff40-4fc6-a883-c8b7ee326009",
        "req_id": "4f7e6264-e1e1-41dc-bc5d-939726a94fc2",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 0,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T14:05:38.639Z",
        "acked_at": "2026-08-02T14:05:38.828Z"
      },
      {
        "id": "5927dd86-5872-4f4c-b552-be32a1e37b47",
        "req_id": "67c99516-c813-4d29-99db-4e8ef8d04e4a",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 1,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T14:04:40.906Z",
        "acked_at": "2026-08-02T14:04:40.981Z"
      },
      {
        "id": "98af0714-0191-412f-a9d4-8d0c97869e1e",
        "req_id": "fe5a1d27-b21e-4783-9e6b-1182181974ed",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 0,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T14:02:45.065Z",
        "acked_at": "2026-08-02T14:02:46.164Z"
      },
      {
        "id": "d50271b4-f815-4b63-8a40-ee397acbcfe7",
        "req_id": "568911e2-d6ff-4b2d-a0bd-43fc6fbf67f5",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 1,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T14:01:41.991Z",
        "acked_at": "2026-08-02T14:01:43.064Z"
      },
      {
        "id": "e8b86a5b-744d-446d-a3cc-31f1653e19c7",
        "req_id": "5b55a6e6-e01e-4935-a186-d4e1384e5c61",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 0,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T13:59:47.504Z",
        "acked_at": "2026-08-02T13:59:47.789Z"
      },
      {
        "id": "3761c859-4ad0-4540-8721-cb35d54660c0",
        "req_id": "a33e0eb9-ff6e-49ef-a97f-23bf6acd6947",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 1,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T13:58:49.416Z",
        "acked_at": "2026-08-02T13:58:49.508Z"
      },
      {
        "id": "07f1b85a-a97e-4928-9659-bf34ce5eba02",
        "req_id": "58cd66cd-37f4-47b3-8e7c-1b3599a07044",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 0,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T13:56:52.429Z",
        "acked_at": "2026-08-02T13:56:53.013Z"
      },
      {
        "id": "6328fd87-aada-4fcf-ab6e-5cd05e1e796e",
        "req_id": "fb64191f-e1d7-409d-a15e-edca78a2bf29",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 1,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T13:55:52.606Z",
        "acked_at": "2026-08-02T13:55:52.809Z"
      },
      {
        "id": "9e5c9b17-c09f-44ca-9ea8-dc9e89402f71",
        "req_id": "37bac6ad-4995-4a33-9f7b-64dd8f129dee",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 0,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T13:53:56.611Z",
        "acked_at": "2026-08-02T13:53:57.029Z"
      },
      {
        "id": "8c016043-5a31-4911-a995-996043311421",
        "req_id": "cd7c19d6-7861-4318-81db-edd898e23092",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 1,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T13:52:57.774Z",
        "acked_at": "2026-08-02T13:52:57.833Z"
      },
      {
        "id": "67f600ac-f0ff-4287-8f16-b2f28a8a656d",
        "req_id": "b04e607d-174c-406a-b2c5-fbc09672281c",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 0,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T13:50:52.502Z",
        "acked_at": "2026-08-02T13:50:57.258Z"
      },
      {
        "id": "24ae2dc6-69f0-4dfa-a9f6-edb50b4f4124",
        "req_id": "efe0041c-934f-404e-8151-f4a436900de8",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 1,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T13:49:54.708Z",
        "acked_at": "2026-08-02T13:49:54.745Z"
      },
      {
        "id": "71ac205b-71f8-4b6e-a23e-3146d1178df3",
        "req_id": "84b78077-8dd1-41b3-831f-6f8c0ebd6d01",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 0,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T13:48:00.426Z",
        "acked_at": "2026-08-02T13:48:00.56Z"
      },
      {
        "id": "c94c92d4-ac35-4f67-95d1-f7b019a0c044",
        "req_id": "ee5f00d7-d0f4-4749-8674-45f33e307f11",
        "node_id": "node-00",
        "target": "load1",
        "tag_name": "",
        "control_type": "interval",
        "value": 1,
        "source": "schedule",
        "schedule_id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "status": "acked",
        "created_at": "2026-08-02T13:46:47.518Z",
        "acked_at": "2026-08-02T13:46:54.361Z"
      }
    ],
    "count": 100
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 200
- **Duration:** 0.0031s
- **Payload:**
```json
{
  "data": {
    "id": "6cce0542-a53c-4cfd-9b1a-db64b4f846b3",
    "node_id": "node-00",
    "module_id": "05609956-3dbd-4245-9012-95e4f19b3f52",
    "name": "node-00",
    "mac": "61:B2:B6:31:9E:99",
    "ip": "172.31.225.221",
    "fw_version": "1.0.0",
    "status": "online",
    "paired": true,
    "last_seen_at": "2026-08-02T16:13:01.288Z",
    "discovered_at": "2026-07-31T06:12:56.177Z",
    "created_at": "2026-07-31T06:12:56.177Z",
    "updated_at": "2026-08-02T16:13:03.399Z"
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 200
- **Duration:** 0.004s
- **Payload:**
```json
{
  "data": {
    "mode": "AUTO",
    "node_id": "node-00"
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 200
- **Duration:** 0.0032s
- **Payload:**
```json
{
  "data": {
    "id": "6cce0542-a53c-4cfd-9b1a-db64b4f846b3",
    "node_id": "node-00",
    "module_id": "05609956-3dbd-4245-9012-95e4f19b3f52",
    "name": "node-00",
    "mac": "61:B2:B6:31:9E:99",
    "ip": "172.31.225.221",
    "fw_version": "1.0.0",
    "status": "online",
    "paired": true,
    "last_seen_at": "2026-08-02T16:13:01.288Z",
    "discovered_at": "2026-07-31T06:12:56.177Z",
    "created_at": "2026-07-31T06:12:56.177Z",
    "updated_at": "2026-08-02T16:13:03.399Z"
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** PUT
- **Status:** 200
- **Duration:** 0.1121s
- **Payload:**
```json
{
  "data": {
    "mode": "MANUAL",
    "node_id": "node-00"
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 200
- **Duration:** 0.0037s
- **Payload:**
```json
{
  "data": {
    "id": "6cce0542-a53c-4cfd-9b1a-db64b4f846b3",
    "node_id": "node-00",
    "module_id": "05609956-3dbd-4245-9012-95e4f19b3f52",
    "name": "node-00",
    "mac": "61:B2:B6:31:9E:99",
    "ip": "172.31.225.221",
    "fw_version": "1.0.0",
    "status": "online",
    "paired": true,
    "last_seen_at": "2026-08-02T16:13:01.288Z",
    "discovered_at": "2026-07-31T06:12:56.177Z",
    "created_at": "2026-07-31T06:12:56.177Z",
    "updated_at": "2026-08-02T16:13:03.399Z"
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 200
- **Duration:** 0.0066s
- **Payload:**
```json
{
  "data": {
    "count": 5,
    "targets": [
      {
        "id": "11a19b58-61af-45e0-8d81-fdd69c49df0b",
        "node_id": "node-00",
        "source_key": "buzzer",
        "tag_name": "buzzer",
        "label": "Alarm",
        "output_type": "DIGITAL",
        "last_value": 0,
        "created_at": "0001-01-01T00:00:00Z",
        "updated_at": "0001-01-01T00:00:00Z"
      },
      {
        "id": "dc56dd77-dcdf-4691-abbc-28ed6be564f2",
        "node_id": "node-00",
        "source_key": "load1",
        "tag_name": "load1",
        "label": "Misting",
        "output_type": "DIGITAL",
        "last_value": 0,
        "created_at": "0001-01-01T00:00:00Z",
        "updated_at": "0001-01-01T00:00:00Z"
      },
      {
        "id": "dfb38ef6-8142-4254-8761-ac7cfeeea338",
        "node_id": "node-00",
        "source_key": "load2",
        "tag_name": "load2",
        "label": "Valve",
        "output_type": "DIGITAL",
        "last_value": 1,
        "created_at": "0001-01-01T00:00:00Z",
        "updated_at": "0001-01-01T00:00:00Z"
      },
      {
        "id": "3b158449-f47b-499d-b8b9-23d00b67c19f",
        "node_id": "node-00",
        "source_key": "load3",
        "tag_name": "load3",
        "label": "load3",
        "output_type": "DIGITAL",
        "last_value": 0,
        "created_at": "0001-01-01T00:00:00Z",
        "updated_at": "0001-01-01T00:00:00Z"
      },
      {
        "id": "7c8fed62-d131-4795-95cc-13f253a9e7de",
        "node_id": "node-00",
        "source_key": "load4",
        "tag_name": "load4",
        "label": "load4",
        "output_type": "DIGITAL",
        "last_value": 0,
        "created_at": "0001-01-01T00:00:00Z",
        "updated_at": "0001-01-01T00:00:00Z"
      }
    ]
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 200
- **Duration:** 0.0027s
- **Payload:**
```json
{
  "data": {
    "id": "6cce0542-a53c-4cfd-9b1a-db64b4f846b3",
    "node_id": "node-00",
    "module_id": "05609956-3dbd-4245-9012-95e4f19b3f52",
    "name": "node-00",
    "mac": "61:B2:B6:31:9E:99",
    "ip": "172.31.225.221",
    "fw_version": "1.0.0",
    "status": "online",
    "paired": true,
    "last_seen_at": "2026-08-02T16:13:01.288Z",
    "discovered_at": "2026-07-31T06:12:56.177Z",
    "created_at": "2026-07-31T06:12:56.177Z",
    "updated_at": "2026-08-02T16:13:03.399Z"
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 200
- **Duration:** 0.003s
- **Payload:**
```json
{
  "data": {
    "count": 5,
    "outputs": [
      {
        "name": "load3",
        "type": "DIGITAL",
        "value": 0
      },
      {
        "name": "load4",
        "type": "DIGITAL",
        "value": 0
      },
      {
        "name": "buzzer",
        "type": "DIGITAL",
        "value": 0
      },
      {
        "name": "load1",
        "type": "DIGITAL",
        "value": 0
      },
      {
        "name": "load2",
        "type": "DIGITAL",
        "value": 1
      }
    ]
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 200
- **Duration:** 0.0034s
- **Payload:**
```json
{
  "data": {
    "id": "6cce0542-a53c-4cfd-9b1a-db64b4f846b3",
    "node_id": "node-00",
    "module_id": "05609956-3dbd-4245-9012-95e4f19b3f52",
    "name": "node-00",
    "mac": "61:B2:B6:31:9E:99",
    "ip": "172.31.225.221",
    "fw_version": "1.0.0",
    "status": "online",
    "paired": true,
    "last_seen_at": "2026-08-02T16:13:01.288Z",
    "discovered_at": "2026-07-31T06:12:56.177Z",
    "created_at": "2026-07-31T06:12:56.177Z",
    "updated_at": "2026-08-02T16:13:03.399Z"
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** POST
- **Status:** 202
- **Duration:** 0.6298s
- **Payload:**
```json
{
  "data": {
    "commands": [
      {
        "id": "0f31ca09-c913-423f-aa46-3adec24f3323",
        "req_id": "078bcc44-21ea-4ed3-81dd-7d22301cc0ee",
        "node_id": "node-00",
        "target": "valve",
        "tag_name": "",
        "control_type": "set_state",
        "value": 1,
        "source": "manual",
        "status": "sent",
        "issued_by": "ccbe3708-eb03-47df-83a2-e70e0d7900e8",
        "created_at": "2026-08-02T16:13:05.37090727Z"
      }
    ],
    "count": 1
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 200
- **Duration:** 0.0032s
- **Payload:**
```json
{
  "data": {
    "id": "6cce0542-a53c-4cfd-9b1a-db64b4f846b3",
    "node_id": "node-00",
    "module_id": "05609956-3dbd-4245-9012-95e4f19b3f52",
    "name": "node-00",
    "mac": "61:B2:B6:31:9E:99",
    "ip": "172.31.225.221",
    "fw_version": "1.0.0",
    "status": "online",
    "paired": true,
    "last_seen_at": "2026-08-02T16:13:01.288Z",
    "discovered_at": "2026-07-31T06:12:56.177Z",
    "created_at": "2026-07-31T06:12:56.177Z",
    "updated_at": "2026-08-02T16:13:03.399Z"
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** POST
- **Status:** 400
- **Duration:** 0.0033s
- **Payload:**
```json
{
  "error": {
    "code": "BAD_REQUEST",
    "message": "node is not paired to a module; please pair the node before issuing control commands"
  },
  "success": false
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 200
- **Duration:** 0.0029s
- **Payload:**
```json
{
  "data": {
    "id": "6cce0542-a53c-4cfd-9b1a-db64b4f846b3",
    "node_id": "node-00",
    "module_id": "05609956-3dbd-4245-9012-95e4f19b3f52",
    "name": "node-00",
    "mac": "61:B2:B6:31:9E:99",
    "ip": "172.31.225.221",
    "fw_version": "1.0.0",
    "status": "online",
    "paired": true,
    "last_seen_at": "2026-08-02T16:13:01.288Z",
    "discovered_at": "2026-07-31T06:12:56.177Z",
    "created_at": "2026-07-31T06:12:56.177Z",
    "updated_at": "2026-08-02T16:13:03.399Z"
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** POST
- **Status:** 200
- **Duration:** 0.1633s
- **Payload:**
```json
{
  "data": {
    "mode": "AUTO",
    "node_id": "node-00"
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 200
- **Duration:** 0.003s
- **Payload:**
```json
{
  "data": {
    "id": "6cce0542-a53c-4cfd-9b1a-db64b4f846b3",
    "node_id": "node-00",
    "module_id": "05609956-3dbd-4245-9012-95e4f19b3f52",
    "name": "node-00",
    "mac": "61:B2:B6:31:9E:99",
    "ip": "172.31.225.221",
    "fw_version": "1.0.0",
    "status": "online",
    "paired": true,
    "last_seen_at": "2026-08-02T16:13:01.288Z",
    "discovered_at": "2026-07-31T06:12:56.177Z",
    "created_at": "2026-07-31T06:12:56.177Z",
    "updated_at": "2026-08-02T16:13:03.399Z"
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 200
- **Duration:** 0.0028s
- **Payload:**
```json
{
  "data": {
    "count": 1,
    "schedules": [
      {
        "id": "48b7ca43-d165-4d5c-a8c9-51139ba08fce",
        "node_id": "node-00",
        "output_name": "load1",
        "tag_name": "",
        "type": "interval",
        "params": {
          "value_on": 1,
          "value_off": 0,
          "on_sec": 60,
          "off_sec": 120
        },
        "enabled": true,
        "created_at": "2026-07-31T08:36:34.026Z",
        "updated_at": "2026-07-31T08:36:34.026Z"
      }
    ]
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 200
- **Duration:** 0.0036s
- **Payload:**
```json
{
  "data": {
    "id": "6cce0542-a53c-4cfd-9b1a-db64b4f846b3",
    "node_id": "node-00",
    "module_id": "05609956-3dbd-4245-9012-95e4f19b3f52",
    "name": "node-00",
    "mac": "61:B2:B6:31:9E:99",
    "ip": "172.31.225.221",
    "fw_version": "1.0.0",
    "status": "online",
    "paired": true,
    "last_seen_at": "2026-08-02T16:13:01.288Z",
    "discovered_at": "2026-07-31T06:12:56.177Z",
    "created_at": "2026-07-31T06:12:56.177Z",
    "updated_at": "2026-08-02T16:13:03.399Z"
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** POST
- **Status:** 201
- **Duration:** 0.7079s
- **Payload:**
```json
{
  "data": {
    "id": "2157c990-f3e7-4782-a736-6510f9a531f5",
    "node_id": "node-00",
    "output_name": "pump",
    "tag_name": "",
    "type": "interval",
    "params": {
      "on_sec": 10,
      "off_sec": 5,
      "value_on": 1,
      "value_off": 0
    },
    "enabled": false,
    "created_at": "2026-08-02T16:13:06.181725965Z",
    "updated_at": "2026-08-02T16:13:06.181725965Z"
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 200
- **Duration:** 0.0033s
- **Payload:**
```json
{
  "data": {
    "id": "6cce0542-a53c-4cfd-9b1a-db64b4f846b3",
    "node_id": "node-00",
    "module_id": "05609956-3dbd-4245-9012-95e4f19b3f52",
    "name": "node-00",
    "mac": "61:B2:B6:31:9E:99",
    "ip": "172.31.225.221",
    "fw_version": "1.0.0",
    "status": "online",
    "paired": true,
    "last_seen_at": "2026-08-02T16:13:01.288Z",
    "discovered_at": "2026-07-31T06:12:56.177Z",
    "created_at": "2026-07-31T06:12:56.177Z",
    "updated_at": "2026-08-02T16:13:03.399Z"
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** DELETE
- **Status:** 200
- **Duration:** 0.2747s
- **Payload:**
```json
{
  "data": {
    "message": "schedule deleted"
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 200
- **Duration:** 0.0029s
- **Payload:**
```json
{
  "data": {
    "id": "6cce0542-a53c-4cfd-9b1a-db64b4f846b3",
    "node_id": "node-00",
    "module_id": "05609956-3dbd-4245-9012-95e4f19b3f52",
    "name": "node-00",
    "mac": "61:B2:B6:31:9E:99",
    "ip": "172.31.225.221",
    "fw_version": "1.0.0",
    "status": "online",
    "paired": true,
    "last_seen_at": "2026-08-02T16:13:01.288Z",
    "discovered_at": "2026-07-31T06:12:56.177Z",
    "created_at": "2026-07-31T06:12:56.177Z",
    "updated_at": "2026-08-02T16:13:03.399Z"
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** PUT
- **Status:** 404
- **Duration:** 0.0032s
- **Payload:**
```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "schedule not found"
  },
  "success": false
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 200
- **Duration:** 0.0038s
- **Payload:**
```json
{
  "data": {
    "id": "6cce0542-a53c-4cfd-9b1a-db64b4f846b3",
    "node_id": "node-00",
    "module_id": "05609956-3dbd-4245-9012-95e4f19b3f52",
    "name": "node-00",
    "mac": "61:B2:B6:31:9E:99",
    "ip": "172.31.225.221",
    "fw_version": "1.0.0",
    "status": "online",
    "paired": true,
    "last_seen_at": "2026-08-02T16:13:01.288Z",
    "discovered_at": "2026-07-31T06:12:56.177Z",
    "created_at": "2026-07-31T06:12:56.177Z",
    "updated_at": "2026-08-02T16:13:03.399Z"
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** POST
- **Status:** 404
- **Duration:** 0.0028s
- **Payload:**
```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "schedule not found"
  },
  "success": false
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 200
- **Duration:** 0.0029s
- **Payload:**
```json
{
  "data": {
    "id": "6cce0542-a53c-4cfd-9b1a-db64b4f846b3",
    "node_id": "node-00",
    "module_id": "05609956-3dbd-4245-9012-95e4f19b3f52",
    "name": "node-00",
    "mac": "61:B2:B6:31:9E:99",
    "ip": "172.31.225.221",
    "fw_version": "1.0.0",
    "status": "online",
    "paired": true,
    "last_seen_at": "2026-08-02T16:13:01.288Z",
    "discovered_at": "2026-07-31T06:12:56.177Z",
    "created_at": "2026-07-31T06:12:56.177Z",
    "updated_at": "2026-08-02T16:13:03.399Z"
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** POST
- **Status:** 404
- **Duration:** 0.0027s
- **Payload:**
```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "schedule not found"
  },
  "success": false
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 200
- **Duration:** 0.0029s
- **Payload:**
```json
{
  "data": {
    "id": "6cce0542-a53c-4cfd-9b1a-db64b4f846b3",
    "node_id": "node-00",
    "module_id": "05609956-3dbd-4245-9012-95e4f19b3f52",
    "name": "node-00",
    "mac": "61:B2:B6:31:9E:99",
    "ip": "172.31.225.221",
    "fw_version": "1.0.0",
    "status": "online",
    "paired": true,
    "last_seen_at": "2026-08-02T16:13:01.288Z",
    "discovered_at": "2026-07-31T06:12:56.177Z",
    "created_at": "2026-07-31T06:12:56.177Z",
    "updated_at": "2026-08-02T16:13:03.399Z"
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** PUT
- **Status:** 200
- **Duration:** 0.0632s
- **Payload:**
```json
{
  "data": {
    "mode": "AUTO",
    "node_id": "node-00",
    "output": "pump"
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 200
- **Duration:** 0.0028s
- **Payload:**
```json
{
  "data": {
    "id": "6cce0542-a53c-4cfd-9b1a-db64b4f846b3",
    "node_id": "node-00",
    "module_id": "05609956-3dbd-4245-9012-95e4f19b3f52",
    "name": "node-00",
    "mac": "61:B2:B6:31:9E:99",
    "ip": "172.31.225.221",
    "fw_version": "1.0.0",
    "status": "online",
    "paired": true,
    "last_seen_at": "2026-08-02T16:13:01.288Z",
    "discovered_at": "2026-07-31T06:12:56.177Z",
    "created_at": "2026-07-31T06:12:56.177Z",
    "updated_at": "2026-08-02T16:13:03.399Z"
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 404
- **Duration:** 0.0032s
- **Payload:**
```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "schedule not found"
  },
  "success": false
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** DELETE
- **Status:** 404
- **Duration:** 0.0025s
- **Payload:**
```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "schedule not found"
  },
  "success": false
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 200
- **Duration:** 0.007s
- **Payload:**
```json
{
  "data": {
    "alerts": [],
    "limit": 50,
    "offset": 0,
    "total": 0
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 200
- **Duration:** 0.003s
- **Payload:**
```json
{
  "data": {
    "thresholds": [],
    "total": 0
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** POST
- **Status:** 201
- **Duration:** 0.4809s
- **Payload:**
```json
{
  "data": {
    "id": "9c48c0e8-f9ec-4744-a667-a19d122fd3d6",
    "node_id": "node-00",
    "metric": "temperature",
    "min": 15,
    "max": 35,
    "enabled": true,
    "severity": "warning"
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** PUT
- **Status:** 200
- **Duration:** 0.1077s
- **Payload:**
```json
{
  "data": {
    "id": "9c48c0e8-f9ec-4744-a667-a19d122fd3d6",
    "node_id": "node-00",
    "metric": "temperature",
    "min": 15,
    "max": 40,
    "enabled": true,
    "severity": "critical"
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** DELETE
- **Status:** 200
- **Duration:** 0.4097s
- **Payload:**
```json
{
  "data": {
    "id": "9c48c0e8-f9ec-4744-a667-a19d122fd3d6",
    "status": "deleted"
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** PUT
- **Status:** 404
- **Duration:** 0.0041s
- **Payload:**
```json
{
  "data": {
    "error": {
      "code": "NOT_FOUND",
      "message": "alert not found"
    },
    "success": false
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** DELETE
- **Status:** 404
- **Duration:** 0.0035s
- **Payload:**
```json
{
  "data": {
    "error": {
      "code": "NOT_FOUND",
      "message": "threshold not found"
    },
    "success": false
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 200
- **Duration:** 0.3843s
- **Payload:**
```json
{
  "data": {
    "limit": 50,
    "logs": [
      {
        "id": "df1d20da-0e19-4256-a47c-6b18acbc01d1",
        "event": "control.schedule.deleted",
        "payload": "{\"schedule_id\":\"2157c990-f3e7-4782-a736-6510f9a531f5\"}",
        "received_at": "2026-08-02T16:13:08.397Z"
      },
      {
        "id": "ee63265d-4526-4338-9e76-8eb13e7aee6c",
        "event": "control.schedule.created",
        "payload": "{\"node_id\":\"node-00\",\"schedule_id\":\"2157c990-f3e7-4782-a736-6510f9a531f5\",\"type\":\"interval\"}",
        "received_at": "2026-08-02T16:13:08.04Z"
      },
      {
        "id": "37a23378-657a-45a7-bfe1-133c411b73b3",
        "event": "control.command.acked",
        "payload": "{\"node_id\":\"node-00\",\"req_id\":\"078bcc44-21ea-4ed3-81dd-7d22301cc0ee\",\"target\":\"valve\"}",
        "received_at": "2026-08-02T16:13:06.367Z"
      },
      {
        "id": "6aa38e9e-bd01-46b0-84f9-a48c4f17beef",
        "event": "control.command.sent",
        "payload": "{\"node_id\":\"node-00\",\"source\":\"manual\",\"target\":\"valve\",\"type\":\"set_state\",\"value\":\"1\"}",
        "received_at": "2026-08-02T16:13:06.042Z"
      },
      {
        "id": "79071ed3-8a27-4d43-89d4-51d4ee3b86f4",
        "event": "node.paired",
        "payload": "{\"module_id\":\"05609956-3dbd-4245-9012-95e4f19b3f52\",\"node_id\":\"node-00\"}",
        "received_at": "2026-08-02T16:13:05.652Z"
      },
      {
        "id": "4fbc0c08-d978-420a-a91d-82c637300c65",
        "event": "node.unpaired",
        "payload": "{\"node_id\":\"node-00\"}",
        "received_at": "2026-08-02T16:13:05.29Z"
      },
      {
        "id": "40e3787e-154d-42f4-ac35-ca30d5a550f9",
        "event": "module.deleted",
        "payload": "{\"module_id\":\"d289299c-ab62-41e5-90f9-47bcdb8ffb9d\"}",
        "received_at": "2026-08-02T16:13:03.988Z"
      },
      {
        "id": "c011786d-a102-4acf-97d8-f17e32618cd9",
        "event": "module.created",
        "payload": "{\"module_id\":\"d289299c-ab62-41e5-90f9-47bcdb8ffb9d\",\"name\":\"Test Greenhouse 1785687182\"}",
        "received_at": "2026-08-02T16:13:03.663Z"
      },
      {
        "id": "275d1bf1-c8e0-410a-ae5f-01b89b69d2a8",
        "event": "module.updated",
        "payload": "{\"module_id\":\"d289299c-ab62-41e5-90f9-47bcdb8ffb9d\"}",
        "received_at": "2026-08-02T16:13:03.349Z"
      },
      {
        "id": "dad8a946-89b0-4e39-9469-0e908149d81b",
        "event": "auth.account.deleted",
        "payload": "{\"user_id\":\"6a2bc2df-6bc1-4120-93cb-871bc2fbda32\",\"ip\":\"172.17.0.1\"}",
        "received_at": "2026-08-02T16:13:02.47Z"
      },
      {
        "id": "8adb242a-3de6-4838-9f3a-489e5ef84d9d",
        "event": "auth.login",
        "payload": "{\"user_id\":\"6a2bc2df-6bc1-4120-93cb-871bc2fbda32\",\"username\":\"testuser_1785687180\",\"ip\":\"172.17.0.1\"}",
        "received_at": "2026-08-02T16:13:02.059Z"
      },
      {
        "id": "e80508ff-e26b-4f9c-a4a0-e1190be3cf75",
        "event": "auth.logout",
        "payload": "{\"user_id\":\"ccbe3708-eb03-47df-83a2-e70e0d7900e8\",\"ip\":\"172.17.0.1\"}",
        "received_at": "2026-08-02T16:13:01.857Z"
      },
      {
        "id": "ad15d673-5efc-4b67-b7f2-aa6654fc981f",
        "event": "auth.register",
        "payload": "{\"user_id\":\"6a2bc2df-6bc1-4120-93cb-871bc2fbda32\",\"username\":\"testuser_1785687180\",\"ip\":\"172.17.0.1\"}",
        "received_at": "2026-08-02T16:13:01.655Z"
      },
      {
        "id": "e4ca9068-cd32-41c3-886e-4c816ce42770",
        "event": "auth.login",
        "payload": "{\"user_id\":\"ccbe3708-eb03-47df-83a2-e70e0d7900e8\",\"username\":\"admin\",\"ip\":\"172.17.0.1\"}",
        "received_at": "2026-08-02T16:13:01.49Z"
      },
      {
        "id": "2bfce773-8652-446b-a05d-4706317234a4",
        "event": "auth.refresh",
        "payload": "{\"user_id\":\"ccbe3708-eb03-47df-83a2-e70e0d7900e8\",\"ip\":\"172.17.0.1\"}",
        "received_at": "2026-08-02T16:13:00.928Z"
      },
      {
        "id": "2449087e-7a50-4a4f-9465-6b0b9de82826",
        "event": "control.command.acked",
        "payload": "{\"node_id\":\"node-00\",\"req_id\":\"9341f895-f124-4450-9070-506839dcfe2d\",\"target\":\"load1\"}",
        "received_at": "2026-08-02T16:11:20.923Z"
      },
      {
        "id": "661e44ab-d208-41ef-a726-c31675b7d0c8",
        "event": "control.command.sent",
        "payload": "{\"node_id\":\"node-00\",\"source\":\"schedule\",\"target\":\"load1\",\"type\":\"interval\",\"value\":\"0\"}",
        "received_at": "2026-08-02T16:11:20.536Z"
      },
      {
        "id": "6cfe5464-afc0-4128-9c80-234226c9f657",
        "event": "control.command.sent",
        "payload": "{\"node_id\":\"node-00\",\"source\":\"schedule\",\"target\":\"load1\",\"type\":\"interval\",\"value\":\"1\"}",
        "received_at": "2026-08-02T16:10:24.029Z"
      },
      {
        "id": "af74e57b-f0cc-4464-9485-ba5dd38800da",
        "event": "control.command.acked",
        "payload": "{\"node_id\":\"node-00\",\"req_id\":\"c06f98e2-452d-4b0f-9746-ecad408d47b8\",\"target\":\"load1\"}",
        "received_at": "2026-08-02T16:10:23.776Z"
      },
      {
        "id": "ae9b5859-d9cc-424a-b1b9-7c4c96c22f0a",
        "event": "control.command.sent",
        "payload": "{\"node_id\":\"node-00\",\"source\":\"schedule\",\"target\":\"load1\",\"type\":\"interval\",\"value\":\"0\"}",
        "received_at": "2026-08-02T16:08:26.868Z"
      },
      {
        "id": "575b69a2-984d-484f-b6b2-e9c80654e522",
        "event": "control.command.acked",
        "payload": "{\"node_id\":\"node-00\",\"req_id\":\"8ee200ce-e0f3-459a-9793-2ddd602113fe\",\"target\":\"load1\"}",
        "received_at": "2026-08-02T16:08:26.638Z"
      },
      {
        "id": "a1022c3d-b814-4129-aebf-dd9513adaa10",
        "event": "control.command.acked",
        "payload": "{\"node_id\":\"node-00\",\"req_id\":\"e86791cd-535c-4f0d-b510-41e14b42a05a\",\"target\":\"load1\"}",
        "received_at": "2026-08-02T16:07:29.866Z"
      },
      {
        "id": "e9b1ecf9-324d-46ef-8f09-aa726860e0ed",
        "event": "control.command.sent",
        "payload": "{\"node_id\":\"node-00\",\"source\":\"schedule\",\"target\":\"load1\",\"type\":\"interval\",\"value\":\"1\"}",
        "received_at": "2026-08-02T16:07:27.868Z"
      },
      {
        "id": "8dfebc88-77b2-41a1-b22a-88fe22651044",
        "event": "control.command.acked",
        "payload": "{\"node_id\":\"node-00\",\"req_id\":\"519fb478-1b17-4f4a-b8e6-4e154f0e4a04\",\"target\":\"load1\"}",
        "received_at": "2026-08-02T16:05:34.558Z"
      },
      {
        "id": "87392574-def0-47b7-8780-5e2de009861f",
        "event": "control.command.sent",
        "payload": "{\"node_id\":\"node-00\",\"source\":\"schedule\",\"target\":\"load1\",\"type\":\"interval\",\"value\":\"0\"}",
        "received_at": "2026-08-02T16:05:34.346Z"
      },
      {
        "id": "29ff4684-a895-4f63-acc9-8c0af7ca6921",
        "event": "control.command.sent",
        "payload": "{\"node_id\":\"node-00\",\"source\":\"schedule\",\"target\":\"load1\",\"type\":\"interval\",\"value\":\"1\"}",
        "received_at": "2026-08-02T16:04:13.192Z"
      },
      {
        "id": "eefa2c57-1945-4d16-8017-e673dbebb6f7",
        "event": "control.command.acked",
        "payload": "{\"node_id\":\"node-00\",\"req_id\":\"1b622dad-a742-4fa2-803c-28f849ccb591\",\"target\":\"load1\"}",
        "received_at": "2026-08-02T16:02:14.361Z"
      },
      {
        "id": "e03bbd46-9a3b-4918-95c7-eba8a9f19d89",
        "event": "control.command.sent",
        "payload": "{\"node_id\":\"node-00\",\"source\":\"schedule\",\"target\":\"load1\",\"type\":\"interval\",\"value\":\"0\"}",
        "received_at": "2026-08-02T16:02:13.999Z"
      },
      {
        "id": "e562130a-f83b-4310-a4aa-93e1a275fab4",
        "event": "control.command.acked",
        "payload": "{\"node_id\":\"node-00\",\"req_id\":\"d65050b4-e644-422f-bd62-3fba2392bf11\",\"target\":\"load1\"}",
        "received_at": "2026-08-02T16:01:17.871Z"
      },
      {
        "id": "4ed977f1-7c94-4078-9b26-0635fed1fdd3",
        "event": "control.command.sent",
        "payload": "{\"node_id\":\"node-00\",\"source\":\"schedule\",\"target\":\"load1\",\"type\":\"interval\",\"value\":\"1\"}",
        "received_at": "2026-08-02T16:01:17.204Z"
      },
      {
        "id": "e6341de7-137c-489e-ab03-f810be794fe5",
        "event": "control.command.acked",
        "payload": "{\"node_id\":\"node-00\",\"req_id\":\"f65fd247-dbfe-4108-929d-fc787fbf85ed\",\"target\":\"load1\"}",
        "received_at": "2026-08-02T15:59:24.17Z"
      },
      {
        "id": "d200c428-7fc0-4567-a527-def9c8d9c48c",
        "event": "control.command.sent",
        "payload": "{\"node_id\":\"node-00\",\"source\":\"schedule\",\"target\":\"load1\",\"type\":\"interval\",\"value\":\"0\"}",
        "received_at": "2026-08-02T15:59:23.692Z"
      },
      {
        "id": "bcebfe33-b904-4a8a-ac56-d56cc351e73d",
        "event": "control.command.acked",
        "payload": "{\"node_id\":\"node-00\",\"req_id\":\"7be62a6d-c6c9-4851-9ae0-7cfb882bdcc7\",\"target\":\"load1\"}",
        "received_at": "2026-08-02T15:58:25.169Z"
      },
      {
        "id": "34ae5b0f-76c8-4e9f-ad7f-f040a2864d99",
        "event": "control.command.sent",
        "payload": "{\"node_id\":\"node-00\",\"source\":\"schedule\",\"target\":\"load1\",\"type\":\"interval\",\"value\":\"1\"}",
        "received_at": "2026-08-02T15:58:24.925Z"
      },
      {
        "id": "dcfb38d8-e3d2-4497-b744-56aced423006",
        "event": "control.command.sent",
        "payload": "{\"node_id\":\"node-00\",\"source\":\"schedule\",\"target\":\"load1\",\"type\":\"interval\",\"value\":\"0\"}",
        "received_at": "2026-08-02T15:56:27.657Z"
      },
      {
        "id": "a309c2eb-4cf3-4b0c-893d-d1665059a7ab",
        "event": "control.command.acked",
        "payload": "{\"node_id\":\"node-00\",\"req_id\":\"8b6ceaee-1596-455f-a157-a2236e66d544\",\"target\":\"load1\"}",
        "received_at": "2026-08-02T15:56:27.43Z"
      },
      {
        "id": "d340307c-74e7-439d-9e93-66764576ee7e",
        "event": "control.command.acked",
        "payload": "{\"node_id\":\"node-00\",\"req_id\":\"87554024-14e5-4f46-9d8a-716d504c187d\",\"target\":\"load1\"}",
        "received_at": "2026-08-02T15:55:31.192Z"
      },
      {
        "id": "4ad1980f-af6c-4209-bd25-8056c0179cb8",
        "event": "control.command.sent",
        "payload": "{\"node_id\":\"node-00\",\"source\":\"schedule\",\"target\":\"load1\",\"type\":\"interval\",\"value\":\"1\"}",
        "received_at": "2026-08-02T15:55:30.718Z"
      },
      {
        "id": "652333d1-9ea9-4918-8c31-0fb5e9f365cc",
        "event": "control.command.sent",
        "payload": "{\"node_id\":\"node-00\",\"source\":\"schedule\",\"target\":\"load1\",\"type\":\"interval\",\"value\":\"0\"}",
        "received_at": "2026-08-02T15:53:35.953Z"
      },
      {
        "id": "39a0b65c-41bd-41b6-a3e8-21cd6a84aa3c",
        "event": "control.command.acked",
        "payload": "{\"node_id\":\"node-00\",\"req_id\":\"7b1a6a11-9289-418a-8c18-bba94ec2d6a3\",\"target\":\"load1\"}",
        "received_at": "2026-08-02T15:53:35.545Z"
      },
      {
        "id": "17bd0791-85a4-4ebe-adc0-5aa4d559d5d8",
        "event": "control.command.acked",
        "payload": "{\"node_id\":\"node-00\",\"req_id\":\"f65cbe0a-baa3-4e30-a211-f7ac571075f2\",\"target\":\"load1\"}",
        "received_at": "2026-08-02T15:52:39.124Z"
      },
      {
        "id": "3d5e0f05-f239-4dfe-b59a-061b7c3b951f",
        "event": "control.command.sent",
        "payload": "{\"node_id\":\"node-00\",\"source\":\"schedule\",\"target\":\"load1\",\"type\":\"interval\",\"value\":\"1\"}",
        "received_at": "2026-08-02T15:52:38.878Z"
      },
      {
        "id": "3b53f87e-ae2a-4617-b74d-d31005ee1b0a",
        "event": "control.command.acked",
        "payload": "{\"node_id\":\"node-00\",\"req_id\":\"453b9645-d82b-4c32-869a-cb48ab697ca3\",\"target\":\"load1\"}",
        "received_at": "2026-08-02T15:50:45.403Z"
      },
      {
        "id": "69c9f75f-41d8-4b53-8fbe-9d70940644ec",
        "event": "control.command.sent",
        "payload": "{\"node_id\":\"node-00\",\"source\":\"schedule\",\"target\":\"load1\",\"type\":\"interval\",\"value\":\"0\"}",
        "received_at": "2026-08-02T15:50:43.403Z"
      },
      {
        "id": "09825fbb-da8a-4e19-ab46-6632b66b11e7",
        "event": "auth.login",
        "payload": "{\"user_id\":\"ccbe3708-eb03-47df-83a2-e70e0d7900e8\",\"username\":\"admin\",\"ip\":\"172.17.0.1\"}",
        "received_at": "2026-08-02T15:50:23.536Z"
      },
      {
        "id": "58f5b82e-7fb8-4b73-befd-f816ab7d3bf7",
        "event": "control.command.acked",
        "payload": "{\"node_id\":\"node-00\",\"req_id\":\"78f92eed-7ff6-4f9b-bac0-1be830cf31e7\",\"target\":\"load1\"}",
        "received_at": "2026-08-02T15:49:46.88Z"
      },
      {
        "id": "cf39ec42-053b-40e4-8648-c4bb26f75e20",
        "event": "control.command.sent",
        "payload": "{\"node_id\":\"node-00\",\"source\":\"schedule\",\"target\":\"load1\",\"type\":\"interval\",\"value\":\"1\"}",
        "received_at": "2026-08-02T15:49:46.617Z"
      },
      {
        "id": "c9484e58-778e-4948-9d36-2e8e48567844",
        "event": "auth.login",
        "payload": "{\"user_id\":\"ccbe3708-eb03-47df-83a2-e70e0d7900e8\",\"username\":\"admin\",\"ip\":\"172.17.0.1\"}",
        "received_at": "2026-08-02T15:49:20.937Z"
      },
      {
        "id": "7f11508c-ee2a-48ab-aa6f-3e6095321c71",
        "event": "control.command.sent",
        "payload": "{\"node_id\":\"node-00\",\"source\":\"schedule\",\"target\":\"load1\",\"type\":\"interval\",\"value\":\"0\"}",
        "received_at": "2026-08-02T15:47:51.772Z"
      },
      {
        "id": "e52f9657-cf5f-4ce8-abbe-f2f49d5dc779",
        "event": "control.command.acked",
        "payload": "{\"node_id\":\"node-00\",\"req_id\":\"76f54bfc-e7e2-474d-a616-ae44d3d582de\",\"target\":\"load1\"}",
        "received_at": "2026-08-02T15:47:51.548Z"
      }
    ],
    "offset": 0,
    "total": 20817
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 200
- **Duration:** 0.0103s
- **Payload:**
```json
{
  "data": {
    "limit": 50,
    "logs": [
      {
        "id": "8adb242a-3de6-4838-9f3a-489e5ef84d9d",
        "event": "auth.login",
        "payload": "{\"user_id\":\"6a2bc2df-6bc1-4120-93cb-871bc2fbda32\",\"username\":\"testuser_1785687180\",\"ip\":\"172.17.0.1\"}",
        "received_at": "2026-08-02T16:13:02.059Z"
      },
      {
        "id": "e4ca9068-cd32-41c3-886e-4c816ce42770",
        "event": "auth.login",
        "payload": "{\"user_id\":\"ccbe3708-eb03-47df-83a2-e70e0d7900e8\",\"username\":\"admin\",\"ip\":\"172.17.0.1\"}",
        "received_at": "2026-08-02T16:13:01.49Z"
      },
      {
        "id": "09825fbb-da8a-4e19-ab46-6632b66b11e7",
        "event": "auth.login",
        "payload": "{\"user_id\":\"ccbe3708-eb03-47df-83a2-e70e0d7900e8\",\"username\":\"admin\",\"ip\":\"172.17.0.1\"}",
        "received_at": "2026-08-02T15:50:23.536Z"
      },
      {
        "id": "c9484e58-778e-4948-9d36-2e8e48567844",
        "event": "auth.login",
        "payload": "{\"user_id\":\"ccbe3708-eb03-47df-83a2-e70e0d7900e8\",\"username\":\"admin\",\"ip\":\"172.17.0.1\"}",
        "received_at": "2026-08-02T15:49:20.937Z"
      },
      {
        "id": "ba68fbd4-9b1b-46a8-b9e2-cd54f0a677d5",
        "event": "auth.login",
        "payload": "{\"user_id\":\"ccbe3708-eb03-47df-83a2-e70e0d7900e8\",\"username\":\"admin\",\"ip\":\"172.17.0.1\"}",
        "received_at": "2026-08-02T15:45:47.527Z"
      },
      {
        "id": "018566e4-00d4-40ca-8f6e-ede852296b7c",
        "event": "auth.login",
        "payload": "{\"user_id\":\"ccbe3708-eb03-47df-83a2-e70e0d7900e8\",\"username\":\"admin\",\"ip\":\"172.17.0.1\"}",
        "received_at": "2026-08-02T15:45:02.858Z"
      },
      {
        "id": "259d3105-029e-4899-abc0-491ae9ed448f",
        "event": "auth.login",
        "payload": "{\"user_id\":\"ccbe3708-eb03-47df-83a2-e70e0d7900e8\",\"username\":\"admin\",\"ip\":\"172.17.0.1\"}",
        "received_at": "2026-08-02T15:44:40.076Z"
      },
      {
        "id": "64421f42-03c5-41f3-b4b4-bf7da760bcbd",
        "event": "auth.login",
        "payload": "{\"user_id\":\"ccbe3708-eb03-47df-83a2-e70e0d7900e8\",\"username\":\"admin\",\"ip\":\"172.17.0.1\"}",
        "received_at": "2026-08-02T15:44:26.666Z"
      },
      {
        "id": "b2feed1b-dca0-43de-b258-4b0d2b2b6218",
        "event": "auth.login",
        "payload": "{\"user_id\":\"ccbe3708-eb03-47df-83a2-e70e0d7900e8\",\"username\":\"admin\",\"ip\":\"172.17.0.1\"}",
        "received_at": "2026-08-02T14:22:03.364Z"
      },
      {
        "id": "34d34843-0bc4-463f-8d3c-95159edc059d",
        "event": "auth.login",
        "payload": "{\"user_id\":\"ccbe3708-eb03-47df-83a2-e70e0d7900e8\",\"username\":\"admin\",\"ip\":\"172.17.0.1\"}",
        "received_at": "2026-08-02T14:20:35.938Z"
      },
      {
        "id": "0e3dd32e-cc1f-473e-9915-23ec7c660400",
        "event": "auth.login",
        "payload": "{\"user_id\":\"ccbe3708-eb03-47df-83a2-e70e0d7900e8\",\"username\":\"admin\",\"ip\":\"172.17.0.1\"}",
        "received_at": "2026-08-02T14:20:25.443Z"
      },
      {
        "id": "5ae8149d-40a4-498c-9790-9ad4a0c1301b",
        "event": "auth.login",
        "payload": "{\"user_id\":\"ccbe3708-eb03-47df-83a2-e70e0d7900e8\",\"username\":\"admin\",\"ip\":\"172.17.0.1\"}",
        "received_at": "2026-08-02T14:20:25.223Z"
      },
      {
        "id": "dc8c3509-f792-43f2-b391-eb1a674891e0",
        "event": "auth.login",
        "payload": "{\"user_id\":\"ccbe3708-eb03-47df-83a2-e70e0d7900e8\",\"username\":\"admin\",\"ip\":\"172.17.0.1\"}",
        "received_at": "2026-08-02T14:20:13.495Z"
      },
      {
        "id": "8b3a9439-3073-4235-9737-2d6aaf570c91",
        "event": "auth.login",
        "payload": "{\"user_id\":\"ccbe3708-eb03-47df-83a2-e70e0d7900e8\",\"username\":\"admin\",\"ip\":\"172.17.0.1\"}",
        "received_at": "2026-08-02T14:19:16.449Z"
      },
      {
        "id": "5ae2bc73-5fec-4efd-a4d0-d450ce02f488",
        "event": "auth.login",
        "payload": "{\"user_id\":\"ccbe3708-eb03-47df-83a2-e70e0d7900e8\",\"username\":\"admin\",\"ip\":\"172.17.0.1\"}",
        "received_at": "2026-08-02T14:04:00.897Z"
      },
      {
        "id": "2e08fcce-df19-4bf3-ac6e-eaeb8bd85ec5",
        "event": "auth.login",
        "payload": "{\"user_id\":\"ccbe3708-eb03-47df-83a2-e70e0d7900e8\",\"username\":\"admin\",\"ip\":\"172.17.0.1\"}",
        "received_at": "2026-08-02T14:03:44.277Z"
      },
      {
        "id": "1d67bc14-4d00-437f-9df9-2d0e0d58c234",
        "event": "auth.login",
        "payload": "{\"user_id\":\"ccbe3708-eb03-47df-83a2-e70e0d7900e8\",\"username\":\"admin\",\"ip\":\"172.17.0.1\"}",
        "received_at": "2026-08-02T14:01:50.354Z"
      },
      {
        "id": "68c96414-46e3-427f-a3fd-940b584eb5d8",
        "event": "auth.login",
        "payload": "{\"username\":\"admin\",\"ip\":\"172.17.0.1\",\"user_id\":\"ccbe3708-eb03-47df-83a2-e70e0d7900e8\"}",
        "received_at": "2026-08-02T14:01:03.599Z"
      },
      {
        "id": "f1d1e6d7-f27d-44ed-87e8-83a27066c64e",
        "event": "auth.login",
        "payload": "{\"user_id\":\"ccbe3708-eb03-47df-83a2-e70e0d7900e8\",\"username\":\"admin\",\"ip\":\"172.17.0.1, 172.17.0.40\"}",
        "received_at": "2026-07-31T20:14:59.891Z"
      },
      {
        "id": "2c145bcb-2701-469d-9ca4-597fd88071dd",
        "event": "auth.login.failed",
        "payload": "{\"identifier\":\"admin\",\"ip\":\"172.17.0.1, 172.17.0.40\"}",
        "received_at": "2026-07-31T20:14:56.608Z"
      },
      {
        "id": "e96379a4-63e6-4dbd-8ed0-9d3651f22c86",
        "event": "auth.login",
        "payload": "{\"user_id\":\"ccbe3708-eb03-47df-83a2-e70e0d7900e8\",\"username\":\"admin\",\"ip\":\"172.17.0.1\"}",
        "received_at": "2026-07-31T18:48:38.324Z"
      },
      {
        "id": "fe844119-b3c6-4edb-8a81-79e74eb4a7ee",
        "event": "auth.login",
        "payload": "{\"ip\":\"172.17.0.1\",\"user_id\":\"7d738226-b180-48df-97b1-1c6479eadc62\",\"username\":\"testuser_1785523701\"}",
        "received_at": "2026-07-31T18:48:24.804Z"
      },
      {
        "id": "f4fd8972-7770-4350-9005-825eb142708f",
        "event": "auth.login",
        "payload": "{\"username\":\"admin\",\"ip\":\"172.17.0.1\",\"user_id\":\"ccbe3708-eb03-47df-83a2-e70e0d7900e8\"}",
        "received_at": "2026-07-31T18:48:21.568Z"
      },
      {
        "id": "d1014aa5-536c-4be8-8d5f-23f98a474564",
        "event": "auth.login",
        "payload": "{\"user_id\":\"ccbe3708-eb03-47df-83a2-e70e0d7900e8\",\"username\":\"admin\",\"ip\":\"172.17.0.1\"}",
        "received_at": "2026-07-31T14:06:08.03Z"
      },
      {
        "id": "0358ceb3-1aec-4b77-9ebe-9be19feb135a",
        "event": "auth.login",
        "payload": "{\"username\":\"testuser_1785506751\",\"ip\":\"172.17.0.1\",\"user_id\":\"f50c32fd-4b43-40e4-b181-c679bf0935ed\"}",
        "received_at": "2026-07-31T14:05:53.191Z"
      },
      {
        "id": "b414e93c-5398-4e97-adf8-d5c53d1f1df4",
        "event": "auth.login",
        "payload": "{\"user_id\":\"ccbe3708-eb03-47df-83a2-e70e0d7900e8\",\"username\":\"admin\",\"ip\":\"172.17.0.1\"}",
        "received_at": "2026-07-31T14:05:48.365Z"
      },
      {
        "id": "aae866d1-09af-4877-8f82-ea5c42c980a7",
        "event": "auth.login.failed",
        "payload": "{\"identifier\":\"admin\",\"ip\":\"172.17.0.1\"}",
        "received_at": "2026-07-31T13:44:13.63Z"
      },
      {
        "id": "95227125-551e-40c5-9ce0-5f8d43e1a303",
        "event": "auth.login",
        "payload": "{\"username\":\"admin\",\"ip\":\"172.17.0.1\",\"user_id\":\"ccbe3708-eb03-47df-83a2-e70e0d7900e8\"}",
        "received_at": "2026-07-31T08:18:41.689Z"
      },
      {
        "id": "7d8415b0-b13d-45ce-8be4-b3286088c62e",
        "event": "auth.login",
        "payload": "{\"user_id\":\"ccbe3708-eb03-47df-83a2-e70e0d7900e8\",\"username\":\"admin\",\"ip\":\"172.17.0.1\"}",
        "received_at": "2026-07-31T08:18:28.494Z"
      },
      {
        "id": "66ae1707-c7e5-403f-8213-83259fd217f0",
        "event": "auth.login",
        "payload": "{\"user_id\":\"ccbe3708-eb03-47df-83a2-e70e0d7900e8\",\"username\":\"admin\",\"ip\":\"172.17.0.1\"}",
        "received_at": "2026-07-31T08:18:15.77Z"
      },
      {
        "id": "b7fe5896-d95f-4d03-aa70-ed4e2b16e210",
        "event": "auth.login",
        "payload": "{\"user_id\":\"ccbe3708-eb03-47df-83a2-e70e0d7900e8\",\"username\":\"admin\",\"ip\":\"172.17.0.1\"}",
        "received_at": "2026-07-31T08:14:05.597Z"
      },
      {
        "id": "c2526419-0c96-4049-8eba-2ae13d04c23d",
        "event": "auth.login",
        "payload": "{\"user_id\":\"ccbe3708-eb03-47df-83a2-e70e0d7900e8\",\"username\":\"admin\",\"ip\":\"172.17.0.1\"}",
        "received_at": "2026-07-31T08:13:13.647Z"
      },
      {
        "id": "3562ce8f-5c30-4205-bbbe-45342cc1c2f6",
        "event": "auth.login",
        "payload": "{\"ip\":\"172.17.0.1\",\"user_id\":\"ccbe3708-eb03-47df-83a2-e70e0d7900e8\",\"username\":\"admin\"}",
        "received_at": "2026-07-31T08:10:33.189Z"
      },
      {
        "id": "5d90eef0-7cc6-459d-9b44-006b2e278cc6",
        "event": "auth.login",
        "payload": "{\"user_id\":\"443a58a3-695a-4b91-a0e2-723f605a3dd3\",\"username\":\"testuser_1785485405\",\"ip\":\"172.17.0.1\"}",
        "received_at": "2026-07-31T08:10:08.15Z"
      },
      {
        "id": "8dc3af5d-c19a-49b6-98dc-fff9aebab863",
        "event": "auth.login",
        "payload": "{\"user_id\":\"ccbe3708-eb03-47df-83a2-e70e0d7900e8\",\"username\":\"admin\",\"ip\":\"172.17.0.1\"}",
        "received_at": "2026-07-31T08:10:04.402Z"
      },
      {
        "id": "69915c44-b3e6-403b-a75f-ff5225c26826",
        "event": "auth.login",
        "payload": "{\"username\":\"admin\",\"ip\":\"172.17.0.1, 172.17.0.40\",\"user_id\":\"ccbe3708-eb03-47df-83a2-e70e0d7900e8\"}",
        "received_at": "2026-07-31T08:09:34.016Z"
      },
      {
        "id": "0db0a00a-4672-40ab-b77d-2ba953ca41a6",
        "event": "auth.login",
        "payload": "{\"user_id\":\"ccbe3708-eb03-47df-83a2-e70e0d7900e8\",\"username\":\"admin\",\"ip\":\"172.17.0.1\"}",
        "received_at": "2026-07-31T08:02:29.568Z"
      },
      {
        "id": "14b1b767-8f12-4afd-8254-9dc41c79ef05",
        "event": "auth.login",
        "payload": "{\"user_id\":\"ccd514bb-afb8-4dad-ae91-cdf96f5bc8b0\",\"username\":\"testuser_1785484932\",\"ip\":\"172.17.0.1\"}",
        "received_at": "2026-07-31T08:02:13.825Z"
      },
      {
        "id": "5c70a4d1-ec83-4df4-9557-efc60518ec0c",
        "event": "auth.login",
        "payload": "{\"user_id\":\"ccbe3708-eb03-47df-83a2-e70e0d7900e8\",\"username\":\"admin\",\"ip\":\"172.17.0.1\"}",
        "received_at": "2026-07-31T08:02:12.38Z"
      },
      {
        "id": "b6f30e25-25f7-43f2-a657-f3d0724abace",
        "event": "auth.login",
        "payload": "{\"user_id\":\"ccbe3708-eb03-47df-83a2-e70e0d7900e8\",\"username\":\"admin\",\"ip\":\"172.17.0.1\"}",
        "received_at": "2026-07-31T08:00:19.158Z"
      },
      {
        "id": "607f902b-16ce-4668-9692-12089498dfa5",
        "event": "auth.login",
        "payload": "{\"ip\":\"172.17.0.1\",\"user_id\":\"36046a46-69f3-4dc5-99f6-82987a55bb6b\",\"username\":\"testuser_1785484802\"}",
        "received_at": "2026-07-31T08:00:03.663Z"
      },
      {
        "id": "e85faf06-2b88-4718-8594-0e1b02d36229",
        "event": "auth.login",
        "payload": "{\"user_id\":\"ccbe3708-eb03-47df-83a2-e70e0d7900e8\",\"username\":\"admin\",\"ip\":\"172.17.0.1\"}",
        "received_at": "2026-07-31T08:00:01.712Z"
      },
      {
        "id": "8c993d1c-d7c2-4e96-8d79-5b3473465cec",
        "event": "auth.login",
        "payload": "{\"user_id\":\"ccbe3708-eb03-47df-83a2-e70e0d7900e8\",\"username\":\"admin\",\"ip\":\"172.17.0.1\"}",
        "received_at": "2026-07-31T07:58:18.558Z"
      },
      {
        "id": "f6a18d37-6570-4644-a39f-92d779063308",
        "event": "auth.login",
        "payload": "{\"user_id\":\"4e133bc2-e1d3-433b-abc9-c7995dad7ecb\",\"username\":\"testuser_1785484683\",\"ip\":\"172.17.0.1\"}",
        "received_at": "2026-07-31T07:58:04.894Z"
      },
      {
        "id": "6b6c674c-48ff-4aea-8220-4251c9366001",
        "event": "auth.login",
        "payload": "{\"username\":\"admin\",\"ip\":\"172.17.0.1\",\"user_id\":\"ccbe3708-eb03-47df-83a2-e70e0d7900e8\"}",
        "received_at": "2026-07-31T07:58:03.27Z"
      },
      {
        "id": "c92232d0-2a09-4a09-a7a0-f98e11fa01d4",
        "event": "auth.login",
        "payload": "{\"user_id\":\"ccbe3708-eb03-47df-83a2-e70e0d7900e8\",\"username\":\"admin\",\"ip\":\"172.17.0.1\"}",
        "received_at": "2026-07-31T07:56:15.83Z"
      },
      {
        "id": "7d6756dc-9af6-45bf-8005-96a8d60ced09",
        "event": "auth.login",
        "payload": "{\"username\":\"testuser_1785484548\",\"ip\":\"172.17.0.1\",\"user_id\":\"421715f3-5e89-42e0-b596-df3e6166e1dc\"}",
        "received_at": "2026-07-31T07:55:49.127Z"
      },
      {
        "id": "0bbf3617-905f-4274-b356-587285d5d78e",
        "event": "auth.login",
        "payload": "{\"user_id\":\"ccbe3708-eb03-47df-83a2-e70e0d7900e8\",\"username\":\"admin\",\"ip\":\"172.17.0.1\"}",
        "received_at": "2026-07-31T07:55:48.05Z"
      },
      {
        "id": "29193064-f7f4-465b-baf0-4cf7adf1cc5b",
        "event": "auth.login",
        "payload": "{\"user_id\":\"ccbe3708-eb03-47df-83a2-e70e0d7900e8\",\"username\":\"admin\",\"ip\":\"172.17.0.1\"}",
        "received_at": "2026-07-31T07:52:44.343Z"
      },
      {
        "id": "6be67b01-0c65-4f47-8b8d-9ef5d3361133",
        "event": "auth.login",
        "payload": "{\"ip\":\"172.17.0.1\",\"user_id\":\"b526b08e-2b1f-4ee6-be4c-6d9dd542210a\",\"username\":\"testuser_1785484349\"}",
        "received_at": "2026-07-31T07:52:29.797Z"
      }
    ],
    "offset": 0,
    "total": 122
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 200
- **Duration:** 0.0052s
- **Payload:**
```json
{
  "data": {
    "limit": 10,
    "logs": [
      {
        "id": "df1d20da-0e19-4256-a47c-6b18acbc01d1",
        "event": "control.schedule.deleted",
        "payload": "{\"schedule_id\":\"2157c990-f3e7-4782-a736-6510f9a531f5\"}",
        "received_at": "2026-08-02T16:13:08.397Z"
      },
      {
        "id": "ee63265d-4526-4338-9e76-8eb13e7aee6c",
        "event": "control.schedule.created",
        "payload": "{\"node_id\":\"node-00\",\"schedule_id\":\"2157c990-f3e7-4782-a736-6510f9a531f5\",\"type\":\"interval\"}",
        "received_at": "2026-08-02T16:13:08.04Z"
      },
      {
        "id": "37a23378-657a-45a7-bfe1-133c411b73b3",
        "event": "control.command.acked",
        "payload": "{\"node_id\":\"node-00\",\"req_id\":\"078bcc44-21ea-4ed3-81dd-7d22301cc0ee\",\"target\":\"valve\"}",
        "received_at": "2026-08-02T16:13:06.367Z"
      },
      {
        "id": "6aa38e9e-bd01-46b0-84f9-a48c4f17beef",
        "event": "control.command.sent",
        "payload": "{\"node_id\":\"node-00\",\"source\":\"manual\",\"target\":\"valve\",\"type\":\"set_state\",\"value\":\"1\"}",
        "received_at": "2026-08-02T16:13:06.042Z"
      },
      {
        "id": "79071ed3-8a27-4d43-89d4-51d4ee3b86f4",
        "event": "node.paired",
        "payload": "{\"module_id\":\"05609956-3dbd-4245-9012-95e4f19b3f52\",\"node_id\":\"node-00\"}",
        "received_at": "2026-08-02T16:13:05.652Z"
      },
      {
        "id": "4fbc0c08-d978-420a-a91d-82c637300c65",
        "event": "node.unpaired",
        "payload": "{\"node_id\":\"node-00\"}",
        "received_at": "2026-08-02T16:13:05.29Z"
      },
      {
        "id": "40e3787e-154d-42f4-ac35-ca30d5a550f9",
        "event": "module.deleted",
        "payload": "{\"module_id\":\"d289299c-ab62-41e5-90f9-47bcdb8ffb9d\"}",
        "received_at": "2026-08-02T16:13:03.988Z"
      },
      {
        "id": "c011786d-a102-4acf-97d8-f17e32618cd9",
        "event": "module.created",
        "payload": "{\"module_id\":\"d289299c-ab62-41e5-90f9-47bcdb8ffb9d\",\"name\":\"Test Greenhouse 1785687182\"}",
        "received_at": "2026-08-02T16:13:03.663Z"
      },
      {
        "id": "275d1bf1-c8e0-410a-ae5f-01b89b69d2a8",
        "event": "module.updated",
        "payload": "{\"module_id\":\"d289299c-ab62-41e5-90f9-47bcdb8ffb9d\"}",
        "received_at": "2026-08-02T16:13:03.349Z"
      },
      {
        "id": "dad8a946-89b0-4e39-9469-0e908149d81b",
        "event": "auth.account.deleted",
        "payload": "{\"user_id\":\"6a2bc2df-6bc1-4120-93cb-871bc2fbda32\",\"ip\":\"172.17.0.1\"}",
        "received_at": "2026-08-02T16:13:02.47Z"
      }
    ],
    "offset": 0,
    "total": 20817
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 200
- **Duration:** 0.0724s
- **Payload:**
```json
{
  "data": {
    "limit": 50,
    "logs": [],
    "offset": 0,
    "total": 0
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 200
- **Duration:** 0.009s
- **Payload:**
```json
{
  "data": {
    "limit": 50,
    "logs": [
      {
        "id": "0965c2e1-a3ba-4e5a-8a1a-e905f02dd400",
        "event": "alert.threshold.created",
        "payload": "{\"by\":\"ccbe3708-eb03-47df-83a2-e70e0d7900e8\",\"metric\":\"temperature\",\"node_id\":\"node-00\",\"severity\":\"warning\",\"threshold_id\":\"9c48c0e8-f9ec-4744-a667-a19d122fd3d6\"}",
        "received_at": "2026-08-02T16:13:08.707Z"
      },
      {
        "id": "df1d20da-0e19-4256-a47c-6b18acbc01d1",
        "event": "control.schedule.deleted",
        "payload": "{\"schedule_id\":\"2157c990-f3e7-4782-a736-6510f9a531f5\"}",
        "received_at": "2026-08-02T16:13:08.397Z"
      },
      {
        "id": "ee63265d-4526-4338-9e76-8eb13e7aee6c",
        "event": "control.schedule.created",
        "payload": "{\"node_id\":\"node-00\",\"schedule_id\":\"2157c990-f3e7-4782-a736-6510f9a531f5\",\"type\":\"interval\"}",
        "received_at": "2026-08-02T16:13:08.04Z"
      },
      {
        "id": "37a23378-657a-45a7-bfe1-133c411b73b3",
        "event": "control.command.acked",
        "payload": "{\"node_id\":\"node-00\",\"req_id\":\"078bcc44-21ea-4ed3-81dd-7d22301cc0ee\",\"target\":\"valve\"}",
        "received_at": "2026-08-02T16:13:06.367Z"
      },
      {
        "id": "6aa38e9e-bd01-46b0-84f9-a48c4f17beef",
        "event": "control.command.sent",
        "payload": "{\"node_id\":\"node-00\",\"source\":\"manual\",\"target\":\"valve\",\"type\":\"set_state\",\"value\":\"1\"}",
        "received_at": "2026-08-02T16:13:06.042Z"
      },
      {
        "id": "79071ed3-8a27-4d43-89d4-51d4ee3b86f4",
        "event": "node.paired",
        "payload": "{\"module_id\":\"05609956-3dbd-4245-9012-95e4f19b3f52\",\"node_id\":\"node-00\"}",
        "received_at": "2026-08-02T16:13:05.652Z"
      },
      {
        "id": "4fbc0c08-d978-420a-a91d-82c637300c65",
        "event": "node.unpaired",
        "payload": "{\"node_id\":\"node-00\"}",
        "received_at": "2026-08-02T16:13:05.29Z"
      },
      {
        "id": "40e3787e-154d-42f4-ac35-ca30d5a550f9",
        "event": "module.deleted",
        "payload": "{\"module_id\":\"d289299c-ab62-41e5-90f9-47bcdb8ffb9d\"}",
        "received_at": "2026-08-02T16:13:03.988Z"
      },
      {
        "id": "c011786d-a102-4acf-97d8-f17e32618cd9",
        "event": "module.created",
        "payload": "{\"module_id\":\"d289299c-ab62-41e5-90f9-47bcdb8ffb9d\",\"name\":\"Test Greenhouse 1785687182\"}",
        "received_at": "2026-08-02T16:13:03.663Z"
      },
      {
        "id": "275d1bf1-c8e0-410a-ae5f-01b89b69d2a8",
        "event": "module.updated",
        "payload": "{\"module_id\":\"d289299c-ab62-41e5-90f9-47bcdb8ffb9d\"}",
        "received_at": "2026-08-02T16:13:03.349Z"
      },
      {
        "id": "dad8a946-89b0-4e39-9469-0e908149d81b",
        "event": "auth.account.deleted",
        "payload": "{\"user_id\":\"6a2bc2df-6bc1-4120-93cb-871bc2fbda32\",\"ip\":\"172.17.0.1\"}",
        "received_at": "2026-08-02T16:13:02.47Z"
      },
      {
        "id": "8adb242a-3de6-4838-9f3a-489e5ef84d9d",
        "event": "auth.login",
        "payload": "{\"user_id\":\"6a2bc2df-6bc1-4120-93cb-871bc2fbda32\",\"username\":\"testuser_1785687180\",\"ip\":\"172.17.0.1\"}",
        "received_at": "2026-08-02T16:13:02.059Z"
      },
      {
        "id": "e80508ff-e26b-4f9c-a4a0-e1190be3cf75",
        "event": "auth.logout",
        "payload": "{\"user_id\":\"ccbe3708-eb03-47df-83a2-e70e0d7900e8\",\"ip\":\"172.17.0.1\"}",
        "received_at": "2026-08-02T16:13:01.857Z"
      },
      {
        "id": "ad15d673-5efc-4b67-b7f2-aa6654fc981f",
        "event": "auth.register",
        "payload": "{\"user_id\":\"6a2bc2df-6bc1-4120-93cb-871bc2fbda32\",\"username\":\"testuser_1785687180\",\"ip\":\"172.17.0.1\"}",
        "received_at": "2026-08-02T16:13:01.655Z"
      },
      {
        "id": "e4ca9068-cd32-41c3-886e-4c816ce42770",
        "event": "auth.login",
        "payload": "{\"user_id\":\"ccbe3708-eb03-47df-83a2-e70e0d7900e8\",\"username\":\"admin\",\"ip\":\"172.17.0.1\"}",
        "received_at": "2026-08-02T16:13:01.49Z"
      },
      {
        "id": "2bfce773-8652-446b-a05d-4706317234a4",
        "event": "auth.refresh",
        "payload": "{\"user_id\":\"ccbe3708-eb03-47df-83a2-e70e0d7900e8\",\"ip\":\"172.17.0.1\"}",
        "received_at": "2026-08-02T16:13:00.928Z"
      },
      {
        "id": "2449087e-7a50-4a4f-9465-6b0b9de82826",
        "event": "control.command.acked",
        "payload": "{\"node_id\":\"node-00\",\"req_id\":\"9341f895-f124-4450-9070-506839dcfe2d\",\"target\":\"load1\"}",
        "received_at": "2026-08-02T16:11:20.923Z"
      },
      {
        "id": "661e44ab-d208-41ef-a726-c31675b7d0c8",
        "event": "control.command.sent",
        "payload": "{\"node_id\":\"node-00\",\"source\":\"schedule\",\"target\":\"load1\",\"type\":\"interval\",\"value\":\"0\"}",
        "received_at": "2026-08-02T16:11:20.536Z"
      },
      {
        "id": "6cfe5464-afc0-4128-9c80-234226c9f657",
        "event": "control.command.sent",
        "payload": "{\"node_id\":\"node-00\",\"source\":\"schedule\",\"target\":\"load1\",\"type\":\"interval\",\"value\":\"1\"}",
        "received_at": "2026-08-02T16:10:24.029Z"
      },
      {
        "id": "af74e57b-f0cc-4464-9485-ba5dd38800da",
        "event": "control.command.acked",
        "payload": "{\"node_id\":\"node-00\",\"req_id\":\"c06f98e2-452d-4b0f-9746-ecad408d47b8\",\"target\":\"load1\"}",
        "received_at": "2026-08-02T16:10:23.776Z"
      },
      {
        "id": "ae9b5859-d9cc-424a-b1b9-7c4c96c22f0a",
        "event": "control.command.sent",
        "payload": "{\"node_id\":\"node-00\",\"source\":\"schedule\",\"target\":\"load1\",\"type\":\"interval\",\"value\":\"0\"}",
        "received_at": "2026-08-02T16:08:26.868Z"
      },
      {
        "id": "575b69a2-984d-484f-b6b2-e9c80654e522",
        "event": "control.command.acked",
        "payload": "{\"node_id\":\"node-00\",\"req_id\":\"8ee200ce-e0f3-459a-9793-2ddd602113fe\",\"target\":\"load1\"}",
        "received_at": "2026-08-02T16:08:26.638Z"
      },
      {
        "id": "a1022c3d-b814-4129-aebf-dd9513adaa10",
        "event": "control.command.acked",
        "payload": "{\"node_id\":\"node-00\",\"req_id\":\"e86791cd-535c-4f0d-b510-41e14b42a05a\",\"target\":\"load1\"}",
        "received_at": "2026-08-02T16:07:29.866Z"
      },
      {
        "id": "e9b1ecf9-324d-46ef-8f09-aa726860e0ed",
        "event": "control.command.sent",
        "payload": "{\"node_id\":\"node-00\",\"source\":\"schedule\",\"target\":\"load1\",\"type\":\"interval\",\"value\":\"1\"}",
        "received_at": "2026-08-02T16:07:27.868Z"
      },
      {
        "id": "8dfebc88-77b2-41a1-b22a-88fe22651044",
        "event": "control.command.acked",
        "payload": "{\"node_id\":\"node-00\",\"req_id\":\"519fb478-1b17-4f4a-b8e6-4e154f0e4a04\",\"target\":\"load1\"}",
        "received_at": "2026-08-02T16:05:34.558Z"
      },
      {
        "id": "87392574-def0-47b7-8780-5e2de009861f",
        "event": "control.command.sent",
        "payload": "{\"node_id\":\"node-00\",\"source\":\"schedule\",\"target\":\"load1\",\"type\":\"interval\",\"value\":\"0\"}",
        "received_at": "2026-08-02T16:05:34.346Z"
      },
      {
        "id": "29ff4684-a895-4f63-acc9-8c0af7ca6921",
        "event": "control.command.sent",
        "payload": "{\"node_id\":\"node-00\",\"source\":\"schedule\",\"target\":\"load1\",\"type\":\"interval\",\"value\":\"1\"}",
        "received_at": "2026-08-02T16:04:13.192Z"
      },
      {
        "id": "eefa2c57-1945-4d16-8017-e673dbebb6f7",
        "event": "control.command.acked",
        "payload": "{\"node_id\":\"node-00\",\"req_id\":\"1b622dad-a742-4fa2-803c-28f849ccb591\",\"target\":\"load1\"}",
        "received_at": "2026-08-02T16:02:14.361Z"
      },
      {
        "id": "e03bbd46-9a3b-4918-95c7-eba8a9f19d89",
        "event": "control.command.sent",
        "payload": "{\"node_id\":\"node-00\",\"source\":\"schedule\",\"target\":\"load1\",\"type\":\"interval\",\"value\":\"0\"}",
        "received_at": "2026-08-02T16:02:13.999Z"
      },
      {
        "id": "e562130a-f83b-4310-a4aa-93e1a275fab4",
        "event": "control.command.acked",
        "payload": "{\"node_id\":\"node-00\",\"req_id\":\"d65050b4-e644-422f-bd62-3fba2392bf11\",\"target\":\"load1\"}",
        "received_at": "2026-08-02T16:01:17.871Z"
      },
      {
        "id": "4ed977f1-7c94-4078-9b26-0635fed1fdd3",
        "event": "control.command.sent",
        "payload": "{\"node_id\":\"node-00\",\"source\":\"schedule\",\"target\":\"load1\",\"type\":\"interval\",\"value\":\"1\"}",
        "received_at": "2026-08-02T16:01:17.204Z"
      },
      {
        "id": "e6341de7-137c-489e-ab03-f810be794fe5",
        "event": "control.command.acked",
        "payload": "{\"node_id\":\"node-00\",\"req_id\":\"f65fd247-dbfe-4108-929d-fc787fbf85ed\",\"target\":\"load1\"}",
        "received_at": "2026-08-02T15:59:24.17Z"
      },
      {
        "id": "d200c428-7fc0-4567-a527-def9c8d9c48c",
        "event": "control.command.sent",
        "payload": "{\"node_id\":\"node-00\",\"source\":\"schedule\",\"target\":\"load1\",\"type\":\"interval\",\"value\":\"0\"}",
        "received_at": "2026-08-02T15:59:23.692Z"
      },
      {
        "id": "bcebfe33-b904-4a8a-ac56-d56cc351e73d",
        "event": "control.command.acked",
        "payload": "{\"node_id\":\"node-00\",\"req_id\":\"7be62a6d-c6c9-4851-9ae0-7cfb882bdcc7\",\"target\":\"load1\"}",
        "received_at": "2026-08-02T15:58:25.169Z"
      },
      {
        "id": "34ae5b0f-76c8-4e9f-ad7f-f040a2864d99",
        "event": "control.command.sent",
        "payload": "{\"node_id\":\"node-00\",\"source\":\"schedule\",\"target\":\"load1\",\"type\":\"interval\",\"value\":\"1\"}",
        "received_at": "2026-08-02T15:58:24.925Z"
      },
      {
        "id": "dcfb38d8-e3d2-4497-b744-56aced423006",
        "event": "control.command.sent",
        "payload": "{\"node_id\":\"node-00\",\"source\":\"schedule\",\"target\":\"load1\",\"type\":\"interval\",\"value\":\"0\"}",
        "received_at": "2026-08-02T15:56:27.657Z"
      },
      {
        "id": "a309c2eb-4cf3-4b0c-893d-d1665059a7ab",
        "event": "control.command.acked",
        "payload": "{\"node_id\":\"node-00\",\"req_id\":\"8b6ceaee-1596-455f-a157-a2236e66d544\",\"target\":\"load1\"}",
        "received_at": "2026-08-02T15:56:27.43Z"
      },
      {
        "id": "d340307c-74e7-439d-9e93-66764576ee7e",
        "event": "control.command.acked",
        "payload": "{\"node_id\":\"node-00\",\"req_id\":\"87554024-14e5-4f46-9d8a-716d504c187d\",\"target\":\"load1\"}",
        "received_at": "2026-08-02T15:55:31.192Z"
      },
      {
        "id": "4ad1980f-af6c-4209-bd25-8056c0179cb8",
        "event": "control.command.sent",
        "payload": "{\"node_id\":\"node-00\",\"source\":\"schedule\",\"target\":\"load1\",\"type\":\"interval\",\"value\":\"1\"}",
        "received_at": "2026-08-02T15:55:30.718Z"
      },
      {
        "id": "652333d1-9ea9-4918-8c31-0fb5e9f365cc",
        "event": "control.command.sent",
        "payload": "{\"node_id\":\"node-00\",\"source\":\"schedule\",\"target\":\"load1\",\"type\":\"interval\",\"value\":\"0\"}",
        "received_at": "2026-08-02T15:53:35.953Z"
      },
      {
        "id": "39a0b65c-41bd-41b6-a3e8-21cd6a84aa3c",
        "event": "control.command.acked",
        "payload": "{\"node_id\":\"node-00\",\"req_id\":\"7b1a6a11-9289-418a-8c18-bba94ec2d6a3\",\"target\":\"load1\"}",
        "received_at": "2026-08-02T15:53:35.545Z"
      },
      {
        "id": "17bd0791-85a4-4ebe-adc0-5aa4d559d5d8",
        "event": "control.command.acked",
        "payload": "{\"node_id\":\"node-00\",\"req_id\":\"f65cbe0a-baa3-4e30-a211-f7ac571075f2\",\"target\":\"load1\"}",
        "received_at": "2026-08-02T15:52:39.124Z"
      },
      {
        "id": "3d5e0f05-f239-4dfe-b59a-061b7c3b951f",
        "event": "control.command.sent",
        "payload": "{\"node_id\":\"node-00\",\"source\":\"schedule\",\"target\":\"load1\",\"type\":\"interval\",\"value\":\"1\"}",
        "received_at": "2026-08-02T15:52:38.878Z"
      },
      {
        "id": "3b53f87e-ae2a-4617-b74d-d31005ee1b0a",
        "event": "control.command.acked",
        "payload": "{\"node_id\":\"node-00\",\"req_id\":\"453b9645-d82b-4c32-869a-cb48ab697ca3\",\"target\":\"load1\"}",
        "received_at": "2026-08-02T15:50:45.403Z"
      },
      {
        "id": "69c9f75f-41d8-4b53-8fbe-9d70940644ec",
        "event": "control.command.sent",
        "payload": "{\"node_id\":\"node-00\",\"source\":\"schedule\",\"target\":\"load1\",\"type\":\"interval\",\"value\":\"0\"}",
        "received_at": "2026-08-02T15:50:43.403Z"
      },
      {
        "id": "09825fbb-da8a-4e19-ab46-6632b66b11e7",
        "event": "auth.login",
        "payload": "{\"user_id\":\"ccbe3708-eb03-47df-83a2-e70e0d7900e8\",\"username\":\"admin\",\"ip\":\"172.17.0.1\"}",
        "received_at": "2026-08-02T15:50:23.536Z"
      },
      {
        "id": "58f5b82e-7fb8-4b73-befd-f816ab7d3bf7",
        "event": "control.command.acked",
        "payload": "{\"node_id\":\"node-00\",\"req_id\":\"78f92eed-7ff6-4f9b-bac0-1be830cf31e7\",\"target\":\"load1\"}",
        "received_at": "2026-08-02T15:49:46.88Z"
      },
      {
        "id": "cf39ec42-053b-40e4-8648-c4bb26f75e20",
        "event": "control.command.sent",
        "payload": "{\"node_id\":\"node-00\",\"source\":\"schedule\",\"target\":\"load1\",\"type\":\"interval\",\"value\":\"1\"}",
        "received_at": "2026-08-02T15:49:46.617Z"
      },
      {
        "id": "c9484e58-778e-4948-9d36-2e8e48567844",
        "event": "auth.login",
        "payload": "{\"user_id\":\"ccbe3708-eb03-47df-83a2-e70e0d7900e8\",\"username\":\"admin\",\"ip\":\"172.17.0.1\"}",
        "received_at": "2026-08-02T15:49:20.937Z"
      },
      {
        "id": "7f11508c-ee2a-48ab-aa6f-3e6095321c71",
        "event": "control.command.sent",
        "payload": "{\"node_id\":\"node-00\",\"source\":\"schedule\",\"target\":\"load1\",\"type\":\"interval\",\"value\":\"0\"}",
        "received_at": "2026-08-02T15:47:51.772Z"
      }
    ],
    "offset": 0,
    "total": 20818
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 200
- **Duration:** 0.7801s
- **Payload:**
```json
{
  "data": {
    "limit": 50,
    "logs": [
      {
        "id": "fd2b586e-e346-4d95-bb63-5c13f0473fc1",
        "channel": "telegram",
        "target": "1020639196",
        "subject": "SmartFarm Test Notification",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "ccbe3708-eb03-47df-83a2-e70e0d7900e8",
        "created_at": "2026-07-31T18:48:33.26Z"
      },
      {
        "id": "cfe4ab13-317b-4b45-b45f-9fcedec0c222",
        "channel": "telegram",
        "target": "1020639196",
        "subject": "SmartFarm Test Notification",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "ccbe3708-eb03-47df-83a2-e70e0d7900e8",
        "created_at": "2026-07-31T14:06:01.552Z"
      },
      {
        "id": "005e9778-f808-4d34-8019-7ec60b5a9ad4",
        "channel": "telegram",
        "target": "1020639196",
        "subject": "SmartFarm Test Notification",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "ccbe3708-eb03-47df-83a2-e70e0d7900e8",
        "created_at": "2026-07-31T08:10:26.149Z"
      },
      {
        "id": "0249e272-1521-4b28-b93d-214ba1f54791",
        "channel": "telegram",
        "target": "1020639196",
        "subject": "SmartFarm Test Notification",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "ccbe3708-eb03-47df-83a2-e70e0d7900e8",
        "created_at": "2026-07-31T08:02:23.447Z"
      },
      {
        "id": "6615bc2e-4a13-40a0-bb47-ca367ba52b17",
        "channel": "telegram",
        "target": "1020639196",
        "subject": "SmartFarm Test Notification",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "ccbe3708-eb03-47df-83a2-e70e0d7900e8",
        "created_at": "2026-07-31T08:00:13.736Z"
      },
      {
        "id": "f14b704b-e6cd-4529-80cb-c833e4cd3ed3",
        "channel": "telegram",
        "target": "1020639196",
        "subject": "SmartFarm Test Notification",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "ccbe3708-eb03-47df-83a2-e70e0d7900e8",
        "created_at": "2026-07-31T07:58:12.022Z"
      },
      {
        "id": "04521229-bb79-426c-9507-392b995e73f2",
        "channel": "telegram",
        "target": "1020639196",
        "subject": "SmartFarm Test Notification",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "ccbe3708-eb03-47df-83a2-e70e0d7900e8",
        "created_at": "2026-07-31T07:56:05.684Z"
      },
      {
        "id": "2e863f2c-9077-4dc3-8aec-911be511caae",
        "channel": "telegram",
        "target": "1020639196",
        "subject": "SmartFarm Test Notification",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "ccbe3708-eb03-47df-83a2-e70e0d7900e8",
        "created_at": "2026-07-31T07:52:39.225Z"
      },
      {
        "id": "50be4b13-b232-482b-a942-4f47acb8a27d",
        "channel": "telegram",
        "target": "1020639196",
        "subject": "SmartFarm Test Notification",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "ccbe3708-eb03-47df-83a2-e70e0d7900e8",
        "created_at": "2026-07-31T07:49:31.997Z"
      },
      {
        "id": "f92e4c44-9ddd-41cb-8060-a38276de1f07",
        "channel": "telegram",
        "target": "1020639196",
        "subject": "SmartFarm Test Notification",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "ccbe3708-eb03-47df-83a2-e70e0d7900e8",
        "created_at": "2026-07-31T07:32:46.964Z"
      },
      {
        "id": "c9b18dc8-ce48-4067-af35-29fae54fd60d",
        "channel": "telegram",
        "target": "1020639196",
        "subject": "SmartFarm Test Notification",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "ccbe3708-eb03-47df-83a2-e70e0d7900e8",
        "created_at": "2026-07-31T07:29:51.27Z"
      },
      {
        "id": "d0267cad-32c9-4007-b51a-3e04c888b715",
        "channel": "telegram",
        "target": "1020639196",
        "subject": "SmartFarm Test Notification",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "ccbe3708-eb03-47df-83a2-e70e0d7900e8",
        "created_at": "2026-07-31T07:26:15.385Z"
      },
      {
        "id": "6003ed2f-09a5-4095-850a-99866450bbd7",
        "channel": "telegram",
        "target": "1020639196",
        "subject": "SmartFarm Test Notification",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "ccbe3708-eb03-47df-83a2-e70e0d7900e8",
        "created_at": "2026-07-31T06:57:17.037Z"
      },
      {
        "id": "20b52780-ee98-4557-a01a-a78d55560d9e",
        "channel": "telegram",
        "target": "1020639196",
        "subject": "SmartFarm Test Notification",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "ccbe3708-eb03-47df-83a2-e70e0d7900e8",
        "created_at": "2026-07-31T06:54:42.508Z"
      },
      {
        "id": "dca82e42-1222-4593-9ada-814b69cb2716",
        "channel": "telegram",
        "target": "1020639196",
        "subject": "SmartFarm Test Notification",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "ccbe3708-eb03-47df-83a2-e70e0d7900e8",
        "created_at": "2026-07-31T06:47:50.382Z"
      },
      {
        "id": "d8068f91-48c4-4901-998d-c5aa9e800218",
        "channel": "telegram",
        "target": "1020639196",
        "subject": "SmartFarm Test Notification",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "ccbe3708-eb03-47df-83a2-e70e0d7900e8",
        "created_at": "2026-07-31T05:47:00.423Z"
      },
      {
        "id": "f4fe83dd-1b90-4a38-b855-cbfa048afb26",
        "channel": "telegram",
        "target": "1020639196",
        "subject": "SmartFarm Test Notification",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "ccbe3708-eb03-47df-83a2-e70e0d7900e8",
        "created_at": "2026-07-31T04:24:28.346Z"
      },
      {
        "id": "3665d3e0-a03d-4694-8e2c-d050cd2f208b",
        "channel": "telegram",
        "target": "1020639196",
        "subject": "SmartFarm Test Notification",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "ccbe3708-eb03-47df-83a2-e70e0d7900e8",
        "created_at": "2026-07-31T04:23:06.058Z"
      },
      {
        "id": "27ede603-c9bc-4e50-bcc6-cfaf7a03b597",
        "channel": "telegram",
        "target": "1020639196",
        "subject": "SmartFarm Test Notification",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "ccbe3708-eb03-47df-83a2-e70e0d7900e8",
        "created_at": "2026-07-31T04:12:10.195Z"
      },
      {
        "id": "fdacb2cf-e702-4a3b-a062-3628b1d56990",
        "channel": "telegram",
        "target": "1020639196",
        "subject": "SmartFarm Test Notification",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "ccbe3708-eb03-47df-83a2-e70e0d7900e8",
        "created_at": "2026-07-31T03:55:00.429Z"
      },
      {
        "id": "26c44d36-bec1-4d77-b65a-2c344b73cf8c",
        "channel": "telegram",
        "target": "1020639196",
        "subject": "SmartFarm Test Notification",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "ccbe3708-eb03-47df-83a2-e70e0d7900e8",
        "created_at": "2026-07-31T02:49:16.591Z"
      },
      {
        "id": "787eb0c2-670a-4290-9c74-81db1e9b1927",
        "channel": "telegram",
        "target": "1020639196",
        "subject": "SmartFarm Test Notification",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "ccbe3708-eb03-47df-83a2-e70e0d7900e8",
        "created_at": "2026-07-31T02:47:30.623Z"
      },
      {
        "id": "e62f1a8a-d736-40ff-becc-ead2914fdc09",
        "channel": "telegram",
        "target": "1020639196",
        "subject": "SmartFarm Test Notification",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "ccbe3708-eb03-47df-83a2-e70e0d7900e8",
        "created_at": "2026-07-31T02:40:19.474Z"
      },
      {
        "id": "b5768af3-3528-49f4-810d-f8caefa62ecf",
        "channel": "telegram",
        "target": "1020639196",
        "subject": "SmartFarm Test Notification",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "ccbe3708-eb03-47df-83a2-e70e0d7900e8",
        "created_at": "2026-07-31T02:40:19.157Z"
      },
      {
        "id": "7d6ded15-5122-44ef-a600-692a11bda399",
        "channel": "telegram",
        "target": "1020639196",
        "subject": "SmartFarm Test Notification",
        "status": "retrying",
        "attempts": 2,
        "error": "http request failed",
        "alert_id": "",
        "user_id": "ccbe3708-eb03-47df-83a2-e70e0d7900e8",
        "created_at": "2026-07-30T17:46:31.95Z"
      }
    ],
    "offset": 0,
    "total": 25
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 200
- **Duration:** 0.0026s
- **Payload:**
```json
{
  "data": {
    "telegram": {
      "enabled": true,
      "target": "1020639196"
    },
    "email": {
      "enabled": true,
      "target": "alifmuhammadrizky01@gmail.com"
    },
    "push": {
      "enabled": false,
      "target": ""
    }
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** POST
- **Status:** 202
- **Duration:** 0.642s
- **Payload:**
```json
{
  "data": {
    "enqueued": 1,
    "message": "test notification(s) queued for delivery"
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** PUT
- **Status:** 400
- **Duration:** 0.0028s
- **Payload:**
```json
{
  "error": {
    "code": "BAD_REQUEST",
    "message": "invalid telegram chat id (must be numeric, e.g. 123456789 or -1001234567890)"
  },
  "success": false
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 200
- **Duration:** 0.0042s
- **Payload:**
```json
{
  "data": {
    "limit": 10,
    "logs": [
      {
        "id": "b773962e-1c2d-4480-8222-9fd1908bc083",
        "channel": "telegram",
        "target": "1020639196",
        "subject": "SmartFarm Test Notification",
        "status": "queued",
        "attempts": 0,
        "error": "",
        "alert_id": "",
        "user_id": "ccbe3708-eb03-47df-83a2-e70e0d7900e8",
        "created_at": "2026-08-02T16:13:09.546Z"
      },
      {
        "id": "fd2b586e-e346-4d95-bb63-5c13f0473fc1",
        "channel": "telegram",
        "target": "1020639196",
        "subject": "SmartFarm Test Notification",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "ccbe3708-eb03-47df-83a2-e70e0d7900e8",
        "created_at": "2026-07-31T18:48:33.26Z"
      },
      {
        "id": "cfe4ab13-317b-4b45-b45f-9fcedec0c222",
        "channel": "telegram",
        "target": "1020639196",
        "subject": "SmartFarm Test Notification",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "ccbe3708-eb03-47df-83a2-e70e0d7900e8",
        "created_at": "2026-07-31T14:06:01.552Z"
      },
      {
        "id": "005e9778-f808-4d34-8019-7ec60b5a9ad4",
        "channel": "telegram",
        "target": "1020639196",
        "subject": "SmartFarm Test Notification",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "ccbe3708-eb03-47df-83a2-e70e0d7900e8",
        "created_at": "2026-07-31T08:10:26.149Z"
      },
      {
        "id": "0249e272-1521-4b28-b93d-214ba1f54791",
        "channel": "telegram",
        "target": "1020639196",
        "subject": "SmartFarm Test Notification",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "ccbe3708-eb03-47df-83a2-e70e0d7900e8",
        "created_at": "2026-07-31T08:02:23.447Z"
      },
      {
        "id": "6615bc2e-4a13-40a0-bb47-ca367ba52b17",
        "channel": "telegram",
        "target": "1020639196",
        "subject": "SmartFarm Test Notification",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "ccbe3708-eb03-47df-83a2-e70e0d7900e8",
        "created_at": "2026-07-31T08:00:13.736Z"
      },
      {
        "id": "f14b704b-e6cd-4529-80cb-c833e4cd3ed3",
        "channel": "telegram",
        "target": "1020639196",
        "subject": "SmartFarm Test Notification",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "ccbe3708-eb03-47df-83a2-e70e0d7900e8",
        "created_at": "2026-07-31T07:58:12.022Z"
      },
      {
        "id": "04521229-bb79-426c-9507-392b995e73f2",
        "channel": "telegram",
        "target": "1020639196",
        "subject": "SmartFarm Test Notification",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "ccbe3708-eb03-47df-83a2-e70e0d7900e8",
        "created_at": "2026-07-31T07:56:05.684Z"
      },
      {
        "id": "2e863f2c-9077-4dc3-8aec-911be511caae",
        "channel": "telegram",
        "target": "1020639196",
        "subject": "SmartFarm Test Notification",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "ccbe3708-eb03-47df-83a2-e70e0d7900e8",
        "created_at": "2026-07-31T07:52:39.225Z"
      },
      {
        "id": "50be4b13-b232-482b-a942-4f47acb8a27d",
        "channel": "telegram",
        "target": "1020639196",
        "subject": "SmartFarm Test Notification",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "ccbe3708-eb03-47df-83a2-e70e0d7900e8",
        "created_at": "2026-07-31T07:49:31.997Z"
      }
    ],
    "offset": 0,
    "total": 26
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 200
- **Duration:** 0.267s
- **Payload:**
```json
{
  "data": {
    "limit": 50,
    "logs": [
      {
        "id": "018da8b0-2a64-4437-8a85-d025d66a9043",
        "channel": "telegram",
        "target": "",
        "subject": "Telegram Update",
        "body": "{\"message\":{\"text\":\"unit test\"}}",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "",
        "created_at": "2026-07-31T18:48:33.567Z"
      },
      {
        "id": "0b6a6cb7-9ba0-4b95-8543-664da04dfc63",
        "channel": "telegram",
        "target": "1020639196",
        "subject": "Webhook Test",
        "body": "webhook test from iot platform",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "ccbe3708-eb03-47df-83a2-e70e0d7900e8",
        "created_at": "2026-07-31T18:48:33.462Z"
      },
      {
        "id": "002d86d5-a205-481b-9c4f-df1d95094fa2",
        "channel": "telegram",
        "target": "",
        "subject": "Telegram Update",
        "body": "{\"message\":{\"text\":\"unit test\"}}",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "",
        "created_at": "2026-07-31T14:06:02.15Z"
      },
      {
        "id": "23e037d8-b84c-43a5-b0fb-6616cef8c37b",
        "channel": "telegram",
        "target": "1020639196",
        "subject": "Webhook Test",
        "body": "webhook test from iot platform",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "ccbe3708-eb03-47df-83a2-e70e0d7900e8",
        "created_at": "2026-07-31T14:06:01.727Z"
      },
      {
        "id": "00860264-3697-4780-996a-e4c66e77bd1f",
        "channel": "telegram",
        "target": "",
        "subject": "Telegram Update",
        "body": "{\"message\":{\"text\":\"unit test\"}}",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "",
        "created_at": "2026-07-31T08:10:26.989Z"
      },
      {
        "id": "8a12087c-c6ea-47f9-ad95-38b6c6fe9bab",
        "channel": "telegram",
        "target": "1020639196",
        "subject": "Webhook Test",
        "body": "webhook test from iot platform",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "ccbe3708-eb03-47df-83a2-e70e0d7900e8",
        "created_at": "2026-07-31T08:10:26.473Z"
      },
      {
        "id": "9d823b15-9d2f-4ad6-b712-8e48940a84fb",
        "channel": "telegram",
        "target": "",
        "subject": "Telegram Update",
        "body": "{\"message\":{\"text\":\"unit test\"}}",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "",
        "created_at": "2026-07-31T08:02:24.248Z"
      },
      {
        "id": "e3874af8-473b-4f81-aae4-a298ae08b812",
        "channel": "telegram",
        "target": "1020639196",
        "subject": "Webhook Test",
        "body": "webhook test from iot platform",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "ccbe3708-eb03-47df-83a2-e70e0d7900e8",
        "created_at": "2026-07-31T08:02:24.029Z"
      },
      {
        "id": "ba4acb6e-030c-4ddd-8518-84b59709f9b1",
        "channel": "telegram",
        "target": "",
        "subject": "Telegram Update",
        "body": "{\"message\":{\"text\":\"unit test\"}}",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "",
        "created_at": "2026-07-31T08:00:14.102Z"
      },
      {
        "id": "28d0df59-0b06-40e5-9082-5c1775c1e405",
        "channel": "telegram",
        "target": "1020639196",
        "subject": "Webhook Test",
        "body": "webhook test from iot platform",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "ccbe3708-eb03-47df-83a2-e70e0d7900e8",
        "created_at": "2026-07-31T08:00:13.966Z"
      },
      {
        "id": "add9efe2-fc6a-4d3e-bdd5-3eeb13408f9b",
        "channel": "telegram",
        "target": "",
        "subject": "Telegram Update",
        "body": "{\"message\":{\"text\":\"unit test\"}}",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "",
        "created_at": "2026-07-31T07:58:13.605Z"
      },
      {
        "id": "3dc11d09-70e0-4b8b-ab9e-bf259d27e8a5",
        "channel": "telegram",
        "target": "1020639196",
        "subject": "Webhook Test",
        "body": "webhook test from iot platform",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "ccbe3708-eb03-47df-83a2-e70e0d7900e8",
        "created_at": "2026-07-31T07:58:13.404Z"
      },
      {
        "id": "f42c2719-b394-4054-b87a-f6df80d965b3",
        "channel": "telegram",
        "target": "",
        "subject": "Telegram Update",
        "body": "{\"message\":{\"text\":\"unit test\"}}",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "",
        "created_at": "2026-07-31T07:56:07.056Z"
      },
      {
        "id": "0441b1b8-2e9b-4f4b-ba51-0d248acd1217",
        "channel": "telegram",
        "target": "1020639196",
        "subject": "Webhook Test",
        "body": "webhook test from iot platform",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "ccbe3708-eb03-47df-83a2-e70e0d7900e8",
        "created_at": "2026-07-31T07:56:06.564Z"
      },
      {
        "id": "4cc0959f-0bb3-422d-a7b2-579f11a82b57",
        "channel": "telegram",
        "target": "",
        "subject": "Telegram Update",
        "body": "{\"message\":{\"text\":\"unit test\"}}",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "",
        "created_at": "2026-07-31T07:52:39.638Z"
      },
      {
        "id": "25414b39-bcd8-491f-875e-21e6b85a409b",
        "channel": "telegram",
        "target": "1020639196",
        "subject": "Webhook Test",
        "body": "webhook test from iot platform",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "ccbe3708-eb03-47df-83a2-e70e0d7900e8",
        "created_at": "2026-07-31T07:52:39.494Z"
      },
      {
        "id": "363c4211-06c4-4d50-a2fb-4a04dbe7f8b1",
        "channel": "telegram",
        "target": "",
        "subject": "Telegram Update",
        "body": "{\"message\":{\"text\":\"unit test\"}}",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "",
        "created_at": "2026-07-31T07:49:32.441Z"
      },
      {
        "id": "a47af5cd-8c9d-45aa-8eb1-116b8c0f8ab3",
        "channel": "telegram",
        "target": "1020639196",
        "subject": "Webhook Test",
        "body": "webhook test from iot platform",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "ccbe3708-eb03-47df-83a2-e70e0d7900e8",
        "created_at": "2026-07-31T07:49:32.115Z"
      },
      {
        "id": "0cf361de-0aac-408b-8757-9d10892a2629",
        "channel": "telegram",
        "target": "",
        "subject": "Telegram Update",
        "body": "{\"message\":{\"text\":\"unit test\"}}",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "",
        "created_at": "2026-07-31T07:32:48.528Z"
      },
      {
        "id": "bc70045e-5f22-4d25-9f6d-71c2e769e6ec",
        "channel": "telegram",
        "target": "1020639196",
        "subject": "Webhook Test",
        "body": "webhook test from iot platform",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "ccbe3708-eb03-47df-83a2-e70e0d7900e8",
        "created_at": "2026-07-31T07:32:47.038Z"
      },
      {
        "id": "7d6e34e2-8f19-471e-a34c-5cf5965c0e0e",
        "channel": "telegram",
        "target": "",
        "subject": "Telegram Update",
        "body": "{\"message\":{\"text\":\"unit test\"}}",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "",
        "created_at": "2026-07-31T07:29:51.699Z"
      },
      {
        "id": "79767515-d390-42a2-86be-b1c8e673a9c0",
        "channel": "telegram",
        "target": "1020639196",
        "subject": "Webhook Test",
        "body": "webhook test from iot platform",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "ccbe3708-eb03-47df-83a2-e70e0d7900e8",
        "created_at": "2026-07-31T07:29:51.512Z"
      },
      {
        "id": "38cc0891-81c5-44e7-a5f8-8164f47816a5",
        "channel": "telegram",
        "target": "",
        "subject": "Telegram Update",
        "body": "{\"message\":{\"text\":\"unit test\"}}",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "",
        "created_at": "2026-07-31T07:26:15.514Z"
      },
      {
        "id": "c9b167a2-9b02-47d8-8a87-57e712bb1992",
        "channel": "telegram",
        "target": "1020639196",
        "subject": "Webhook Test",
        "body": "webhook test from iot platform",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "ccbe3708-eb03-47df-83a2-e70e0d7900e8",
        "created_at": "2026-07-31T07:26:15.453Z"
      },
      {
        "id": "7a0530ce-2997-4128-b7ee-b9e67a850acd",
        "channel": "telegram",
        "target": "",
        "subject": "Telegram Update",
        "body": "{\"message\":{\"text\":\"unit test\"}}",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "",
        "created_at": "2026-07-31T06:57:17.512Z"
      },
      {
        "id": "7e8be56a-d05b-4407-bcfe-9062ddb9ea81",
        "channel": "telegram",
        "target": "1020639196",
        "subject": "Webhook Test",
        "body": "webhook test from iot platform",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "ccbe3708-eb03-47df-83a2-e70e0d7900e8",
        "created_at": "2026-07-31T06:57:17.358Z"
      },
      {
        "id": "5e12e716-6e19-4133-8974-2a1aa0af8e26",
        "channel": "telegram",
        "target": "",
        "subject": "Telegram Update",
        "body": "{\"message\":{\"text\":\"unit test\"}}",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "",
        "created_at": "2026-07-31T06:54:43.198Z"
      },
      {
        "id": "e071e1b9-fd70-4c82-96f6-593bd93c3d74",
        "channel": "telegram",
        "target": "1020639196",
        "subject": "Webhook Test",
        "body": "webhook test from iot platform",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "ccbe3708-eb03-47df-83a2-e70e0d7900e8",
        "created_at": "2026-07-31T06:54:42.784Z"
      },
      {
        "id": "48beec51-f4eb-4e7b-9043-b0d28d6f1290",
        "channel": "telegram",
        "target": "",
        "subject": "Telegram Update",
        "body": "{\"message\":{\"text\":\"unit test\"}}",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "",
        "created_at": "2026-07-31T06:47:50.778Z"
      },
      {
        "id": "2bb3cecb-047e-4b09-b2ed-5da6b3d07d27",
        "channel": "telegram",
        "target": "1020639196",
        "subject": "Webhook Test",
        "body": "webhook test from iot platform",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "ccbe3708-eb03-47df-83a2-e70e0d7900e8",
        "created_at": "2026-07-31T06:47:50.569Z"
      },
      {
        "id": "239c71ae-49ff-4050-a4c4-2ddb52f6c631",
        "channel": "telegram",
        "target": "",
        "subject": "Telegram Update",
        "body": "{\"message\":{\"text\":\"unit test\"}}",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "",
        "created_at": "2026-07-31T05:47:01.887Z"
      },
      {
        "id": "2173cfc4-fac0-444b-9faa-ce926c1d10b5",
        "channel": "telegram",
        "target": "1020639196",
        "subject": "Webhook Test",
        "body": "webhook test from iot platform",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "ccbe3708-eb03-47df-83a2-e70e0d7900e8",
        "created_at": "2026-07-31T05:47:01.203Z"
      },
      {
        "id": "2b24415d-dba9-4e2b-b9b8-ec12caae4076",
        "channel": "telegram",
        "target": "",
        "subject": "Telegram Update",
        "body": "{\"message\":{\"text\":\"unit test\"}}",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "",
        "created_at": "2026-07-31T04:24:29.521Z"
      },
      {
        "id": "056cd644-0118-48e9-a1a8-8e8529b4996c",
        "channel": "telegram",
        "target": "1020639196",
        "subject": "Webhook Test",
        "body": "webhook test from iot platform",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "ccbe3708-eb03-47df-83a2-e70e0d7900e8",
        "created_at": "2026-07-31T04:24:29.172Z"
      },
      {
        "id": "f8a19e16-cf72-42b3-a02e-5f934f307a24",
        "channel": "telegram",
        "target": "",
        "subject": "Telegram Update",
        "body": "{\"message\":{\"text\":\"unit test\"}}",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "",
        "created_at": "2026-07-31T04:23:07.576Z"
      },
      {
        "id": "c83f53ce-6978-4648-b02e-fea29cca3ed2",
        "channel": "telegram",
        "target": "1020639196",
        "subject": "Webhook Test",
        "body": "webhook test from iot platform",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "ccbe3708-eb03-47df-83a2-e70e0d7900e8",
        "created_at": "2026-07-31T04:23:07.265Z"
      },
      {
        "id": "a608d6eb-5c75-4090-871d-67d03f88ca1a",
        "channel": "telegram",
        "target": "",
        "subject": "Telegram Update",
        "body": "{\"message\":{\"text\":\"unit test\"}}",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "",
        "created_at": "2026-07-31T04:12:13.244Z"
      },
      {
        "id": "db0958c8-e10e-410d-9e87-562a42ae3b0e",
        "channel": "telegram",
        "target": "1020639196",
        "subject": "Webhook Test",
        "body": "webhook test from iot platform",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "ccbe3708-eb03-47df-83a2-e70e0d7900e8",
        "created_at": "2026-07-31T04:12:11.193Z"
      },
      {
        "id": "ec6108b9-e404-43c4-bc63-cbfae572cce0",
        "channel": "telegram",
        "target": "",
        "subject": "Telegram Update",
        "body": "{\"message\":{\"text\":\"unit test\"}}",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "",
        "created_at": "2026-07-31T03:55:01.388Z"
      },
      {
        "id": "634864d6-ddd3-46df-8a73-10e1f5306eda",
        "channel": "telegram",
        "target": "1020639196",
        "subject": "Webhook Test",
        "body": "webhook test from iot platform",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "ccbe3708-eb03-47df-83a2-e70e0d7900e8",
        "created_at": "2026-07-31T03:55:00.981Z"
      },
      {
        "id": "c4b8991b-301f-4cb2-8d16-1bad559b82ea",
        "channel": "telegram",
        "target": "",
        "subject": "Telegram Update",
        "body": "{\"message\":{\"text\":\"unit test\"}}",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "",
        "created_at": "2026-07-31T02:49:17.464Z"
      },
      {
        "id": "5d70e5da-2545-4f71-a2a1-4c70aea3aa01",
        "channel": "telegram",
        "target": "1020639196",
        "subject": "Webhook Test",
        "body": "webhook test from iot platform",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "ccbe3708-eb03-47df-83a2-e70e0d7900e8",
        "created_at": "2026-07-31T02:49:16.996Z"
      },
      {
        "id": "dd26a54b-5ff1-49d9-804d-b92b005eccf2",
        "channel": "telegram",
        "target": "",
        "subject": "Telegram Update",
        "body": "{\"message\":{\"text\":\"unit test\"}}",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "",
        "created_at": "2026-07-31T02:47:31.201Z"
      },
      {
        "id": "ee5b82c5-2975-4852-870a-9025e37333ea",
        "channel": "telegram",
        "target": "1020639196",
        "subject": "Webhook Test",
        "body": "webhook test from iot platform",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "ccbe3708-eb03-47df-83a2-e70e0d7900e8",
        "created_at": "2026-07-31T02:47:30.933Z"
      },
      {
        "id": "1e3b4215-f8e9-428e-a812-839ca4999fd6",
        "channel": "telegram",
        "target": "",
        "subject": "Telegram Update",
        "body": "{\"message\":{\"text\":\"unit test\"}}",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "",
        "created_at": "2026-07-31T02:40:21.423Z"
      },
      {
        "id": "9dbed110-2e9b-41d0-8490-75bed4d2615c",
        "channel": "telegram",
        "target": "1020639196",
        "subject": "Webhook Test",
        "body": "webhook test from iot platform",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "ccbe3708-eb03-47df-83a2-e70e0d7900e8",
        "created_at": "2026-07-31T02:40:20.557Z"
      },
      {
        "id": "e4652fa6-241d-4ece-9c5f-5194374e0b0f",
        "channel": "telegram",
        "target": "",
        "subject": "Telegram Update",
        "body": "{\"message\":{\"text\":\"unit test\"}}",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "",
        "created_at": "2026-07-31T02:40:20.161Z"
      },
      {
        "id": "93495227-3c18-45dc-93e7-0e051b8312bf",
        "channel": "telegram",
        "target": "1020639196",
        "subject": "Webhook Test",
        "body": "webhook test from iot platform",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "ccbe3708-eb03-47df-83a2-e70e0d7900e8",
        "created_at": "2026-07-31T02:40:19.713Z"
      },
      {
        "id": "2ee114e1-d9fb-4820-a16a-a114eba19e8f",
        "channel": "telegram",
        "target": "1020639196",
        "subject": "Webhook Test",
        "body": "webhook test from iot platform",
        "status": "queued",
        "attempts": 0,
        "error": "",
        "alert_id": "",
        "user_id": "ccbe3708-eb03-47df-83a2-e70e0d7900e8",
        "created_at": "2026-07-30T17:46:48.502Z"
      },
      {
        "id": "7148aa13-bcad-4536-8d95-463f6bd930bf",
        "channel": "telegram",
        "target": "",
        "subject": "Telegram Update",
        "body": "{\"message\":{\"text\":\"unit test\"}}",
        "status": "sent",
        "attempts": 1,
        "error": "",
        "alert_id": "",
        "user_id": "",
        "created_at": "2026-07-30T17:46:36.068Z"
      }
    ],
    "offset": 0,
    "total": 51
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 200
- **Duration:** 0.0032s
- **Payload:**
```json
{
  "data": {
    "telegram": {
      "enabled": true,
      "target": "1020639196"
    },
    "email": {
      "enabled": true,
      "target": "alifmuhammadrizky01@gmail.com"
    },
    "webhook": {
      "enabled": false,
      "target": ""
    }
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** POST
- **Status:** 202
- **Duration:** 0.4204s
- **Payload:**
```json
{
  "data": {
    "enqueued": 1,
    "message": "test webhook queued for delivery"
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** PUT
- **Status:** 400
- **Duration:** 0.0025s
- **Payload:**
```json
{
  "error": {
    "code": "BAD_REQUEST",
    "message": "invalid telegram chat id"
  },
  "success": false
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** POST
- **Status:** 202
- **Duration:** 0.4929s
- **Payload:**
```json
{
  "data": {
    "status": "accepted"
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 200
- **Duration:** 0.0043s
- **Payload:**
```json
{
  "data": {
    "count": 1,
    "streams": [
      {
        "id": "4a3b07e9-3616-47a1-9d5f-d6609e3bc21b",
        "name": "cctv-1",
        "device_label": "",
        "location": "",
        "source_rtsp": "rtsp://mediamtx-dummy:8554/live1",
        "module_id": "05609956-3dbd-4245-9012-95e4f19b3f52",
        "enabled": true,
        "status": "waiting",
        "hls_url": "http://localhost:8000/hls/cctv-1/index.m3u8",
        "webrtc_url": "http://localhost:8889/cctv-1/whep",
        "recording": false,
        "created_at": "2026-07-31T09:40:31.49Z",
        "updated_at": "2026-07-31T09:40:31.49Z"
      }
    ]
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 200
- **Duration:** 0.0032s
- **Payload:**
```json
{
  "data": {
    "count": 1,
    "snapshots": [
      {
        "id": "090981ff-84aa-43fa-afc2-af0428a1b18e",
        "stream_id": "4a3b07e9-3616-47a1-9d5f-d6609e3bc21b",
        "stream_name": "cctv-1",
        "module_id": "05609956-3dbd-4245-9012-95e4f19b3f52",
        "url": "/storage/stream/snapshots/cctv-1/9f675078-9f32-429f-b766-a7e7c787e217.jpg",
        "kind": "snapshot",
        "size": 49212,
        "created_at": "2026-08-02T14:20:59.434Z"
      }
    ]
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** POST
- **Status:** 500
- **Duration:** 0.0026s
- **Payload:**
```json
{
  "error": {
    "code": "ERROR_500",
    "message": "failed to create stream"
  },
  "success": false
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** PUT
- **Status:** 404
- **Duration:** 0.0028s
- **Payload:**
```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "stream not found"
  },
  "success": false
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** POST
- **Status:** 404
- **Duration:** 0.0026s
- **Payload:**
```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "stream not found"
  },
  "success": false
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** POST
- **Status:** 502
- **Duration:** 0.0036s
- **Payload:**
```json
{
  "error": {
    "code": "BAD_GATEWAY",
    "message": "stream not found"
  },
  "success": false
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** POST
- **Status:** 502
- **Duration:** 0.0043s
- **Payload:**
```json
{
  "error": {
    "code": "BAD_GATEWAY",
    "message": "mediamtx operation failed: no active recording for this stream"
  },
  "success": false
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 404
- **Duration:** 0.0046s
- **Payload:**
```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "snapshot not found"
  },
  "success": false
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** DELETE
- **Status:** 404
- **Duration:** 0.003s
- **Payload:**
```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "snapshot not found"
  },
  "success": false
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 404
- **Duration:** 0.0033s
- **Payload:**
```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "object not found"
  },
  "success": false
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 200
- **Duration:** 0.0103s
- **Payload:**
```json
{
  "success": true,
  "data": {
    "total": 1,
    "items": [
      {
        "id": "a3c743b4-9559-40f2-bdd8-32e9b1c13e5d",
        "name": "Vision Aeroponik",
        "slug": "vision-aeroponik",
        "description": "YOLO model for aeroponic plant/crop detection (user-triggered snapshots).",
        "model_type": "yolov8",
        "framework": "ultralytics",
        "version": null,
        "file_path": "/app/models/vision-aeroponik-model-root.pt",
        "class_names": [
          "Akar 1",
          "Akar 2",
          "Akar 3",
          "Akar 4",
          "Akar 5",
          "Akar 6",
          "Akar 7",
          "Umbi"
        ],
        "input_size": 640,
        "confidence_threshold": 0.25,
        "iou_threshold": 0.45,
        "status": "active",
        "is_default": true,
        "metadata": null,
        "loaded": true,
        "num_classes": 8,
        "created_at": "2026-08-02T13:57:13",
        "updated_at": "2026-08-02T13:59:33"
      }
    ]
  }
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** POST
- **Status:** 404
- **Duration:** 0.0086s
- **Payload:**
```json
{
  "success": false,
  "error": {
    "code": "NOT_FOUND",
    "message": "Frame not found in stream bucket: S3 operation failed; code: AccessDenied, message: Access Denied., resource: /stream, request_id: 18C8090A25614C18, host_id: dd9025bab4ad464b049177c95eb6ebf374d3b3fd1af9251148b658df7ac2e3e8, bucket_name: stream"
  }
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 200
- **Duration:** 0.0112s
- **Payload:**
```json
{
  "success": true,
  "data": {
    "total": 10,
    "limit": 50,
    "offset": 0,
    "items": [
      {
        "id": 10,
        "detection_uid": "5c55c06b-67e6-41f1-8f02-4537f677ce5a",
        "model_id": "a3c743b4-9559-40f2-bdd8-32e9b1c13e5d",
        "model_name": "Vision Aeroponik",
        "source_type": "upload",
        "source_ref": "test_valid.jpg",
        "original_url": "http://localhost:8000/minio/mlbucket/original/20260802_155027_ngik40_test_valid.jpg",
        "annotated_url": "http://localhost:8000/minio/mlbucket/detected/20260802_155028_64k2f2_test_valid.jpg",
        "num_detections": 0,
        "classes": [],
        "confidence_min": null,
        "confidence_max": null,
        "confidence_avg": null,
        "execution_time_ms": 221.58,
        "status": "success",
        "created_at": "2026-08-02T15:50:28"
      },
      {
        "id": 9,
        "detection_uid": "3429c3bb-24a2-45b3-a8d3-376136700520",
        "model_id": "a3c743b4-9559-40f2-bdd8-32e9b1c13e5d",
        "model_name": "Vision Aeroponik",
        "source_type": "upload",
        "source_ref": "cctv-1_3922d406-d716-4aea-bc88-1e328e516ce4.jpg",
        "original_url": "http://localhost:8000/minio/mlbucket/original/20260802_155026_9imw7t_cctv-1_3922d406-d716-4aea-bc88-1e328e516ce4.jpg",
        "annotated_url": "http://localhost:8000/minio/mlbucket/detected/20260802_155026_s6ilzc_cctv-1_3922d406-d716-4aea-bc88-1e328e516ce4.jpg",
        "num_detections": 4,
        "classes": [
          "Akar 1",
          "Umbi"
        ],
        "confidence_min": 0.2594,
        "confidence_max": 0.5949,
        "confidence_avg": 0.4006,
        "execution_time_ms": 197.22,
        "status": "success",
        "created_at": "2026-08-02T15:50:26"
      },
      {
        "id": 8,
        "detection_uid": "7dee35f2-e0a1-4118-be41-7ff017edcfab",
        "model_id": "a3c743b4-9559-40f2-bdd8-32e9b1c13e5d",
        "model_name": "Vision Aeroponik",
        "source_type": "upload",
        "source_ref": "cctv-1_51d0cdb1-d8d4-4d64-8cbd-7d4ab6220baa.jpg",
        "original_url": "http://localhost:8000/minio/mlbucket/original/20260802_154926_sbxf79_cctv-1_51d0cdb1-d8d4-4d64-8cbd-7d4ab6220baa.jpg",
        "annotated_url": "http://localhost:8000/minio/mlbucket/detected/20260802_154926_0zj5tj_cctv-1_51d0cdb1-d8d4-4d64-8cbd-7d4ab6220baa.jpg",
        "num_detections": 4,
        "classes": [
          "Akar 1",
          "Umbi"
        ],
        "confidence_min": 0.2582,
        "confidence_max": 0.5294,
        "confidence_avg": 0.4254,
        "execution_time_ms": 2987.59,
        "status": "success",
        "created_at": "2026-08-02T15:49:26"
      },
      {
        "id": 7,
        "detection_uid": "dfa826f6-1761-4485-89fe-a7825d74686a",
        "model_id": "a3c743b4-9559-40f2-bdd8-32e9b1c13e5d",
        "model_name": "Vision Aeroponik",
        "source_type": "upload",
        "source_ref": "cctv-1_2febab61-a699-4766-8e44-65cdb2651b9f.jpg",
        "original_url": "http://localhost:8000/minio/mlbucket/original/20260802_154550_x6oefi_cctv-1_2febab61-a699-4766-8e44-65cdb2651b9f.jpg",
        "annotated_url": "http://localhost:8000/minio/mlbucket/detected/20260802_154550_2zq4e2_cctv-1_2febab61-a699-4766-8e44-65cdb2651b9f.jpg",
        "num_detections": 5,
        "classes": [
          "Akar 1",
          "Akar 3",
          "Umbi"
        ],
        "confidence_min": 0.2703,
        "confidence_max": 0.4507,
        "confidence_avg": 0.3713,
        "execution_time_ms": 229.44,
        "status": "success",
        "created_at": "2026-08-02T15:45:50"
      },
      {
        "id": 6,
        "detection_uid": "4d13afa9-a89b-4f4f-966f-1c4370d104cd",
        "model_id": "a3c743b4-9559-40f2-bdd8-32e9b1c13e5d",
        "model_name": "Vision Aeroponik",
        "source_type": "upload",
        "source_ref": "cctv-1_7c39b1d6-70d4-46c3-a23e-cabcee921481.jpg",
        "original_url": "http://localhost:8000/minio/mlbucket/original/20260802_154449_qwczj5_cctv-1_7c39b1d6-70d4-46c3-a23e-cabcee921481.jpg",
        "annotated_url": "http://localhost:8000/minio/mlbucket/detected/20260802_154450_xdqbu8_cctv-1_7c39b1d6-70d4-46c3-a23e-cabcee921481.jpg",
        "num_detections": 5,
        "classes": [
          "Akar 1",
          "Umbi"
        ],
        "confidence_min": 0.3079,
        "confidence_max": 0.4552,
        "confidence_avg": 0.3804,
        "execution_time_ms": 3063.17,
        "status": "success",
        "created_at": "2026-08-02T15:44:50"
      },
      {
        "id": 5,
        "detection_uid": "d1bff013-d74f-461c-b8fc-385654819478",
        "model_id": "a3c743b4-9559-40f2-bdd8-32e9b1c13e5d",
        "model_name": "Vision Aeroponik",
        "source_type": "upload",
        "source_ref": "cctv-1_c69f86b0-f9d6-4ee0-a5ad-0a7a88c79689.jpg",
        "original_url": null,
        "annotated_url": null,
        "num_detections": 3,
        "classes": [
          "Akar 1",
          "Umbi"
        ],
        "confidence_min": 0.32,
        "confidence_max": 0.4838,
        "confidence_avg": 0.3945,
        "execution_time_ms": 216.86,
        "status": "success",
        "created_at": "2026-08-02T15:36:27"
      },
      {
        "id": 4,
        "detection_uid": "f063d211-9700-4e4c-a330-6d160902f789",
        "model_id": "a3c743b4-9559-40f2-bdd8-32e9b1c13e5d",
        "model_name": "Vision Aeroponik",
        "source_type": "upload",
        "source_ref": "cctv-1_1993a9db-ec99-4d61-83df-2b5559acd731.jpg",
        "original_url": null,
        "annotated_url": null,
        "num_detections": 2,
        "classes": [
          "Akar 1",
          "Akar 3"
        ],
        "confidence_min": 0.3484,
        "confidence_max": 0.3773,
        "confidence_avg": 0.3629,
        "execution_time_ms": 338.83,
        "status": "success",
        "created_at": "2026-08-02T14:22:08"
      },
      {
        "id": 3,
        "detection_uid": "119732f9-df04-4d84-967a-3cf425f99049",
        "model_id": "a3c743b4-9559-40f2-bdd8-32e9b1c13e5d",
        "model_name": "Vision Aeroponik",
        "source_type": "upload",
        "source_ref": "cctv-1_fc9e4fb5-02fc-459e-bf34-83435119c213.jpg",
        "original_url": null,
        "annotated_url": null,
        "num_detections": 2,
        "classes": [
          "Akar 1",
          "Akar 3"
        ],
        "confidence_min": 0.3819,
        "confidence_max": 0.3927,
        "confidence_avg": 0.3873,
        "execution_time_ms": 887.04,
        "status": "success",
        "created_at": "2026-08-02T14:21:04"
      },
      {
        "id": 2,
        "detection_uid": "520e66df-6f48-4882-a351-67a6ce7465a8",
        "model_id": "a3c743b4-9559-40f2-bdd8-32e9b1c13e5d",
        "model_name": "Vision Aeroponik",
        "source_type": "upload",
        "source_ref": "test_valid.jpg",
        "original_url": null,
        "annotated_url": null,
        "num_detections": 0,
        "classes": [],
        "confidence_min": null,
        "confidence_max": null,
        "confidence_avg": null,
        "execution_time_ms": 1254.7,
        "status": "success",
        "created_at": "2026-08-02T14:20:14"
      },
      {
        "id": 1,
        "detection_uid": "b0698e84-7b39-492a-8347-75f592110a60",
        "model_id": "a3c743b4-9559-40f2-bdd8-32e9b1c13e5d",
        "model_name": "Vision Aeroponik",
        "source_type": "upload",
        "source_ref": "test.jpg",
        "original_url": null,
        "annotated_url": null,
        "num_detections": 0,
        "classes": [],
        "confidence_min": null,
        "confidence_max": null,
        "confidence_avg": null,
        "execution_time_ms": 5928.04,
        "status": "success",
        "created_at": "2026-08-02T14:19:34"
      }
    ]
  }
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 404
- **Duration:** 0.0062s
- **Payload:**
```json
{
  "success": false,
  "error": {
    "code": "NOT_FOUND",
    "message": "Model not found"
  }
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** POST
- **Status:** 200
- **Duration:** 1.399s
- **Payload:**
```json
{
  "success": true,
  "data": {
    "count": 1,
    "results": [
      {
        "detection_uid": "6ffe1c00-6e48-4250-ab18-e5115fcde76e",
        "model_id": "a3c743b4-9559-40f2-bdd8-32e9b1c13e5d",
        "model_name": "Vision Aeroponik",
        "source_type": "base64",
        "source_ref": "base64",
        "original_url": "http://localhost:8000/minio/mlbucket/original/20260802_161311_nug8yt_base64",
        "annotated_url": "http://localhost:8000/minio/mlbucket/detected/20260802_161312_p3zy0x_base64",
        "num_detections": 0,
        "classes": [],
        "detections": [],
        "confidence_min": null,
        "confidence_max": null,
        "confidence_avg": null,
        "root_length_cm": null,
        "tuber_size_cm": null,
        "condition": null,
        "execution_time_ms": 104.53,
        "status": "success"
      }
    ]
  }
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 200
- **Duration:** 0.0241s
- **Payload:**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "detection_uid": "b0698e84-7b39-492a-8347-75f592110a60",
    "model_id": "a3c743b4-9559-40f2-bdd8-32e9b1c13e5d",
    "model_name": "Vision Aeroponik",
    "source_type": "upload",
    "source_ref": "test.jpg",
    "original_url": null,
    "annotated_url": null,
    "num_detections": 0,
    "classes": [],
    "confidence_min": null,
    "confidence_max": null,
    "confidence_avg": null,
    "execution_time_ms": 5928.04,
    "status": "success",
    "created_at": "2026-08-02T14:19:34"
  }
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 200
- **Duration:** 0.0064s
- **Payload:**
```json
{
  "success": true,
  "data": {
    "total": 7,
    "items": [
      {
        "key": "frames/cctv-1/20260802_155027.jpg",
        "url": "/storage/mlbucket/frames/cctv-1/20260802_155027.jpg",
        "size": 70728,
        "last_modified": "2026-08-02T15:50:27.048000+00:00",
        "kind": "frame"
      },
      {
        "key": "frames/cctv-1/20260802_154926.jpg",
        "url": "/storage/mlbucket/frames/cctv-1/20260802_154926.jpg",
        "size": 70501,
        "last_modified": "2026-08-02T15:49:26.614000+00:00",
        "kind": "frame"
      },
      {
        "key": "frames/cctv-1/20260802_154550.jpg",
        "url": "/storage/mlbucket/frames/cctv-1/20260802_154550.jpg",
        "size": 68126,
        "last_modified": "2026-08-02T15:45:50.809000+00:00",
        "kind": "frame"
      },
      {
        "key": "frames/cctv-1/20260802_154450.jpg",
        "url": "/storage/mlbucket/frames/cctv-1/20260802_154450.jpg",
        "size": 67357,
        "last_modified": "2026-08-02T15:44:50.440000+00:00",
        "kind": "frame"
      },
      {
        "key": "frames/cctv-1/20260802_153628.jpg",
        "url": "/storage/mlbucket/frames/cctv-1/20260802_153628.jpg",
        "size": 62783,
        "last_modified": "2026-08-02T15:36:28.192000+00:00",
        "kind": "frame"
      },
      {
        "key": "frames/cctv-1/20260802_142208.jpg",
        "url": "/storage/mlbucket/frames/cctv-1/20260802_142208.jpg",
        "size": 50806,
        "last_modified": "2026-08-02T14:22:08.486000+00:00",
        "kind": "frame"
      },
      {
        "key": "frames/cctv-1/20260802_142105.jpg",
        "url": "/storage/mlbucket/frames/cctv-1/20260802_142105.jpg",
        "size": 49248,
        "last_modified": "2026-08-02T14:21:05.070000+00:00",
        "kind": "frame"
      }
    ]
  }
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** PUT
- **Status:** 404
- **Duration:** 0.0086s
- **Payload:**
```json
{
  "success": false,
  "error": {
    "code": "NOT_FOUND",
    "message": "Model not found"
  }
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** POST
- **Status:** 404
- **Duration:** 0.0059s
- **Payload:**
```json
{
  "success": false,
  "error": {
    "code": "NOT_FOUND",
    "message": "Model not found"
  }
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** DELETE
- **Status:** 404
- **Duration:** 0.0062s
- **Payload:**
```json
{
  "success": false,
  "error": {
    "code": "NOT_FOUND",
    "message": "Model not found"
  }
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 200
- **Duration:** 3.0373s
- **Payload:**
```json
{
  "data": {
    "nodes": [
      {
        "node_id": "node-00",
        "module_id": "05609956-3dbd-4245-9012-95e4f19b3f52",
        "metrics": [
          "connection_stats.mqtt_connected",
          "connection_stats.uptime_s",
          "device_info.cpu_freq_mhz",
          "device_info.flash_size_mb",
          "device_info.free_heap_kb",
          "device_info.uptime_s",
          "network.wifi_rssi",
          "telemetry.inputs.input1",
          "telemetry.inputs.input2",
          "telemetry.inputs.input3",
          "telemetry.inputs.input4",
          "telemetry.modbus.cwt1.hum",
          "telemetry.modbus.cwt1.temp",
          "telemetry.modbus.cwt2.hum",
          "telemetry.modbus.cwt2.temp",
          "telemetry.modbus.npk.ec_nutrisi",
          "telemetry.modbus.npk.ph_nutrisi",
          "telemetry.modbus.npk.temp_nutrisi",
          "telemetry.outputs.buzzer",
          "telemetry.outputs.load1",
          "telemetry.outputs.load2",
          "telemetry.outputs.load3",
          "telemetry.outputs.load4"
        ]
      }
    ]
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 200
- **Duration:** 0.0073s
- **Payload:**
```json
{
  "data": {
    "from": "2026-08-01T16:13:15Z",
    "metrics": [
      "temperature"
    ],
    "node_ids": [
      "node-00"
    ],
    "to": "2026-08-02T16:13:15Z",
    "total": 0
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 200
- **Duration:** 0.0031s
- **Payload:**
```json
{
  "components": {
    "securitySchemes": {
      "bearerAuth": {
        "bearerFormat": "JWT",
        "scheme": "bearer",
        "type": "http"
      }
    }
  },
  "info": {
    "description": "Historical telemetry export (CSV) with cursor-based pagination and RBAC.",
    "title": "Export Service API",
    "version": "1.0.0"
  },
  "openapi": "3.0.3",
  "paths": {
    "/export/v1/nodes": {
      "get": {
        "responses": {
          "200": {
            "description": "Node list"
          },
          "401": {
            "description": "Unauthorized"
          },
          "403": {
            "description": "Forbidden"
          }
        },
        "summary": "List nodes with telemetry and their available metrics"
      }
    },
    "/export/v1/openapi": {
      "get": {
        "responses": {
          "200": {
            "description": "OpenAPI JSON"
          }
        },
        "summary": "This OpenAPI specification"
      }
    },
    "/export/v1/telemetry": {
      "get": {
        "parameters": [
          {
            "description": "Comma-separated node IDs",
            "in": "query",
            "name": "node_id",
            "required": true,
            "schema": {
              "type": "string"
            }
          },
          {
            "description": "Comma-separated metric names",
            "in": "query",
            "name": "metric",
            "required": true,
            "schema": {
              "type": "string"
            }
          },
          {
            "description": "RFC3339 start (default 24h ago)",
            "in": "query",
            "name": "from",
            "schema": {
              "type": "string"
            }
          },
          {
            "description": "RFC3339 end (default now)",
            "in": "query",
            "name": "to",
            "schema": {
              "type": "string"
            }
          },
          {
            "description": "Rows per page (max 100000)",
            "in": "query",
            "name": "limit",
            "schema": {
              "type": "integer"
            }
          },
          {
            "description": "Opaque keyset cursor for the next page",
            "in": "query",
            "name": "cursor",
            "schema": {
              "type": "string"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "CSV file attachment"
          },
          "400": {
            "description": "Bad request (invalid params / window too large)"
          },
          "401": {
            "description": "Unauthorized"
          },
          "403": {
            "description": "Forbidden (insufficient role)"
          }
        },
        "summary": "Stream a paginated CSV export of raw telemetry"
      }
    }
  },
  "security": [
    {
      "bearerAuth": []
    }
  ],
  "servers": [
    {
      "description": "via Kong gateway",
      "url": "http://localhost:8000"
    }
  ]
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 200
- **Duration:** 0.0044s
- **Payload:**
```
time,node_id,module_id

```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 200
- **Duration:** 0.0373s
- **Payload:**
```json
{
  "data": {
    "limit": 50,
    "messages": [],
    "offset": 0,
    "total": 0
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 200
- **Duration:** 0.0044s
- **Payload:**
```json
{
  "data": {
    "limit": 50,
    "messages": [],
    "offset": 0,
    "total": 0
  },
  "success": true
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 200
- **Duration:** 0.0036s
- **Payload:**
```json
{
  "success": true,
  "data": {
    "status": "ok",
    "model_loaded": true,
    "vec_norm_loaded": true
  }
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** POST
- **Status:** 200
- **Duration:** 0.0042s
- **Payload:**
```json
{
  "success": true,
  "data": {
    "D_mist": 900.0,
    "interval_sec": 899.9996948242188,
    "A_valve": 1.0
  }
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** GET
- **Status:** 200
- **Duration:** 0.0048s
- **Payload:**
```json
{
  "status": "ok",
  "node_id": "node-00",
  "schedule_id": "35461f5f-d6ef-4c30-abfc-9eb680b5dfe7",
  "valve_output": "load2",
  "interval_sec": 5
}
```

## unknown

- **Service:** unknown
- **Endpoint:** ``
- **Method:** POST
- **Status:** 200
- **Duration:** 0.097s
- **Payload:**
```json
{
  "status": "tick executed"
}
```

