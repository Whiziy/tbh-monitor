"""Low-level, read-only memory access + IL2CPP offset scaffold.

Two layers:

1. ProcessMemory - a thin, generic wrapper around OpenProcess /
   ReadProcessMemory (Windows only). This part works as-is for any process.

2. GameOffsets - a placeholder for the actual field offsets inside
   Task Bar Hero's IL2CPP classes (DPS, gold, stage, etc). These are
   NOT included here because they are game- and build-specific and can
   only be found by dumping this exact game build with a tool like
   Il2CppDumper (reads GameAssembly.dll + global-metadata.dat and
   reconstructs class/field layouts + offsets). See README.md "Finding
   the offsets" section for the step-by-step.

Until real offsets are filled in, `GameReader.read()` runs in demo mode
and returns synthetic data so the UI/overlay can be built and tested
independently of reverse-engineering work.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes as wintypes
import random
import time
from dataclasses import dataclass
from typing import Optional

from core.models import RunStats

PROCESS_VM_READ = 0x0010
PROCESS_QUERY_INFORMATION = 0x0400


class ProcessMemory:
    """Read-only handle to another process's memory. Never writes."""

    def __init__(self, pid: int):
        self.pid = pid
        self._handle = ctypes.windll.kernel32.OpenProcess(
            PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid
        )
        if not self._handle:
            raise OSError(f"Could not open process {pid} (need matching bitness / permissions)")

    def close(self) -> None:
        if self._handle:
            ctypes.windll.kernel32.CloseHandle(self._handle)
            self._handle = None

    def read_bytes(self, address: int, size: int) -> Optional[bytes]:
        buf = ctypes.create_string_buffer(size)
        bytes_read = ctypes.c_size_t(0)
        ok = ctypes.windll.kernel32.ReadProcessMemory(
            self._handle, ctypes.c_void_p(address), buf, size, ctypes.byref(bytes_read)
        )
        if not ok:
            return None
        return buf.raw[: bytes_read.value]

    def read_i32(self, address: int) -> Optional[int]:
        data = self.read_bytes(address, 4)
        return int.from_bytes(data, "little", signed=True) if data else None

    def read_u32(self, address: int) -> Optional[int]:
        data = self.read_bytes(address, 4)
        return int.from_bytes(data, "little", signed=False) if data else None

    def read_f32(self, address: int) -> Optional[float]:
        data = self.read_bytes(address, 4)
        return ctypes.cast(data, ctypes.POINTER(ctypes.c_float)).contents.value if data else None

    def read_i64(self, address: int) -> Optional[int]:
        data = self.read_bytes(address, 8)
        return int.from_bytes(data, "little", signed=True) if data else None

    def read_ptr(self, address: int) -> Optional[int]:
        return self.read_i64(address)

    def module_base(self, module_name: str) -> Optional[int]:
        """Base address of a loaded module (e.g. 'GameAssembly.dll') in the
        target process, via CreateToolhelp32Snapshot."""
        TH32CS_SNAPMODULE = 0x00000008
        TH32CS_SNAPMODULE32 = 0x00000010

        class MODULEENTRY32(ctypes.Structure):
            _fields_ = [
                ("dwSize", wintypes.DWORD),
                ("th32ModuleID", wintypes.DWORD),
                ("th32ProcessID", wintypes.DWORD),
                ("GlblcntUsage", wintypes.DWORD),
                ("ProccntUsage", wintypes.DWORD),
                ("modBaseAddr", ctypes.POINTER(ctypes.c_byte)),
                ("modBaseSize", wintypes.DWORD),
                ("hModule", wintypes.HMODULE),
                ("szModule", ctypes.c_char * 256),
                ("szExePath", ctypes.c_char * 260),
            ]

        snapshot = ctypes.windll.kernel32.CreateToolhelp32Snapshot(
            TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, self.pid
        )
        if snapshot == -1:
            return None
        try:
            entry = MODULEENTRY32()
            entry.dwSize = ctypes.sizeof(MODULEENTRY32)
            found = ctypes.windll.kernel32.Module32First(snapshot, ctypes.byref(entry))
            while found:
                if entry.szModule.decode(errors="ignore").lower() == module_name.lower():
                    return ctypes.addressof(entry.modBaseAddr.contents)
                found = ctypes.windll.kernel32.Module32Next(snapshot, ctypes.byref(entry))
            return None
        finally:
            ctypes.windll.kernel32.CloseHandle(snapshot)


@dataclass
class GameOffsets:
    """TODO: fill these in after dumping this game build with Il2CppDumper.
    Everything here is a placeholder (0x0) until then — see README.md.
    """

    game_assembly_module: str = "GameAssembly.dll"
    # Static pointer chain from GameAssembly.dll base to the "run manager"
    # instance. Format: base + static_offset, then dereference through
    # each offset in ptr_chain.
    run_manager_static_offset: int = 0x0
    run_manager_ptr_chain: tuple[int, ...] = ()

    # Field offsets *within* the resolved run-manager instance.
    off_dps: int = 0x0
    off_total_damage: int = 0x0
    off_gold: int = 0x0
    off_exp: int = 0x0
    off_mobs_killed: int = 0x0
    off_mobs_total: int = 0x0
    off_stage_index: int = 0x0
    off_mode_index: int = 0x0


class GameReader:
    """Turns raw memory into a RunStats snapshot. Falls back to demo mode
    (synthetic numbers) when offsets aren't configured yet, so the rest of
    the app can be built and demoed without the real game running.
    """

    def __init__(self, pid: int, demo_mode: bool = False):
        self.offsets = GameOffsets()
        self._mem: Optional[ProcessMemory] = None
        self._run_manager_addr: Optional[int] = None
        self._t0 = time.time()
        self._offsets_ready = self._offsets_configured()

        if demo_mode:
            self.demo_mode = True
        elif not self._offsets_ready:
            self.demo_mode = False
            self._mem = None
        else:
            self.demo_mode = False
            try:
                self._mem = ProcessMemory(pid)
            except OSError:
                self._mem = None

    @staticmethod
    def _offsets_configured() -> bool:
        o = GameOffsets()
        return o.off_dps != 0x0  # becomes True once real offsets are filled in

    def close(self) -> None:
        if self._mem:
            self._mem.close()

    def _resolve_run_manager(self) -> Optional[int]:
        if self._mem is None:
            return None
        base = self._mem.module_base(self.offsets.game_assembly_module)
        if base is None:
            return None
        addr = self._mem.read_ptr(base + self.offsets.run_manager_static_offset)
        if addr is None:
            return None
        for off in self.offsets.run_manager_ptr_chain:
            addr = self._mem.read_ptr(addr + off)
            if addr is None:
                return None
        return addr

    def read(self, stats: RunStats) -> RunStats:
        if self.demo_mode:
            return self._read_demo(stats)
        if not self._offsets_ready or self._mem is None:
            stats.connected = True
            stats.elapsed_sec = time.time() - stats.run_start_ts
            return stats
        return self._read_real(stats)

    def _read_real(self, stats: RunStats) -> RunStats:
        if self._run_manager_addr is None:
            self._run_manager_addr = self._resolve_run_manager()
        if self._run_manager_addr is None or self._mem is None:
            stats.connected = False
            return stats

        o = self.offsets
        addr = self._run_manager_addr
        stats.connected = True
        stats.dps = self._mem.read_f32(addr + o.off_dps) or stats.dps
        stats.total_damage = self._mem.read_f32(addr + o.off_total_damage) or stats.total_damage
        stats.gold = self._mem.read_i32(addr + o.off_gold) or stats.gold
        stats.exp = self._mem.read_i32(addr + o.off_exp) or stats.exp
        stats.mobs_killed = self._mem.read_i32(addr + o.off_mobs_killed) or stats.mobs_killed
        stats.mobs_total = self._mem.read_i32(addr + o.off_mobs_total) or stats.mobs_total
        stats.elapsed_sec = time.time() - stats.run_start_ts
        return stats

    def _read_demo(self, stats: RunStats) -> RunStats:
        stats.connected = True
        elapsed = time.time() - self._t0
        stats.elapsed_sec = elapsed
        stats.dps = max(0.0, 12000 + 4000 * random.uniform(-1, 1))
        stats.total_damage += stats.dps * 0.25
        stats.gold = int(elapsed * 3.7)
        stats.exp = int(elapsed * 5.2)
        stats.mobs_killed = int(elapsed * 0.8)
        stats.mobs_total = max(stats.mobs_total, stats.mobs_killed + 12)
        stats.mode = "Nightmare"
        stats.stage = "Stage 4 - Act 2"

        stats.chest_detected = None
        if random.random() < 0.005:
            stats.chest_detected = random.choice(["blue", "gold", "other"])

        return stats
