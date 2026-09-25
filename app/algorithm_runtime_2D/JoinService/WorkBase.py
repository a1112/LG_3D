import multiprocessing
import threading
import time
from dataclasses import dataclass
from itertools import count
from queue import Empty, Full, Queue
from typing import Any, Hashable

from algorithm_runtime_2D.utils.MultiprocessColorLogger import logger
from algorithm_runtime_2D.runtime_heartbeat import runtime_heartbeat


@dataclass(frozen=True)
class WorkTicket:
    work_id: Hashable | None
    token: int


@dataclass(frozen=True)
class WorkRequest:
    ticket: WorkTicket
    value: Any


@dataclass(frozen=True)
class WorkResult:
    ticket: WorkTicket
    value: Any


class _WorkBase_:
    _STOP_SENTINEL = object()

    def __init__(self, config, *, deduplicate: bool = False):
        self.config = config
        self.queue_in = Queue(maxsize=10)
        self.queue_out = Queue(maxsize=10)
        self._run_ = True
        self.coil_id = None
        self._deduplicate = deduplicate
        self._state_changed = threading.Condition(threading.RLock())
        self._pending_work_ids: set[Hashable] = set()
        self._active_work_id: Hashable | None = None
        self._active_ticket: WorkTicket | None = None
        self._deferred_results: dict[WorkTicket, Any] = {}
        self._outstanding_tickets: set[WorkTicket] = set()
        self._result_tickets: set[WorkTicket] = set()
        self._ticket_counter = count(1)
        self._stop_event = threading.Event()
        self._submission_lock = threading.Lock()
        self._accepting_work = True
        self._heartbeat_activity_token: str | None = None

    @property
    def __run__(self):
        return self.config.is_run()

    @staticmethod
    def get_work_id(work_item) -> Hashable | None:
        if isinstance(work_item, WorkRequest):
            return work_item.ticket.work_id
        candidate = work_item
        if isinstance(work_item, (list, tuple)) and work_item:
            candidate = work_item[0]
        try:
            hash(candidate)
        except (TypeError, ValueError):
            return None
        return candidate

    @staticmethod
    def get_work_value(work_item):
        return work_item.value if isinstance(work_item, WorkRequest) else work_item

    @staticmethod
    def get_work_ticket(work_item) -> WorkTicket | None:
        return work_item.ticket if isinstance(work_item, WorkRequest) else None

    def add_work(self, work_item, timeout: float = 5.0) -> WorkTicket | None:
        with self._submission_lock:
            if not self._accepting_work:
                logger.warning(
                    "2D work rejected after stop: worker=%s",
                    self.__class__.__name__,
                )
                return None
            if self.ident is not None and not self.is_alive():
                self._accepting_work = False
                logger.error(
                    "2D work rejected because worker died: worker=%s",
                    self.__class__.__name__,
                )
                return None
            work_id = self.get_work_id(work_item)
            reserved = False
            if self._deduplicate and work_id is not None:
                with self._state_changed:
                    if work_id in self._pending_work_ids:
                        logger.debug(
                            "2D duplicate work skipped: worker=%s work_id=%s",
                            self.__class__.__name__,
                            work_id,
                        )
                        return None
                    self._pending_work_ids.add(work_id)
                    reserved = True
            ticket = WorkTicket(work_id, next(self._ticket_counter))
            with self._state_changed:
                self._outstanding_tickets.add(ticket)
            try:
                self.queue_in.put(WorkRequest(ticket, work_item), timeout=timeout)
                return ticket
            except Full:
                with self._state_changed:
                    self._outstanding_tickets.discard(ticket)
                    if reserved:
                        self._pending_work_ids.discard(work_id)
                    self._state_changed.notify_all()
                logger.warning(
                    "2D work queue full: worker=%s work_id=%s",
                    self.__class__.__name__,
                    work_id,
                )
                return None

    def _child_workers(self):
        return ()

    def get_next_work(self, poll_timeout: float = 0.5):
        """Return the next request, or ``None`` after shutdown was requested."""
        while True:
            try:
                work_request = self.queue_in.get(timeout=max(poll_timeout, 0.01))
            except Empty:
                if self._stop_event.is_set():
                    return None
                continue
            if work_request is self._STOP_SENTINEL:
                self.queue_in.task_done()
                return None
            return work_request

    def request_stop(self, timeout: float = 1.0) -> None:
        for child in tuple(self._child_workers()):
            try:
                child.request_stop(timeout=timeout)
            except Exception as e:
                logger.exception(
                    "2D child stop request failed: parent=%s child=%s error=%s",
                    self.__class__.__name__,
                    child.__class__.__name__,
                    e,
                )
        with self._submission_lock:
            if not self._accepting_work:
                return
            self._accepting_work = False
            self._run_ = False
            self._stop_event.set()
            try:
                # The submission lock guarantees that the sentinel is ordered
                # after every request accepted before shutdown.
                self.queue_in.put_nowait(self._STOP_SENTINEL)
            except Full:
                # A busy worker will observe _stop_event once its finite queue
                # drains. Never wait forever merely to enqueue a stop marker.
                logger.warning(
                    "2D stop signal queue full: worker=%s",
                    self.__class__.__name__,
                )
        with self._state_changed:
            self._state_changed.notify_all()

    def wait_stopped(self, timeout: float = 5.0) -> bool:
        deadline = time.monotonic() + max(timeout, 0.0)
        workers = (self, *tuple(self._child_workers()))
        stopped = True
        for worker in workers:
            if worker is not self and hasattr(worker, "wait_stopped"):
                remaining = max(deadline - time.monotonic(), 0.0)
                stopped = worker.wait_stopped(remaining) and stopped
                continue
            if threading.current_thread() is worker:
                continue
            remaining = max(deadline - time.monotonic(), 0.0)
            try:
                worker.join(timeout=remaining)
            except RuntimeError:
                continue
            stopped = not worker.is_alive() and stopped
        return stopped

    def stop(self, timeout: float = 5.0) -> bool:
        self.request_stop(timeout=min(max(timeout, 0.01), 1.0))
        stopped = self.wait_stopped(timeout)
        if not stopped:
            logger.warning(
                "2D worker did not stop within %ss: worker=%s",
                timeout,
                self.__class__.__name__,
            )
        return stopped

    def mark_started(self, work_item) -> Hashable | None:
        work_id = self.get_work_id(work_item)
        runtime_heartbeat.end_activity(self._heartbeat_activity_token)
        self._heartbeat_activity_token = runtime_heartbeat.begin_activity(
            self.__class__.__name__,
            work_id,
        )
        with self._state_changed:
            if self._deduplicate and work_id is not None:
                self._pending_work_ids.add(work_id)
            self._active_work_id = work_id
            self._active_ticket = self.get_work_ticket(work_item)
            self.coil_id = work_id
            self._state_changed.notify_all()
        return work_id

    def mark_finished(self, work_item) -> None:
        work_id = self.get_work_id(work_item)
        ticket = self.get_work_ticket(work_item)
        activity = self._heartbeat_activity_token
        try:
            with self._state_changed:
                if self._deduplicate and work_id is not None:
                    self._pending_work_ids.discard(work_id)
                if self._active_work_id == work_id:
                    self._active_work_id = None
                    self._active_ticket = None
                if ticket is not None and ticket not in self._result_tickets:
                    self._outstanding_tickets.discard(ticket)
                    self._deferred_results.pop(ticket, None)
                self._state_changed.notify_all()
        finally:
            runtime_heartbeat.end_activity(activity)
            self._heartbeat_activity_token = None

    def pending_work_ids(self) -> set[Hashable]:
        with self._state_changed:
            return set(self._pending_work_ids)

    def pending_count(self) -> int:
        with self._state_changed:
            if self._deduplicate:
                return len(self._pending_work_ids)
            return self.queue_in.qsize() + int(self._active_work_id is not None)

    def has_pending(self, work_id: Hashable) -> bool:
        with self._state_changed:
            if self._deduplicate:
                return work_id in self._pending_work_ids
            return self._active_work_id == work_id

    @property
    def active_work_id(self) -> Hashable | None:
        with self._state_changed:
            return self._active_work_id

    @property
    def active_ticket(self) -> WorkTicket | None:
        with self._state_changed:
            return self._active_ticket

    def wait_for_completion(self, work_id: Hashable, timeout: float | None = None) -> bool:
        deadline = None if timeout is None else time.monotonic() + timeout
        with self._state_changed:
            while work_id in self._pending_work_ids:
                if self._stop_event.is_set():
                    return False
                remaining = None if deadline is None else deadline - time.monotonic()
                if remaining is not None and remaining <= 0:
                    return False
                self._state_changed.wait(remaining)
        return True

    def drain_output(self) -> int:
        with self._state_changed:
            drained = len(self._deferred_results)
            for ticket in self._deferred_results:
                self._outstanding_tickets.discard(ticket)
                self._result_tickets.discard(ticket)
            self._deferred_results.clear()
        while True:
            try:
                result = self.queue_out.get_nowait()
                if isinstance(result, WorkResult):
                    with self._state_changed:
                        self._outstanding_tickets.discard(result.ticket)
                        self._result_tickets.discard(result.ticket)
                drained += 1
            except Empty:
                break
        if drained:
            logger.debug("2D dropped stale outputs: worker=%s count=%s", self.__class__.__name__, drained)
        return drained

    def _take_deferred_result(
            self,
            expected_work_id: Hashable | None,
            expected_ticket: WorkTicket | None,
    ):
        with self._state_changed:
            if expected_ticket is not None:
                if expected_ticket in self._deferred_results:
                    return True, expected_ticket, self._deferred_results.pop(expected_ticket)
                return False, None, None

            for ticket, value in self._deferred_results.items():
                if expected_work_id is None or ticket.work_id == expected_work_id:
                    del self._deferred_results[ticket]
                    return True, ticket, value
        return False, None, None

    def _release_result_ticket(self, ticket: WorkTicket) -> None:
        with self._state_changed:
            self._outstanding_tickets.discard(ticket)
            self._result_tickets.discard(ticket)
            self._deferred_results.pop(ticket, None)

    def _abandon_expected_result(
            self,
            expected_work_id: Hashable | None,
        expected_ticket: WorkTicket | None,
    ) -> None:
        with self._state_changed:
            if expected_ticket is not None:
                tickets = (expected_ticket,)
            elif expected_work_id is None:
                tickets = ()
            else:
                tickets = tuple(
                    ticket for ticket in self._outstanding_tickets
                    if ticket.work_id == expected_work_id
                )
            for ticket in tickets:
                self._outstanding_tickets.discard(ticket)
                self._result_tickets.discard(ticket)
                self._deferred_results.pop(ticket, None)

    def get(
            self,
            timeout: float | None = None,
            expected_work_id: Hashable | None = None,
            expected_ticket: WorkTicket | None = None,
    ):
        if expected_ticket is not None:
            expected_work_id = expected_ticket.work_id
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            found, result_ticket, value = self._take_deferred_result(expected_work_id, expected_ticket)
            if found:
                self._release_result_ticket(result_ticket)
                return value

            remaining = None if deadline is None else deadline - time.monotonic()
            poll_timeout = 0.05 if remaining is None else min(max(remaining, 0.0), 0.05)
            try:
                result = self.queue_out.get(timeout=poll_timeout)
            except Empty:
                if self._stop_event.is_set():
                    self._abandon_expected_result(expected_work_id, expected_ticket)
                    return None
                if remaining is None or remaining > 0:
                    continue
                self._abandon_expected_result(expected_work_id, expected_ticket)
                logger.warning(
                    "2D work output timeout: worker=%s work_id=%s",
                    self.__class__.__name__,
                    expected_work_id,
                )
                return None

            if not isinstance(result, WorkResult):
                return result
            if expected_ticket is not None and result.ticket == expected_ticket:
                self._release_result_ticket(result.ticket)
                return result.value
            if expected_ticket is None and (expected_work_id is None or result.ticket.work_id == expected_work_id):
                self._release_result_ticket(result.ticket)
                return result.value

            with self._state_changed:
                is_outstanding = result.ticket in self._outstanding_tickets
                if is_outstanding:
                    self._deferred_results[result.ticket] = result.value
                    self._state_changed.notify_all()
            logger.debug(
                "2D work output %s: worker=%s expected=%s/%s actual=%s/%s",
                "deferred" if is_outstanding else "discarded",
                self.__class__.__name__,
                expected_work_id,
                expected_ticket.token if expected_ticket is not None else None,
                result.ticket.work_id,
                result.ticket.token,
            )

    def set(
            self,
            data,
            timeout: float = 5.0,
            work_id: Hashable | None = None,
            work_request=None,
    ) -> bool:
        ticket = self.get_work_ticket(work_request)
        if ticket is None:
            ticket = self.active_ticket
        if ticket is None:
            ticket = WorkTicket(work_id, 0)
        with self._state_changed:
            if ticket.token != 0 and ticket not in self._outstanding_tickets:
                logger.debug(
                    "2D late work output discarded: worker=%s work_id=%s token=%s",
                    self.__class__.__name__,
                    ticket.work_id,
                    ticket.token,
                )
                return True
            self._result_tickets.add(ticket)
        try:
            self.queue_out.put(WorkResult(ticket, data), timeout=timeout)
            return True
        except Full:
            self._release_result_ticket(ticket)
            logger.warning(
                "2D work output queue full: worker=%s work_id=%s",
                self.__class__.__name__,
                ticket.work_id,
            )
            return False


class WorkBaseThread(_WorkBase_, threading.Thread):
    def __init__(self, config, *, deduplicate: bool = False):
        threading.Thread.__init__(self, daemon=True)
        _WorkBase_.__init__(self, config, deduplicate=deduplicate)


class WorkBaseMultiProcess(_WorkBase_, multiprocessing.Process):
    def __init__(self, config, *, deduplicate: bool = False):
        _WorkBase_.__init__(self, config, deduplicate=deduplicate)
        multiprocessing.Process.__init__(self)
