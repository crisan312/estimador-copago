import json
import pathlib

_HOSPITALS_PATH = pathlib.Path(__file__).parent.parent / "data" / "hospitales_red.json"
_cache: list[dict] = []


def _load() -> list[dict]:
    global _cache
    if not _cache:
        _cache = json.loads(_HOSPITALS_PATH.read_text(encoding="utf-8"))
    return _cache


def get_hospitals(city: str | None = None, specialty: str | None = None) -> list[dict]:
    hospitals = _load()
    if city:
        hospitals = [h for h in hospitals if h.get("ciudad", "").lower() == city.lower()]
    if specialty:
        hospitals = [
            h for h in hospitals
            if specialty.lower() in [s.lower() for s in h.get("especialidades", [])]
        ]
    return hospitals


def get_all() -> list[dict]:
    return _load()
