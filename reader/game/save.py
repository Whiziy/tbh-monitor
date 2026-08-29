"""save.py — PlayerSaveData readers (plaintext, snapshot) + picking the LIVE instance."""

from config.offsets import (PlayerSaveData, CurrencySaveData, HeroSaveData,
                            CommonSaveData, GOLD_KEY)
from game.build import read_live_party


def read_gold(reader, psd):
    if not psd:
        return 0
    for e in reader.list_iter(reader.rptr(psd + PlayerSaveData.CURRENCIES), cap=200):
        if reader.ri32(e + CurrencySaveData.KEY) == GOLD_KEY:
            return reader.ri64(e + CurrencySaveData.QUANTITY) or 0
    return 0


def read_heroes(reader, psd):
    res = {}
    if not psd:
        return res
    for e in reader.list_iter(reader.rptr(psd + PlayerSaveData.HEROES), cap=200):
        k = reader.ri32(e + HeroSaveData.HERO_KEY)
        lvl = reader.ri32(e + HeroSaveData.LEVEL)
        exp = reader.rf64(e + HeroSaveData.EXP)
        if k is None or lvl is None or exp is None:
            continue
        if lvl > 1 or exp > 0:
            res[k] = (lvl, exp)
    return res


def pick_live_psd(reader, cands):
    best, bg = None, -1
    for a in (cands or [])[:200]:
        g = read_gold(reader, a)
        if g and g > bg:
            bg, best = g, a
    return best


def pick_live_sm(reader, cands, hero_cat=None):
    for a in (cands or []):
        if read_live_party(reader, a, hero_cat):
            return a
    return None


_MAX_PLAYTIME_S = 1e9


def pick_live_csd(reader, cands, stage_info=None):
    best, best_rank = None, (False, -1.0)
    for a in (cands or []):
        key = reader.ri32(a + CommonSaveData.CURRENT_STAGE_KEY)
        pt = reader.rf32(a + CommonSaveData.PLAYTIME)
        if key is None or not (0 < key < 10_000_000):
            continue
        if pt is None or not (0.0 < pt < _MAX_PLAYTIME_S):
            continue
        rank = (bool(stage_info) and key in stage_info, pt)
        if rank > best_rank:
            best_rank, best = rank, a
    return best
