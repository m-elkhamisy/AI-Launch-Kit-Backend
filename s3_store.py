from typing import Optional
"""
S3 data layer: write and read business submissions.

A submission is stored as TWO objects per company under a shared id:
   submissions/raw/{id}.json          -> exactly what the user typed (audit trail)
   submissions/normalized/{id}.json   -> cleaned, prompt-ready 10-field version

Exposes:
  save_submission(raw)        -> dict   (writes raw + normalized, returns {id, raw, normalized})
  get_company_raw(id)         -> dict   (reads normalized — what the prompt needs)
  get_raw_submission(id)      -> dict   (reads the untouched raw version)
  list_companies()            -> list   (ids that have a normalized record)
  normalize_company(raw)      -> dict   (the field mapping; also used at write time)
"""
import os
import io
import json
import uuid
import boto3
from dotenv import load_dotenv

load_dotenv()

AWS_REGION = os.getenv("AWS_REGION", "me-central-1")     # me-central-1 = UAE
S3_BUCKET = os.getenv("S3_BUCKET")
S3_PREFIX = os.getenv("S3_PREFIX", "submissions/")        # base folder inside the bucket

RAW_PREFIX = f"{S3_PREFIX}raw/"
NORM_PREFIX = f"{S3_PREFIX}normalized/"
BUILDS_PREFIX = f"{S3_PREFIX}builds/"
DOCS_PREFIX = f"{S3_PREFIX}documents/"

# boto3 reads credentials from the environment (AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY)
# or, on AWS, from the instance IAM role. Client creation is lazy.
_s3 = boto3.client("s3", region_name=AWS_REGION)


class NotFound(Exception):
    """Raised when no submission matches the given id."""


# ----------------------------------------------------------------------
# Map YOUR form's field names (the lists) onto the prompt's fields (the keys).
# First non-empty match wins, case-insensitively. Edit to match your form.
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
    """Merge a nested submission (a `raw` column holding a JSON string or dict) into one flat dict."""
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


def _put_json(key: str, obj: dict) -> None:
    _s3.put_object(
        Bucket=S3_BUCKET,
        Key=key,
        Body=json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8"),
        ContentType="application/json",
    )


def _get_json(key: str) -> dict:
    from botocore.exceptions import ClientError
    try:
        obj = _s3.get_object(Bucket=S3_BUCKET, Key=key)
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") in ("NoSuchKey", "404"):
            raise NotFound(key)
        raise
    return json.loads(obj["Body"].read())


# ---------- WRITE ----------

def save_submission(raw: dict, company_id: Optional[str] = None) -> dict:
    """
    Store both versions of a submission in S3 and return {id, raw, normalized}.
    A new uuid id is generated unless one is supplied.
    """
    company_id = company_id or uuid.uuid4().hex
    normalized = normalize_company(raw)

    # keep a tiny bit of provenance alongside each stored object
    raw_record = {"id": company_id, "data": raw}
    norm_record = {"id": company_id, **normalized}

    _put_json(f"{RAW_PREFIX}{company_id}.json", raw_record)
    _put_json(f"{NORM_PREFIX}{company_id}.json", norm_record)

    return {"id": company_id, "raw": raw, "normalized": normalized}


# ---------- READ ----------

def get_company_raw(company_id: str) -> dict:
    """Read the NORMALIZED record (what the prompt needs). Name kept for API compatibility."""
    return _get_json(f"{NORM_PREFIX}{company_id}.json")


def get_raw_submission(company_id: str) -> dict:
    """Read the untouched raw record."""
    return _get_json(f"{RAW_PREFIX}{company_id}.json")


def list_companies() -> list:
    """Return the ids of all stored (normalized) submissions."""
    ids = []
    paginator = _s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=NORM_PREFIX):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if key.endswith(".json"):
                ids.append(key[len(NORM_PREFIX):-len(".json")])
    return sorted(ids)


# ---------- PREVIEWS (screen 7) ----------

PREV_PREFIX = f"{S3_PREFIX}previews/"


def save_previews(company_id: str, data: dict) -> None:
    """Persist the 3 preview versions (briefs + chat ids) for a company."""
    _put_json(f"{PREV_PREFIX}{company_id}.json", {"id": company_id, **data})


def get_previews(company_id: str) -> dict:
    """Load the stored previews for a company. Raises NotFound if none exist."""
    return _get_json(f"{PREV_PREFIX}{company_id}.json")


# ---------- BUILD META (readiness grace tracking) ----------

def get_build_meta(chat_id: str) -> dict:
    try:
        return _get_json(f"{BUILDS_PREFIX}{chat_id}.json")
    except NotFound:
        return {}


def set_build_meta(chat_id: str, meta: dict) -> None:
    _put_json(f"{BUILDS_PREFIX}{chat_id}.json", meta)


# ---------- CLIENT DOCUMENTS (brochure / portfolio PDFs) ----------

def save_document(company_id: str, kind: str, data: bytes) -> None:
    _s3().put_object(Bucket=S3_BUCKET, Key=f"{DOCS_PREFIX}{company_id}/{kind}.pdf",
                     Body=data, ContentType="application/pdf")


def get_document(company_id: str, kind: str) -> bytes:
    try:
        r = _s3().get_object(Bucket=S3_BUCKET, Key=f"{DOCS_PREFIX}{company_id}/{kind}.pdf")
        return r["Body"].read()
    except Exception:
        raise NotFound(f"{kind} for {company_id}")


def has_document(company_id: str, kind: str) -> bool:
    try:
        _s3().head_object(Bucket=S3_BUCKET, Key=f"{DOCS_PREFIX}{company_id}/{kind}.pdf")
        return True
    except Exception:
        return False
