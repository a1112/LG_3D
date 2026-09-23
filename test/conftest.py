"""Keep unit-test imports away from production databases and service scripts."""
import os
from pathlib import Path
from tempfile import TemporaryDirectory

# Resolve the project package before service tests prepend their own folders.
import scripts  # noqa: F401


_TEST_DIRECTORY = TemporaryDirectory(prefix="lg3d-tests-", ignore_cleanup_errors=True)
_TEST_DATABASE = Path(_TEST_DIRECTORY.name) / "coil.db"
os.environ["COIL_DATABASE_URL"] = f"sqlite:///{_TEST_DATABASE.as_posix()}"
os.environ["COIL_DATABASE_AUTO_CREATE"] = "false"
os.environ["IMAGE_CACHE_BACKEND"] = "memory"
os.environ["CONFIG_3D_DIR"] = str(Path(__file__).resolve().parents[1] / "CONFIG_3D")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
