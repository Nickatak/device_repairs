"""EXIF handling for uploaded repair media — taken_at extraction and the GPS strip.

Policy (Nick, 2026-07-24): strip GPS coordinates from stored files (bench photos
carry home coordinates, and repair photos may eventually travel on guest
share-links); keep device identity (make/model) and the datetime tags.
"""

import io
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import piexif
from PIL import ExifTags, Image

# EXIF datetimes are naive local time. Every photo in this system comes off the
# bench, so bench-local is the fallback when the camera wrote no UTC offset.
BENCH_TZ = ZoneInfo("America/Los_Angeles")


def extract_taken_at(data: bytes):
    """DateTimeOriginal (+ OffsetTimeOriginal when the camera wrote one) as aware UTC.

    None when the file carries no parseable EXIF timestamp.
    """
    try:
        exif = Image.open(io.BytesIO(data)).getexif().get_ifd(ExifTags.IFD.Exif)
    except Exception:
        return None
    raw = exif.get(ExifTags.Base.DateTimeOriginal)
    if not raw:
        return None
    try:
        naive = datetime.strptime(str(raw).strip(), "%Y:%m:%d %H:%M:%S")
    except ValueError:
        return None
    offset = exif.get(ExifTags.Base.OffsetTimeOriginal)
    if offset:
        try:
            aware = datetime.strptime(
                f"{str(raw).strip()} {str(offset).strip()}", "%Y:%m:%d %H:%M:%S %z"
            )
            return aware.astimezone(timezone.utc)
        except ValueError:
            pass
    return naive.replace(tzinfo=BENCH_TZ).astimezone(timezone.utc)


def strip_gps(data: bytes) -> bytes:
    """Drop the GPS IFD from a JPEG's EXIF, losslessly (segment swap, no re-encode).

    Files piexif can't parse (PNG etc.) pass through unchanged — they don't carry
    an EXIF GPS IFD in the form phones write.
    """
    try:
        exif_dict = piexif.load(data)
    except Exception:
        return data
    if not exif_dict.get("GPS"):
        return data
    exif_dict["GPS"] = {}
    # piexif chokes re-dumping some maker-specific Interop/thumbnail quirks; a
    # failed strip must fail the upload rather than silently store coordinates.
    out = io.BytesIO()
    piexif.insert(piexif.dump(exif_dict), data, out)
    return out.getvalue()
