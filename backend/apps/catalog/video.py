"""Local content inspection with optional auto-detected ffprobe; scoped range delivery."""

import json
import re
import shutil
import struct
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

from django.conf import settings
from django.core.files.storage import default_storage
from django.http import HttpResponse, StreamingHttpResponse
from rest_framework.exceptions import NotFound, ValidationError

from .video_metadata import inspect_video


def validate_video(upload):
    # ASVS 5.2.1/5.2.2: bounded content/codec inspection, independent of client MIME.
    limit = settings.PRODUCT_VIDEO_MAX_BYTES
    if not upload.size or upload.size > limit:
        raise ValidationError({"video": "Vídeo vazio ou acima do limite de envio."})
    try:
        extension = inspect_video(upload)
        suffix = Path(upload.name).suffix.lower()
        if suffix not in ({".mp4", ".mov"} if extension == "mp4" else {".webm"}):
            raise ValueError("Extension does not match the inspected container")
        binary = shutil.which(settings.FFPROBE_BINARY or "ffprobe")
        if binary:
            with TemporaryDirectory(prefix="tapserve-video-") as directory:
                path = Path(directory) / ("upload." + extension)
                size = 0
                upload.seek(0)
                with path.open("wb") as output:
                    for chunk in upload.chunks():
                        size += len(chunk)
                        if size > limit:
                            raise ValueError("Oversized video")
                        output.write(chunk)
                result = subprocess.run(  # noqa: S603 ? discovered executable, fixed arguments, no shell.
                    [
                        binary,
                        "-v",
                        "error",
                        "-max_alloc",
                        "16777216",
                        "-probesize",
                        "5242880",
                        "-analyzeduration",
                        "5000000",
                        "-protocol_whitelist",
                        "file,pipe",
                        "-format_whitelist",
                        "mov,matroska,webm",
                        "-enable_drefs",
                        "0",
                        "-show_entries",
                        "format=format_name,duration:stream=codec_type,codec_name",
                        "-of",
                        "json",
                        str(path),
                    ],
                    capture_output=True,
                    timeout=15,
                    check=False,
                )
            if result.returncode or len(result.stdout) > 131072:
                raise ValueError("Invalid probe response")
            data = json.loads(result.stdout)
            streams = data.get("streams", [])
            video = [stream for stream in streams if stream.get("codec_type") == "video"]
            if len(video) != 1 or video[0].get("codec_name") not in {"h264", "vp8", "vp9", "av1"}:
                raise ValueError("Incompatible video codec")
        return extension
    except (
        OSError,
        subprocess.TimeoutExpired,
        ValueError,
        TypeError,
        KeyError,
        OverflowError,
        struct.error,
    ) as error:
        raise ValidationError(
            {
                "video": "Vídeo inválido ou incompatível. Use MP4/MOV com H.264 e AAC, ou WebM com VP8/VP9/AV1 e Opus/Vorbis."
            }
        ) from error
    finally:
        upload.seek(0)


def video_response(request, product):
    if product is None or not product.video_key:
        raise NotFound()
    try:
        size = default_storage.size(product.video_key)
        file = default_storage.open(product.video_key, "rb")
    except FileNotFoundError as error:
        raise NotFound() from error
    start, end = 0, size - 1
    partial = request.headers.get("Range")
    if partial:
        match = re.fullmatch(r"bytes=([0-9]{0,20})-([0-9]{0,20})", partial)
        if match and any(match.groups()):
            left, right = match.groups()
            start = int(left) if left else max(0, size - int(right))
            end = min(int(right), size - 1) if left and right else size - 1
        else:
            start = size
        if start > end or start >= size:
            file.close()
            invalid_range = HttpResponse(status=416)
            invalid_range["Content-Range"] = f"bytes */{size}"
            return invalid_range

    def chunks():
        try:
            file.seek(start)
            remaining = end - start + 1
            while remaining > 0:
                chunk = file.read(min(65536, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk
        finally:
            file.close()

    extension = "webm" if product.video_key.endswith(".webm") else "mp4"
    response = StreamingHttpResponse(
        chunks(), status=206 if partial else 200, content_type=f"video/{extension}"
    )
    response["Accept-Ranges"] = "bytes"
    response["Content-Length"] = str(end - start + 1)
    response["Content-Disposition"] = f'inline; filename="product.{extension}"'
    if partial:
        response["Content-Range"] = f"bytes {start}-{end}/{size}"
    if request.method == "HEAD":
        file.close()
        return HttpResponse(status=response.status_code, headers=response.headers)
    return response
