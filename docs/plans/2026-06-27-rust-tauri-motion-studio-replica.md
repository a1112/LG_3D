# Rust Tauri Motion Studio Replica Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Recreate the Python FastAPI service in Rust and recreate the QML MotionStudio desktop UI with Tauri + React until the core workflows are functionally equivalent.

**Architecture:** Build a Rust Axum API service that preserves the existing Python route contracts, connects to the same `COIL_DATABASE_URL`, and initially coexists with the current Rust image service before later unifying image/data serving. Keep the Tauri + React app as the replacement shell, progressively filling QML-equivalent workflows and pointing Vite/Tauri to the Rust API once each vertical slice is verified.

**Tech Stack:** Rust 2021/2024, Axum, SQLx MySQL, Tokio, Serde, Tauri 2, React 18, Vite, TypeScript, TanStack Query, Zustand, Ant Design, Three.js.

---

### Task 1: Rust API Service Baseline

**Files:**
- Create: `app/Server/rust_api_service/Cargo.toml`
- Create: `app/Server/rust_api_service/src/lib.rs`
- Create: `app/Server/rust_api_service/src/main.rs`
- Create: `app/Server/rust_api_service/src/config.rs`
- Create: `app/Server/rust_api_service/src/models.rs`
- Create: `app/Server/rust_api_service/src/repository.rs`
- Create: `app/Server/rust_api_service/src/routes.rs`

**Step 1: Write failing tests**

Add route tests for:
- `GET /health` returns `{ "status": "ok", "service": "rust_api_service" }`.
- `GET /coilList/20` returns Python-compatible list JSON with `Id`, `CoilNo`, `CreateTime`, `AlarmInfo`, `DefectCountS`, `DefectCountL`, `Status_S`, `Status_L`, `Grade`, and `childrenCoilDefect`.
- `GET /search/defects/:coil_id/:surface` returns defect rows with Python field names.
- `normalize_database_url` converts `mysql+pymysql://...?...` into a SQLx-compatible MySQL URL.

**Step 2: Run tests to verify failure**

Run: `cargo test` in `app/Server/rust_api_service`.

Expected: FAIL because the crate and route implementation do not exist yet.

**Step 3: Implement minimal service**

Implement:
- App construction with an injected repository trait for testability.
- An in-memory repository for tests.
- A SQLx MySQL repository for production.
- JSON response models matching the current Python/QML contract.
- `main.rs` CLI with `--host`, `--port`, and env-driven database URL.

**Step 4: Verify**

Run:
- `cargo test`
- `cargo check`

Expected: PASS.

### Task 2: Database-Backed Coil and Defect Endpoints

**Files:**
- Modify: `app/Server/rust_api_service/src/repository.rs`
- Modify: `app/Server/rust_api_service/src/routes.rs`

**Step 1: Write failing integration checks**

Add tests covering SQL field aliases and empty-table behavior using repository-level test doubles.

**Step 2: Implement SQL queries**

Implement MySQL queries for:
- `coil_summary` list/search/detail.
- `coildefect` / `CoilDefect` defect list.
- `defectclassdict` defect dictionary.
- `database_info`, `version`, `delay`, `runtime_info`.

**Step 3: Verify against local MySQL**

Run the Rust service on an unused port with `COIL_DATABASE_URL` and compare sample responses to Python service `5010`.

### Task 3: React API Target Switching

**Files:**
- Modify: `app/UI/MotionStudioWeb/vite.config.ts`
- Modify: `app/UI/MotionStudioWeb/.env.development`
- Modify: `app/UI/MotionStudioWeb/src/services/api.ts`

**Step 1: Write failing tests**

Add TypeScript tests for base URL construction and Python-compatible response normalization.

**Step 2: Implement**

Allow `VITE_API_BASE_URL` and `VITE_WS_BASE_URL` to select Python or Rust API without code changes.

**Step 3: Verify**

Run `npm test` and `npm run build`.

### Task 4: QML Workflow Parity Inventory

**Files:**
- Create: `docs/rust-tauri-parity.md`

**Step 1: Extract route usage**

Generate a table from `app/UI/MotionStudio/qml/Api/*.qml` and React service calls.

**Step 2: Map features**

Track each QML workflow:
- Left coil list/search/refresh.
- Data show S/L area viewer, height lines, height point, 3D mesh/render.
- Defect list/detail/manual defect CRUD/export.
- Alarm page, hardware/camera status, PLC curves.
- Settings/test mode/camera settings/software update.
- Backup/export/re-detection/2D algorithm test WebSockets.

**Step 3: Keep status current**

Mark each workflow as missing, partial, compatible, or verified.

### Task 5: Tauri + React UI Parity Slices

**Files:**
- Modify React pages/components under `app/UI/MotionStudioWeb/src/`

**Step 1: Implement core shell parity**

Match QML navigation, left list, footer status, top tool areas, and S/L data layout.

**Step 2: Implement data parity**

Wire coil list/search/refresh/detail, area tiles, preview/source images, defects, height lines, and 3D data.

**Step 3: Implement operations parity**

Wire export, manual defect editing, test mode, camera settings, and diagnostics.

**Step 4: Verify visually and functionally**

Run Tauri dev app, compare against QML app screenshots, verify API calls target Rust service, and keep a mismatch ledger.

### Task 6: Service Consolidation and Launch Scripts

**Files:**
- Create/modify Rust launch scripts under `scripts/` or `app/Server/`
- Modify: `app/UI/MotionStudioWeb/README.md`
- Modify: `app/UI/MotionStudioWeb/DEPLOYMENT.md`

**Step 1: Decide service topology**

Either:
- Keep `rust_api_service` and `rust_image_service` as two services behind Vite/Tauri proxy, or
- Merge image routes into the API service once behavior is stable.

**Step 2: Implement production startup**

Add Windows startup commands that start Rust API, Rust image service if separate, and Tauri app.

**Step 3: Verify**

Start from a clean terminal with `COIL_DATABASE_URL`, run the full app, and verify the core workflows without Python FastAPI.
