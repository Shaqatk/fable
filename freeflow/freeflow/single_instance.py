"""Single-instance guard for FreeFlow on Windows.

Uses a PID lock file plus a localhost socket. A second launch notifies the
running instance to show its window. If the lock-file PID is alive but does
not respond, the stale process is terminated so a fresh launch can proceed.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import os
import socket
import threading
import time
from typing import Callable

from freeflow.config import APP_DIR

kernel32 = ctypes.windll.kernel32

OpenProcess = kernel32.OpenProcess
OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
OpenProcess.restype = wt.HANDLE

TerminateProcess = kernel32.TerminateProcess
TerminateProcess.argtypes = [wt.HANDLE, wt.UINT]
TerminateProcess.restype = wt.BOOL

CloseHandle = kernel32.CloseHandle
CloseHandle.argtypes = [wt.HANDLE]
CloseHandle.restype = wt.BOOL

PROCESS_TERMINATE = 0x0001

LOCK_PATH = APP_DIR / "instance.pid"
HOST = "127.0.0.1"
PORT = 52389
SHOW_CMD = b"SHOW"

_server: socket.socket | None = None
_show_callback: Callable[[], None] | None = None
_pending_show = False
_listener_started = False
_listener_lock = threading.Lock()
_stop = threading.Event()


def acquire_or_notify_show() -> bool:
    """Return True if this process should start; False if another instance handled it."""
    existing = _read_lock_pid()
    if existing is not None and existing != os.getpid() and _pid_alive(existing):
        if _notify_show(retries=10, delay=0.15):
            return False
        _terminate_pid(existing)
        time.sleep(0.3)

    _clear_stale_lock()
    return True


def claim_primary() -> bool:
    """Bind the show socket and write the PID lock. Call once startup is underway."""
    if not start_show_listener():
        return False
    APP_DIR.mkdir(parents=True, exist_ok=True)
    LOCK_PATH.write_text(str(os.getpid()), encoding="utf-8")
    return True


def register_show_handler(on_show: Callable[[], None]) -> None:
    global _show_callback, _pending_show
    _show_callback = on_show
    if _pending_show:
        _pending_show = False
        on_show()


def start_show_listener() -> bool:
    """Bind the show socket and start listening."""
    global _listener_started, _server

    with _listener_lock:
        if _listener_started:
            return _server is not None
        _listener_started = True

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    for _ in range(12):
        try:
            sock.bind((HOST, PORT))
            break
        except OSError:
            existing = _read_lock_pid()
            if existing is not None and existing != os.getpid() and _pid_alive(existing):
                if _notify_show(retries=3, delay=0.1):
                    sock.close()
                    return False
                _terminate_pid(existing)
                time.sleep(0.3)
            else:
                time.sleep(0.15)
    else:
        sock.close()
        return False

    sock.listen(5)
    _server = sock
    thread = threading.Thread(
        target=_serve, args=(sock,), name="single-instance", daemon=True
    )
    thread.start()
    return True


def release() -> None:
    """Release the PID lock and close the listener socket during shutdown."""
    global _server

    _stop.set()
    if _server is not None:
        try:
            _server.close()
        except OSError:
            pass
        _server = None
    _clear_stale_lock()


def _read_lock_pid() -> int | None:
    try:
        return int(LOCK_PATH.read_text(encoding="utf-8").strip())
    except (FileNotFoundError, ValueError, OSError):
        return None


def _clear_stale_lock() -> None:
    try:
        pid = _read_lock_pid()
        if pid is None or pid == os.getpid() or not _pid_alive(pid):
            LOCK_PATH.unlink(missing_ok=True)
    except OSError:
        pass


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _terminate_pid(pid: int) -> None:
    handle = OpenProcess(PROCESS_TERMINATE, False, pid)
    if handle:
        TerminateProcess(handle, 0)
        CloseHandle(handle)


def _notify_show(retries: int = 8, delay: float = 0.15) -> bool:
    for _ in range(retries):
        try:
            with socket.create_connection((HOST, PORT), timeout=0.3) as sock:
                sock.sendall(SHOW_CMD)
                return True
        except OSError:
            time.sleep(delay)
    return False


def _dispatch_show() -> None:
    global _pending_show
    callback = _show_callback
    if callback is not None:
        callback()
    else:
        _pending_show = True


def _serve(sock: socket.socket) -> None:
    sock.settimeout(1.0)
    while not _stop.is_set():
        try:
            conn, _ = sock.accept()
        except socket.timeout:
            continue
        except OSError:
            break
        try:
            if conn.recv(16) == SHOW_CMD:
                _dispatch_show()
        finally:
            conn.close()
