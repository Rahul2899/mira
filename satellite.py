import os
import numpy as np

ASSET = "GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL"
YEAR = 2024
EE_PROJECT = os.environ.get("EE_PROJECT", "invertix-asa")
HUB_LAT, HUB_LON = 50.11, 8.68  # Frankfurt: reference dense data-center / grid hub
_ee = None
_ready = False
_hub_vec = None


def _init():
    global _ee, _ready
    if _ready:
        return _ee is not None
    _ready = True
    try:
        import ee
        ee.Initialize(project=EE_PROJECT)
        _ee = ee
    except Exception:
        _ee = None
    return _ee is not None


def available():
    return _init()


_init()  # warm the EE state once at import so the first request is not slowed


def infra_score(lat, lon):
    """Mean AlphaEarth embedding magnitude over a small patch around the region centroid,
    used as a proxy for built/grid-infrastructure density. Returns 0-100 or None if EE unavailable."""
    if not _init():
        return None
    try:
        pt = _ee.Geometry.Point([lon, lat])
        img = _ee.ImageCollection(ASSET).filterDate(f"{YEAR}-01-01", f"{YEAR + 1}-01-01").filterBounds(pt).mosaic()
        vals = img.reduceRegion(_ee.Reducer.mean(), pt.buffer(5000), scale=100, bestEffort=True, maxPixels=1e9).getInfo()
        v = np.array([x for x in vals.values() if x is not None])
        if not len(v):
            return None
        magnitude = float(np.sqrt((v ** 2).sum()))
        return round(min(100.0, magnitude / 1.6 * 100), 1)
    except Exception:
        return None
