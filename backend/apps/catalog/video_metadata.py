"""Bounded local metadata inspection for browser-compatible MP4/MOV and WebM."""

import math
import struct


class MediaReader:
    def __init__(self, stream, size):
        self.stream, self.size, self.remaining = stream, size, 10000

    def read(self, offset, length):
        if offset < 0 or length > 65536 or offset + length > self.size:
            raise ValueError("Invalid metadata bounds")
        self.stream.seek(offset)
        result = self.stream.read(length)
        if len(result) != length:
            raise ValueError("Truncated media")
        return result

    def boxes(self, start, end):
        while start < end:
            self.remaining -= 1
            if self.remaining < 0 or end - start < 8:
                raise ValueError("Invalid box count/size")
            size, kind = struct.unpack(">I4s", self.read(start, 8))
            header = 8
            if size == 1:
                size = int.from_bytes(self.read(start + 8, 8), "big")
                header = 16
            elif size == 0:
                size = end - start
            if size < header or start + size > end:
                raise ValueError("Invalid media box")
            yield kind, start + header, start + size
            start += size

    def vint(self, offset, *, identifier=False):
        first = self.read(offset, 1)[0]
        width = next((n for n in range(1, 9) if first & (1 << (8 - n))), 0)
        if not width or identifier and width > 4:
            raise ValueError("Invalid EBML integer")
        raw = self.read(offset, width)
        value = int.from_bytes(raw, "big")
        return (value if identifier else value & ((1 << (7 * width)) - 1)), width

    def elements(self, start, end):
        while start < end:
            self.remaining -= 1
            if self.remaining < 0:
                raise ValueError("Too many media elements")
            kind, width = self.vint(start, identifier=True)
            size, length = self.vint(start + width)
            payload = start + width + length
            unknown = size == (1 << (length * 7)) - 1
            if unknown and kind not in {0x18538067, 0x1F43B675}:
                raise ValueError("Unknown metadata length")
            stop = end if unknown else payload + size
            if stop > end or stop < payload:
                raise ValueError("Invalid EBML bounds")
            yield kind, payload, stop
            start = stop


def inspect_mp4(reader):
    duration, video, media, movie = 0.0, 0, False, False

    def visit(start, end, depth=0):
        nonlocal duration, video, media, movie
        if depth > 8:
            raise ValueError("Nested media")
        for kind, left, right in reader.boxes(start, end):
            if kind == b"mdat":
                media = media or right > left
            elif kind == b"moov":
                movie = True
                visit(left, right, depth + 1)
            elif kind in {b"trak", b"mdia", b"minf", b"stbl", b"dinf"}:
                visit(left, right, depth + 1)
            elif kind == b"mvhd":
                version = reader.read(left, 1)[0]
                if version not in {0, 1}:
                    raise ValueError("Unsupported movie header")
                if right - left < (32 if version else 20):
                    raise ValueError("Truncated movie header")
                offset = left + (20 if version else 12)
                scale = int.from_bytes(reader.read(offset, 4), "big")
                ticks = int.from_bytes(reader.read(offset + 4, 8 if version else 4), "big")
                duration = ticks / scale if scale else 0
            elif kind == b"stsd":
                count = int.from_bytes(reader.read(left + 4, 4), "big")
                entries = list(reader.boxes(left + 8, right))
                if count != len(entries) or count > 16:
                    raise ValueError("Invalid sample description")
                for codec, begin, stop in entries:
                    if codec in {b"avc1", b"avc3"}:
                        width, height = struct.unpack(">HH", reader.read(begin + 24, 4))
                        if not 0 < width <= 8192 or not 0 < height <= 8192:
                            raise ValueError("Invalid video dimensions")
                        config = [
                            reader.read(a, min(b - a, 8))
                            for tag, a, b in reader.boxes(begin + 78, stop)
                            if tag == b"avcC"
                        ]
                        if len(config) != 1 or len(config[0]) < 7 or config[0][0] != 1:
                            raise ValueError("Invalid H.264 configuration")
                        video += 1
                    elif codec != b"mp4a":
                        raise ValueError("Use H.264 video and AAC audio")
            elif kind == b"dref":
                for tag, begin, stop in reader.boxes(left + 8, right):
                    if tag != b"url " or stop - begin != 4 or reader.read(begin, 4) != b"\0\0\0\1":
                        raise ValueError("External media references are forbidden")

    visit(0, reader.size)
    if not movie or not media or video != 1 or not math.isfinite(duration) or duration <= 0:
        raise ValueError("Incomplete MP4/MOV")
    return "mp4"


def inspect_webm(reader):
    duration, scale, videos, media, document = 0, 1000000, 0, False, False
    last_tick = 0
    for kind, start, end in reader.elements(0, reader.size):
        if kind == 0x1A45DFA3:
            document = any(
                tag == 0x4282 and reader.read(a, b - a) == b"webm"
                for tag, a, b in reader.elements(start, end)
            )
        elif kind == 0x18538067:
            for tag, left, right in reader.elements(start, end):
                if tag == 0x1549A966:
                    for field, a, b in reader.elements(left, right):
                        if field == 0x2AD7B1:
                            scale = int.from_bytes(reader.read(a, b - a), "big")
                        elif field == 0x4489:
                            if b - a not in {4, 8}:
                                raise ValueError("Invalid WebM duration")
                            duration = struct.unpack(
                                ">f" if b - a == 4 else ">d", reader.read(a, b - a)
                            )[0]
                elif tag == 0x1654AE6B:
                    for entry, a, b in reader.elements(left, right):
                        if entry != 0xAE:
                            continue
                        fields = {
                            field: reader.read(c, d - c)
                            for field, c, d in reader.elements(a, b)
                            if field in {0x83, 0x86}
                        }
                        track = int.from_bytes(fields.get(0x83, b""), "big")
                        codec = fields.get(0x86)
                        if track == 1 and codec in {b"V_VP8", b"V_VP9", b"V_AV1"}:
                            videos += 1
                        elif track != 2 or codec not in {b"A_OPUS", b"A_VORBIS"}:
                            raise ValueError("Unsupported WebM codec")
                elif tag == 0x1F43B675:
                    timestamp = 0
                    for field, a, b in reader.elements(left, right):
                        if field == 0xE7:
                            timestamp = int.from_bytes(reader.read(a, b - a), "big")
                        elif field in {0xA3, 0xA0}:
                            blocks = reader.elements(a, b) if field == 0xA0 else [(field, a, b)]
                            for block, start, stop in blocks:
                                if block not in {0xA3, 0xA1}:
                                    continue
                                _, width = reader.vint(start)
                                if start + width + 3 >= stop:
                                    raise ValueError("Truncated WebM block")
                                relative = int.from_bytes(
                                    reader.read(start + width, 2), "big", signed=True
                                )
                                last_tick = max(last_tick, timestamp + relative + 1)
                                media = True
    if (
        not document
        or not media
        or videos != 1
        or not math.isfinite(duration)
        or scale <= 0
        or max(duration, last_tick) <= 0
    ):
        raise ValueError("Incomplete WebM")
    return "webm"


def inspect_video(upload):
    reader = MediaReader(upload, upload.size)
    header = reader.read(0, min(12, upload.size))
    if header.startswith(b"\x1a\x45\xdf\xa3"):
        return inspect_webm(reader)
    if len(header) >= 12 and header[4:8] == b"ftyp":
        return inspect_mp4(reader)
    raise ValueError("Unsupported container")
