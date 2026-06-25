import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PACKAGE_DIR = PROJECT_ROOT / "package" / "CoilDataBase"

for import_path in (PROJECT_ROOT, DB_PACKAGE_DIR):
    path_text = str(import_path)
    if path_text not in sys.path:
        sys.path.insert(0, path_text)

from CoilDataBase.migration_add_max_defect_fields import main

if __name__ == "__main__":
    main()
