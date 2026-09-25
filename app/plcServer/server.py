import asyncio
import logging
import math
import threading
import time
from contextlib import asynccontextmanager
from typing import Any, Callable, Optional

from fastapi import FastAPI, HTTPException, Path, Response
from HslCommunication import SiemensPLCS, SiemensS7Net
from snap7.util import get_bool, get_dword, get_int, get_real, get_word

try:
    from . import config
except ImportError:  # pragma: no cover - direct script/PyInstaller execution
    import config


logger = logging.getLogger(__name__)

READ_TYPE_LIST = ("int", "real", "dword", "string", "bytes", "word", "bool")
SUPPORTED_READ_TYPES = frozenset(READ_TYPE_LIST)
SUPPORTED_WRITE_TYPES = frozenset({"int", "real", "word", "bool"})
MINIMUM_READ_LENGTH = {
    "int": 2,
    "real": 4,
    "dword": 4,
    "string": 0,
    "bytes": 0,
    "word": 2,
    "bool": 1,
}
MAX_READ_LENGTH = 4096


class PLCError(RuntimeError):
    """Base error for predictable PLC failures."""


class PLCConfigurationError(PLCError, ValueError):
    """The requested PLC target, value type, or payload is invalid."""


class PLCBusyError(PLCError):
    """Another PLC operation exceeded the bounded serialization wait."""


class PLCUnavailableError(PLCError):
    """The PLC or its SDK is unavailable after a reconnect attempt."""


class PLCOperationError(PLCError):
    """The vendor SDK explicitly returned a failed/malformed result."""


def _validate_target(plc_ip: str, rack: int, slot: int) -> tuple[str, int, int]:
    plc_ip = str(plc_ip).strip()
    if not plc_ip or len(plc_ip) > 255 or any(character.isspace() for character in plc_ip):
        raise PLCConfigurationError("PLC IP/host is invalid")
    try:
        normalized_rack = int(rack)
        normalized_slot = int(slot)
    except (TypeError, ValueError) as error:
        raise PLCConfigurationError("PLC rack and slot must be integers") from error
    if not 0 <= normalized_rack <= 255:
        raise PLCConfigurationError("PLC rack must be between 0 and 255")
    if not 0 <= normalized_slot <= 255:
        raise PLCConfigurationError("PLC slot must be between 0 and 255")
    return plc_ip, normalized_rack, normalized_slot


def _normalize_type(type_str: str, supported: frozenset[str]) -> str:
    normalized = str(type_str).strip().lower()
    if normalized not in supported:
        choices = ", ".join(sorted(supported))
        raise PLCConfigurationError(f"unsupported PLC value type {type_str!r}; expected one of: {choices}")
    return normalized


def _validate_read_request(addr: str, type_str: str, length: int) -> tuple[str, str, int]:
    address = str(addr).strip()
    if not address or len(address) > 128:
        raise PLCConfigurationError("PLC address is empty or too long")
    normalized_type = _normalize_type(type_str, SUPPORTED_READ_TYPES)
    try:
        normalized_length = int(length)
    except (TypeError, ValueError) as error:
        raise PLCConfigurationError("PLC read length must be an integer") from error
    if not 1 <= normalized_length <= MAX_READ_LENGTH:
        raise PLCConfigurationError(f"PLC read length must be between 1 and {MAX_READ_LENGTH}")
    minimum = MINIMUM_READ_LENGTH[normalized_type]
    if normalized_length < minimum:
        raise PLCConfigurationError(
            f"PLC type {normalized_type!r} requires at least {minimum} bytes, got {normalized_length}"
        )
    return address, normalized_type, normalized_length


def get_value(value: Any, type_str: str) -> Any:
    normalized_type = _normalize_type(type_str, SUPPORTED_READ_TYPES)
    if not isinstance(value, (bytes, bytearray, memoryview)):
        raise PLCOperationError(f"PLC SDK returned non-byte content: {type(value).__name__}")
    payload = bytes(value)
    mutable_payload = bytearray(payload)
    minimum = MINIMUM_READ_LENGTH[normalized_type]
    if len(payload) < minimum:
        raise PLCOperationError(
            f"PLC SDK returned {len(payload)} bytes for {normalized_type}; at least {minimum} required"
        )
    if normalized_type == "int":
        return get_int(mutable_payload, 0)
    if normalized_type == "real":
        return get_real(mutable_payload, 0)
    if normalized_type == "dword":
        return get_dword(mutable_payload, 0)
    if normalized_type == "string":
        try:
            return payload.rstrip(b"\x00").decode("utf-8")
        except UnicodeDecodeError as error:
            raise PLCOperationError("PLC string is not valid UTF-8") from error
    if normalized_type == "bytes":
        return payload
    if normalized_type == "word":
        return get_word(mutable_payload, 0)
    return get_bool(mutable_payload, 0, 0)


# Backwards-compatible name used by older helper scripts.
getValue = get_value


def get_siemens(plc_ip: str, plc_rack: int, plc_slot: int) -> SiemensS7Net:
    plc_ip, plc_rack, plc_slot = _validate_target(plc_ip, plc_rack, plc_slot)
    client = SiemensS7Net(SiemensPLCS.S400, plc_ip)
    client.SetSlotAndRack(plc_rack, plc_slot)
    return client


# Backwards-compatible name used by older code and release scripts.
getSiemens = get_siemens


def _sdk_failure_message(result: Any, operation: str) -> str:
    if result is None:
        return f"{operation} returned no SDK result"
    message = getattr(result, "Message", "") or "unknown SDK error"
    error_code = getattr(result, "ErrorCode", None)
    if error_code is None:
        return f"{operation} failed: {message}"
    return f"{operation} failed (code={error_code}): {message}"


def _require_success(result: Any, operation: str) -> Any:
    if result is None or getattr(result, "IsSuccess", None) is not True:
        raise PLCOperationError(_sdk_failure_message(result, operation))
    return result


class PLCConnectionManager:
    """Own one PLC session and serialize all use of the non-thread-safe SDK."""

    def __init__(
        self,
        client_factory: Callable[[str, int, int], Any] = get_siemens,
        *,
        plc_ip: Optional[str] = None,
        rack: Optional[int] = None,
        slot: Optional[int] = None,
        connect_timeout_ms: Optional[int] = None,
        receive_timeout_ms: Optional[int] = None,
        lock_timeout_seconds: Optional[float] = None,
        stuck_threshold_seconds: Optional[float] = None,
    ) -> None:
        self._client_factory = client_factory
        self._target = _validate_target(
            plc_ip if plc_ip is not None else config.plcForwarderUrl,
            rack if rack is not None else config.plcForwarderRack,
            slot if slot is not None else config.plcForwarderSlot,
        )
        self._connect_timeout_ms = max(
            int(connect_timeout_ms if connect_timeout_ms is not None else config.plc_connect_timeout_ms),
            1,
        )
        self._receive_timeout_ms = max(
            int(receive_timeout_ms if receive_timeout_ms is not None else config.plc_receive_timeout_ms),
            1,
        )
        self._lock_timeout_seconds = max(
            float(
                lock_timeout_seconds
                if lock_timeout_seconds is not None
                else config.plc_operation_lock_timeout_seconds
            ),
            0.01,
        )
        self._stuck_threshold_seconds = max(
            float(
                stuck_threshold_seconds
                if stuck_threshold_seconds is not None
                else config.plc_stuck_threshold_seconds
            ),
            0.1,
        )
        self._lock = threading.Lock()
        self._client: Any = None
        self._connected = False
        self._last_error: Optional[str] = None
        self._last_success_at: Optional[float] = None
        self._active_operation: Optional[str] = None
        self._active_operation_started_at: Optional[float] = None
        self._active_operation_started_monotonic: Optional[float] = None

    @property
    def target(self) -> tuple[str, int, int]:
        return self._target

    def _acquire(self) -> None:
        if not self._lock.acquire(timeout=self._lock_timeout_seconds):
            raise PLCBusyError(
                f"PLC operation queue waited longer than {self._lock_timeout_seconds:g} seconds"
            )

    def configure(self, plc_ip: str, rack: int, slot: int, *, connect: bool = True) -> None:
        target = _validate_target(plc_ip, rack, slot)
        self._acquire()
        self._begin_operation("PLC configure")
        try:
            self._disconnect_locked()
            self._target = target
            config.plcForwarderUrl, config.plcForwarderRack, config.plcForwarderSlot = target
            if connect:
                self._connect_locked()
        finally:
            self._end_operation()
            self._lock.release()

    def connect(self) -> None:
        self._acquire()
        self._begin_operation("PLC connect")
        try:
            self._connect_locked()
        finally:
            self._end_operation()
            self._lock.release()

    def _begin_operation(self, operation: str) -> None:
        self._active_operation = operation
        self._active_operation_started_at = time.time()
        self._active_operation_started_monotonic = time.monotonic()

    def _end_operation(self) -> None:
        self._active_operation = None
        self._active_operation_started_at = None
        self._active_operation_started_monotonic = None

    def _new_client(self) -> Any:
        plc_ip, rack, slot = self._target
        client = self._client_factory(plc_ip, rack, slot)
        if client is None:
            raise PLCOperationError("PLC client factory returned None")
        # These are the timeout field names provided by HslCommunication.
        client.connectTimeOut = self._connect_timeout_ms
        client.receiveTimeOut = self._receive_timeout_ms
        return client

    def _connect_locked(self) -> Any:
        if self._client is not None and self._connected:
            return self._client
        client = None
        try:
            client = self._new_client()
            _require_success(client.ConnectServer(), "PLC connect")
        except Exception as error:
            self._connected = False
            self._last_error = f"{type(error).__name__}: {error}"
            self._safe_close(client)
            if isinstance(error, PLCError):
                raise
            raise PLCOperationError(f"PLC connect raised {type(error).__name__}: {error}") from error
        self._client = client
        self._connected = True
        self._last_error = None
        logger.info("PLC connected: ip=%s rack=%s slot=%s", *self._target)
        return client

    @staticmethod
    def _safe_close(client: Any) -> None:
        if client is None:
            return
        internal_lock = getattr(client, "interactiveLock", None)
        if internal_lock is not None:
            try:
                lock_available = internal_lock.acquire(blocking=False)
            except (AttributeError, TypeError):
                lock_available = True
            if not lock_available:
                # HslCommunication uses manual acquire/release calls rather
                # than try/finally. An SDK exception can therefore leave its
                # lock permanently held; ConnectClose would deadlock here.
                PLCConnectionManager._force_close_socket(client)
                logger.warning("forced PLC socket close because the SDK lock remained held")
                return
            try:
                internal_lock.release()
            except (AttributeError, RuntimeError):
                pass
        try:
            result = client.ConnectClose()
            if result is not None and getattr(result, "IsSuccess", True) is False:
                PLCConnectionManager._force_close_socket(client)
                logger.warning("PLC close reported failure: %s", _sdk_failure_message(result, "PLC close"))
        except Exception as error:
            PLCConnectionManager._force_close_socket(client)
            logger.warning("PLC close failed: %s", error)

    @staticmethod
    def _force_close_socket(client: Any) -> None:
        socket = getattr(client, "CoreSocket", None)
        try:
            client.CoreSocket = None
        except (AttributeError, TypeError):
            pass
        try:
            client.isPersistentConn = False
        except (AttributeError, TypeError):
            pass
        if socket is not None:
            try:
                socket.close()
            except (AttributeError, OSError):
                pass

    def _disconnect_locked(self) -> None:
        client = self._client
        self._client = None
        self._connected = False
        self._safe_close(client)

    def _execute(self, operation: str, callback: Callable[[Any], Any]) -> Any:
        self._acquire()
        self._begin_operation(operation)
        try:
            errors: list[str] = []
            for attempt in range(2):
                try:
                    client = self._connect_locked()
                    value = callback(client)
                    self._connected = True
                    self._last_error = None
                    self._last_success_at = time.time()
                    return value
                except Exception as error:
                    message = f"{type(error).__name__}: {error}"
                    errors.append(message)
                    self._last_error = message
                    self._disconnect_locked()
                    if attempt == 0:
                        logger.warning("%s failed; reconnecting once: %s", operation, message)
            joined_errors = " | ".join(errors)
            raise PLCUnavailableError(f"{operation} unavailable after reconnect: {joined_errors}")
        finally:
            self._end_operation()
            self._lock.release()

    def read(self, addr: str, length: int) -> bytes:
        def read_operation(client: Any) -> bytes:
            result = _require_success(client.Read(addr, length), f"PLC read {addr}")
            content = getattr(result, "Content", None)
            if not isinstance(content, (bytes, bytearray, memoryview)):
                raise PLCOperationError(
                    f"PLC read {addr} returned invalid content: {type(content).__name__}"
                )
            if len(content) != length:
                raise PLCOperationError(
                    f"PLC read {addr} returned {len(content)} bytes; expected {length}"
                )
            return bytes(content)

        return self._execute(f"PLC read {addr}", read_operation)

    def write(self, addr: str, type_str: str, value: Any) -> Any:
        normalized_type = _normalize_type(type_str, SUPPORTED_WRITE_TYPES)
        try:
            if normalized_type == "int":
                normalized_value: Any = int(value)
                if not -32768 <= normalized_value <= 32767:
                    raise ValueError("outside signed 16-bit range")
            elif normalized_type == "word":
                normalized_value = int(value)
                if not 0 <= normalized_value <= 65535:
                    raise ValueError("outside unsigned 16-bit range")
            elif normalized_type == "real":
                normalized_value = float(value)
                if not math.isfinite(normalized_value):
                    raise ValueError("must be finite")
            elif isinstance(value, bool):
                normalized_value = value
            elif value in (0, 1):
                normalized_value = bool(value)
            else:
                raise ValueError("bool must be True, False, 0, or 1")
        except (TypeError, ValueError) as error:
            raise PLCConfigurationError(f"invalid {normalized_type} value {value!r}: {error}") from error

        def write_operation(client: Any) -> Any:
            if normalized_type == "int":
                result = client.WriteInt16(addr, normalized_value)
            elif normalized_type == "word":
                result = client.WriteUInt16(addr, normalized_value)
            elif normalized_type == "real":
                # Siemens REAL is 32-bit. WriteDouble would silently send an
                # 8-byte value and overwrite the following PLC address range.
                result = client.WriteFloat(addr, normalized_value)
            else:
                result = client.WriteBool(addr, normalized_value)
            return _require_success(result, f"PLC write {addr}")

        return self._execute(f"PLC write {addr}", write_operation)

    def status(self) -> dict[str, Any]:
        acquired = self._lock.acquire(blocking=False)
        busy = not acquired
        if acquired:
            try:
                target = self._target
                connected = self._connected
                last_error = self._last_error
                last_success_at = self._last_success_at
                active_operation = self._active_operation
                operation_started_at = self._active_operation_started_at
                operation_started_monotonic = self._active_operation_started_monotonic
            finally:
                self._lock.release()
        else:
            # Tuple/reference reads are atomic under CPython. Health must remain
            # responsive even while a vendor SDK call is blocked.
            target = self._target
            connected = self._connected
            last_error = self._last_error
            last_success_at = self._last_success_at
            active_operation = self._active_operation
            operation_started_at = self._active_operation_started_at
            operation_started_monotonic = self._active_operation_started_monotonic
        operation_age_seconds = (
            max(time.monotonic() - operation_started_monotonic, 0.0)
            if operation_started_monotonic is not None
            else None
        )
        stuck = (
            operation_age_seconds is not None
            and operation_age_seconds >= self._stuck_threshold_seconds
        )
        return {
            "service": "unhealthy" if stuck else "ok",
            "plc_connected": connected,
            "plc_busy": busy,
            "plc_ip": target[0],
            "rack": target[1],
            "slot": target[2],
            "last_error": last_error,
            "last_success_at": last_success_at,
            "active_operation": active_operation,
            "operation_started_at": operation_started_at,
            "operation_age_seconds": operation_age_seconds,
            "stuck_threshold_seconds": self._stuck_threshold_seconds,
            "stuck": stuck,
        }

    def close(self, timeout_seconds: float = 1.0) -> bool:
        if not self._lock.acquire(timeout=max(float(timeout_seconds), 0.0)):
            logger.warning("PLC shutdown skipped close because an SDK operation is still blocked")
            return False
        try:
            self._disconnect_locked()
            return True
        finally:
            self._lock.release()


plc_manager = PLCConnectionManager()


@asynccontextmanager
async def _lifespan(_: FastAPI):
    try:
        yield
    finally:
        await asyncio.to_thread(plc_manager.close)


app = FastAPI(lifespan=_lifespan)


@app.get("/health")
async def health(response: Response) -> dict[str, Any]:
    status = plc_manager.status()
    if status.get("stuck") is True:
        response.status_code = 503
    return status


@app.get("/plc/info/")
@app.get("/plc/info")
async def info_plc() -> dict[str, Any]:
    plc_ip, rack, slot = plc_manager.target
    return {
        "typeList": list(READ_TYPE_LIST),
        "plc_ip": plc_ip,
        "rack": rack,
        "slot": slot,
    }


@app.get("/plc/connect/{plc_ip}/{rack}/{slot}")
def connect_plc(
    plc_ip: str,
    rack: int = Path(ge=0, le=255),
    slot: int = Path(ge=0, le=255),
) -> bool:
    try:
        plc_manager.configure(plc_ip, rack, slot, connect=True)
        return True
    except PLCConfigurationError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except (PLCBusyError, PLCUnavailableError, PLCOperationError) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@app.get("/plc/get/{addr}/{typeStr}/{length}")
def forward_request(addr: str, typeStr: str, length: int) -> Any:
    try:
        value = read_plc(addr, typeStr, length)
        # JSON has no byte scalar. Returning an integer array is unambiguous
        # and matches the public API schema used by the main service.
        return list(value) if isinstance(value, bytes) else value
    except PLCConfigurationError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except (PLCBusyError, PLCUnavailableError, PLCOperationError) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


def initialize_plc() -> None:
    """Attempt an initial connection without hiding a startup failure."""
    plc_manager.connect()


def read_plc(addr: str, typeStr: str, length: int) -> Any:
    address, normalized_type, normalized_length = _validate_read_request(addr, typeStr, length)
    payload = plc_manager.read(address, normalized_length)
    return get_value(payload, normalized_type)


def write_plc(addr: str, typeStr: str, value: Any) -> Any:
    address = str(addr).strip()
    if not address or len(address) > 128:
        raise PLCConfigurationError("PLC address is empty or too long")
    return plc_manager.write(address, typeStr, value)
