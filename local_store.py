"""
Local "fake S3" data layer — drop-in replacement for s3_store.py for development
BEFORE the real bucket exists.

Same functions, same shapes as s3_store.py, but reads/writes JSON files in a local
folder instead of S3:
   ./local_data/submissions/raw/{id}.json          -> exactly what the user typed
   ./local_data/submissions/normalized/{id}.json   -> cleaned, prompt-ready 10 fields

When the real bucket is ready, change ONE import line in main.py
(`import local_store as store`  ->  `import s3_store as store`) and nothing else changes.

Exposes:
  save_submission(raw)    -> {id, raw, normalized}
  get_company_raw(id)     -> normalized record (what the prompt needs)
  get_raw_submission(id)  -> untouched raw record
  list_companies()        -> [id, ...]
  normalize_company(raw)  -> the field mapping
"""
import os
import json
import uuid
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Where files live on disk. Override with LOCAL_DATA_DIR in .env if you like.
BASE_DIR = Path(os.getenv("LOCAL_DATA_DIR", "local_data")) / "submissions"
RAW_DIR = BASE_DIR / "raw"
NORM_DIR = BASE_DIR / "normalized"
RAW_DIR.mkdir(parents=True, exist_ok=True)
NORM_DIR.mkdir(parents=True, exist_ok=True)


class NotFound(Exception):
    """Raised when no submission matches the given id."""


# ----------------------------------------------------------------------
# Map YOUR form's field names (the lists) onto the prompt's fields (the keys).
# First non-empty match wins, case-insensitively. Tuned to the real schema:
#   columns: id, name, description, industry, website, email, phone, raw, ...
# ----------------------------------------------------------------------
FIELD_MAP = {
    "name":          ["name", "company_name", "businessName", "business_name"],
    "industry":      ["industry", "sector", "category"],
    "tagline":       ["tagline", "slogan"],
    "description":   ["description", "about", "what_you_do", "summary", "overview"],
    "services":      ["services", "offerings", "products", "service_list"],
    "audience":      ["audience", "target_audience", "customers", "target"],
    "tone":          ["tone", "brand_tone", "voice", "style"],
    "location":      ["location", "city", "address"],
    "website":       ["website", "url", "site"],
    "contact_email": ["email", "contact_email", "contactEmail"],
    "contact_phone": ["phone", "contact_phone", "phone_number", "contactPhone"],
    # user design preferences from the frontend form
    "colorway":        ["colorway", "color_way", "colors", "brand_colors", "color_preference", "colour", "color"],
    "animation_level": ["animation_level", "animations", "motion_level", "animation"],
}


def _flatten(raw: dict) -> dict:
    """
    Merge a nested submission into one flat dict.

    Rows can carry a `raw` column that is itself the submission, either as a JSON
    string or an already-parsed dict. We parse it and merge it UNDER the top-level
    columns (top-level wins on conflicts, since those are the curated values).
    """
    if not isinstance(raw, dict):
        return {}
    inner = raw.get("raw")
    if isinstance(inner, str):
        try:
            inner = json.loads(inner)
        except (json.JSONDecodeError, TypeError):
            inner = None
    merged = {}
    if isinstance(inner, dict):
        merged.update(inner)
    merged.update({k: v for k, v in raw.items() if k != "raw"})
    return merged


def _first(raw: dict, candidates: list, default=""):
    lower = {k.lower(): v for k, v in raw.items() if isinstance(k, str)}
    for c in candidates:
        v = lower.get(c.lower())
        if v not in (None, "", [], {}):
            return v
    return default


def normalize_company(raw: dict) -> dict:
    """Turn a raw submission into the exact fields the prompt template expects."""
    flat = _flatten(raw)
    services = _first(flat, FIELD_MAP["services"], default=[])
    if isinstance(services, list):
        services = "; ".join(str(s).strip() for s in services if str(s).strip())

    return {
        "name":          str(_first(flat, FIELD_MAP["name"], "this company")).strip(),
        "industry":      str(_first(flat, FIELD_MAP["industry"], "—")).strip(),
        "tagline":       str(_first(flat, FIELD_MAP["tagline"], "")).strip(),
        "description":   str(_first(flat, FIELD_MAP["description"], "")).strip(),
        "services":      str(services or "—").strip(),
        "audience":      str(_first(flat, FIELD_MAP["audience"], "general customers")).strip(),
        "tone":          str(_first(flat, FIELD_MAP["tone"], "professional and trustworthy")).strip(),
        "location":      str(_first(flat, FIELD_MAP["location"], "")).strip(),
        "website":       str(_first(flat, FIELD_MAP["website"], "")).strip(),
        "contact_email": str(_first(flat, FIELD_MAP["contact_email"], "")).strip(),
        "contact_phone": str(_first(flat, FIELD_MAP["contact_phone"], "")).strip(),
        "colorway":        str(_first(flat, FIELD_MAP["colorway"], "")).strip(),
        "animation_level": str(_first(flat, FIELD_MAP["animation_level"], "")).strip(),
    }


def _write(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def _read(path: Path) -> dict:
    if not path.exists():
        raise NotFound(str(path))
    return json.loads(path.read_text(encoding="utf-8"))


# ---------- WRITE ----------

def save_submission(raw: dict, company_id: str | None = None) -> dict:
    """Store both versions on disk and return {id, raw, normalized}."""
    company_id = company_id or uuid.uuid4().hex
    normalized = normalize_company(raw)

    _write(RAW_DIR / f"{company_id}.json", {"id": company_id, "data": raw})
    _write(NORM_DIR / f"{company_id}.json", {"id": company_id, **normalized})

    return {"id": company_id, "raw": raw, "normalized": normalized}


# ---------- READ ----------

def get_company_raw(company_id: str) -> dict:
    """Read the NORMALIZED record (what the prompt needs). Name kept for API compatibility."""
    return _read(NORM_DIR / f"{company_id}.json")


def get_raw_submission(company_id: str) -> dict:
    """Read the untouched raw record."""
    return _read(RAW_DIR / f"{company_id}.json")


def list_companies() -> list:
    """Return the ids of all stored (normalized) submissions."""
    return sorted(p.stem for p in NORM_DIR.glob("*.json"))
