from collections import deque
from collections.abc import Callable


def merge_history_candidates(
        history_candidates: deque[int],
        known_ids: set[int],
        candidates: list[int],
        max_candidates: int | None = None,
) -> list[int]:
    new_candidates = [coil_id for coil_id in candidates if coil_id not in known_ids]
    for coil_id in reversed(new_candidates):
        history_candidates.appendleft(coil_id)
    if max_candidates is not None:
        max_candidates = max(int(max_candidates), 1)
        while len(history_candidates) > max_candidates:
            history_candidates.pop()
    # Rebuild from the retained queue so IDs evicted by a moving live window
    # can be discovered again without the companion set growing forever.
    known_ids.clear()
    known_ids.update(history_candidates)
    return new_candidates


def prune_retry_state(retry_state: dict[int, dict], retained_ids: set[int],
                      max_entries: int) -> None:
    """Drop retry metadata for coils no longer retained by recovery."""
    for coil_id in tuple(retry_state):
        if coil_id not in retained_ids:
            retry_state.pop(coil_id, None)
    while len(retry_state) > max(max_entries, 1):
        oldest_coil_id = next(iter(retry_state))
        retry_state.pop(oldest_coil_id, None)


def take_next_history_candidate(
        history_candidates: deque[int],
        evaluate: Callable[[int], tuple[bool, str]],
        max_checks: int,
) -> int | None:
    for _ in range(min(len(history_candidates), max(max_checks, 0))):
        coil_id = history_candidates.popleft()
        needs_work, reason = evaluate(coil_id)
        if reason != "processed":
            history_candidates.append(coil_id)
        if needs_work:
            return coil_id
    return None
