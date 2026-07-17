from typing import Optional
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
    "industry":      ["industry", "sector", "category", "business_category"],
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
    # screen 3 (business form / PDF extraction)
    "unique_selling_point": ["unique_selling_point", "usp", "what_makes_you_unique", "unique", "differentiator"],
    "cta_text":        ["cta_text", "cta", "main_cta", "main_call_to_action", "call_to_action"],
    "extra_context":   ["extra_context", "anything_else", "additional_context", "notes"],
    # screen 4 (design category & mood)
    "design_mood":     ["design_mood", "mood"],
    "theme_mode":      ["theme_mode", "theme"],
    # screen 5 (fonts)
    "font_pairing":    ["font_pairing", "fonts", "font_pair", "typography"],
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


def _clean_pages(pages):
    """Validate the user's page/section selection into [{name, sections[]}] or []."""
    out = []
    if isinstance(pages, list):
        for p in pages:
            if not isinstance(p, dict):
                continue
            name = str(p.get("name", "")).strip()
            if not name:
                continue
            sections = [str(s).strip() for s in (p.get("sections") or []) if str(s).strip()]
            out.append({"name": name, "sections": sections})
    return out


# frontend animation slider values -> pipeline levels
_ANIMATION_MAP = {
    "minimal": "minimal", "none": "minimal",
    "low": "low", "light": "low",
    "balanced": "moderate", "moderate": "moderate", "medium": "moderate", "recommended": "moderate",
    "high": "lively", "lively": "lively", "dynamic": "lively",
}


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
        "animation_level": _ANIMATION_MAP.get(
            str(_first(flat, FIELD_MAP["animation_level"], "")).strip().lower(),
            str(_first(flat, FIELD_MAP["animation_level"], "")).strip().lower(),
        ),
        "unique_selling_point": str(_first(flat, FIELD_MAP["unique_selling_point"], "")).strip(),
        "cta_text":        str(_first(flat, FIELD_MAP["cta_text"], "")).strip(),
        "extra_context":   str(_first(flat, FIELD_MAP["extra_context"], "")).strip(),
        "design_mood":     str(_first(flat, FIELD_MAP["design_mood"], "")).strip(),
        "theme_mode":      str(_first(flat, FIELD_MAP["theme_mode"], "")).strip().lower(),
        "font_pairing":    str(_first(flat, FIELD_MAP["font_pairing"], "")).strip(),
        "pages":           _clean_pages(flat.get("pages")),
    }


def _write(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def _read(path: Path) -> dict:
    if not path.exists():
        raise NotFound(str(path))
    return json.loads(path.read_text(encoding="utf-8"))


# ---------- WRITE ----------

def save_submission(raw: dict, company_id: Optional[str] = None) -> dict:
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


# ---------- PREVIEWS (screen 7) ----------

PREV_DIR = BASE_DIR / "previews"
BUILDS_DIR = BASE_DIR / "builds"
DOCS_DIR = BASE_DIR / "documents"
PREV_DIR.mkdir(parents=True, exist_ok=True)
BUILDS_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR.mkdir(parents=True, exist_ok=True)


def save_previews(company_id: str, data: dict) -> None:
    """Persist the 3 preview versions (briefs + chat ids) for a company."""
    _write(PREV_DIR / f"{company_id}.json", {"id": company_id, **data})


def get_previews(company_id: str) -> dict:
    """Load the stored previews for a company. Raises NotFound if none exist."""
    return _read(PREV_DIR / f"{company_id}.json")


# ---------- BUILD META (readiness grace tracking) ----------

def get_build_meta(chat_id: str) -> dict:
    """Small per-build metadata record ({} if none yet)."""
    try:
        return _read(BUILDS_DIR / f"{chat_id}.json")
    except NotFound:
        return {}


def set_build_meta(chat_id: str, meta: dict) -> None:
    _write(BUILDS_DIR / f"{chat_id}.json", meta)


# ---------- CLIENT DOCUMENTS (brochure / portfolio PDFs) ----------

def save_document(company_id: str, kind: str, data: bytes) -> None:
    d = DOCS_DIR / company_id
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{kind}.pdf").write_bytes(data)


def get_document(company_id: str, kind: str) -> bytes:
    p = DOCS_DIR / company_id / f"{kind}.pdf"
    if not p.exists():
        raise NotFound(f"{kind} for {company_id}")
    return p.read_bytes()


def has_document(company_id: str, kind: str) -> bool:
    return (DOCS_DIR / company_id / f"{kind}.pdf").exists()
