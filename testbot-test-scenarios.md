# Skyramp Testbot — Plane Test Scenarios

## Overview

This document defines end-to-end test scenarios for validating the Skyramp Testbot against the Plane project management API. Each scenario targets a specific testbot behavior (ADD, UPDATE, REGENERATE, DELETE, or No action) and maps to a realistic code change in the Plane API (`apps/api/`).

**Repository**: `makeplane/plane`
**API Stack**: Django REST Framework (Python)
**Base URL (CI)**: `http://localhost:8000`
**Existing Skyramp Tests**: `apps/api/plane/tests/skyramp/`

**Action Types Covered**

| Action | Meaning |
|---|---|
| ADD | New route introduced in the diff — generate new test |
| UPDATE | Existing endpoint changed (new field, status code, etc.) — edit test in-place |
| REGENERATE | Endpoint substantially restructured (path renamed, schema overhauled) — replace test |
| DELETE | Endpoint removed — remove test file |
| No action | All changes are non-application (docs, CI/CD, lock files) — skip entirely |

---

## Scenario 1 — ADD: New cycle progress endpoint

**Branch name**: `test/scenario-1-add-cycle-progress`
**Expected testbot action**: ADD

### Code Change

Add a new read-only progress summary endpoint for a sprint cycle.

**File**: `apps/api/plane/api/views/cycle.py` — add new view:
```python
class CycleProgressAPIEndpoint(BaseAPIView):
    """Returns progress statistics for a cycle."""

    def get(self, request, slug, project_id, cycle_id):
        cycle = Cycle.objects.get(pk=cycle_id, project_id=project_id, workspace__slug=slug)
        issues = cycle.issue_cycle.all()
        total = issues.count()
        completed = issues.filter(issue__state__group="completed").count()
        cancelled = issues.filter(issue__state__group="cancelled").count()
        return Response({
            "total_issues": total,
            "completed_issues": completed,
            "cancelled_issues": cancelled,
            "completion_percentage": round((completed / total * 100) if total else 0, 2),
        })
```

**File**: `apps/api/plane/api/urls/cycle.py` — register the route:
```python
path(
    "workspaces/<str:slug>/projects/<uuid:project_id>/cycles/<uuid:cycle_id>/progress/",
    CycleProgressAPIEndpoint.as_view(http_method_names=["get"]),
    name="cycle-progress",
),
```

### Expected Testbot Behavior

- `skyramp_analyze_changes` finds 0 existing tests for the progress endpoint
- `skyramp_analyze_test_health` skipped (no existing tests)
- Decision table:

| Test/Endpoint | Action | Reason |
|---|---|---|
| `GET /api/v1/workspaces/{slug}/projects/{id}/cycles/{id}/progress/` | ADD | New route in diff, no existing test |

- Generates contract + integration tests for the new endpoint
- No existing test files modified

### Verification

- [ ] New test file created (e.g., `test_contract_cycle_progress.py` or `test_integration_cycle_progress.py`)
- [ ] Test asserts response contains `total_issues`, `completed_issues`, `cancelled_issues`, `completion_percentage`
- [ ] Existing `test_cycles.py` not modified
- [ ] Report `newTestsCreated` contains only cycle progress tests

---

## Scenario 2 — UPDATE: New field added to cycle response

**Branch name**: `test/scenario-2-update-cycle-overdue`
**Expected testbot action**: UPDATE

### Code Change

Add an `overdue_issues` count to the cycle detail response (already covered by `test_cycles.py`).

**File**: `apps/api/plane/api/serializers/cycle.py`:
```python
class CycleSerializer(BaseSerializer):
    # ADD this field:
    overdue_issues = serializers.SerializerMethodField()

    def get_overdue_issues(self, obj):
        from django.utils import timezone
        return obj.issue_cycle.filter(
            issue__due_date__lt=timezone.now().date(),
            issue__completed_at__isnull=True
        ).count()
```

### Expected Testbot Behavior

- `skyramp_analyze_test_health` detects additive field change on covered endpoint
- Drift score ≥ 30 for cycle test files
- Decision table:

| Test/Endpoint | Action | Reason |
|---|---|---|
| `test_contract_cycle_progress.py` (or `test_cycles.py`) | UPDATE | `overdue_issues` added to cycle detail response — coverage gap |

- Edits test file in-place, adds:
  ```python
  assert "overdue_issues" in response.data
  assert isinstance(response.data["overdue_issues"], int)
  assert response.data["overdue_issues"] >= 0
  ```
- No new test files created

### Verification

- [ ] Existing cycle test file has new assertion for `overdue_issues`
- [ ] No new test files created
- [ ] Report `newTestsCreated` shows `testType: "contract (updated)"` or similar

---

## Scenario 3 — REGENERATE: `cycle-issues` renamed to `work-items`

**Branch name**: `test/scenario-3-regen-cycle-issues-rename`
**Expected testbot action**: REGENERATE

### Code Change

Rename the cycle sub-resource path from `cycle-issues` to `work-items` in the cycle router.

**File**: `apps/api/plane/api/urls/cycle.py`:
```python
# BEFORE:
path(
    "workspaces/<str:slug>/projects/<uuid:project_id>/cycles/<uuid:cycle_id>/cycle-issues/",
    CycleIssueListCreateAPIEndpoint.as_view(http_method_names=["get", "post"]),
    name="cycle-issues",
),
path(
    "workspaces/<str:slug>/projects/<uuid:project_id>/cycles/<uuid:cycle_id>/cycle-issues/<uuid:issue_id>/",
    CycleIssueDetailAPIEndpoint.as_view(http_method_names=["get", "delete"]),
    name="cycle-issues",
),

# AFTER:
path(
    "workspaces/<str:slug>/projects/<uuid:project_id>/cycles/<uuid:cycle_id>/work-items/",
    CycleIssueListCreateAPIEndpoint.as_view(http_method_names=["get", "post"]),
    name="cycle-work-items",
),
path(
    "workspaces/<str:slug>/projects/<uuid:project_id>/cycles/<uuid:cycle_id>/work-items/<uuid:issue_id>/",
    CycleIssueDetailAPIEndpoint.as_view(http_method_names=["get", "delete"]),
    name="cycle-work-items-detail",
),
```

### Expected Testbot Behavior

- `skyramp_analyze_test_health` detects the `/cycle-issues/` path no longer exists
- Drift score ≥ 71 for all cycle issue test files
- Decision table:

| Test/Endpoint | Action | Reason |
|---|---|---|
| `test_contract_cycle_issues.py` | REGENERATE | `/cycle-issues/` path gone; now `/work-items/` |
| `test_integration_cycle_issues.py` | REGENERATE | Same — path fundamentally broken |

- Calls generation tools with `endpointURL` pointing to the new `/work-items/` path
- Overwrites existing test files with regenerated versions

### Verification

- [ ] All regenerated tests use `/work-items/` not `/cycle-issues/`
- [ ] Test files overwritten (same filenames)
- [ ] No orphaned test files left calling the old path

---

## Scenario 4 — DELETE: `transfer-issues` endpoint removed

**Branch name**: `test/scenario-4-delete-transfer-issues`
**Prerequisite**: `test_contract_transfer_issues.py` and `test_integration_transfer_issues.py` are committed
**Expected testbot action**: DELETE

### Code Change

Remove the `TransferCycleIssueAPIEndpoint` route which is superseded by bulk work-item operations.

**File**: `apps/api/plane/api/urls/cycle.py` — remove this block:
```python
# DELETE this entire path:
path(
    "workspaces/<str:slug>/projects/<uuid:project_id>/cycles/<uuid:cycle_id>/transfer-issues/",
    TransferCycleIssueAPIEndpoint.as_view(http_method_names=["post"]),
    name="transfer-issues",
),
```

**File**: `apps/api/plane/api/urls/cycle.py` — remove the import:
```python
# REMOVE from imports:
TransferCycleIssueAPIEndpoint,
```

### Expected Testbot Behavior

- `skyramp_analyze_test_health` detects `POST .../transfer-issues/` no longer exists in codebase
- Drift score = 100 (endpoint gone)
- Decision table:

| Test/Endpoint | Action | Reason |
|---|---|---|
| `test_contract_transfer_issues.py` | DELETE | `/transfer-issues/` endpoint removed in diff |
| `test_integration_transfer_issues.py` | DELETE | Same |

- Removes both test files

### Verification

- [ ] `test_contract_transfer_issues.py` no longer exists
- [ ] `test_integration_transfer_issues.py` no longer exists
- [ ] Existing cycle CRUD tests untouched
- [ ] Report `newTestsCreated` is empty array

---

## Scenario 5 — No action: Documentation-only changes

**Branch name**: `test/scenario-5-docs-only`
**Expected testbot action**: Skip entirely

### Code Change

Only non-application files changed:

| File | Change |
|---|---|
| `README.md` | Update self-hosting instructions |
| `docs/api-guide.md` | Add API authentication examples |
| `.env.example` | Add comment about `API_KEY_RATE_LIMIT` |
| `docker-compose.yml` | Add comment explaining MinIO setup |

No Python source files in `apps/api/plane/` modified.

### Expected Testbot Behavior

- `skyramp_analyze_changes` detects all changed files match `NON_APP_PATTERNS`
- Returns early: `"All 4 changed file(s) are non-application. No test analysis needed."`
- No tools called after `skyramp_analyze_changes`
- Decision table: empty

### Verification

- [ ] `skyramp_analyze_test_health` never called
- [ ] No test files in `apps/api/plane/tests/skyramp/` created or modified
- [ ] Report has empty `newTestsCreated` and `testMaintenance` arrays
- [ ] `businessCaseAnalysis` mentions documentation/cosmetic change

---

## Scenario 6 — Multi-commit PR: UPDATE → skip (bot commit) → UPDATE → no-op

**Branch name**: `test/scenario-6-multi-commit-project-summary`
**Tests**: `prNumber` deduplication, `SKYRAMP_TEST_FILE_PATTERN` filter, latest-comment-only logic

### Commit Sequence

**Commit 1 (user)**: Add `open_issues` to project summary response

```python
# apps/api/plane/api/views/project.py — ProjectSummaryAPIEndpoint
return Response({
    "total_issues": total,
    "completed_issues": completed,
    "open_issues": total - completed,  # NEW field
})
```

→ **Testbot run 1**: UPDATE both project summary test files, add assertion for `open_issues`. Testbot commits updated tests.

**Commit 2 (testbot)**: Testbot commits updated test files (`test_contract_project_summary.py`)

→ **Testbot run 2** (triggered by bot's own commit): `SKYRAMP_TEST_FILE_PATTERN` filters out bot-committed test files from `changedFiles`. No application code changed since run 1 → skip.

**Commit 3 (user)**: Add `priority_breakdown` to project summary

```python
return Response({
    "total_issues": total,
    "completed_issues": completed,
    "open_issues": total - completed,
    "priority_breakdown": {   # NEW field
        "urgent": issues.filter(priority="urgent").count(),
        "high": issues.filter(priority="high").count(),
        "medium": issues.filter(priority="medium").count(),
        "low": issues.filter(priority="low").count(),
        "none": issues.filter(priority="none").count(),
    },
})
```

→ **Testbot run 3**: PR history (via `prNumber`) shows `open_issues` UPDATE already done. Only acts on `priority_breakdown` gap → UPDATE again, no duplicates.

**Commit 4 (user)**: Fix docstring typo in `project.py`

```python
# was: "Returns a sumary of project issues"
# now: "Returns a summary of project issues"
```

→ **Testbot run 4**: Only a comment changed — no endpoint or field change → VERIFY, no action.

### Verification Per Run

| Run | Trigger | Expected outcome |
|---|---|---|
| 1 | User pushes `open_issues` | UPDATE tests, commit test files |
| 2 | Testbot commit triggers CI | Skip — bot file filter active |
| 3 | User pushes `priority_breakdown` | UPDATE tests again, no duplicate for `open_issues` |
| 4 | User fixes docstring | No action — VERIFY |

---

## Scenario 7 — Mixed PR: UPDATE existing + ADD new in one diff

**Branch name**: `test/scenario-7-mixed-module-update-add`
**Expected testbot actions**: UPDATE + ADD in same run

### Code Change

Two independent changes in one PR:

**Change 1** — Add field to existing module detail endpoint (covered by tests):
```python
# apps/api/plane/api/serializers/module.py
class ModuleSerializer(BaseSerializer):
    # ADD:
    issue_count = serializers.SerializerMethodField()

    def get_issue_count(self, obj):
        return obj.issue_module.count()
```

**Change 2** — Add a completely new module statistics endpoint (no existing test):
```python
# apps/api/plane/api/views/module.py
class ModuleStatisticsAPIEndpoint(BaseAPIView):
    """Returns issue statistics grouped by state for a module."""

    def get(self, request, slug, project_id, module_id):
        module = Module.objects.get(pk=module_id, project_id=project_id, workspace__slug=slug)
        stats = (
            module.issue_module
            .values("issue__state__group")
            .annotate(count=Count("id"))
        )
        return Response({"state_breakdown": list(stats)})
```

**File**: `apps/api/plane/api/urls/module.py` — register:
```python
path(
    "workspaces/<str:slug>/projects/<uuid:project_id>/modules/<uuid:module_id>/statistics/",
    ModuleStatisticsAPIEndpoint.as_view(http_method_names=["get"]),
    name="module-statistics",
),
```

### Expected Testbot Behavior

- Decision table:

| Test/Endpoint | Action | Reason |
|---|---|---|
| `test_contract_modules.py` | UPDATE | `issue_count` added to module detail response — coverage gap |
| `GET .../modules/{id}/statistics/` | ADD | New route in diff, no existing test |

- In-place edits to module tests + new test file generated for statistics endpoint

### Verification

- [ ] Module contract test updated with `issue_count` assertion
- [ ] New `test_contract_module_statistics.py` (or `test_integration_module_statistics.py`) created
- [ ] Report shows 1 updated + 1 new test

---

## Scenario 8 — Two-PR lifecycle: ADD then REGENERATE

**Tests**: Testbot managing its own previously-generated tests across separate PRs

### PR 1 — ADD

**Branch**: `test/scenario-8a-add-label-stats`

Add `GET /api/v1/workspaces/{slug}/projects/{project_id}/labels/{label_id}/stats/` endpoint.

```python
# apps/api/plane/api/views/label.py
class LabelStatsAPIEndpoint(BaseAPIView):
    """Issue count statistics for a label."""

    def get(self, request, slug, project_id, label_id):
        label = Label.objects.get(pk=label_id, project_id=project_id, workspace__slug=slug)
        issue_count = label.label_issue.count()
        open_count = label.label_issue.filter(issue__completed_at__isnull=True).count()
        return Response({
            "label_id": str(label.id),
            "label_name": label.name,
            "total_issues": issue_count,
            "open_issues": open_count,
            "closed_issues": issue_count - open_count,
        })
```

**File**: `apps/api/plane/api/urls/label.py` — register the route.

→ **Testbot run**: ADD → generates `test_contract_label_stats.py` targeting `GET /api/v1/.../labels/{id}/stats/`. Merges to `preview`.

### PR 2 — REGENERATE

**Branch**: `test/scenario-8b-rename-label-stats`

Rename the sub-resource from `/stats/` to `/summary/` for consistency with other endpoints:

```python
# apps/api/plane/api/urls/label.py
# BEFORE:
path("...labels/<uuid:label_id>/stats/", LabelStatsAPIEndpoint.as_view(...), name="label-stats"),
# AFTER:
path("...labels/<uuid:label_id>/summary/", LabelStatsAPIEndpoint.as_view(...), name="label-summary"),
```

→ **Testbot run**: `test_contract_label_stats.py` calls `.../labels/{id}/stats/` which no longer exists → REGENERATE with new path `.../labels/{id}/summary/`.

### Verification

| PR | Expected |
|---|---|
| PR 1 | New `test_contract_label_stats.py` created |
| PR 2 | Same file regenerated with `/summary/` path |

---

## Summary Table

| # | Endpoint Area | Action | Trigger | Key Validation |
|---|---|---|---|---|
| 1 | Cycles | ADD | New `GET .../cycles/{id}/progress/` endpoint | New test files generated; existing cycle tests untouched |
| 2 | Cycles | UPDATE | `overdue_issues` added to cycle detail response | In-place edit of cycle test; no new files |
| 3 | Cycle Issues | REGENERATE | `/cycle-issues/` renamed to `/work-items/` | All cycle-issue tests regenerated with new path |
| 4 | Cycle Transfer | DELETE | `POST .../transfer-issues/` endpoint removed | Both transfer test files deleted |
| 5 | (none) | No action | README + docs + .env.example + docker-compose only | Early return; zero test activity |
| 6 | Project Summary | Multi-commit | UPDATE → skip (bot commit) → UPDATE → no-op | Dedup via `prNumber`; bot file filter; VERIFY on docstring |
| 7 | Modules | UPDATE + ADD | New field on existing + new statistics endpoint | In-place update AND new file in same run |
| 8 | Labels | ADD → REGENERATE | Two separate PRs on same label stats endpoint | Testbot manages its own previously-generated tests |

---

## Setup Checklist (Before Running)

- [ ] Plane API running at `http://localhost:8000` (or via CI workflow)
- [ ] PostgreSQL + Redis service containers healthy
- [ ] `apps/api/.env` configured with `ENABLE_DRF_SPECTACULAR=1` (exposes `/api/schema/`)
- [ ] `.skyramp/workspace.yml` committed with correct `baseUrl` and `outputDir`
- [ ] Secrets configured in GitHub repo: `SKYRAMP_TESTBOT_APP_ID`, `SKYRAMP_TESTBOT_APP_PRIVATE_KEY`, `SKYRAMP_LICENSE_FILE`, `SKYRAMP_TESTBOT_API_KEY`
- [ ] For Scenarios 4, 6, 7: prerequisite test files committed before running
- [ ] Each scenario runs on a fresh branch from `preview`
- [ ] For multi-commit scenario (6, 8): note the PR number and pass as `prNumber` argument to testbot
