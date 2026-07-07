# Backup SQL and SQLite Deep Parity Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Close export parity for `GET /save_to_sql/{sql_file:path}` and its React/Tauri database-backup workflows, while explicitly documenting that restore/import parity is outside this export route until a real restore API is implemented.

**Architecture:** Use Python `package/CoilDataBase/CoilDataBase/backup.py` and `app/Server/api/ApiBackupServer.py` as the backend contract: `.sql` delegates to `mysqldump` or `pg_dump` with password environment variables, `.db` creates CoilDataBase ORM tables and copies table rows, unsupported suffixes return `{"state": false}`, and failures return `{"state": false}` rather than throwing route errors. Rust must preserve that observable contract while its SQLite writer uses repository-backed rows and explicit schema writers. React/Tauri should keep QML's save-dialog backup flow and keep restore visible as a disabled placeholder until a safe restore implementation exists.

**Tech Stack:** Python FastAPI reference API, CoilDataBase SQLAlchemy models, Rust Axum, rusqlite, MySQL/PostgreSQL dump tools, Tauri native save/open commands, React maintenance menu and system diagnostics, Vitest, focused Rust route tests, bounded live dump/snapshot smoke checks.

---

### Task 1: Capture Python `.sql` dump command contract

**Files:**
- Create: `test/backup_sql_parity/test_python_backup_reference.py`
- Modify: `app/Server/rust_api_service/tests/routes.rs`

**Step 1: Write failing Python command tests**

Mock `CoilDataBase.backup._current_url()` and `subprocess.run()` so no real database tools execute.

Required cases:
- MySQL URL builds `mysqldump_exe -h host -P port -u user --default-character-set=charset database`.
- MySQL password is passed through `MYSQL_PWD`, not on the command line.
- PostgreSQL URL builds `pg_dump_exe -h host -p port -U user -d database -f save_file`.
- PostgreSQL password is passed through `PGPASSWORD`.
- Missing URL port falls back to Python defaults.
- `_run_dump()` creates parent directories before running the tool.
- Timeout, `OSError`, and `CalledProcessError` return `False`.
- MySQL opens the output file before running the command, so a failed run may leave an empty file.

**Step 2: Run Python reference tests**

Run: `pytest test/backup_sql_parity/test_python_backup_reference.py -v`

Expected: FAIL until mocks capture the current Python behavior.

**Step 3: Add Rust dump-command tests**

Use fake dump executables or existing test helpers. Assert Rust command construction matches Python observable behavior, including password env vars and missing-tool `state = false`.

**Step 4: Run focused Rust dump tests**

Run: `cargo test --target-dir target-codex-test save_to_sql_writes_sql -- --nocapture`

Expected: FAIL for any command/env/default mismatch.

### Task 2: Lock `.sql` route behavior and path handling

**Files:**
- Modify: `app/Server/rust_api_service/src/routes.rs`
- Modify: `app/Server/rust_api_service/tests/routes.rs`
- Modify: `app/UI/MotionStudioWeb/src/services/api.ts`
- Test: `app/UI/MotionStudioWeb/src/services/api.test.ts`

**Step 1: Write failing route tests**

Required cases:
- `.sql` anywhere in the path triggers SQL dump behavior like Python's `if ".sql" in sql_file.lower()`.
- Unsupported suffix returns `{"state": false}`.
- A path containing both `.sql` and `.db` follows Python's sequential `if` behavior and documents which operation wins in Rust.
- Parent directories are created when possible.
- Missing `COIL_DATABASE_URL` or invalid database URL returns `{"state": false}`.
- Tool failure returns `{"state": false}` and does not expose credentials in response bodies.

**Step 2: Run focused route tests**

Run: `cargo test --target-dir target-codex-test save_to_sql_ -- --nocapture`

Expected: PASS after route state shape and path handling are locked.

**Step 3: Lock frontend path builder**

Assert Windows paths preserve Python path-route semantics:

```ts
expect(buildSaveToSqlPath('D:\\Backup\\coil.db')).toBe('/save_to_sql/D:/Backup/coil.db')
```

**Step 4: Run focused service tests**

Run: `npm test -- api backup --runInBand`

Expected: PASS for route builders and backup helper flow.

### Task 3: Lock SQLite schema and table coverage

**Files:**
- Modify: `app/Server/rust_api_service/src/routes.rs`
- Modify: `app/Server/rust_api_service/src/repository.rs`
- Modify: `app/Server/rust_api_service/tests/routes.rs`
- Create: `docs/backup-sqlite-schema-map.md`

**Step 1: Build a Python schema manifest**

From `CoilDataBase.models.Base.metadata.tables`, document each Python table name and expected columns in `docs/backup-sqlite-schema-map.md`.

**Step 2: Write failing SQLite schema tests**

Required cases:
- Rust `.db` creates every Python CoilDataBase table.
- The legacy `coil_summary_snapshot` compatibility table remains documented as Rust-only compatibility, not Python schema parity.
- Required columns match Python table names and common types closely enough for downstream import/read tools.
- Empty repository still creates all tables and returns `{"state": true}`.

**Step 3: Run focused schema tests**

Run: `cargo test --target-dir target-codex-test save_to_sql_writes_sqlite_snapshot_files_with_python_state_shape -- --nocapture`

Expected: PASS for existing coverage, then extend for any missing tables/columns.

**Step 4: Correct schema writers minimally**

Do not invent new denormalized tables except the already-documented compatibility table. Prefer matching Python table/column names over Rust-friendly names.

### Task 4: Lock SQLite row-copy fidelity

**Files:**
- Modify: `app/Server/rust_api_service/src/repository.rs`
- Modify: `app/Server/rust_api_service/src/routes.rs`
- Modify: `app/Server/rust_api_service/tests/routes.rs`

**Step 1: Write failing row fidelity tests**

Required row groups:
- `SecondaryCoil`, `Coil`, `AlarmInfo`, `CoilDefect`, `ManualDefect`.
- `CoilState`, `PlcData`, `PointData`, `LineData`.
- `DefectClassDict`, `CoilCheck`, `CoilAlarmStatus`, `DefectCheck`.
- Algorithm/runtime tables such as `DataEllipse`, `DeepPoint`, `DetectionSpeed`, `ImageJoinLog`.
- Alarm tables such as `AlarmFlatRoll`, `AlarmFlatRollData`, `AlarmTaperShape`, `AlarmLooseCoil`, `TaperShapePoint`.
- Capture/error/dictionary tables such as `CapTrueLog`, `CapTrueLogItem`, `ServerDetectionError`, `NextCodeDict`.

**Step 2: Run focused row-copy tests**

Run: `cargo test --target-dir target-codex-test save_to_sql_writes_sqlite_snapshot_files_with_python_state_shape -- --nocapture`

Expected: FAIL for any missing row group or synthesized field that should be copied from repository rows.

**Step 3: Correct repository backup queries**

Each backed-up table should copy real repository/MySQL rows when available. Avoid deriving rows from `coil_summary` if a real source table exists.

**Step 4: Add orphan-row cases**

Python ORM copy does not require every child row to have a corresponding `coil_summary`. Rust should preserve orphan rows from real source tables where the repository exposes them.

### Task 5: Define restore/import boundary explicitly

**Files:**
- Modify: `app/UI/MotionStudioWeb/src/utils/maintenanceTools.ts`
- Modify: `app/UI/MotionStudioWeb/src/utils/maintenanceTools.test.ts`
- Modify: `app/UI/MotionStudioWeb/src/components/MaintenanceMenuModal/index.tsx`
- Modify: `app/UI/MotionStudioWeb/src/components/MaintenanceMenuModal/MaintenanceMenuModal.test.ts`
- Create: `docs/database-restore-boundary.md`

**Step 1: Write UI boundary tests**

Required cases:
- `数据库备份 / 备份到 ...` is enabled in Tauri and routes through native save dialog.
- `数据库备份 / 从 备份 恢复` remains visible but disabled, matching QML's visible item and avoiding unsafe undeclared restore behavior.
- Disabled restore action has clear placeholder status text.
- No React path silently imports `.db` or `.sql` into production databases.

**Step 2: Run focused maintenance tests**

Run: `npm test -- maintenanceTools MaintenanceMenuModal backup --runInBand`

Expected: PASS after restore boundary is explicit.

**Step 3: Document restore scope**

`docs/database-restore-boundary.md` should state:
- `/save_to_sql` is export-only.
- Python/QML exposes restore menu text but no implemented safe restore path in the current reference surface.
- A future restore feature requires a separate route, authentication/operator confirmation, dry-run validation, and backup integrity checks.

### Task 6: Lock Tauri/Web backup UX parity

**Files:**
- Modify: `app/UI/MotionStudioWeb/src/utils/backup.ts`
- Modify: `app/UI/MotionStudioWeb/src/utils/backup.test.ts`
- Modify: `app/UI/MotionStudioWeb/src/pages/SystemDiagnostics/index.tsx`
- Modify: `app/UI/MotionStudioWeb/src/pages/SystemDiagnostics/SystemDiagnostics.test.ts`
- Modify: `app/UI/MotionStudioWeb/src-tauri/src/lib.rs`

**Step 1: Write helper tests**

Required cases:
- Default names use `lg3d_backup_yyyyMMdd_HHmmss.db` or `.sql`.
- Native save dialog receives `.db/.sql` filters.
- Cancelled or unavailable save path does not call `/save_to_sql`.
- Successful `{state:true}` opens the saved path through Tauri `open_path`.
- `{state:false}` shows failure and does not open the path.

**Step 2: Run focused UI/Tauri tests**

Run: `npm test -- backup SystemDiagnostics MaintenanceMenuModal nativeDialogs --runInBand`

Run Tauri-side tests only if they already exist and do not launch the full app.

Expected: PASS for backup menu and system diagnostics fallback.

**Step 3: Keep Web preview safe**

In Web preview, maintenance menu should direct operators to `/system` backup controls instead of trying to open native save dialogs.

### Task 7: Add bounded live backup checker

**Files:**
- Create: `scripts/backup_sql_parity/check_save_to_sql.py`
- Create: `docs/backup-sql-parity-samples.md`
- Modify: `docs/rust-tauri-parity.md`

**Step 1: Write the checker script**

The script should require explicit output directory and API URL:

```bash
python scripts/backup_sql_parity/check_save_to_sql.py --api http://127.0.0.1:5011 --out D:\Temp\lg3d-backup-check --mode sqlite
```

**Step 2: Keep side effects bounded**

The script must refuse broad or production directories unless a force flag is provided. It must delete only files it created in the explicit output directory.

**Step 3: Check SQLite output invariants**

Assert:
- Route returns `{"state": true}` for `.db` when repository is available.
- SQLite header is valid.
- Expected table list exists.
- Representative row counts and key values are present.

**Step 4: Check SQL dump output when explicitly enabled**

Only run `.sql` checks with a flag such as `--allow-sql-dump`, because this executes external tools and may touch live DB credentials. Assert route returns state and file existence; never print passwords.

**Step 5: Document sample results**

Record API URL, output mode, table count, selected row counts, dump tool availability, and any skipped live SQL dump reason.

### Task 8: Final evidence and ledger update

**Files:**
- Modify: `docs/backup-sqlite-schema-map.md`
- Modify: `docs/database-restore-boundary.md`
- Modify: `docs/backup-sql-parity-samples.md`
- Modify: `docs/rust-tauri-parity.md`

**Step 1: Run focused Python reference tests**

Run: `pytest test/backup_sql_parity -v`

Expected: PASS for Python command and SQLite reference behavior captured by mocks/fixtures.

**Step 2: Run focused Rust tests**

Run: `cargo test --target-dir target-codex-test save_to_sql openapi_json_describes_save_to_sql_response_for_qml_tauri_ui -- --nocapture`

Expected: PASS for route state, dump tool behavior, SQLite schema, row-copy fidelity, and OpenAPI response.

**Step 3: Run focused UI tests**

Run: `npm test -- backup MaintenanceMenuModal SystemDiagnostics nativeDialogs api --runInBand`

Expected: PASS for QML/Tauri backup flow and restore boundary.

**Step 4: Run bounded checker**

Run the `.db` checker against an explicit temporary output directory. Run `.sql` mode only when external dump tools and non-production credentials are explicitly approved.

**Step 5: Update parity row only after evidence exists**

Move `Backup SQL/SQLite task` from Partial only after schema/row-copy tests, UI tests, and bounded `.db` live checker are documented. Keep restore/import parity as a separate future feature unless a real reference-compatible restore API is implemented.

**Step 6: Optional commit only when requested by repository owner**

Do not commit automatically in this workspace. If requested, use:

```bash
git add app/Server/rust_api_service app/UI/MotionStudioWeb test/backup_sql_parity scripts/backup_sql_parity docs

git commit -m "api: close database backup parity"
```
