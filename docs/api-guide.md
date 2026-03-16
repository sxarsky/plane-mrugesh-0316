# Plane API Guide

## Overview

The Plane REST API allows you to programmatically interact with your workspace data — work items, projects, cycles, modules, and more.

- **Base URL**: `https://<your-plane-instance>/api/v1/`
- **Format**: JSON
- **Schema / Swagger UI**: `https://<your-plane-instance>/api/schema/swagger-ui/`
- **OpenAPI spec**: `https://<your-plane-instance>/api/schema/`

---

## Authentication

All API requests must be authenticated using an **API key** passed in the request header.

```
X-Api-Key: <your-api-key>
```

### Generating an API Key

1. Sign in to your Plane instance
2. Go to **Profile → API Tokens** (or navigate to `/<workspace-slug>/settings/api-tokens/`)
3. Click **Add API Token**, set a label and optional expiry, and copy the token

> **Important**: The token value is only shown once at creation time. Store it securely.

You can also create tokens programmatically (requires an existing session):

```bash
curl -X POST https://<your-plane-instance>/api/users/api-tokens/ \
  -H "Content-Type: application/json" \
  -d '{
    "label": "my-integration",
    "description": "Token for CI/CD pipeline",
    "expired_at": "2027-01-01T00:00:00Z"
  }'
```

Response:

```json
{
  "id": "3f7a1b2c-...",
  "label": "my-integration",
  "description": "Token for CI/CD pipeline",
  "token": "plane_api_xxxxxxxxxxxxxxxx",
  "expired_at": "2027-01-01T00:00:00Z",
  "created_at": "2026-03-16T12:00:00Z"
}
```

---

## Making Authenticated Requests

### curl

```bash
curl https://<your-plane-instance>/api/v1/workspaces/<slug>/projects/ \
  -H "X-Api-Key: plane_api_xxxxxxxxxxxxxxxx"
```

### Python (requests)

```python
import requests

BASE_URL = "https://<your-plane-instance>/api/v1"
API_KEY  = "plane_api_xxxxxxxxxxxxxxxx"

headers = {"X-Api-Key": API_KEY}

# List projects in a workspace
response = requests.get(
    f"{BASE_URL}/workspaces/my-workspace/projects/",
    headers=headers,
)
response.raise_for_status()
projects = response.json()
```

### Python (with a session helper)

```python
import requests

class PlaneClient:
    def __init__(self, base_url: str, api_key: str):
        self.session = requests.Session()
        self.session.headers.update({"X-Api-Key": api_key})
        self.base_url = base_url.rstrip("/")

    def get(self, path: str, **kwargs):
        return self.session.get(f"{self.base_url}{path}", **kwargs)

    def post(self, path: str, **kwargs):
        return self.session.post(f"{self.base_url}{path}", **kwargs)

    def patch(self, path: str, **kwargs):
        return self.session.patch(f"{self.base_url}{path}", **kwargs)

    def delete(self, path: str, **kwargs):
        return self.session.delete(f"{self.base_url}{path}", **kwargs)


client = PlaneClient(
    base_url="https://<your-plane-instance>/api/v1",
    api_key="plane_api_xxxxxxxxxxxxxxxx",
)

# Get current user
me = client.get("/users/me/").json()

# List work items in a project
items = client.get(
    "/workspaces/my-workspace/projects/<project-id>/work-items/"
).json()
```

### JavaScript / TypeScript (fetch)

```typescript
const BASE_URL = "https://<your-plane-instance>/api/v1";
const API_KEY  = "plane_api_xxxxxxxxxxxxxxxx";

const headers = {
  "X-Api-Key": API_KEY,
  "Content-Type": "application/json",
};

// List projects
const res = await fetch(`${BASE_URL}/workspaces/my-workspace/projects/`, { headers });
const projects = await res.json();

// Create a work item
const newItem = await fetch(
  `${BASE_URL}/workspaces/my-workspace/projects/<project-id>/work-items/`,
  {
    method: "POST",
    headers,
    body: JSON.stringify({
      name: "Fix login bug",
      priority: "high",
    }),
  }
).then((r) => r.json());
```

### JavaScript / TypeScript (axios)

```typescript
import axios from "axios";

const plane = axios.create({
  baseURL: "https://<your-plane-instance>/api/v1",
  headers: { "X-Api-Key": "plane_api_xxxxxxxxxxxxxxxx" },
});

// Get a specific project
const { data: project } = await plane.get(
  "/workspaces/my-workspace/projects/<project-id>/"
);

// Update a work item
const { data: updated } = await plane.patch(
  "/workspaces/my-workspace/projects/<project-id>/work-items/<item-id>/",
  { state: "<state-id>", priority: "urgent" }
);
```

---

## Service API Tokens (Workspace-scoped)

For automation that acts on behalf of a workspace (not a specific user), use a **service API token**. These are created by workspace admins and have a higher rate limit.

```bash
# Create a service token (requires workspace admin session)
curl -X POST https://<your-plane-instance>/api/workspaces/<slug>/service-api-tokens/ \
  -H "X-Api-Key: <admin-api-key>" \
  -H "Content-Type: application/json" \
  -d '{"label": "ci-bot", "description": "Used by GitHub Actions"}'
```

Use service tokens exactly like regular API keys — same `X-Api-Key` header.

---

## Rate Limits

| Token type | Limit |
|---|---|
| Personal API key | 60 requests / minute |
| Service API token | 300 requests / minute |

Rate limit status is returned in every response:

| Header | Description |
|---|---|
| `X-RateLimit-Remaining` | Requests remaining in the current window |
| `X-RateLimit-Reset` | Unix timestamp when the window resets |

When the limit is exceeded the API returns `429 Too Many Requests`.

```python
response = requests.get(url, headers=headers)

remaining = response.headers.get("X-RateLimit-Remaining")
reset_at   = response.headers.get("X-RateLimit-Reset")

if response.status_code == 429:
    print(f"Rate limited. Retry after {reset_at}")
```

---

## Managing API Tokens

### List your tokens

```bash
curl https://<your-plane-instance>/api/users/api-tokens/ \
  -H "X-Api-Key: plane_api_xxxxxxxxxxxxxxxx"
```

### Revoke a token

```bash
curl -X DELETE https://<your-plane-instance>/api/users/api-tokens/<token-id>/ \
  -H "X-Api-Key: plane_api_xxxxxxxxxxxxxxxx"
```

### Update a token (label / expiry)

```bash
curl -X PATCH https://<your-plane-instance>/api/users/api-tokens/<token-id>/ \
  -H "X-Api-Key: plane_api_xxxxxxxxxxxxxxxx" \
  -H "Content-Type: application/json" \
  -d '{"label": "renamed-token", "expired_at": "2027-06-01T00:00:00Z"}'
```

---

## Common Errors

| Status | Meaning | Fix |
|---|---|---|
| `401 Unauthorized` | Missing or invalid `X-Api-Key` | Check the header name and token value |
| `403 Forbidden` | Token valid but lacks permission | Use a token with the required workspace/project role |
| `404 Not Found` | Resource does not exist or you lack access | Verify the workspace slug, project ID, and item ID |
| `429 Too Many Requests` | Rate limit exceeded | Back off and retry after `X-RateLimit-Reset` |

---

## Quick Reference

```bash
PLANE="https://<your-plane-instance>"
KEY="plane_api_xxxxxxxxxxxxxxxx"
SLUG="my-workspace"
PROJECT="<project-uuid>"

# Current user
curl $PLANE/api/v1/users/me/                             -H "X-Api-Key: $KEY"

# List projects
curl $PLANE/api/v1/workspaces/$SLUG/projects/            -H "X-Api-Key: $KEY"

# List work items
curl $PLANE/api/v1/workspaces/$SLUG/projects/$PROJECT/work-items/ \
                                                         -H "X-Api-Key: $KEY"

# Create work item
curl -X POST $PLANE/api/v1/workspaces/$SLUG/projects/$PROJECT/work-items/ \
  -H "X-Api-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"name": "New task", "priority": "medium"}'

# List cycles
curl $PLANE/api/v1/workspaces/$SLUG/projects/$PROJECT/cycles/ \
                                                         -H "X-Api-Key: $KEY"

# List modules
curl $PLANE/api/v1/workspaces/$SLUG/projects/$PROJECT/modules/ \
                                                         -H "X-Api-Key: $KEY"
```
