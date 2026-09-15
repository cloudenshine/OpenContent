"""Own the lifecycle of adapter descendants as well as the immediate process."""
import ctypes
import os
import signal
import subprocess
from ctypes import wintypes


class ProcessGroup:
    def __init__(self):
        self.job = None
        if os.name == "nt":
            class BasicLimits(ctypes.Structure):
                _fields_ = [("process_time", ctypes.c_int64), ("job_time", ctypes.c_int64),
                            ("flags", wintypes.DWORD), ("min_ws", ctypes.c_size_t), ("max_ws", ctypes.c_size_t),
                            ("active", wintypes.DWORD), ("affinity", ctypes.c_size_t),
                            ("priority", wintypes.DWORD), ("scheduling", wintypes.DWORD)]

            class IoCounters(ctypes.Structure):
                _fields_ = [(name, ctypes.c_uint64) for name in ("read_ops", "write_ops", "other_ops", "read_bytes", "write_bytes", "other_bytes")]

            class ExtendedLimits(ctypes.Structure):
                _fields_ = [("basic", BasicLimits), ("io", IoCounters), ("process_memory", ctypes.c_size_t),
                            ("job_memory", ctypes.c_size_t), ("peak_process", ctypes.c_size_t), ("peak_job", ctypes.c_size_t)]

            self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            self.kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
            self.kernel.CreateJobObjectW.restype = wintypes.HANDLE
            self.kernel.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
            self.kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
            self.kernel.CloseHandle.argtypes = [wintypes.HANDLE]
            self.job = self.kernel.CreateJobObjectW(None, None)
            if not self.job:
                raise ctypes.WinError(ctypes.get_last_error())
            limits = ExtendedLimits()
            limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            if not self.kernel.SetInformationJobObject(self.job, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
                self.close()
                raise ctypes.WinError(ctypes.get_last_error())

    def start(self, argv, **kwargs):
        # On Windows suspend until attached, so descendants cannot escape during startup.
        process = subprocess.Popen(argv, creationflags=0x4 if os.name == "nt" else 0,
                                   start_new_session=os.name != "nt", **kwargs)
        self.process = process
        if self.job:
            if not self.kernel.AssignProcessToJobObject(self.job, wintypes.HANDLE(process._handle)):
                process.kill(); process.wait()
                self.close()
                raise OSError("Cannot attach adapter to owned Windows job")
            ntdll = ctypes.WinDLL("ntdll")
            ntdll.NtResumeProcess.argtypes = [wintypes.HANDLE]
            ntdll.NtResumeProcess.restype = ctypes.c_long
            if ntdll.NtResumeProcess(wintypes.HANDLE(process._handle)) != 0:
                self.close(); process.wait()
                raise OSError("Cannot resume owned adapter")
        return process

    def close(self):
        if self.job:
            self.kernel.CloseHandle(self.job)
            self.job = None
        elif os.name != "nt" and hasattr(self, "process"):
            try:
                os.killpg(self.process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
