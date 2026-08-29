"""obscured.py — decode ACTk (CodeStage.AntiCheat) Obscured values from their OWN struct.

ObscuredInt:    value = ((hidden - key) & 0xFFFFFFFF) ^ key
ObscuredFloat:  value = reinterpret_f32( key ^ byteswap_1_2(hidden) )
ObscuredDouble: value = reinterpret_f64( key ^ byteswap8(hidden) )
"""

import struct


def _byteswap_1_2(v):
    return (v & 0xFF) | ((v >> 16) & 0xFF) << 8 | ((v >> 8) & 0xFF) << 16 | (v & 0xFF000000)


_BYTE8_PERM = (1, 0, 2, 3, 7, 4, 6, 5)


def _byteswap8(v):
    b = [(v >> (8 * i)) & 0xFF for i in range(8)]
    r = 0
    for i, src in enumerate(_BYTE8_PERM):
        r |= b[src] << (8 * i)
    return r


def decode_obscured_int(hidden, key):
    if hidden is None or key is None:
        return None
    raw = ((((hidden - key) & 0xFFFFFFFF) ^ key) & 0xFFFFFFFF)
    return struct.unpack("<i", struct.pack("<I", raw))[0]


def decode_obscured_float(hidden, key):
    if hidden is None or key is None:
        return None
    bits = (key ^ _byteswap_1_2(hidden)) & 0xFFFFFFFF
    return struct.unpack("<f", struct.pack("<I", bits))[0]


def decode_obscured_double(hidden, key):
    if hidden is None or key is None:
        return None
    bits = (key ^ _byteswap8(hidden)) & 0xFFFFFFFFFFFFFFFF
    return struct.unpack("<d", struct.pack("<Q", bits))[0]
