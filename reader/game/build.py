"""build.py — reads the hero's BUILD: equips/mods/skills (from the save) + the 64 live
FINAL stats (id-only) + the LIVE deployed party identity (heroKeys from StageManager.HeroList)."""

import json
import os
import struct

from config.offsets import (HeroRuntime, StatsHolder, Dict, DictFloat, Array, List, Unit,
                            StageManager, HeroInfoData, HeroSaveData, PlayerSaveData,
                            AttributeSaveData, ItemSaveData, ItemEnchant,
                            name_map, EItemParts, EGradeType, EEquipClassType, ERecipeType,
                            StatType, RuneSaveData, InventorySaveData, StashSaveData)
from game import obscured
from shared.utils import resource_path

_PARTS = name_map(EItemParts)
_GRADE = name_map(EGradeType)
_CLAZZ = name_map(EEquipClassType)
_RECIPE = name_map(ERecipeType)
_STAT = name_map(StatType)

UNKNOWN_ITEM_KEY = -1

_SKILL_ATTR = None
_PASSIVE_KEYS = None


def skill_attr_map():
    global _SKILL_ATTR
    if _SKILL_ATTR is None:
        try:
            with open(resource_path(os.path.join("config", "skill_attr_map.json")),
                      encoding="utf-8") as f:
                _SKILL_ATTR = {int(k): int(v) for k, v in json.load(f).items()}
        except Exception:
            _SKILL_ATTR = {}
    return _SKILL_ATTR


def passive_skill_keys():
    global _PASSIVE_KEYS
    if _PASSIVE_KEYS is None:
        try:
            with open(resource_path(os.path.join("config", "passive_skill_keys.json")),
                      encoding="utf-8") as f:
                _PASSIVE_KEYS = {int(k) for k in json.load(f)}
        except Exception:
            _PASSIVE_KEYS = set()
    return _PASSIVE_KEYS


def read_attribute_levels(reader, psd):
    res = {}
    if not psd:
        return res
    try:
        for a in reader.list_iter(reader.rptr(psd + PlayerSaveData.ATTRIBUTES)):
            k = reader.ri32(a + AttributeSaveData.KEY)
            if k is None:
                continue
            lv = reader.ri32(a + AttributeSaveData.LEVEL)
            if lv is not None:
                res[k] = lv
    except Exception:
        return {}
    return res


def _iter_party_slots(reader, sm, hero_cat=None):
    try:
        if not sm:
            return
        hl = reader.rptr(sm + StageManager.HERO_LIST)
        if not hl:
            return
        n = reader.ri32(hl + Array.MAX_LENGTH)
        if n is None or not (0 < n <= 12):
            return
        for i in range(n):
            h = reader.rptr(hl + Array.DATA + i * 8)
            if not h:
                continue
            uf = reader.rptr(h + Unit.CACHE)
            if not uf:
                continue
            hi = reader.rptr(uf + HeroRuntime.INFO)
            hk = reader.ri32(hi + HeroInfoData.HERO_KEY) if hi else None
            if hk is None or not (0 < hk < 10_000_000):
                continue
            if hero_cat is not None and hk not in hero_cat:
                continue
            yield i, hk, uf
    except Exception:
        return


def read_live_party(reader, sm, hero_cat=None, save_heroes=None):
    res = {}
    try:
        for _slot, hk, uf in _iter_party_slots(reader, sm, hero_cat):
            lvl = obscured.decode_obscured_int(reader.ru32(uf + HeroRuntime.LEVEL_HIDDEN),
                                               reader.ru32(uf + HeroRuntime.LEVEL_KEY))
            if lvl is None or not (0 < lvl <= 200):
                lvl = (save_heroes or {}).get(hk, (None, None))[0]
            exp = obscured.decode_obscured_double(reader.ru64(uf + HeroRuntime.EXP_HIDDEN),
                                                  reader.ru64(uf + HeroRuntime.EXP_KEY))
            res[hk] = (lvl, exp)
    except Exception:
        return {}
    return res


def read_party_slots(reader, sm, hero_cat=None):
    return {hk: slot for slot, hk, _uf in _iter_party_slots(reader, sm, hero_cat)}


def _raw_hero_list(reader, sm):
    out = []
    try:
        if not sm:
            return out
        hl = reader.rptr(sm + StageManager.HERO_LIST)
        if not hl:
            return out
        n = reader.ri32(hl + Array.MAX_LENGTH)
        if n is None or not (0 < n <= 12):
            return out
        for i in range(n):
            h = reader.rptr(hl + Array.DATA + i * 8)
            uf = reader.rptr(h + Unit.CACHE) if h else None
            hi = reader.rptr(uf + HeroRuntime.INFO) if uf else None
            hk = reader.ri32(hi + HeroInfoData.HERO_KEY) if hi else None
            lvl = reader.ri32(uf + HeroRuntime.LEVEL_FAKE) if uf else None
            exp = reader.rf64(uf + HeroRuntime.EXP_FAKE) if uf else None
            out.append((hk, lvl, exp))
    except Exception:
        return out
    return out


def describe_sm_candidates(reader, sm_list, picked, hero_cat=None):
    hk_accept, carriers, ghosts = 0, 0, []
    try:
        for a in (sm_list or []):
            heroes = _raw_hero_list(reader, a)
            if not any(hk is not None and 0 < hk < 10_000_000 for hk, _, _ in heroes):
                continue
            hk_accept += 1
            if read_live_party(reader, a, hero_cat):
                carriers += 1
            elif len(ghosts) < 5:
                ghosts.append((a, heroes[:6]))
    except Exception:
        pass
    return {"total": len(sm_list or []), "hk_accept": hk_accept,
            "carriers": carriers, "picked": picked, "ghosts": ghosts}


def hero_in_run(hero_key, live_keys):
    return bool(live_keys) and hero_key in live_keys


def slot_sort_key(slot):
    return (slot is None, slot or 0)


def order_party_by_slot(heroes):
    return sorted(heroes, key=lambda h: slot_sort_key(h.get("slot")))


def resolve_party_slots(hero_keys, slots_now, slots_seen=None):
    seen = slots_seen or {}
    used = set(slots_now.values())
    out = {}
    for hk in hero_keys:
        if hk in slots_now:
            out[hk] = slots_now[hk]
        else:
            s = seen.get(hk)
            if s is not None and s not in used:
                out[hk] = s
                used.add(s)
            else:
                out[hk] = None
    return out


def read_stats_dict(reader, uf):
    try:
        xd = reader.rptr(uf + HeroRuntime.STATS_HOLDER)
        d = reader.rptr(xd + StatsHolder.FINAL_STATS) if xd else None
        if not d:
            return {}
        ent = reader.rptr(d + Dict.ENTRIES)
        n = reader.ri32(ent + Array.MAX_LENGTH) if ent else None
        if n is None or not (0 < n <= 512):
            return {}
        raw = reader.read(ent + Array.DATA, n * DictFloat.STRIDE)
        if not raw or len(raw) < n * DictFloat.STRIDE:
            return {}
        out = {}
        for i in range(n):
            o = i * DictFloat.STRIDE
            if struct.unpack_from("<i", raw, o + DictFloat.HASH)[0] < 0:
                continue
            key = struct.unpack_from("<i", raw, o + DictFloat.KEY)[0]
            val = struct.unpack_from("<f", raw, o + DictFloat.VALUE)[0]
            out[key] = round(val, 4)
        return out
    except Exception:
        return {}


def read_live_stats_by_hero(reader, sm):
    res = {}
    try:
        if not sm:
            return res
        hl = reader.rptr(sm + StageManager.HERO_LIST)
        n = reader.ri32(hl + Array.MAX_LENGTH) if hl else None
        if n is None or not (0 < n <= 12):
            return res
        for i in range(n):
            h = reader.rptr(hl + Array.DATA + i * 8)
            uf = reader.rptr(h + Unit.CACHE) if h else None
            hi = reader.rptr(uf + HeroRuntime.INFO) if uf else None
            hk = reader.ri32(hi + HeroInfoData.HERO_KEY) if hi else None
            if hk is None or not (0 < hk < 10_000_000):
                continue
            st = read_stats_dict(reader, uf)
            if st:
                res[hk] = st
    except Exception:
        return {}
    return res


def read_mods(reader, item_addr):
    arr = reader.rptr(item_addr + ItemSaveData.ENCHANT_DATA)
    if not arr:
        return []
    ln = reader.ri32(arr + Array.MAX_LENGTH)
    if ln is None or ln < 0 or ln > 64:
        return []
    res = []
    for i in range(ln):
        b = arr + Array.DATA + i * ItemEnchant.STRIDE
        st = reader.ri32(b + ItemEnchant.STAT_TYPE)
        val = reader.ri32(b + ItemEnchant.VALUE)
        if (not st) and (not val):
            continue
        rc = reader.ri32(b + ItemEnchant.RECIPE)
        res.append({"recipeId": rc, "recipe": _RECIPE.get(rc, f"r{rc}"),
                    "statId": st, "stat": _STAT.get(st, f"stat{st}"),
                    "value": val, "tier": reader.ri32(b + ItemEnchant.TIER)})
    return res


def read_build(reader, psd, item_cat, hero_cat):
    out = []
    if not psd:
        return out
    attr_levels = read_attribute_levels(reader, psd)
    skill_attr = skill_attr_map()
    passive_keys = passive_skill_keys()
    uid2item = {}
    for a in reader.list_iter(reader.rptr(psd + PlayerSaveData.ITEMS)):
        uid = reader.ru64(a + ItemSaveData.UNIQUE_ID)
        if uid:
            uid2item[uid] = a
    for h in reader.list_iter(reader.rptr(psd + PlayerSaveData.HEROES), cap=200):
        hk = reader.ri32(h + HeroSaveData.HERO_KEY)
        lvl = reader.ri32(h + HeroSaveData.LEVEL)
        exp = reader.rf64(h + HeroSaveData.EXP)
        if hk is None or lvl is None:
            continue
        if not (lvl > 1 or (exp or 0) > 0):
            continue
        cls = hero_cat.get(hk)
        items = []
        for pos, uid in enumerate(reader.arr_u64(reader.rptr(h + HeroSaveData.EQUIPPED_ITEMS))):
            if not uid:
                continue
            it = uid2item.get(uid)
            if not it:
                pslot = pos + 1
                items.append({"slot": _PARTS.get(pslot, "?"),
                              "slotId": pslot if pslot in _PARTS else None,
                              "grade": "?", "gradeId": None, "itemKey": UNKNOWN_ITEM_KEY,
                              "uniqueId": str(uid), "level": None, "mods": []})
                continue
            ik = reader.ri32(it + ItemSaveData.ITEM_KEY)
            grade, parts, ilvl = item_cat.get(ik, (None, None, None))
            items.append({"slot": _PARTS.get(parts, "?"), "slotId": parts,
                          "grade": _GRADE.get(grade, "?"), "gradeId": grade,
                          "itemKey": ik, "uniqueId": str(uid), "level": ilvl,
                          "mods": read_mods(reader, it)})
        skills = [{"key": k, "lv": attr_levels.get(skill_attr.get(k))}
                  for k in reader.arr_i32(reader.rptr(h + HeroSaveData.EQUIPPED_SKILLS)) if k]
        skills += [{"key": a, "lv": lv}
                   for a, lv in sorted(attr_levels.items())
                   if lv and lv > 0 and a // 1000 == hk and a in passive_keys]
        skill_levels = {str(a): lv for a, lv in attr_levels.items()
                        if lv and lv > 0 and a // 1000 == hk}
        out.append({"heroKey": hk, "class": _CLAZZ.get(cls, "?"), "classId": cls,
                    "level": lvl, "exp": round(exp or 0.0, 2), "items": items,
                    "skills": skills, "skillLevels": skill_levels})
    return out


def _item_view(reader, it, item_cat):
    ik = reader.ri32(it + ItemSaveData.ITEM_KEY)
    if ik is None:
        return None
    grade, parts, ilvl = item_cat.get(ik, (None, None, None))
    return {"itemKey": ik, "uniqueId": str(reader.ru64(it + ItemSaveData.UNIQUE_ID) or 0),
            "slotId": parts, "gradeId": grade, "level": ilvl, "mods": read_mods(reader, it)}


def _list_or_none(reader, list_obj, cap):
    if not list_obj:
        return None
    size = reader.ri32(list_obj + List.SIZE)
    if size is None or size < 0 or size > cap:
        return None
    if size == 0:
        return []
    items = reader.rptr(list_obj + List.ITEMS)
    if not items:
        return None
    b = reader.read(items + Array.DATA, size * 8)
    if not b or len(b) < size * 8:
        return None
    return [p for p in struct.unpack(f"<{size}Q", b) if p]


def _read_runes(reader, psd):
    try:
        raw = _list_or_none(reader, reader.rptr(psd + PlayerSaveData.RUNES), 5000)
        if raw is None:
            return None
        out = []
        for a in raw:
            k = reader.ri32(a + RuneSaveData.KEY)
            lv = reader.ri32(a + RuneSaveData.LEVEL)
            if k is not None and lv is not None:
                out.append({"key": k, "level": lv})
        return out
    except Exception:
        return None


def _read_slot_items(reader, psd, list_off, uid_off, uid2item, item_cat):
    if uid2item is None:
        return None
    try:
        raw = _list_or_none(reader, reader.rptr(psd + list_off), 100000)
        if raw is None:
            return None
        out = []
        for s in raw:
            uid = reader.ru64(s + uid_off)
            if not uid:
                continue
            it = uid2item.get(uid)
            if it:
                v = _item_view(reader, it, item_cat)
                if v:
                    out.append(v)
        return out
    except Exception:
        return None


def read_account_snapshot(reader, psd, item_cat):
    if not psd:
        return None, None, None
    runes = _read_runes(reader, psd)
    try:
        items_raw = _list_or_none(reader, reader.rptr(psd + PlayerSaveData.ITEMS), 100000)
        uid2item = None
        if items_raw is not None:
            uid2item = {}
            for it in items_raw:
                uid = reader.ru64(it + ItemSaveData.UNIQUE_ID)
                if uid:
                    uid2item[uid] = it
    except Exception:
        uid2item = None
    inventory = _read_slot_items(reader, psd, PlayerSaveData.INVENTORY_SLOTS,
                                 InventorySaveData.UNIQUE_ID, uid2item, item_cat)
    stash = _read_slot_items(reader, psd, PlayerSaveData.STASH,
                             StashSaveData.UNIQUE_ID, uid2item, item_cat)
    return runes, inventory, stash
