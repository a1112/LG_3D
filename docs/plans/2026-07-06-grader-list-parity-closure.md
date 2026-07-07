# Grader List Parity Closure Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Close `/grader_list?count={count}` parity by proving and, if needed, correcting the remaining Python/Rust semantic edge cases for child-coil flattening, count handling, OpenAPI schema, and React/Tauri access.

**Architecture:** Treat Python `app/Server/api/ApiInfo.py` as the source of truth: `get_grad_list(count)` is serialized through `to_dict`, the first `childrenCoil` entry is merged into the root object when present, `childrenCoil` is deleted only in that branch, and `Next` is calculated from `CONFIG.infoConfigProperty.get_next(Weight)`. Rust should keep repository access in `Repository::grader_list`, Python-shape JSON construction in `grader_to_python_json`, and optional UI consumption behind a typed API helper instead of embedding route strings in components.

**Tech Stack:** Python FastAPI reference service, Rust Axum/SQLx API service, serde_json ordered JSON construction, React/Vite/Tauri TypeScript API client, Vitest, Rust `cargo test`, bounded live HTTP parity probes.

---

### Task 1: Capture the exact Python child-coil flattening contract

**Files:**
- Modify: `app/Server/rust_api_service/tests/routes.rs`
- Reference: `app/Server/api/ApiInfo.py`
- Reference: `app/Server/rust_api_service/src/models.rs`

**Step 1: Add a failing Rust test for rows that have a child coil**

Add a test fixture row where `child_id`, `child_secondary_coil_id`, `detection_time`, `defect_count_s`, `defect_count_l`, `check_status`, `status_l`, `status_s`, `grade`, and `msg` are all populated.

Add a test named `grader_list_flattens_first_child_coil_like_python_when_present` that calls `GET /grader_list?count=1` and asserts:

```rust
assert_eq!(rows[0]["Id"], 4201);
assert_eq!(rows[0]["SecondaryCoilId"], 42);
assert_eq!(rows[0]["DetectionTime"]["year"], 2026);
assert_eq!(rows[0]["DefectCountS"], 3);
assert_eq!(rows[0]["DefectCountL"], 4);
assert_eq!(rows[0]["CheckStatus"], 1);
assert_eq!(rows[0]["Status_L"], 2);
assert_eq!(rows[0]["Status_S"], 1);
assert_eq!(rows[0]["Grade"], 2);
assert_eq!(rows[0]["Msg"], "manual grade message");
assert!(rows[0].get("childrenCoil").is_none());
assert_eq!(rows[0]["Next"], "外委横切(配送)");
```

**Step 2: Run the focused failing test**

Run only when validation is authorized:

```powershell
cd app\Server\rust_api_service
cargo test grader_list_flattens_first_child_coil_like_python_when_present
```

Expected before implementation: FAIL if Rust still keeps `childrenCoil` or does not flatten child fields exactly like Python.

**Step 3: Implement the Python-compatible branch**

Modify `app/Server/rust_api_service/src/models.rs` in `grader_to_python_json`:

```rust
if let Some(child_id) = row.child_id {
    body.insert("Id".to_string(), json!(child_id));
    body.insert(
        "SecondaryCoilId".to_string(),
        json!(row.child_secondary_coil_id.unwrap_or(row.id)),
    );
    body.insert(
        "DetectionTime".to_string(),
        python_datetime_json(row.detection_time.as_deref()),
    );
    body.insert("DefectCountL".to_string(), json!(row.defect_count_l));
    body.insert("Status_L".to_string(), json!(row.status_l));
    body.insert("Grade".to_string(), json!(row.grade));
    body.insert("DefectCountS".to_string(), json!(row.defect_count_s));
    body.insert("CheckStatus".to_string(), json!(row.check_status));
    body.insert("Status_S".to_string(), json!(row.status_s));
    body.insert("Msg".to_string(), json!(row.msg));
} else {
    body.insert("childrenCoil".to_string(), json!([]));
}
body.insert("Next".to_string(), json!(next));
```

Preserve the current Python/FastAPI object member order for the no-child case. For the child case, match Python `d.update(sc[0]); del d["childrenCoil"]` insertion behavior as closely as serde_json map insertion allows.

**Step 4: Run the focused test**

Run only when validation is authorized:

```powershell
cd app\Server\rust_api_service
cargo test grader_list_flattens_first_child_coil_like_python_when_present
```

Expected after implementation: PASS.

### Task 2: Preserve existing no-child and validation behavior

**Files:**
- Modify: `app/Server/rust_api_service/tests/routes.rs`
- Modify if required: `app/Server/rust_api_service/src/routes.rs`
- Modify if required: `app/Server/rust_api_service/src/repository.rs`

**Step 1: Keep existing no-child behavior explicit**

Retain or tighten these existing tests:

```rust
#[tokio::test]
async fn grader_list_returns_python_secondary_coil_shape_and_next_text() { /* existing */ }

#[tokio::test]
async fn grader_list_secondary_coil_serializes_in_python_field_order() { /* existing */ }
```

The no-child response must continue to contain `childrenCoil: []`, because Python only deletes `childrenCoil` when the list is truthy.

**Step 2: Add count boundary tests**

Add tests for:

```rust
GET /grader_list
GET /grader_list?count=0
GET /grader_list?count=-1
GET /grader_list?count=abc
GET /grader_list?count=1001
```

Expected behavior to verify against live Python before locking in:

```text
missing count -> default 100
abc -> FastAPI 422 int_parsing
negative -> FastAPI-compatible validation or Python-observed behavior
0 -> Python-observed behavior from SQLAlchemy limit(0)
1001 -> Python-observed behavior; Rust clamp must not diverge if Python does not clamp
```

**Step 3: Correct Rust parsing or repository limiting only if Python differs**

If Python accepts `count=0`, Rust must not coerce it to `1` in a way that returns one row. If Python does not clamp large values, either remove Rust's `limit.clamp(1, 1000)` for this route or document and expose the deliberate safety cap in the ledger with evidence.

**Step 4: Run focused route tests**

Run only when validation is authorized:

```powershell
cd app\Server\rust_api_service
cargo test grader_list_
```

Expected: all `/grader_list` unit tests pass.

### Task 3: Align OpenAPI schema with the conditional response shape

**Files:**
- Modify: `app/Server/rust_api_service/src/routes.rs`
- Modify: `app/Server/rust_api_service/tests/routes.rs`

**Step 1: Update `GraderListItem` schema**

The schema must allow both Python shapes:

```json
{
  "childrenCoil": "present as [] when no child coil was flattened",
  "SecondaryCoilId/DetectionTime/DefectCount*/Status*/Grade/Msg": "present when first child coil was flattened"
}
```

Do not mark child-only fields as always required unless Python always emits them for every row in the selected dataset.

**Step 2: Add an OpenAPI regression assertion**

Extend `openapi_json_describes_grader_and_summary_sync_response_contracts_for_qml_tauri_ui` to verify:

```rust
assert_eq!(
    body["components"]["schemas"]["GraderListItem"]["additionalProperties"],
    json!(true)
);
assert!(body["components"]["schemas"]["GraderListItem"]["properties"].get("SecondaryCoilId").is_some());
assert!(body["components"]["schemas"]["GraderListItem"]["properties"].get("childrenCoil").is_some());
```

**Step 3: Run OpenAPI focused test**

Run only when validation is authorized:

```powershell
cd app\Server\rust_api_service
cargo test openapi_json_describes_grader_and_summary_sync_response_contracts_for_qml_tauri_ui
```

Expected: PASS.

### Task 4: Add a React/Tauri API helper without changing visible UI behavior

**Files:**
- Modify: `app/UI/MotionStudioWeb/src/services/api.ts`
- Modify: `app/UI/MotionStudioWeb/src/services/api.test.ts`

**Step 1: Add path builder and API helper**

Add:

```ts
export function buildGraderListPath(count = 100): string {
  const params = new URLSearchParams({ count: String(Math.trunc(count)) })
  return `/grader_list?${params.toString()}`
}
```

Expose through `coilApi`:

```ts
getGraderList: (count = 100) =>
  apiClient
    .get<BackendListResponse<unknown> | unknown[], BackendListResponse<unknown> | unknown[]>(buildGraderListPath(count))
    .then((response) => normalizeListResponse(response, normalizeCoil)),
```

This keeps the route available to Tauri/React screens and tools while leaving current sidebar behavior on `/coilList/{number}` unchanged.

**Step 2: Add TypeScript tests**

Add tests asserting:

```ts
expect(buildGraderListPath()).toBe('/grader_list?count=100')
expect(buildGraderListPath(3)).toBe('/grader_list?count=3')
```

Add a mocked API test that normalizes a Python-shaped grader item with `CreateTime` object and `CoilType` into a `CoilData` row whose `coilNo`, `dateTime`, `grade`, and raw object are preserved.

**Step 3: Run focused UI tests**

Run only when validation is authorized:

```powershell
cd app\UI\MotionStudioWeb
npm test -- src/services/api.test.ts
```

Expected: PASS.

### Task 5: Add a bounded live parity checker for the route

**Files:**
- Create: `app/Server/rust_api_service/tools/check_grader_list_parity.ps1`
- Modify: `docs/rust-tauri-parity.md`

**Step 1: Create a read-only checker**

Create a PowerShell script that accepts:

```powershell
param(
  [string]$PythonBase = 'http://127.0.0.1:5010',
  [string]$RustBase = 'http://127.0.0.1:5011',
  [string]$ViteBase = 'http://127.0.0.1:3015/api',
  [int[]]$Counts = @(0, 1, 3, 100)
)
```

For each count, request:

```text
/grader_list?count=<count>
```

Compare status code, content type, raw body bytes, parsed top-level array length, first-row key order, first-row `Id`, `CoilNo`, `CoilType`, `Weight`, `Next`, and whether `childrenCoil` is present.

**Step 2: Run checker only when services are already running and validation is authorized**

```powershell
app\Server\rust_api_service\tools\check_grader_list_parity.ps1 `
  -PythonBase http://127.0.0.1:5010 `
  -RustBase http://127.0.0.1:5011 `
  -ViteBase http://127.0.0.1:3015/api `
  -Counts 0,1,3,100
```

Expected: zero diff for supported counts, or a documented Python-observed exception where FastAPI itself errors.

**Step 3: Update ledger evidence**

Only after the focused Rust tests, UI tests, and live checker pass, update `docs/rust-tauri-parity.md` from `Partial` to either:

```text
Complete
```

or keep `Partial` with a precise remaining gap and the checker evidence attached.

### Task 6: Optional commit only when requested

**Files:**
- Stage only files changed for this plan.

**Step 1: Review changed files**

Run only when commit is requested:

```powershell
git diff -- app/Server/rust_api_service/tests/routes.rs app/Server/rust_api_service/src/models.rs app/Server/rust_api_service/src/routes.rs app/Server/rust_api_service/src/repository.rs app/UI/MotionStudioWeb/src/services/api.ts app/UI/MotionStudioWeb/src/services/api.test.ts app/Server/rust_api_service/tools/check_grader_list_parity.ps1 docs/rust-tauri-parity.md
```

**Step 2: Commit**

Run only when commit is requested:

```powershell
git add app/Server/rust_api_service/tests/routes.rs app/Server/rust_api_service/src/models.rs app/Server/rust_api_service/src/routes.rs app/Server/rust_api_service/src/repository.rs app/UI/MotionStudioWeb/src/services/api.ts app/UI/MotionStudioWeb/src/services/api.test.ts app/Server/rust_api_service/tools/check_grader_list_parity.ps1 docs/rust-tauri-parity.md

git commit -m "api: close grader-list parity"
```
