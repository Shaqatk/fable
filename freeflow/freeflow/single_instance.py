"""Single-instance guard for FreeFlow on Windows.

Uses a named Windows mutex to guarantee a single process, plus a localhost
socket so secondary launches can tell the primary instance to show its window.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import socket
import threading
import time
from typing import Callable

kernel32 = ctypes.windll.kernel32

CloseHandle = kernel32.CloseHandle
CloseHandle.argtypes = [wt.HANDLE]
CloseHandle.restype = wt.BOOL

CreateMutexW = kernel32.CreateMutexW
CreateMutexW.argtypes = [wt.LPVOID, wt.BOOL, wt.LPCWSTR]
CreateMutexW.restype = wt.HANDLE

GetLastError = kernel32.GetLastError
GetLastError.argtypes = []
GetLastError.restype = wt.DWORD

ERROR_ALREADY_EXISTS = 183
MUTEX_NAME = "Local\\FreeFlow_SingleInstance"
HOST = "127.0.0.1"
PORT = 52389
SHOW_CMD = b"SHOW"

_mutex: wt.HANDLE | None = None
_server: socket.socket | None = None
_show_callback: Callable[[], None] | None = None
_pending_show = False
_listener_started = False
_listener_lock = threading.Lock()
_stop = threading.Event()


def acquire_or_notify_show() -> bool:
    """Return True if this process should start; False if another instance handled it."""
    if _acquire_mutex():
        return True
    _notify_show(retries=24, delay=0.15)
    return False


def claim_primary() -> bool:
    """Bind the show socket for secondary-launch activation."""
    return start_show_listener()


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

    _stop.clear()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    for _ in range(12):
        try:
            sock.bind((HOST, PORT))
            break
        except OSError:
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
    """Release resources during shutdown."""
    global _mutex, _server

    _stop.set()
    if _server is not None:
        try:
            _server.close()
        except OSError:
            pass
        _server = None
    if _mutex is not None:
        CloseHandle(_mutex)
        _mutex = None


def _notify_show(retries: int = 8, delay: float = 0.15) -> bool:
    for _ in range(retries):
        try:
            with socket.create_connection((HOST, PORT), timeout=0.3) as sock:
                sock.sendall(SHOW_CMD)
                return True
        except OSError:
            time.sleep(delay)
    return False


def _acquire_mutex() -> bool:
    """Try to acquire app-wide process ownership."""
    global _mutex
    if _mutex is not None:
        return True
    handle = CreateMutexW(None, False, MUTEX_NAME)
    if not handle:
        return False
    if GetLastError() == ERROR_ALREADY_EXISTS:
        CloseHandle(handle)
        return False
    _mutex = handle
    return True


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
