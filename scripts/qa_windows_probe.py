"""Inspect the current Windows token and exercise only our own temporary objects.

No token/ACL/policy changes. Exit 2 means this context is unsuitable for the lab.
Run the same probe in an ordinary operator terminal to obtain a real comparison.
"""
import argparse
import ctypes as c
import json
import os
import subprocess
import sys
import uuid
from ctypes import wintypes as w
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def inspect_token_and_pipe():
    kernel = c.WinDLL("kernel32", use_last_error=True)
    security = c.WinDLL("advapi32", use_last_error=True)
    kernel.GetCurrentProcess.restype = w.HANDLE
    kernel.GetCurrentThread.restype = w.HANDLE
    kernel.CloseHandle.argtypes = [w.HANDLE]
    kernel.LocalFree.argtypes = [w.HLOCAL]
    security.OpenProcessToken.argtypes = [w.HANDLE, w.DWORD, c.POINTER(w.HANDLE)]
    security.OpenThreadToken.argtypes = [w.HANDLE, w.DWORD, w.BOOL, c.POINTER(w.HANDLE)]
    security.GetTokenInformation.argtypes = [w.HANDLE, c.c_int, w.LPVOID, w.DWORD, c.POINTER(w.DWORD)]
    security.ConvertSidToStringSidW.argtypes = [w.LPVOID, c.POINTER(w.LPWSTR)]
    security.IsTokenRestricted.argtypes = [w.HANDLE]
    security.GetSecurityInfo.argtypes = [w.HANDLE, c.c_int, w.DWORD, w.LPVOID,
        w.LPVOID, w.LPVOID, w.LPVOID, c.POINTER(w.LPVOID)]
    security.ConvertSecurityDescriptorToStringSecurityDescriptorW.argtypes = [w.LPVOID,
        w.DWORD, w.DWORD, c.POINTER(w.LPWSTR), w.LPVOID]
    security.GetSecurityDescriptorDacl.argtypes = [w.LPVOID, c.POINTER(w.BOOL),
        c.POINTER(w.LPVOID), c.POINTER(w.BOOL)]

    class SidAttributes(c.Structure):
        _fields_ = [("sid", w.LPVOID), ("attributes", w.DWORD)]

    class Groups(c.Structure):
        _fields_ = [("count", w.DWORD), ("groups", SidAttributes * 1)]

    def sid_string(pointer):
        value = w.LPWSTR()
        if not security.ConvertSidToStringSidW(pointer, c.byref(value)):
            raise c.WinError(c.get_last_error())
        try:
            return value.value
        finally:
            kernel.LocalFree(value)

    def information(token, kind):
        size = w.DWORD()
        security.GetTokenInformation(token, kind, None, 0, c.byref(size))
        if not size.value:
            raise c.WinError(c.get_last_error())
        buffer = c.create_string_buffer(size.value)
        if not security.GetTokenInformation(token, kind, buffer, size, c.byref(size)):
            raise c.WinError(c.get_last_error())
        return buffer

    def sddl(descriptor):
        value = w.LPWSTR()
        if not security.ConvertSecurityDescriptorToStringSecurityDescriptorW(
            descriptor, 1, 5, c.byref(value), None
        ):
            raise c.WinError(c.get_last_error())
        try:
            return value.value
        finally:
            kernel.LocalFree(value)

    def handle_security(handle):
        descriptor = w.LPVOID()
        error = security.GetSecurityInfo(handle, 6, 5, None, None, None, None, c.byref(descriptor))
        if error:
            return {"read_error": error}
        try:
            return {"sddl": sddl(descriptor)}
        finally:
            kernel.LocalFree(descriptor)

    token = w.HANDLE()
    if security.OpenThreadToken(kernel.GetCurrentThread(), 8, True, c.byref(token)):
        effective = "thread_impersonation"
    else:
        error = c.get_last_error()
        if error != 1008:  # ERROR_NO_TOKEN: the process token is effective.
            raise c.WinError(error)
        if not security.OpenProcessToken(kernel.GetCurrentProcess(), 8, c.byref(token)):
            raise c.WinError(c.get_last_error())
        effective = "process_primary"
    try:
        restricted = information(token, 11)
        count = w.DWORD.from_buffer(restricted).value
        entries = (SidAttributes * count).from_buffer(restricted, Groups.groups.offset) if count else []
        user = information(token, 1)
        integrity = information(token, 25)
        result = dict(effective_token=effective,
            user_sid=sid_string(SidAttributes.from_buffer(user).sid),
            integrity_sid=sid_string(SidAttributes.from_buffer(integrity).sid),
            is_restricted=bool(security.IsTokenRestricted(token)),
            restricting_sids=[dict(sid=sid_string(x.sid), attributes=x.attributes) for x in entries],
            elevation_type=w.DWORD.from_buffer(information(token, 18)).value,
            is_app_container=bool(w.DWORD.from_buffer(information(token, 29)).value))
        # Inspect our own default ACL via a descriptor built only in memory.
        default = information(token, 6)
        acl = w.LPVOID.from_buffer(default).value
        descriptor = c.create_string_buffer(64)
        security.InitializeSecurityDescriptor.argtypes = [w.LPVOID, w.DWORD]
        security.SetSecurityDescriptorDacl.argtypes = [w.LPVOID, w.BOOL, w.LPVOID, w.BOOL]
        if not security.InitializeSecurityDescriptor(descriptor, 1):
            raise c.WinError(c.get_last_error())
        if not security.SetSecurityDescriptorDacl(descriptor, True, acl, False):
            raise c.WinError(c.get_last_error())
        result["token_default_dacl"] = sddl(descriptor)
    finally:
        kernel.CloseHandle(token)

    kernel.CreateNamedPipeW.argtypes = [w.LPCWSTR, w.DWORD, w.DWORD, w.DWORD,
        w.DWORD, w.DWORD, w.DWORD, w.LPVOID]
    kernel.CreateNamedPipeW.restype = w.HANDLE
    kernel.CreateFileW.argtypes = [w.LPCWSTR, w.DWORD, w.DWORD, w.LPVOID,
        w.DWORD, w.DWORD, w.HANDLE]
    kernel.CreateFileW.restype = w.HANDLE
    kernel.ConnectNamedPipe.argtypes = [w.HANDLE, w.LPVOID]
    kernel.WriteFile.argtypes = [w.HANDLE, w.LPVOID, w.DWORD, c.POINTER(w.DWORD), w.LPVOID]
    kernel.ReadFile.argtypes = [w.HANDLE, w.LPVOID, w.DWORD, c.POINTER(w.DWORD), w.LPVOID]
    invalid = c.c_void_p(-1).value
    result["own_named_pipes"] = {}
    for label, access in (("read", 0x80000000), ("write", 0x40000000), ("duplex", 0xC0000000)):
        name = "\\\\.\\pipe\\tapserve_probe_" + uuid.uuid4().hex
        server = kernel.CreateNamedPipeW(name, 3, 6, 1, 64, 64, 2000, None)
        pipe = result["own_named_pipes"][label] = {"requested_access": hex(access)}
        if server == invalid:
            pipe.update(create_error=c.get_last_error(), passed=False)
            continue
        client = invalid
        try:
            pipe["security"] = handle_security(server)
            client = kernel.CreateFileW(name, access, 0, None, 3, 0, None)
            if client == invalid:
                pipe.update(open_error=c.get_last_error(), passed=False)
                continue
            connected = kernel.ConnectNamedPipe(server, None)
            if not connected and c.get_last_error() != 535:  # ERROR_PIPE_CONNECTED
                raise c.WinError(c.get_last_error())
            size = w.DWORD()
            data = c.create_string_buffer(4)
            writer, reader = (client, server) if label == "write" else (server, client)
            if not kernel.WriteFile(writer, b"ping", 4, c.byref(size), None):
                raise c.WinError(c.get_last_error())
            if not kernel.ReadFile(reader, data, 4, c.byref(size), None):
                raise c.WinError(c.get_last_error())
            pipe["passed"] = data.raw == b"ping" and size.value == 4
        finally:
            if client != invalid:
                kernel.CloseHandle(client)
            kernel.CloseHandle(server)
    return result


def probe():
    if sys.platform != "win32":
        raise RuntimeError("This diagnostic is for Windows only")
    report = dict(pid=os.getpid(), parent_pid=os.getppid(), executable=sys.executable,
        cwd=str(Path.cwd().resolve()), platform=sys.platform, python=sys.version,
        windows=inspect_token_and_pipe())
    directory = ROOT / ".local" / ("fase2b-capabilities-" + uuid.uuid4().hex)
    directory.mkdir()
    sample = directory / "owned.txt"
    sample.write_text("synthetic", encoding="utf-8")
    report["workspace_read_write_delete"] = sample.read_text() == "synthetic"
    sample.unlink()
    # Only this freshly created child handle is ever stopped, never a process name/PID lookup.
    child = subprocess.Popen([sys.executable, "-B", "-c", "import time; time.sleep(30)"],
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW)
    child.terminate()
    report["own_child_stop"] = child.wait(timeout=5) is not None
    result = subprocess.run([sys.executable, "-B", "-c", "print('synthetic')"],
        capture_output=True, text=True, timeout=5, creationflags=subprocess.CREATE_NO_WINDOW)
    report["python_anonymous_pipe"] = result.returncode == 0 and result.stdout.strip() == "synthetic"
    report["lab_gate_passed"] = all((report["windows"]["own_named_pipes"]["duplex"]["passed"],
        report["workspace_read_write_delete"], report["own_child_stop"], report["python_anonymous_pipe"]))
    directory.rmdir()
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    destination = args.output.resolve()
    if not destination.is_relative_to(ROOT) or destination.exists():
        parser.error("Use a NEW report file inside this workspace")
    destination.parent.mkdir(parents=True, exist_ok=True)
    result = probe()
    with destination.open("x", encoding="utf-8") as output:
        json.dump(result, output, indent=2)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["lab_gate_passed"] else 2)
