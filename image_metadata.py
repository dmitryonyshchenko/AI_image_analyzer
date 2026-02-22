"""
Image metadata extraction using standard Python libraries only (no AI).

Reads EXIF data (GPS coordinates, capture date) from image files via Pillow.
Reverse geocoding is done via OpenStreetMap Nominatim (free, no API key required).
"""
import json
import urllib.request
import urllib.error

from PIL import Image

# EXIF tag IDs
_TAG_DATETIME_ORIGINAL = 36867   # DateTimeOriginal
_TAG_DATETIME          = 306     # DateTime (fallback)
_TAG_GPS_INFO          = 34853   # GPSInfo IFD pointer

# GPS sub-tags inside the GPSInfo IFD
_GPS_LAT_REF = 1
_GPS_LAT     = 2
_GPS_LON_REF = 3
_GPS_LON     = 4


def _rational_to_float(value) -> float:
    """Convert a Pillow IFDRational or (numerator, denominator) tuple to float."""
    if hasattr(value, "numerator") and hasattr(value, "denominator"):
        return value.numerator / value.denominator if value.denominator else 0.0
    if isinstance(value, tuple) and len(value) == 2:
        return value[0] / value[1] if value[1] else 0.0
    return float(value)


def _dms_to_decimal(dms, ref: str) -> float | None:
    """Convert DMS (degrees / minutes / seconds) tuple + hemisphere ref to decimal degrees."""
    try:
        degrees = _rational_to_float(dms[0])
        minutes = _rational_to_float(dms[1])
        seconds = _rational_to_float(dms[2])
        decimal = degrees + minutes / 60.0 + seconds / 3600.0
        if ref in ("S", "W"):
            decimal = -decimal
        return decimal
    except Exception:
        return None


def _reverse_geocode(lat: float, lon: float) -> str:
    """
    Call OpenStreetMap Nominatim reverse geocoding.
    Returns a human-readable address string, or empty string on failure.
    Usage policy: User-Agent header is required.
    """
    url = (
        f"https://nominatim.openstreetmap.org/reverse"
        f"?format=jsonv2&lat={lat:.6f}&lon={lon:.6f}"
    )
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "AI-Image-Analyzer/1.0 (demo project, non-commercial)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data.get("display_name", "")
    except Exception:
        return ""


def extract_metadata(image_path: str) -> dict:
    """
    Extract GPS coordinates and capture date/time from an image's EXIF data.

    Performs reverse geocoding if GPS data is found.

    Returns a dict with zero or more of the following keys:
        datetime  — capture date/time string (from EXIF)
        gps_lat   — latitude float
        gps_lon   — longitude float
        location  — human-readable address from reverse geocoding
    """
    result: dict = {}
    try:
        image = Image.open(image_path)
        exif = image.getexif()
        if not exif:
            return result

        # ── Capture date/time ────────────────────────────────────────────────
        dt = exif.get(_TAG_DATETIME_ORIGINAL) or exif.get(_TAG_DATETIME)
        if dt:
            result["datetime"] = str(dt)

        # ── GPS coordinates ───────────────────────────────────────────────────
        gps_ifd = exif.get_ifd(_TAG_GPS_INFO)
        if gps_ifd:
            lat_ref = gps_ifd.get(_GPS_LAT_REF)
            lat_dms = gps_ifd.get(_GPS_LAT)
            lon_ref = gps_ifd.get(_GPS_LON_REF)
            lon_dms = gps_ifd.get(_GPS_LON)

            if lat_dms and lon_dms and lat_ref and lon_ref:
                lat = _dms_to_decimal(lat_dms, lat_ref)
                lon = _dms_to_decimal(lon_dms, lon_ref)
                if lat is not None and lon is not None:
                    result["gps_lat"] = round(lat, 6)
                    result["gps_lon"] = round(lon, 6)
                    location = _reverse_geocode(lat, lon)
                    if location:
                        result["location"] = location

    except Exception:
        pass  # Return whatever was collected; don't crash on bad EXIF

    return result
