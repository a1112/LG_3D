# Repository Guidelines

## Project Structure & Module Organization
- `服务/` hosts FastAPI microservices consumed by UI dashboards; routers, schemas, and dependency wiring here.
- `plcServer/` PLC bridge (`main.py` launches uvicorn) with PyInstaller spec and PLC configuration JSON.
- `app/` main application logic: `algorithm_runtime/` for detection algorithms, `Communication/` for TCP/HTTP servers, `plcServer/` for PLC bridge.
- `package/CoilDataBase/` reusable DB client packaged via `setup.py`; edits must stay backward compatible.
- `采集/` camera capture servers; `UI/` front-end assets.
- `scripts/` utilities (`train/` for models, `redis_test/` for connectivity); `test/` for ad-hoc experiments.
- `CONFIG_3D/` production configs; `debug_log/` for troubleshooting output.
- `Base/` shared property definitions and data structures.

## Build, Test, and Development Commands
- `python -m venv .venv && .venv\\Scripts\\Activate.ps1`: activate virtual environment before installing.
- `pip install -r requirements.txt`: FastAPI, Ultralytics, Open3D, PLC drivers, tooling (yapf).
- `uvicorn 服务.main:app --reload --host 0.0.0.0 --port 6005`: run public API locally.
- `python plcServer/main.py`: start PLC adapter with values from `plcServer/config.py`; use `pyinstaller --name plc_server plcServer/main.py` for releases.
- `pytest scripts/train/pytorch-image-models/tests -m "not slow"`: primary regression suite.
- `pytest test/redis测试/t_redis.py`: run single Redis test.
- `pytest test/ -v`: run all tests with verbose output.
- `pytest test/test_file.py -v`: run specific test file.
- `pytest test/test_file.py::test_function -v`: run single test function.
- Service batch files: `app/Communication/start.bat`, `app/plcServer/build.bat`, `app/UI/MotionStudio/start_ui.bat`.

## Coding Style & Naming Conventions
PEP 8 with 4-space indents, snake_case modules/functions, PascalCase classes.

### Import Order
1. Standard library (os, sys, time, threading, pathlib, logging, etc.)
2. Third-party (fastapi, sqlalchemy, cv2, numpy, redis, etc.)
3. Local application (from Base, from app, from CoilDataBase, etc.)

Example:
```python
import logging
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from Base.CONFIG import serverConfigProperty
from app.algorithm_runtime.main import main
```

### Type Hints
- Public functions: `def add_coil(coil: dict) -> None:`
- Nullable fields: `self.flatRollData: Optional[FlatRollData] = None`

### Class & Function Naming
- Classes: PascalCase (`SecondaryCoil`, `AlarmData`, `ThreadLis`)
- Functions: snake_case (`add_coil`, `kill_process`, `get_folder_last_by_folder`)
- Private: prefix underscore (`_detectionAlarmDefect_`)

### Formatting
- Format staged files: `yapf -ir 服务/*.py plcServer/*.py app/**/*.py`
- Line length: aim for <120 characters

### Error Handling
- Always specify exception types: `except Exception as e:` (never bare `except:`)
- Logger imports: `from Log import logger` OR `from utils.MultiprocessColorLogger import logger`
- Log with context: `logger.debug(f"解析数据包失败: {e}")`, `logger.error(f"camera {key} exception: {e}")`
- Log levels: `debug` for verbose, `info` for normal operations, `warning` for recoverable issues, `error` for failures.

### Constants & Config
- Config files: descriptive names in `CONFIG_3D/` (e.g., `coil-line-a.json`)
- Module constants: UPPER_SNAKE_CASE (`SERVER_ADDRESS = '0.0.0.0'`, `DEFAULT_PORT = 6001`)

### File Organization
- Models: `app/algorithm_runtime/AlarmDetection/Configs/`
- Data processing: `app/algorithm_runtime/AlarmDetection/DataProcessing/`
- Results: `app/algorithm_runtime/AlarmDetection/Result/`

### Concurrency
- Threading: inherit from `Thread` for camera capture (`app/CapTrue/Camera.py`)
- Multiprocessing: use `multiprocessing.Queue`, `multiprocessing.Process` for isolation
- Async: use `async def` for FastAPI endpoints; avoid `asyncio.run()` in sync contexts.

## Testing Guidelines
Store tests alongside verified code:
- API checks: `test/test_<feature>.py`
- GPU/model coverage: `scripts/train/pytorch-image-models/tests/`
- Fixtures: use `pytest` fixtures for PLC or Redis stubs
- GPU gating: `@pytest.mark.skipif` when unavailable
- Payload capture: `test/redis测试/t_redis.py` for stateful regressions
- Test file naming: `test_<module_name>.py` or descriptive like `t_redis.py`
- Test function naming: `test_<function_name>` prefix
- Run single test: `pytest test/test_file.py::test_function -v`

## Test Mode
System supports test mode for development:
- Enable via UI (Settings → Other → Test Mode) or environment variable `API_DEVELOPER_MODE=true`
- Test data from `TestData/125143/` directory
- Configuration in `CONFIG_3D/test_mode_config.json` (git-ignored)
- Visual indicator: "[测试模式]" in window title when active

## Commit & Pull Request Guidelines
Commit format: `<scope>: <imperative>`, e.g., `svc3d: lower-belt-threshold`.
Scopes: `algo` (algorithm), `api` (FastAPI), `db` (schema/migration), `ui` (frontend), `plc` (PLC communication), `infra` (infrastructure).

PR checklist:
- Commands run: `pytest ...`, `uvicorn ...`
- Issue links included
- Screenshots for vision output changes
- Highlight edits to shared assets (`CONFIG_3D/*.json`, `package/CoilDataBase/`)
- Note services requiring redeploy (PLC bridge, Redis microservice)

## Security & Configuration
- Never commit live PLC, database, or Redis credentials
- Mirror `plcServer/config.py` keys in local `.env`
- Verify Redis MSI checksum before installing
- Adjusting hardware parameters: copy closest `CONFIG_3D/*.json`, document calibration in-file, keep obsolete configs until rollout verified
- SQLAlchemy: `pool_pre_ping=True`, `pool_size=10`, `max_overflow=20`, `pool_timeout=30`, `pool_recycle=3600`

## Python Environment
- Python: 3.11.9
- Virtual environment: `.venv/`
- Entry points:
  - `app/plcServer/main.py`: PLC bridge server
  - `app/algorithm_runtime/main.py`: Algorithm runtime
  - `app/Communication/TcpServer.py`: TCP data receiver
  - `app/algorithm_runtime_2D/server.py`: 2D API server (port 6020)
  - `app/Server/api/api_core.py`: Core API with image caching
