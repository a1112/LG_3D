import argparse
import importlib.util
import logging
import sys
from collections import deque
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import datetime, time
from pathlib import Path
from typing import Iterable, Iterator, List, Optional, Sequence, Set
from urllib import error, request


SERVER_ROOT = Path(__file__).resolve().parents[1]
BUILDER_PATH = SERVER_ROOT / "cache" / "area_tile_builder.py"
_builder_spec = importlib.util.spec_from_file_location("area_tile_builder", BUILDER_PATH)
if _builder_spec is None or _builder_spec.loader is None:
    raise RuntimeError(f"failed to load AREA tile builder: {BUILDER_PATH}")
_builder_module = importlib.util.module_from_spec(_builder_spec)
sys.modules[_builder_spec.name] = _builder_module
_builder_spec.loader.exec_module(_builder_module)

DEFAULT_AREA_TILE_COUNT = _builder_module.DEFAULT_AREA_TILE_COUNT
rebuild_area_tile_cache = _builder_module.rebuild_area_tile_cache


IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png")
DEFAULT_TYPES = ("AREA", "AREA_MASK")


def _parse_coil_ids(values: Optional[Sequence[str]]) -> Set[str]:
    result: Set[str] = set()
    for value in values or []:
        for part in value.split(","):
            part = part.strip()
            if part:
                result.add(part)
    return result


def _coil_number(coil_dir: Path) -> Optional[int]:
    try:
        return int(coil_dir.name)
    except ValueError:
        return None


def _coil_in_scope(coil_dir: Path,
                   coil_ids: Set[str],
                   from_id: Optional[int],
                   to_id: Optional[int]) -> bool:
    if coil_ids and coil_dir.name not in coil_ids:
        return False
    coil_number = _coil_number(coil_dir)
    if from_id is not None and (coil_number is None or coil_number < from_id):
        return False
    if to_id is not None and (coil_number is None or coil_number > to_id):
        return False
    return True


def _parse_datetime(value: Optional[str], *, end_of_day: bool = False) -> Optional[datetime]:
    if not value:
        return None
    normalized = value.strip().replace("/", "-")
    parsed = datetime.fromisoformat(normalized)
    if "T" not in normalized and " " not in normalized:
        return datetime.combine(parsed.date(), time.max if end_of_day else time.min)
    return parsed


def _file_mtime(path: Path) -> Optional[datetime]:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime)
    except OSError:
        return None


def _image_in_date_scope(image_path: Path,
                         from_date: Optional[datetime],
                         to_date: Optional[datetime]) -> bool:
    if from_date is None and to_date is None:
        return True
    mtime = _file_mtime(image_path)
    if mtime is None:
        return False
    if from_date is not None and mtime < from_date:
        return False
    if to_date is not None and mtime > to_date:
        return False
    return True


def _candidate_image_paths(coil_dir: Path, image_type: str) -> Iterator[Path]:
    image_type = image_type.upper()
    for folder_name in ("jpg", "png", ""):
        folder = coil_dir / folder_name if folder_name else coil_dir
        for suffix in IMAGE_SUFFIXES:
            yield folder / f"{image_type}{suffix}"


def _find_existing_image(coil_dir: Path, image_type: str) -> Optional[Path]:
    for image_path in _candidate_image_paths(coil_dir, image_type):
        if image_path.exists():
            return image_path
    return None


def _looks_like_coil_dir(path: Path, image_types: Sequence[str]) -> bool:
    return any(_find_existing_image(path, image_type) for image_type in image_types)


def iter_area_images(roots: Iterable[Path],
                     image_types: Sequence[str],
                     coil_ids: Set[str],
                     from_id: Optional[int],
                     to_id: Optional[int],
                     from_date: Optional[datetime],
                     to_date: Optional[datetime]) -> Iterator[Path]:
    seen: Set[str] = set()
    normalized_types = [image_type.upper() for image_type in image_types]
    for root in roots:
        root = Path(root)
        if root.is_file():
            if root.stem.upper() in normalized_types and _image_in_date_scope(root, from_date, to_date):
                resolved = str(root.resolve(strict=False))
                if resolved not in seen:
                    seen.add(resolved)
                    yield root
            continue
        if not root.exists():
            logging.warning("skip missing root: %s", root)
            continue

        if _looks_like_coil_dir(root, normalized_types):
            coil_dirs = [root]
        else:
            coil_dirs = (item for item in root.iterdir() if item.is_dir())

        for coil_dir in coil_dirs:
            if not _coil_in_scope(coil_dir, coil_ids, from_id, to_id):
                continue
            for image_type in normalized_types:
                image_path = _find_existing_image(coil_dir, image_type)
                if image_path is None:
                    continue
                if not _image_in_date_scope(image_path, from_date, to_date):
                    continue
                resolved = str(image_path.resolve(strict=False))
                if resolved in seen:
                    continue
                seen.add(resolved)
                yield image_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rebuild AREA/AREA_MASK tile caches using the current 3x3 L0-L4 strategy."
    )
    parser.add_argument("roots",
                        nargs="+",
                        type=Path,
                        help="Save root, coil directory, or AREA image path. UNC paths are supported.")
    parser.add_argument("--types",
                        nargs="+",
                        default=list(DEFAULT_TYPES),
                        help="Image types to rebuild. Default: AREA AREA_MASK")
    parser.add_argument("--coil-id",
                        action="append",
                        help="Only rebuild specific coil ids. May be repeated or comma-separated.")
    parser.add_argument("--from-id", type=int, help="Only rebuild coils with id >= this value.")
    parser.add_argument("--to-id", type=int, help="Only rebuild coils with id <= this value.")
    parser.add_argument("--from-date",
                        help="Only rebuild images modified at or after this local date/time, e.g. 2026-05-01.")
    parser.add_argument("--to-date",
                        help="Only rebuild images modified at or before this local date/time, e.g. 2026-07-05.")
    parser.add_argument("--tile-count",
                        type=int,
                        default=DEFAULT_AREA_TILE_COUNT,
                        help="Tile count per axis. Default: 3")
    parser.add_argument("--workers",
                        type=int,
                        default=1,
                        help="Parallel workers. Keep low for network shares. Default: 1")
    parser.add_argument("--limit", type=int, help="Stop after this many images.")
    parser.add_argument("--clear-cache-url",
                        action="append",
                        default=[],
                        help="POST this URL to clear running image-service cache. May be repeated.")
    parser.add_argument("--evict-rust-url",
                        help="Rust image service base URL used to evict old LRU cache entries, e.g. http://127.0.0.1:6013.")
    parser.add_argument("--evict-window",
                        type=int,
                        default=90,
                        help="Number of rebuilt image paths to use when evicting Rust LRU cache. Default: 90")
    parser.add_argument("--clear-every",
                        type=int,
                        default=20,
                        help="Clear running caches after this many successful rebuilds. Default: 20")
    parser.add_argument("--execute",
                        action="store_true",
                        help="Actually remove and rebuild caches. Without this flag the script is dry-run.")
    return parser.parse_args()


def _clear_running_caches(urls: Sequence[str]) -> None:
    for url in urls:
        try:
            req = request.Request(url, data=b"{}", method="POST", headers={"Content-Type": "application/json"})
            with request.urlopen(req, timeout=3) as response:
                logging.info("cleared running cache: %s status=%s", url, response.status)
        except (error.URLError, TimeoutError, OSError) as exc:
            logging.warning("clear running cache failed: %s error=%s", url, exc)


def _infer_area_request(image_path: Path) -> Optional[tuple[str, str, str]]:
    path_text = str(image_path).lower().replace("/", "\\")
    if "\\save_s\\" in path_text or "\\surface_s\\" in path_text:
        surface_key = "S"
    elif "\\save_l\\" in path_text or "\\surface_l\\" in path_text or "\\save_d\\" in path_text:
        surface_key = "L"
    else:
        return None

    coil_dir = image_path.parent.parent if image_path.parent.name.lower() in {"jpg", "png"} else image_path.parent
    coil_id = coil_dir.name
    image_type = image_path.stem.upper()
    if image_type not in DEFAULT_TYPES:
        return None
    return surface_key, coil_id, image_type


def _evict_rust_lru_cache(base_url: str, image_paths: Sequence[Path]) -> None:
    if not base_url or not image_paths:
        return
    base_url = base_url.rstrip("/")
    evicted = 0
    for image_path in image_paths:
        request_parts = _infer_area_request(image_path)
        if request_parts is None:
            continue
        surface_key, coil_id, image_type = request_parts
        if image_type == "AREA":
            url = f"{base_url}/image/area/{surface_key}/{coil_id}?row=0&col=0&count=3&level=0"
        else:
            url = (
                f"{base_url}/image/area/{surface_key}/{coil_id}/{image_type}"
                "?row=0&col=0&count=3&level=0"
            )
        try:
            with request.urlopen(url, timeout=2) as response:
                response.read(256)
            evicted += 1
        except (error.URLError, TimeoutError, OSError) as exc:
            logging.debug("rust LRU eviction request failed: %s error=%s", url, exc)
    logging.info("rust LRU eviction touched %s tile urls", evicted)


def _limit_iter(items: Iterable[Path], limit: Optional[int]) -> Iterator[Path]:
    for index, item in enumerate(items):
        if limit is not None and index >= max(0, limit):
            return
        yield item


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    coil_ids = _parse_coil_ids(args.coil_id)
    from_date = _parse_datetime(args.from_date)
    to_date = _parse_datetime(args.to_date, end_of_day=True)
    image_paths = _limit_iter(
        iter_area_images(args.roots, args.types, coil_ids, args.from_id, args.to_id, from_date, to_date),
        args.limit,
    )

    if not args.execute:
        logging.info("dry-run only; add --execute to rebuild caches")
        matched = 0
        for image_path in image_paths:
            matched += 1
            if matched <= 50:
                logging.info("would rebuild: %s modified=%s", image_path, _file_mtime(image_path))
        if matched > 50:
            logging.info("... %s more", matched - 50)
        logging.info("matched %s AREA images", matched)
        return 0

    workers = max(1, args.workers)
    clear_every = max(0, args.clear_every)
    succeeded = 0
    failed = 0
    completed = 0
    submitted = 0
    image_iter = iter(image_paths)
    pending = {}
    recent_rebuilt_paths = deque(maxlen=max(1, args.evict_window))

    def submit_next(executor: ThreadPoolExecutor) -> bool:
        nonlocal submitted
        try:
            image_path = next(image_iter)
        except StopIteration:
            return False
        future = executor.submit(rebuild_area_tile_cache, image_path, tile_count=args.tile_count)
        pending[future] = image_path
        submitted += 1
        return True

    with ThreadPoolExecutor(max_workers=workers) as executor:
        for _ in range(max(1, workers * 2)):
            if not submit_next(executor):
                break

        while pending:
            done, _ = wait(pending, return_when=FIRST_COMPLETED)
            for future in done:
                image_path = pending.pop(future)
                result = future.result()
                completed += 1
                if result.rebuilt:
                    succeeded += 1
                    recent_rebuilt_paths.append(image_path)
                    logging.info("rebuilt %s/%s submitted %s tiles=%s removed=%s cache=%s",
                                 completed,
                                 submitted,
                                 image_path,
                                 result.tiles,
                                 result.removed_files,
                                 result.cache_dir)
                    if args.clear_cache_url and clear_every and succeeded % clear_every == 0:
                        _clear_running_caches(args.clear_cache_url)
                    if args.evict_rust_url and clear_every and succeeded % clear_every == 0:
                        _evict_rust_lru_cache(args.evict_rust_url, list(recent_rebuilt_paths))
                else:
                    failed += 1
                    logging.error("failed %s: %s", image_path, result.error)

            while len(pending) < max(1, workers * 2):
                if not submit_next(executor):
                    break

    if args.clear_cache_url:
        _clear_running_caches(args.clear_cache_url)
    if args.evict_rust_url:
        _evict_rust_lru_cache(args.evict_rust_url, list(recent_rebuilt_paths))

    logging.info("done: submitted=%s succeeded=%s failed=%s", submitted, succeeded, failed)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
