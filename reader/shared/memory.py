"""memory.py — READ-ONLY access to the game's memory (the foundation of everything).

INVIOLABLE: only PROCESS_QUERY_INFORMATION|PROCESS_VM_READ (no WRITE, no inject).
"""

import ctypes
import struct
import time
from ctypes import wintypes

from config.offsets import (PROCESS_NAME, MODULE_NAME,
                            Array, List, String, Dict, Dict8B)


# ============================ structs / Win32 constants ====================== #
TH32CS_SNAPPROCESS = 0x2
TH32CS_SNAPMODULE = 0x8
TH32CS_SNAPMODULE32 = 0x10
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
INVALID_HANDLE = 0xFFFFFFFFFFFFFFFF
MAX_PATH = 260

MEM_COMMIT = 0x1000
PAGE_GUARD = 0x100
READABLE = 0x02 | 0x04 | 0x08 | 0x20 | 0x40 | 0x80
WRITABLE = 0x04 | 0x08 | 0x40 | 0x80


class PROCESSENTRY32(ctypes.Structure):
    _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
                ("th32ProcessID", wintypes.DWORD),
                ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
                ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
                ("th32ParentProcessID", wintypes.DWORD),
                ("pcPriClassBase", ctypes.c_long), ("dwFlags", wintypes.DWORD),
                ("szExeFile", ctypes.c_char * MAX_PATH)]


class MODULEENTRY32(ctypes.Structure):
    _fields_ = [("dwSize", wintypes.DWORD), ("th32ModuleID", wintypes.DWORD),
                ("th32ProcessID", wintypes.DWORD), ("GlblcntUsage", wintypes.DWORD),
                ("ProccntUsage", wintypes.DWORD), ("modBaseAddr", ctypes.c_void_p),
                ("modBaseSize", wintypes.DWORD), ("hModule", wintypes.HMODULE),
                ("szModule", ctypes.c_char * 256), ("szExePath", ctypes.c_char * MAX_PATH)]


class MBI(ctypes.Structure):
    _fields_ = [("BaseAddress", ctypes.c_void_p), ("AllocationBase", ctypes.c_void_p),
                ("AllocationProtect", wintypes.DWORD), ("PartitionId", wintypes.WORD),
                ("__pad", wintypes.WORD), ("RegionSize", ctypes.c_size_t),
                ("State", wintypes.DWORD), ("Protect", wintypes.DWORD),
                ("Type", wintypes.DWORD)]


# ============================ process: attach (read-only) ==================== #
_K = None


def _kernel32():
    global _K
    if _K is not None:
        return _K
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    k.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    k.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    k.Process32First.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32)]
    k.Process32Next.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32)]
    k.Module32First.argtypes = [wintypes.HANDLE, ctypes.POINTER(MODULEENTRY32)]
    k.Module32Next.argtypes = [wintypes.HANDLE, ctypes.POINTER(MODULEENTRY32)]
    k.OpenProcess.restype = wintypes.HANDLE
    k.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    k.ReadProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                    ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
    k.VirtualQueryEx.restype = ctypes.c_size_t
    k.VirtualQueryEx.argtypes = [wintypes.HANDLE, ctypes.c_void_p,
                                 ctypes.POINTER(MBI), ctypes.c_size_t]
    k.CloseHandle.argtypes = [wintypes.HANDLE]
    k.QueryFullProcessImageNameW.restype = wintypes.BOOL
    k.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD,
                                             wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    _K = k
    return k


def find_pid(name=None):
    nm = name or PROCESS_NAME
    nm = nm.encode() if isinstance(nm, str) else nm
    k = _kernel32()
    snap = k.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if not snap or snap == INVALID_HANDLE:
        return None
    try:
        e = PROCESSENTRY32()
        e.dwSize = ctypes.sizeof(PROCESSENTRY32)
        ok = k.Process32First(snap, ctypes.byref(e))
        while ok:
            if e.szExeFile.lower() == nm.lower():
                return e.th32ProcessID
            ok = k.Process32Next(snap, ctypes.byref(e))
    finally:
        k.CloseHandle(snap)
    return None


def open_process(pid):
    """READ-ONLY handle (QUERY_INFORMATION|VM_READ). The ONE audited attach point."""
    return _kernel32().OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)


def close(handle):
    if handle:
        try:
            _kernel32().CloseHandle(handle)
        except Exception:
            pass


def process_image_path(handle):
    size = wintypes.DWORD(MAX_PATH * 4)
    buf = ctypes.create_unicode_buffer(size.value)
    if not _kernel32().QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
        return None
    return buf.value or None


def module_base(pid, name=None):
    nm = name or MODULE_NAME
    nm = nm.encode() if isinstance(nm, str) else nm
    k = _kernel32()
    for _ in range(4):
        snap = k.CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid)
        if snap and snap != INVALID_HANDLE:
            try:
                me = MODULEENTRY32()
                me.dwSize = ctypes.sizeof(MODULEENTRY32)
                ok = k.Module32First(snap, ctypes.byref(me))
                while ok:
                    if me.szModule.lower() == nm.lower():
                        return me.modBaseAddr
                    ok = k.Module32Next(snap, ctypes.byref(me))
            finally:
                k.CloseHandle(snap)
            return None
        time.sleep(0.05)
    return None


# ============================ scanner: regions + scanning ==================== #
def regions(reader, protect_mask=READABLE):
    res = []
    mbi = MBI()
    k = _kernel32()
    addr = 0
    MAX = 0x7FFFFFFFFFFF
    while addr < MAX:
        if not k.VirtualQueryEx(reader.handle, ctypes.c_void_p(addr),
                                ctypes.byref(mbi), ctypes.sizeof(mbi)):
            break
        size = mbi.RegionSize
        if mbi.State == MEM_COMMIT and (mbi.Protect & protect_mask) and not (mbi.Protect & PAGE_GUARD):
            res.append((mbi.BaseAddress or addr, size))
        if size == 0:
            break
        addr += size
    return res


def writable_regions(reader):
    return regions(reader, WRITABLE)


def scan(reader, regs, needles, aligned=False):
    found = {n: [] for n in needles}
    if aligned and needles and all(len(n) == 8 for n in needles):
        val2needle = {struct.unpack("<Q", n)[0]: n for n in needles}
        wanted = set(val2needle)
        CHUNK = 16 * 1024 * 1024
        for base, size in regs:
            off = 0
            while off < size:
                n = min(CHUNK, size - off)
                n -= n % 8
                if n <= 0:
                    break
                data = reader.read(base + off, n)
                if data and len(data) >= 8:
                    m = len(data) // 8
                    present = wanted.intersection(struct.unpack("<%dQ" % m, data[:m * 8]))
                    for v in present:
                        nd = val2needle[v]
                        start = 0
                        while True:
                            i = data.find(nd, start)
                            if i < 0:
                                break
                            if i % 8 == 0:
                                found[nd].append(base + off + i)
                            start = i + 1
                off += CHUNK
        return found
    CHUNK = 32 * 1024 * 1024
    OVER = 256
    for base, size in regs:
        off = 0
        while off < size:
            data = reader.read(base + off, min(CHUNK + OVER, size - off))
            if data:
                for nd in needles:
                    start = 0
                    while True:
                        i = data.find(nd, start)
                        if i < 0:
                            break
                        a = base + off + i
                        if not aligned or a % 8 == 0:
                            found[nd].append(a)
                        start = i + 1
            off += CHUNK
    return found


def scan_i64_range(reader, regs, lo, hi, cap=20000):
    hits = []
    CHUNK = 16 * 1024 * 1024
    for base, size in regs:
        off = 0
        while off < size:
            n = min(CHUNK, size - off)
            n -= n % 8
            if n <= 0:
                break
            data = reader.read(base + off, n)
            if data and len(data) >= 8:
                m = len(data) // 8
                for i, v in enumerate(struct.unpack("<%dQ" % m, data[:m * 8])):
                    if lo <= v <= hi:
                        hits.append(base + off + i * 8)
                        if len(hits) >= cap:
                            return hits
            off += CHUNK
    return hits


def in_region(regs, addr):
    return any(b <= addr < b + s for b, s in regs)


# ============================ Reader: typed reads ============================ #
class Reader:
    def __init__(self, handle):
        self.handle = handle

    def read(self, addr, size):
        if not addr or size <= 0:
            return None
        buf = (ctypes.c_char * size)()
        n = ctypes.c_size_t(0)
        if not _kernel32().ReadProcessMemory(
                self.handle, ctypes.c_void_p(addr), buf, size, ctypes.byref(n)):
            return None
        return bytes(buf[:n.value])

    def rptr(self, a):
        b = self.read(a, 8)
        return struct.unpack("<Q", b)[0] if b and len(b) == 8 else None

    def ri32(self, a):
        b = self.read(a, 4)
        return struct.unpack("<i", b)[0] if b and len(b) == 4 else None

    def ru32(self, a):
        b = self.read(a, 4)
        return struct.unpack("<I", b)[0] if b and len(b) == 4 else None

    def ri64(self, a):
        b = self.read(a, 8)
        return struct.unpack("<q", b)[0] if b and len(b) == 8 else None

    def ru64(self, a):
        b = self.read(a, 8)
        return struct.unpack("<Q", b)[0] if b and len(b) == 8 else None

    def rf32(self, a):
        b = self.read(a, 4)
        return struct.unpack("<f", b)[0] if b and len(b) == 4 else None

    def rf64(self, a):
        b = self.read(a, 8)
        return struct.unpack("<d", b)[0] if b and len(b) == 8 else None

    def read_cstr(self, a, maxlen=64):
        if not a:
            return None
        b = self.read(a, maxlen)
        if not b:
            return None
        nul = b.find(b"\x00")
        s = b[:nul] if nul >= 0 else b
        return s.decode("ascii", "replace") if s and all(32 <= c < 127 for c in s) else ("" if not s else None)

    def read_string(self, a):
        if not a:
            return None
        ln = self.ri32(a + String.LENGTH)
        if ln is None or ln < 0 or ln > 4096:
            return None
        if ln == 0:
            return ""
        raw = self.read(a + String.CHARS, ln * 2)
        return raw.decode("utf-16-le", "replace") if raw else None

    def read_struct(self, addr, fmt):
        size = struct.calcsize(fmt)
        b = self.read(addr, size)
        return struct.unpack(fmt, b) if b and len(b) == size else None

    def read_array_ptrs(self, arr, count):
        if not arr or count <= 0:
            return []
        b = self.read(arr + Array.DATA, count * 8)
        return list(struct.unpack(f"<{count}Q", b)) if b and len(b) == count * 8 else []

    def list_ptrs(self, list_obj, cap=8000):
        if not list_obj:
            return []
        size = self.ri32(list_obj + List.SIZE)
        items = self.rptr(list_obj + List.ITEMS)
        if not size or not items or size < 0 or size > cap:
            return []
        return [p for p in self.read_array_ptrs(items, size) if p]

    def list_iter(self, list_obj, cap=8000):
        yield from self.list_ptrs(list_obj, cap)

    def arr_u64(self, arr, cap=64):
        if not arr:
            return []
        ln = self.ri32(arr + Array.MAX_LENGTH)
        if ln is None or ln < 0 or ln > cap:
            return []
        b = self.read(arr + Array.DATA, ln * 8)
        return list(struct.unpack(f"<{ln}Q", b)) if b and len(b) == ln * 8 else []

    def arr_i32(self, arr, cap=64):
        if not arr:
            return []
        ln = self.ri32(arr + Array.MAX_LENGTH)
        if ln is None or ln < 0 or ln > cap:
            return []
        b = self.read(arr + Array.DATA, ln * 4)
        return list(struct.unpack(f"<{ln}i", b)) if b and len(b) == ln * 4 else []

    def dict8b_items(self, dict_obj, cap=100000):
        if not dict_obj:
            return
        ent = self.rptr(dict_obj + Dict.ENTRIES)
        cnt = self.ri32(dict_obj + Dict.COUNT)
        if not ent or cnt is None or cnt < 0 or cnt > cap:
            return
        used = j = 0
        limit = cnt + 64
        while used < cnt and j < limit:
            e = ent + Dict.DATA + j * Dict8B.STRIDE
            j += 1
            h = self.ri32(e + Dict8B.HASH)
            if h is None:
                break
            if h < 0:
                continue
            used += 1
            yield self.ri32(e + Dict8B.KEY), self.ri64(e + Dict8B.VALUE)

    pointer = rptr
    i32 = ri32
    i64 = ri64
    f32 = rf32
