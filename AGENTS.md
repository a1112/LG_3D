# Repository Guidelines

## Project Structure & Module Organization
- `服务/` hosts the FastAPI microservices consumed by the UI dashboards; keep routers, schemas, and dependency wiring here.
- `plcServer/` is the PLC bridge (`plcServer/main.py` launches uvicorn) and includes the PyInstaller spec plus PLC configuration JSON.
- `app/` contains the main application logic: `algorithm_runtime/` for detection algorithms, `Communication/` for TCP/HTTP servers, `plcServer/` for PLC bridge.
- `package/CoilDataBase/` contains the reusable DB client packaged via `setup.py`; edits here should stay backward compatible.
- `采集/` covers camera capture servers, and `UI/` holds front-end assets.
- `scripts/` stores one-off utilities (`scripts/train/` for model work, `scripts/redis_test/` for connectivity), while `test/` houses ad-hoc experiments; production configs live in `CONFIG_3D/` and troubleshooting output belongs in `debug_log/`.
- `Base/` contains shared property definitions and data structures.

## Build, Test, and Development Commands
- `python -m venv .venv && .venv\\Scripts\\Activate.ps1`: align the interpreter before any install.
- `pip install -r requirements.txt`: pull FastAPI, Ultralytics, Open3D, PLC drivers, and tooling (yapf, typer).
- `uvicorn 服务.main:app --reload --host 0.0.0.0 --port 6005`: run the public API locally.
- `python plcServer/main.py`: start the PLC adapter with values from `plcServer/config.py`; `pyinstaller --name plc_server plcServer/main.py` mirrors `plcServer/build.bat` for releases.
- `pytest scripts/train/pytorch-image-models/tests -m "not slow"`: primary regression suite.
- `pytest test/redis测试/t_redis.py`: run single Redis test.
- `pytest test/ -v`: run all tests with verbose output.
- `pytest test/test_file.py -v`: run specific test file.
- `pytest test/test_file.py::test_function -v`: run single test function.

## Coding Style & Naming Conventions
Adopt PEP 8 with 4-space indents, snake_case modules/functions, and PascalCase classes.

### Import Order
1. Standard library imports (os, sys, time, threading, etc.)
2. Third-party imports (fastapi, sqlalchemy, cv2, numpy, etc.)
3. Local application imports (from Base, from app, from CoilDataBase, etc.)

### Type Hints
- Include type hints for new public functions: `def add_coil(coil: dict) -> None:`
- Use `Optional[T]` for nullable fields: `self.flatRollData: Optional[FlatRollData] = None`

### Class & Function Naming
- Classes: PascalCase (`SecondaryCoil`, `AlarmData`, `ThreadLis`)
- Functions: snake_case (`add_coil`, `kill_process`, `get_folder_last_by_folder`)
- Private functions: prefix with underscore (`_detectionAlarmDefect_`)

### Formatting
- Format staged files with `yapf -ir 服务/*.py plcServer/*.py app/**/*.py`
- Keep line length reasonable (aim for <120 chars)

### Error Handling
- Always specify exception types: `except Exception as e:` instead of bare `except:`
- Use logger from `Log import logger` for error logging: `logger.debug(f"解析数据包失败: {e}")`
- Log specific error messages with context

### Constants & Config
- Name configs descriptively (`CONFIG_3D/coil-line-a.json`) so deployment scripts auto-detect the target line.
- Module-level constants use UPPER_SNAKE_CASE: `address = '0.0.0.0'`, `port = 6001`

### File Organization
- Models in `app/algorithm_runtime/AlarmDetection/Configs/` for configuration classes
- Data processing in `app/algorithm_runtime/AlarmDetection/DataProcessing/`
- Results in `app/algorithm_runtime/AlarmDetection/Result/`

## Testing Guidelines
Store new tests alongside the code they verify:
- API checks in `test/test_<feature>.py`
- GPU/model coverage in `scripts/train/pytorch-image-models/tests/`
- Use `pytest` fixtures for PLC or Redis stubs
- Gate heavy cases with `@pytest.mark.skipif` when GPUs are unavailable
- Capture sample payloads (see `test/redis测试/t_redis.py`) so stateful regressions stay reproducible
- Test file naming: `test_<module_name>.py` or descriptive names like `t_redis.py`
- Test function naming: `test_<function_name>` prefix

## Commit & Pull Request Guidelines
Keep commit summaries terse like the existing `ch 2d speed`, but express them as `<scope>: <imperative>` (example: `svc3d: lower-belt-threshold`).
Common scopes:
- `algo`: algorithm changes
- `api`: FastAPI endpoint changes
- `db`: database schema/migration changes
- `ui`: frontend changes
- `plc`: PLC communication changes
- `infra`: infrastructure/deployment changes

In PRs:
- List the commands you ran (`pytest ...`, `uvicorn ...`)
- Link issues
- Attach screenshots when vision output changes
- Highlight edits to shared assets (`CONFIG_3D/*.json`, `package/CoilDataBase/`)
- Note which services (PLC bridge, Redis microservice) require redeploy

## Security & Configuration Tips
- Do not commit live PLC, database, or Redis credentials
- Mirror the keys from `plcServer/config.py` inside a local `.env`
- Verify the bundled `Redis-x64-5.0.14.1.msi` checksum before installing
- When adjusting hardware parameters, copy the closest `CONFIG_3D/*.json`, document calibration values in-file, and keep obsolete configs in place until the rollout is verified
- Use SQLAlchemy connection pooling with `pool_pre_ping=True` for connection health checks
- Database connections should use connection pooling: `pool_size=10, max_overflow=20, pool_timeout=30, pool_recycle=3600`

## Python Environment
- Python version: 3.x (check `requirements.txt` for specific version)
- Virtual environment: `.venv/` directory
- Main entry points:
  - `app/plcServer/main.py`: PLC bridge server
  - `app/algorithm_runtime/main.py`: Algorithm runtime
  - `app/Communication/TcpServer.py`: TCP data receiver
  - `app/Communication/HttpServer.py`: HTTP API server
