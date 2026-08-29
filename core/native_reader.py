"""Native memory reader for Task Bar Hero.

Thin orchestrator that bridges the reader/ package (tbh-meter's IL2CPP resolver + game data readers)
to our RunStats model. No dependency on tbh-meter app — reads game memory directly.
"""

from __future__ import annotations

import sys
import os
import time
import threading
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'reader'))

from core.models import RunStats, StageClearEvent
from shared import memory
from il2cpp import resolver, typeinfo
from il2cpp.finder import bbwf_from_klass
from game import models, save, build
from metrics.dps import DpsTracker
from metrics import gold as gold_metric
from config.offsets import (
    Monster, EStageDifficulty, MonsterSpawnManager, List,
    LogManager, GetBoxLog, StageClearLog, Class, Obj, CommonSaveData
)


class NativeReader:
    def __init__(self):
        self._handle = None
        self._reader = None
        self._pid = None
        self._msm = None
        self._log_mgr = None
        self._stage_mgr = None
        self._psd_list = []
        self._gold_klass = None
        self._dps_tracker = None
        self._last_stage_key = None
        self._run_start_ts = time.time()
        self._resolved = False
        self._resolving = False
        self._resolve_thread = None
        self._last_log_count = -1
        self._initial_gold = None
        self._mobs_killed_count = 0
        self._prev_monster_addrs = set()

    def close(self) -> None:
        if self._handle:
            memory.close(self._handle)
            self._handle = None
        self._reader = None
        self._resolved = False

    def _try_attach(self) -> bool:
        if self._handle:
            return True
        pid = memory.find_pid()
        if not pid:
            return False
        handle = memory.open_process(pid)
        if not handle:
            return False
        self._handle = handle
        self._reader = memory.Reader(handle)
        self._pid = pid
        return True

    def _resolve_background(self):
        try:
            print("[native_reader] Resolving IL2CPP classes in background...")
            regions = memory.regions(self._reader)
            targets = [
                "MonsterSpawnManager", "LogManager", "StageManager",
                "PlayerSaveData", "CommonSaveData", "GetBoxLog"
            ]
            classes, instances = resolver.resolve(self._reader, regions, targets)
            
            # Resolve MSM via bbwf
            msm_classes = classes.get("MonsterSpawnManager", set())
            if msm_classes:
                K = next(iter(msm_classes))
                self._msm = bbwf_from_klass(self._reader, K)
            
            # Resolve LogManager via bbwf
            log_classes = classes.get("LogManager", set())
            if log_classes:
                K = next(iter(log_classes))
                self._log_mgr = bbwf_from_klass(self._reader, K)

            # Save PSD instances
            self._psd_list = instances.get("PlayerSaveData", [])
            self._gold_klass = None

            if self._msm:
                ml = self._reader.rptr(self._msm + MonsterSpawnManager.MONSTER_LIST)
                s = self._reader.ri32(ml + List.SIZE) if ml else None
                if s is not None and 0 <= s < 100000:
                    self._dps_tracker = DpsTracker()
                    self._resolved = True
                    print(f"[native_reader] Resolved MSM at 0x{self._msm:X} (list size={s})")
                    if self._log_mgr:
                        print(f"[native_reader] Resolved LogManager at 0x{self._log_mgr:X}")
                else:
                    print(f"[native_reader] MSM instance invalid (size={s})")
                    self._msm = None
            else:
                print("[native_reader] MonsterSpawnManager not found or invalid")
        except Exception as e:
            print(f"[native_reader] Resolve failed: {e}")
        finally:
            self._resolving = False

    def _try_resolve(self) -> bool:
        if self._resolved:
            return True
        if self._resolving:
            return False
        if not self._reader:
            return False
        
        self._resolving = True
        self._resolve_thread = threading.Thread(target=self._resolve_background, daemon=True)
        self._resolve_thread.start()
        return False

    def _check_logs(self, stats: RunStats) -> tuple[Optional[str], Optional[StageClearEvent]]:
        if not self._log_mgr:
            return None, None
        log_list_obj = self._reader.rptr(self._log_mgr + LogManager.LOG_LIST)
        if not log_list_obj:
            return None, None
        size = self._reader.ri32(log_list_obj + List.SIZE)
        if size is None or size < 0:
            return None, None

        if self._last_log_count < 0:
            self._last_log_count = size
            return None, None

        if size <= self._last_log_count:
            self._last_log_count = size
            return None, None

        detected_chest = None
        clear_event = None
        logs = self._reader.list_ptrs(log_list_obj, cap=100000)
        new_logs = logs[self._last_log_count:size]
        self._last_log_count = size

        for log_addr in new_logs:
            if not log_addr:
                continue
            klass = self._reader.rptr(log_addr + Obj.KLASS)
            if not klass:
                continue
            name = self._reader.read_cstr(self._reader.rptr(klass + Class.NAME))
            if name == "GetBoxLog":
                mtype = self._reader.ri32(log_addr + GetBoxLog.MONSTER_TYPE)
                if mtype == 2:
                    detected_chest = "blue"
                elif mtype == 1:
                    detected_chest = "gold"
                else:
                    detected_chest = "other"
            elif name == "StageClearLog":
                act = self._reader.ri32(log_addr + StageClearLog.ACT) or 1
                stg = self._reader.ri32(log_addr + StageClearLog.STAGE) or 1
                tm = self._reader.ri32(log_addr + StageClearLog.CLEAR_TIME) or 0
                clear_event = StageClearEvent(act=act, stage=stg, duration_sec=tm)

        return detected_chest, clear_event

    def read(self, stats: RunStats) -> RunStats:
        if not self._try_attach():
            stats.connected = False
            return stats

        if not self._try_resolve():
            stats.connected = False
            return stats

        if not self._resolved:
            stats.connected = False
            return stats

        try:
            stats.connected = True
            stats.stage_clear_event = None

            monsters = list(models.live_monsters(self._reader, self._msm))
            
            self._dps_tracker.update(monsters)
            stats.dps = self._dps_tracker.dps()
            stats.total_damage = self._dps_tracker.total_damage

            # Track killed mobs
            current_addrs = {addr for addr, hp, _ in monsters if hp > 0}
            if self._prev_monster_addrs:
                dead_count = len(self._prev_monster_addrs - current_addrs)
                self._mobs_killed_count += dead_count
            self._prev_monster_addrs = current_addrs

            stats.mobs_killed = self._mobs_killed_count
            stats.mobs_total = len(monsters)

            stage_key = models.live_stage_key(self._reader, self._msm)
            if stage_key and stage_key != self._last_stage_key:
                self._last_stage_key = stage_key
                self._run_start_ts = time.time()
                self._mobs_killed_count = 0
                self._prev_monster_addrs.clear()
                self._initial_gold = None
                stats.reset_run()
                self._dps_tracker.reset()

            stats.elapsed_sec = time.time() - self._run_start_ts

            if stage_key:
                # Stage & Mode formatting (e.g. 1202 -> Act 2 - Stage 2 Normal, 2202 -> Act 2 - Stage 2 Nightmare)
                diff_map = {0: "Normal", 1: "Nightmare", 2: "Hell", 3: "Torment"}
                if 1000 <= stage_key <= 9999:
                    diff_code = (stage_key // 1000) - 1
                    act = (stage_key // 100) % 10
                    stage_no = stage_key % 100
                    stats.mode = diff_map.get(diff_code, "Normal")
                    stats.stage = f"Act {act} - Stage {stage_no}"
                elif stage_key >= 100000:
                    s = str(stage_key)
                    act = int(s[2:4]) if len(s) >= 4 else 1
                    stage_no = int(s[4:6]) if len(s) >= 6 else 1
                    stats.mode = "Normal"
                    stats.stage = f"Act {act} - Stage {stage_no}"
                else:
                    act = (stage_key // 100)
                    stage_no = stage_key % 100
                    stats.mode = "Normal"
                    stats.stage = f"Act {act} - Stage {stage_no}"
            else:
                stats.stage = "-"
                stats.mode = "-"

            # Live / Save Gold
            live_psd = save.pick_live_psd(self._reader, self._psd_list) if self._psd_list else None
            wallet_gold = save.read_gold(self._reader, live_psd) if live_psd else 0

            current_gold = None
            if self._gold_klass:
                current_gold = gold_metric.combat_gold_live(self._reader, self._gold_klass)

            if current_gold is not None:
                if self._initial_gold is None:
                    self._initial_gold = current_gold
                combat_gain = max(0, current_gold - self._initial_gold)
                stats.gold = combat_gain if combat_gain > 0 else wallet_gold
            else:
                stats.gold = wallet_gold

            # Live EXP (Total party EXP or levels)
            heroes = save.read_heroes(self._reader, live_psd) if live_psd else {}
            if heroes:
                total_exp = sum(int(exp) for lvl, exp in heroes.values() if exp is not None)
                if total_exp == 0:
                    total_exp = sum(lvl for lvl, _ in heroes.values() if lvl is not None)
                stats.exp = total_exp
            else:
                stats.exp = 0

            # Check logs for chests & stage clear
            chest, clear_evt = self._check_logs(stats)
            if chest:
                stats.chest_detected = chest
            if clear_evt:
                stats.stage_clear_event = clear_evt

        except Exception as e:
            print(f"[native_reader] Read error: {e}")
            stats.connected = False

        return stats

