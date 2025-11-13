# Repository Guidelines

## Project Structure & Module Organization
- `服务/` hosts the FastAPI microservices consumed by the UI dashboards; keep routers, schemas, and dependency wiring here.
- `plcServer/` is the PLC bridge (`plcServer/main.py` launches uvicorn) and includes the PyInstaller spec plus PLC configuration JSON.
- `package/CoilDataBase/` contains the reusable DB client packaged via `setup.py`; edits here should stay backward compatible.
- `采集/` covers camera capture servers, and `UI/` holds front-end assets.
- `scripts/` stores one-off utilities (`scripts/train/` for model work, `scripts/redis_test/` for connectivity), while `test/` houses ad-hoc experiments; production configs live in `CONFIG_3D/` and troubleshooting output belongs in `debug_log/`.

## Build, Test, and Development Commands
- `python -m venv .venv && .venv\\Scripts\\Activate.ps1`: align the interpreter before any install.
- `pip install -r requirements.txt`: pull FastAPI, Ultralytics, Open3D, PLC drivers, and tooling (yapf, typer).
- `uvicorn 服务.main:app --reload --host 0.0.0.0 --port 6005`: run the public API locally.
- `python plcServer/main.py`: start the PLC adapter with values from `plcServer/config.py`; `pyinstaller --name plc_server plcServer/main.py` mirrors `plcServer/build.bat` for releases.
- `pytest scripts/train/pytorch-image-models/tests -m "not slow"`: primary regression suite; `pytest test/redis*` replays Redis flows.

## Coding Style & Naming Conventions
Adopt PEP 8 with 4-space indents, snake_case modules, and PascalCase models/controllers. Format staged files with `yapf -ir 服务/*.py plcServer/*.py`, and include type hints for new public functions. Name configs descriptively (`CONFIG_3D/coil-line-a.json`) so deployment scripts auto-detect the target line.

## Testing Guidelines
Store new tests alongside the code they verify: API checks in `test/test_<feature>.py`, GPU/model coverage in `scripts/train/pytorch-image-models/tests/`. Use `pytest` fixtures for PLC or Redis stubs, gate heavy cases with `@pytest.mark.skipif` when GPUs are unavailable, and capture sample payloads (see `test/redis*/t_redis.py`) so stateful regressions stay reproducible.

## Commit & Pull Request Guidelines
Keep commit summaries terse like the existing `ch 2d speed`, but express them as `<scope>: <imperative>` (example: `svc3d: lower-belt-threshold`). In PRs list the commands you ran (`pytest ...`, `uvicorn ...`), link issues, and attach screenshots when vision output changes. Highlight edits to shared assets (`CONFIG_3D/*.json`, `package/CoilDataBase/`) and note which services (PLC bridge, Redis microservice) require redeploy.

## Security & Configuration Tips
Do not commit live PLC, database, or Redis credentials; mirror the keys from `plcServer/config.py` inside a local `.env`. Verify the bundled `Redis-x64-5.0.14.1.msi` checksum before installing. When adjusting hardware parameters, copy the closest `CONFIG_3D/*.json`, document calibration values in-file, and keep obsolete configs in place until the rollout is verified.
