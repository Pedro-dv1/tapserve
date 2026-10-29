"""Minimal container metadata fixtures, not playback/decoder fixtures."""

import struct


def box(kind, payload):
    return struct.pack(">I4s", len(payload) + 8, kind) + payload


def mp4_metadata(codec=b"avc1", payload=b"frame", brand=b"isom"):
    visual = bytearray(78)
    visual[24:28] = struct.pack(">HH", 16, 16)
    sample = box(codec, bytes(visual) + box(b"avcC", b"\x01\x42\x00\x1e\xff\xe1\x00\x01"))
    stsd = box(b"stsd", b"\0" * 4 + struct.pack(">I", 1) + sample)
    movie = box(b"mvhd", b"\0" * 12 + struct.pack(">II", 1000, 1000))
    movie += box(b"trak", box(b"mdia", box(b"minf", box(b"stbl", stsd))))
    return box(b"ftyp", brand + b"\0" * 4 + b"isom") + box(b"moov", movie) + box(b"mdat", payload)


def element(identifier, payload):
    if len(payload) >= 127:
        size = (0x4000 | len(payload)).to_bytes(2, "big")
    else:
        size = bytes([0x80 | len(payload)])
    return identifier.to_bytes((identifier.bit_length() + 7) // 8, "big") + size + payload


def webm_metadata(codec=b"V_VP9"):
    header = element(0x1A45DFA3, element(0x4282, b"webm"))
    info = element(0x1549A966, element(0x4489, struct.pack(">d", 1000)))
    tracks = element(0x1654AE6B, element(0xAE, element(0x83, b"\x01") + element(0x86, codec)))
    cluster = element(0xE7, b"\0") + element(0xA3, b"\x81\0\0\x80frame")
    return header + element(0x18538067, info + tracks + element(0x1F43B675, cluster))
