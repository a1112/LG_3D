# OpenAPI Docs UI Deep Parity Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Bring Rust `/docs` and `/redoc` closer to FastAPI Swagger UI/ReDoc behavior beyond the current lightweight operation list.

**Architecture:** Keep the existing local/offline static assets, but add missing observable behavior in small browser-verifiable increments. Treat Python/FastAPI docs as the reference for page shell, OAuth redirect, operation grouping, expandable operation details, schemas, request/response rendering, and browser interaction behavior. Avoid remote CDN dependencies unless explicitly approved.

**Tech Stack:** Rust, Axum route tests in `app/Server/rust_api_service/tests/routes.rs`, inline static assets in `app/Server/rust_api_service/src/routes.rs`, optional Browser QA through the in-app browser, Python/FastAPI reference pages `/docs` and `/redoc`.

---

### Task 1: Lock docs shell metadata and asset parity

**Files:**
- Modify: `app/Server/rust_api_service/tests/routes.rs`
- Modify: `app/Server/rust_api_service/src/routes.rs`
- Modify: `docs/rust-tauri-parity.md`

**Step 1: Write the failing test**

Lock closer FastAPI shell details so future changes do not drift:

```rust
#[tokio::test]
async fn docs_shell_uses_fastapi_titles_and_oauth_redirect_aliases() {
    let docs = request_response(app_with_seed_data(), "GET", "/docs").await;
    assert_eq!(docs.status(), StatusCode::OK);
    let docs_body = String::from_utf8(response_bytes(docs).await.to_vec()).expect("docs html");
    assert!(docs_body.contains("<title>FastAPI - Swagger UI</title>"));
    assert!(docs_body.contains("oauth2RedirectUrl"));
    assert!(docs_body.contains("/docs/oauth2-redirect"));

    let redirect_alias = request_response(app_with_seed_data(), "GET", "/docs/oauth2-redirect.html").await;
    assert_eq!(redirect_alias.status(), StatusCode::OK);

    let redoc = request_response(app_with_seed_data(), "GET", "/redoc").await;
    assert_eq!(redoc.status(), StatusCode::OK);
    let redoc_body = String::from_utf8(response_bytes(redoc).await.to_vec()).expect("redoc html");
    assert!(redoc_body.contains("<title>FastAPI - ReDoc</title>"));
    assert!(redoc_body.contains("spec-url=\"/openapi.json\""));
}
```

**Step 2: Run test to verify it fails**

Run:

```powershell
cd app/Server/rust_api_service
cargo test docs_shell_uses_fastapi_titles_and_oauth_redirect_aliases --test routes
```

Expected: FAIL only for missing shell/alias details.

**Step 3: Write minimal implementation**

Patch `swagger_docs()`, `redoc_docs()`, and OAuth redirect routes to mirror FastAPI-observable shell details while keeping local assets.

**Step 4: Run test**

Run:

```powershell
cd app/Server/rust_api_service
cargo test docs_shell_uses_fastapi_titles_and_oauth_redirect_aliases --test routes
```

Expected: PASS.

**Step 5: Commit**

```powershell
git add app/Server/rust_api_service/tests/routes.rs app/Server/rust_api_service/src/routes.rs docs/rust-tauri-parity.md
git commit -m "api: align docs html shells"
```

### Task 2: Group operations by tag like Swagger UI/ReDoc

**Files:**
- Modify: `app/Server/rust_api_service/tests/routes.rs`
- Modify: `app/Server/rust_api_service/src/routes.rs`

**Step 1: Write the failing asset test**

```rust
#[tokio::test]
async fn docs_static_assets_group_operations_by_tag() {
    let js = request_response(app_with_seed_data(), "GET", "/static/swagger-ui-bundle.js").await;
    let body = String::from_utf8(response_bytes(js).await.to_vec()).expect("swagger js");
    assert!(body.contains("groupOperationsByTag"));
    assert!(body.contains("docs-tag-section"));
    assert!(body.contains("docs-tag-heading"));

    let css = request_response(app_with_seed_data(), "GET", "/static/swagger-ui.css").await;
    let css_body = String::from_utf8(response_bytes(css).await.to_vec()).expect("swagger css");
    assert!(css_body.contains("docs-tag-section"));
    assert!(css_body.contains("docs-tag-heading"));
}
```

**Step 2: Run test to verify it fails**

Run:

```powershell
cd app/Server/rust_api_service
cargo test docs_static_assets_group_operations_by_tag --test routes
```

Expected: FAIL until grouping support exists.

**Step 3: Write minimal implementation**

Update both Swagger and ReDoc inline JS renderers to group operations by `operation.tags[0]`, falling back to `default`. Render each group with a heading and preserve current search/filter behavior across groups.

**Step 4: Run test**

Run:

```powershell
cd app/Server/rust_api_service
cargo test docs_static_assets_group_operations_by_tag --test routes
```

Expected: PASS.

**Step 5: Commit**

```powershell
git add app/Server/rust_api_service/tests/routes.rs app/Server/rust_api_service/src/routes.rs
git commit -m "api: group docs operations by tag"
```

### Task 3: Add expandable/collapsible operation details

**Files:**
- Modify: `app/Server/rust_api_service/tests/routes.rs`
- Modify: `app/Server/rust_api_service/src/routes.rs`

**Step 1: Write the failing test**

```rust
#[tokio::test]
async fn docs_static_assets_support_expandable_operations() {
    let js = request_response(app_with_seed_data(), "GET", "/static/swagger-ui-bundle.js").await;
    let body = String::from_utf8(response_bytes(js).await.to_vec()).expect("swagger js");
    assert!(body.contains("toggleOperationDetails"));
    assert!(body.contains("aria-expanded"));
    assert!(body.contains("docs-operation-toggle"));

    let css = request_response(app_with_seed_data(), "GET", "/static/swagger-ui.css").await;
    let css_body = String::from_utf8(response_bytes(css).await.to_vec()).expect("swagger css");
    assert!(css_body.contains("docs-operation-toggle"));
}
```

**Step 2: Run test**

Run:

```powershell
cd app/Server/rust_api_service
cargo test docs_static_assets_support_expandable_operations --test routes
```

Expected: FAIL until expand/collapse markers exist.

**Step 3: Write minimal implementation**

Render each operation header as a button with `aria-expanded`, initially collapsed like Swagger UI. Clicking toggles parameter/request/response/schema details.

**Step 4: Run test**

Run:

```powershell
cd app/Server/rust_api_service
cargo test docs_static_assets_support_expandable_operations --test routes
```

Expected: PASS.

**Step 5: Commit**

```powershell
git add app/Server/rust_api_service/tests/routes.rs app/Server/rust_api_service/src/routes.rs
git commit -m "api: make docs operations expandable"
```

### Task 4: Render schemas/components and model references

**Files:**
- Modify: `app/Server/rust_api_service/tests/routes.rs`
- Modify: `app/Server/rust_api_service/src/routes.rs`

**Step 1: Write the failing test**

```rust
#[tokio::test]
async fn docs_static_assets_render_component_schemas() {
    let js = request_response(app_with_seed_data(), "GET", "/static/redoc.standalone.js").await;
    let body = String::from_utf8(response_bytes(js).await.to_vec()).expect("redoc js");
    assert!(body.contains("renderComponentSchemas"));
    assert!(body.contains("components.schemas"));
    assert!(body.contains("docs-schema-section"));

    let css = request_response(app_with_seed_data(), "GET", "/static/swagger-ui.css").await;
    let css_body = String::from_utf8(response_bytes(css).await.to_vec()).expect("css");
    assert!(css_body.contains("docs-schema-section"));
}
```

**Step 2: Run test**

Run:

```powershell
cd app/Server/rust_api_service
cargo test docs_static_assets_render_component_schemas --test routes
```

Expected: FAIL until schema section rendering exists.

**Step 3: Write minimal implementation**

Render a model/schema section from `schema.components.schemas`, including schema name, type, required fields, properties, `$ref`, arrays, enum values, and defaults. Keep this read-only and static; do not implement Try-It-Out.

**Step 4: Run test**

Run:

```powershell
cd app/Server/rust_api_service
cargo test docs_static_assets_render_component_schemas --test routes
```

Expected: PASS.

**Step 5: Commit**

```powershell
git add app/Server/rust_api_service/tests/routes.rs app/Server/rust_api_service/src/routes.rs
git commit -m "api: render docs component schemas"
```

### Task 5: Add browser QA for interactive docs behavior

**Files:**
- Modify: `docs/rust-tauri-parity.md`

**Step 1: Start services only with explicit authorization**

Only after user authorization:

```powershell
cd app/Server/rust_api_service
cargo run -- --host 127.0.0.1 --port 5011
```

**Step 2: Browser QA checklist**

Use the in-app browser or Playwright-compatible browser tool:

- Open `http://127.0.0.1:5011/docs`.
- Confirm title and page content render without a framework error overlay.
- Search for `camera_adjust`; confirm only matching operations remain.
- Expand one operation; confirm parameters, request body, responses, and schema refs are visible.
- Open `http://127.0.0.1:5011/redoc`.
- Confirm tag grouping, operation details, schema section, and filter behavior.
- Confirm console has no fresh errors.

**Step 3: Record evidence**

Update `docs/rust-tauri-parity.md` with date, tested URLs, browser findings, and remaining known gaps.

### Task 6: Decide whether full bundled assets are required

**Files:**
- Modify: `docs/rust-tauri-parity.md`
- Optional create: `app/Server/rust_api_service/static/` assets if approved

**Step 1: Compare options**

Two viable endpoints:

- `Local lightweight parity`: no CDN, implements enough read-only operator behavior locally.
- `Bundled upstream parity`: vendor Swagger UI/ReDoc static bundles into the Rust service.

**Step 2: If bundled upstream assets are chosen**

Add a dependency/source audit:

- asset source and version
- license
- file size impact
- offline behavior
- update process

Do not fetch or vendor assets without explicit approval.

**Step 3: Ledger update**

If lightweight behavior covers the operator requirements, keep the row `Partial` only for missing Try-It-Out/OAuth internals. If bundled upstream assets are approved and verified, update the row with exact asset version and QA evidence.
