"""resolver.py — finds IL2CPP classes and their instances by SCANNING (no calibration).

PROVEN method (3 passes), identical to the one validated in the monolith:
  1) scan the name STRING ("StageManager\0") across the regions;
  2) scan 8-aligned pointers to each string -> K = ploc - Class.NAME; validate that
     K is an Il2CppClass (name round-trips == name AND element_class/cast_class == K);
  3) scan pointers to each K -> instances (excluding self-refs [K, K+0x400)).
Re-resolve on every launch (ASLR). Does NOT work for names < 3 letters (use finder.py).

resolve_via_rva() is the PRIMARY in the fast path (index + bbwf, ~ms); resolve() (scan) is the
permanent FALLBACK. Any sanity-fail in rva → None → the caller falls back to the scan."""

import struct
import time

from config.offsets import Class, List, LogManager, MonsterSpawnManager
from il2cpp import typeinfo
from il2cpp.finder import bbwf_from_klass
from shared.memory import scan

SINGLETONS = {"MonsterSpawnManager", "LogManager", "StageManager"}


def _manager_inst_ok(reader, name, inst):
    if not inst:
        return False
    if name == "MonsterSpawnManager":
        s = reader.ri32((reader.rptr(inst + MonsterSpawnManager.MONSTER_LIST) or 0) + List.SIZE)
        return s is not None and 0 <= s < 2000
    if name == "LogManager":
        s = reader.ri32((reader.rptr(inst + LogManager.LOG_LIST) or 0) + List.SIZE)
        return s is not None and 0 <= s < 100000
    return True


def resolve_via_rva(reader, tbase, indices, targets, singletons=SINGLETONS):
    classes = {}
    instances = {}
    for name in targets:
        idx = indices.get(name)
        if idx is None:
            return None
        K = typeinfo.class_by_index(reader, tbase, idx)
        if not K or typeinfo.class_name(reader, K) != name:
            return None
        classes[name] = {K}
        if name in singletons:
            inst = bbwf_from_klass(reader, K)
            if not _manager_inst_ok(reader, name, inst):
                return None
            instances[name] = [inst]
        else:
            instances[name] = []
    return classes, instances


def instances_of(reader, regions, k_by_name, cap=4000):
    targets = {name: K for name, K in (k_by_name or {}).items() if K}
    needles = {struct.pack("<Q", K): K for K in set(targets.values())}
    res = scan(reader, regions, list(needles.keys()), aligned=True) if needles else {}
    out = {name: [] for name in targets}
    for name, K in targets.items():
        for a in res.get(struct.pack("<Q", K), []):
            if not (K <= a < K + 0x400):
                out[name].append(a)
                if len(out[name]) >= cap:
                    break
    return out


def resolve(reader, regions, targets):
    _t0 = time.time()
    _mb = sum(s for _, s in regions) / (1024 * 1024)
    print(f"[resolve] scanning {len(regions)} readable regions (~{_mb:.0f} MB) for {len(targets)} classes")
    str_needles = {t: (t.encode() + b"\x00") for t in targets}
    res1 = scan(reader, regions, list(str_needles.values()))
    name_addrs = {t: res1.get(str_needles[t], []) for t in targets}
    _t1 = time.time()
    print(f"[resolve] pass1 name-strings: {len(targets)} needles -> "
          f"{sum(len(v) for v in name_addrs.values())} hits in {_t1 - _t0:.1f}s")

    all_str = {a for addrs in name_addrs.values() for a in addrs}
    needles2 = {struct.pack("<Q", a): a for a in all_str}
    res2 = scan(reader, regions, list(needles2.keys()), aligned=True) if needles2 else {}
    classes = {t: set() for t in targets}
    for nd, sval in needles2.items():
        owner = next((t for t in targets if sval in name_addrs[t]), None)
        if not owner:
            continue
        for ploc in res2.get(nd, []):
            K = ploc - Class.NAME
            if reader.read_cstr(reader.rptr(K + Class.NAME)) == owner and (
                    reader.rptr(K + Class.ELEMENT_CLASS) == K or reader.rptr(K + Class.CAST_CLASS) == K):
                classes[owner].add(K)
    _t2 = time.time()
    print(f"[resolve] pass2 ptr->name: {len(needles2)} needles -> "
          f"{sum(len(res2.get(nd, [])) for nd in needles2)} ptr-hits, "
          f"{sum(len(v) for v in classes.values())} classes in {_t2 - _t1:.1f}s")

    all_K = {k for ks in classes.values() for k in ks}
    needles3 = {struct.pack("<Q", k): k for k in all_K}
    res3 = scan(reader, regions, list(needles3.keys()), aligned=True) if needles3 else {}
    instances = {t: [] for t in targets}
    for nd, kval in needles3.items():
        owner = next((t for t in targets if kval in classes[t]), None)
        if owner:
            for a in res3.get(nd, []):
                if not (kval <= a < kval + 0x400):
                    instances[owner].append(a)
    _t3 = time.time()
    print(f"[resolve] pass3 ptr->class: {len(needles3)} needles -> "
          f"{sum(len(v) for v in instances.values())} instances in {_t3 - _t2:.1f}s "
          f"(total resolve {_t3 - _t0:.1f}s)")
    return classes, instances
