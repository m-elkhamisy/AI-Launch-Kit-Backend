"""
FastAPI service.

WRITE path (new):
  POST /submit  ->  Claude guardrail  ->  (pass) store raw + normalized in S3  ->  start v0 build

READ path:
  GET  /companies            list stored submission ids
  GET  /companies/{id}        normalized record (+ raw)
  POST /companies/{id}/brief  re-generate the brief for a stored company (no v0 credit)
  POST /companies/{id}/generate   re-run the v0 build for a stored company
  GET  /builds/{chatId}       poll a v0 build

Run it:
    python -m uvicorn main:app --reload --port 8000
    docs: http://localhost:8000/docs
"""
import io
import time

from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, RedirectResponse
from pydantic import BaseModel
from typing import Any, Dict

import local_store as store      # DEV: filesystem store. Switch to `s3_store` when the bucket exists.
import pipeline
import vercel_deploy
import documents

app = FastAPI(title="Innovation City — License-to-Launch API")

# CORS — in dev, allow any localhost port (Vite hops ports when 5173 is busy).
# In production, set FRONTEND_ORIGINS in .env to the real domain(s), comma-separated.
import os as _os
_env_origins = [o.strip() for o in _os.getenv("FRONTEND_ORIGINS", "").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_env_origins,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Submission(BaseModel):
    """Raw form data from the frontend. Free-form so it works with any form schema."""
    data: Dict[str, Any]
    build: bool = True          # validate + store + build by default


def _fetch_normalized(company_id: str) -> dict:
    try:
        return store.get_company_raw(company_id)      # returns the normalized record
    except store.NotFound:
        raise HTTPException(404, f"No submission found for '{company_id}'")
    except Exception as e:
        raise HTTPException(502, f"Storage error: {e}")


@app.get("/")
def root():
    return {
        "ok": True,
        "endpoints": [
            "POST /extract                   (upload a PDF -> extracted business fields)",
            "POST /submit                    (guardrail -> store raw+normalized [-> build])",
            "POST /companies/{id}/previews  (generate 3 homepage preview versions)",
            "POST /companies/{id}/select-version  (build the full site from the chosen preview)",
            "GET  /companies",
            "GET  /companies/{id}",
            "POST /companies/{id}/brief      (Claude only — no v0 credit spent)",
            "POST /companies/{id}/generate   (re-run the v0 build)",
            "GET  /builds/{chatId}           (poll until status == completed)",
            "GET  /builds/{chatId}/download  (download the generated site as a zip)",
            "GET  /builds/{chatId}/handoff   (get the claimable v0 link for the site)",
            "GET  /builds/{chatId}/claim     (redirect the user to claim the site on v0)",
            "POST /builds/{chatId}/claim-deploy  (deploy under platform account + return a 24h claim URL)",
        ],
    }


@app.post("/submit")
def submit(submission: Submission):
    """
    The main frontend entry point.
      1. Claude guardrail reviews the raw submission.
      2. If rejected -> 422 with the reason, nothing is stored.
      3. If accepted -> write raw + normalized to S3.
      4. If build=true -> start the v0 build and return chatId + live webUrl.
    """
    raw = submission.data

    # 1) guardrail
    try:
        verdict = pipeline.review_submission(raw)
    except pipeline.PipelineError as e:
        raise HTTPException(502, str(e))

    if verdict["decision"] == "reject":
        raise HTTPException(
            status_code=422,
            detail={"rejected": True,
                    "reason": verdict.get("reason", "Submission could not be accepted."),
                    "categories": verdict.get("categories", [])},
        )

    # 2) store raw + normalized
    try:
        stored = store.save_submission(raw)
    except Exception as e:
        raise HTTPException(502, f"Storage error: {e}")

    result = {
        "id": stored["id"],
        "accepted": True,
        "reason": verdict.get("reason", ""),
        "normalized": stored["normalized"],
        "status": "stored",
    }

    if not submission.build:
        return result

    # 3) generate the brief + start the v0 build
    try:
        brief = pipeline.write_brief(stored["normalized"])
        chat = pipeline.start_build(brief)
    except pipeline.BriefFlagged as e:
        # the prompt-writer flagged the stored data as a suspected injection
        result["status"] = "stored_flagged"
        result["flagged_reason"] = str(e)
        return result
    except pipeline.PipelineError as e:
        # stored successfully; only the build failed — tell the caller both facts
        result["status"] = "stored_build_failed"
        result["build_error"] = str(e)
        return result

    chat_id = chat.get("id")
    version = chat.get("latestVersion") or {}
    result.update({
        "status": version.get("status") or "pending",
        "chatId": chat_id,
        "webUrl": chat.get("webUrl"),
        "demoUrl": version.get("demoUrl"),          # live preview of the finished site
        "claimUrl": chat.get("webUrl"),             # where the user claims/forks it on v0 (unlisted)
        "downloadPath": f"/builds/{chat_id}/download",
        "handoffPath": f"/builds/{chat_id}/handoff",
        "files": [f.get("name") for f in (version.get("files") or [])],
        "brief": brief,
        "poll": f"/builds/{chat_id}",               # still available to re-check later
    })
    return result


@app.get("/companies")
def list_companies():
    try:
        return {"companies": store.list_companies()}
    except Exception as e:
        raise HTTPException(502, f"Storage error: {e}")


@app.get("/companies/{company_id}")
def get_company(company_id: str):
    """Return the normalized record plus the original raw submission."""
    normalized = _fetch_normalized(company_id)
    try:
        raw = store.get_raw_submission(company_id)
    except store.NotFound:
        raw = None
    return {"id": company_id, "normalized": normalized, "raw": raw}


@app.post("/companies/{company_id}/brief")
def brief_only(company_id: str):
    """Re-generate the v0 brief for an already-stored company. No v0 credit spent."""
    company = _fetch_normalized(company_id)
    try:
        brief = pipeline.write_brief(company)
    except pipeline.BriefFlagged as e:
        raise HTTPException(422, {"flagged": True, "reason": str(e)})
    except pipeline.PipelineError as e:
        raise HTTPException(502, str(e))
    return {"company": company.get("name"), "brief": brief}


@app.post("/companies/{company_id}/generate")
def generate(company_id: str):
    """Re-run the full v0 build for an already-stored company."""
    company = _fetch_normalized(company_id)
    try:
        brief = pipeline.write_brief(company)
        chat = pipeline.start_build(brief)
    except pipeline.BriefFlagged as e:
        raise HTTPException(422, {"flagged": True, "reason": str(e)})
    except pipeline.PipelineError as e:
        raise HTTPException(502, str(e))

    chat_id = chat.get("id")
    version = chat.get("latestVersion") or {}
    return {
        "company": company.get("name"),
        "chatId": chat_id,
        "webUrl": chat.get("webUrl"),
        "demoUrl": version.get("demoUrl"),
        "files": [f.get("name") for f in (version.get("files") or [])],
        "status": version.get("status") or "pending",
        "brief": brief,
        "poll": f"/builds/{chat_id}",
    }


import time as _time

# After v0 first reports a build 'completed', hold it as pending for this many
# seconds — v0 can keep finalizing pages/demo deployment briefly after the flag.
BUILD_READY_GRACE_SECONDS = int(_os.getenv("BUILD_READY_GRACE_SECONDS", "45"))


def _gated_build_status(chat_id: str) -> dict:
    """pipeline.check_build + version-aware readiness gating.

    Two protections:
    * after /select-version we record the chat's pre-expansion versionId; while the
      latest version is still that old one, report pending ("expanding") so the UI
      never shows the homepage-only build as the finished site;
    * the first time a NEW version reports 'completed' we start a grace window and
      keep reporting pending until it passes (v0 finalizes briefly after the flag).
    """
    b = pipeline.check_build(chat_id)
    meta = store.get_build_meta(chat_id)
    vid = b.get("versionId")

    awaiting = meta.get("awaiting_after_version")
    if awaiting and vid == awaiting:
        return {**b, "status": "pending",
                "note": "expanding the chosen design into the full website"}

    if b.get("status") != "completed":
        return b

    now = _time.time()
    first = meta.get("first_completed_at")
    if meta.get("completed_version") != vid or not first:
        store.set_build_meta(chat_id, {"completed_version": vid, "first_completed_at": now})
        first = now
    if now - float(first) < BUILD_READY_GRACE_SECONDS:
        remaining = int(BUILD_READY_GRACE_SECONDS - (now - float(first)))
        return {**b, "status": "pending",
                "note": f"finalizing the site — ready in about {remaining}s"}
    return b


@app.get("/builds/{chat_id}")
def build_status(chat_id: str):
    try:
        return _gated_build_status(chat_id)
    except pipeline.PipelineError as e:
        raise HTTPException(502, str(e))


@app.get("/builds/{chat_id}/download")
def download_build(chat_id: str):
    """Download the generated website's full source code as a zip archive."""
    try:
        zip_bytes, filename = pipeline.download_zip(chat_id)
    except pipeline.PipelineError as e:
        raise HTTPException(502, str(e))
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/builds/{chat_id}/handoff")
def build_handoff(chat_id: str):
    """Return a claimable handoff link for the generated site.

    The frontend uses claimUrl to render a "Claim your website" button. The site is made
    unlisted (viewable by anyone with the link); when the user opens it and signs in to v0,
    they can fork/edit/deploy it into their own account.
    """
    try:
        return pipeline.handoff_link(chat_id)
    except pipeline.PipelineError as e:
        raise HTTPException(502, str(e))


@app.get("/builds/{chat_id}/claim")
def build_claim_redirect(chat_id: str):
    """Convenience endpoint: 302-redirect the user straight to their site's v0 page to claim it."""
    try:
        info = pipeline.handoff_link(chat_id)
    except pipeline.PipelineError as e:
        raise HTTPException(502, str(e))
    return RedirectResponse(url=info["claimUrl"])


@app.post("/builds/{chat_id}/claim-deploy")
def claim_deploy(chat_id: str):
    """Claim Deployments flow: deploy the site under the PLATFORM's Vercel account,
    then return a claim URL the business owner opens to transfer the whole project
    into THEIR OWN Vercel account (code valid 24h).

    POST because each call creates a fresh deployment + transfer code. The frontend
    shows the returned claimUrl as a "Claim your website" button/link.
    """
    try:
        return vercel_deploy.claimable_deploy(chat_id)
    except vercel_deploy.DeployError as e:
        raise HTTPException(502, str(e))


class VersionChoice(BaseModel):
    version: int          # 1, 2, or 3


@app.post("/extract")
async def extract_from_pdf(file: UploadFile = File(...)):
    """Screen 3 (upload path): extract business info from an uploaded PDF.

    Returns {"fields": {...}} matching the intake field names, for the frontend to
    pre-fill the form (the user reviews/edits before submitting). Extraction leaves
    unknown fields empty — it never invents facts.
    """
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(415, "Please upload a PDF file")
    raw = await file.read()
    if len(raw) > 15 * 1024 * 1024:
        raise HTTPException(413, "PDF too large (max 15 MB)")

    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(raw))
        text = "\n".join((page.extract_text() or "") for page in reader.pages).strip()
    except Exception as e:
        raise HTTPException(422, f"Could not read that PDF: {e}")

    if len(text) < 40:
        raise HTTPException(422, "No extractable text found — the PDF may be scanned images. "
                                 "Please fill the form manually.")

    try:
        fields = pipeline.extract_business_info(text)
    except pipeline.BriefFlagged as e:
        raise HTTPException(422, {"flagged": True, "reason": str(e)})
    except pipeline.PipelineError as e:
        raise HTTPException(502, str(e))
    return {"fields": fields}


def _preview_status_payload(company_id: str, record: dict) -> dict:
    """Contract shape for previews: check each chat's live status and assemble
    {id, status, versions:[{version, chatId, status, demoUrl, webUrl}]}."""
    versions = []
    for key in sorted(record.get("versions", {}), key=int):
        entry = record["versions"][key]
        chat_id = entry.get("chatId")
        try:
            b = _gated_build_status(chat_id)   # tolerates early 404s; grace-gated completion
            status, demo, web = b.get("status") or "pending", b.get("demoUrl"), b.get("webUrl")
        except pipeline.PipelineError:
            status, demo, web = "pending", None, None
        versions.append({
            "version": int(key),
            "chatId": chat_id,
            "status": status,
            "demoUrl": demo,
            "webUrl": web,
        })
    if versions and all(v["status"] != "pending" for v in versions):
        overall = "completed" if any(v["status"] == "completed" for v in versions) else "failed"
    else:
        overall = "pending"
    return {"id": company_id, "status": overall, "versions": versions}


@app.post("/companies/{company_id}/previews")
def generate_previews(company_id: str, request: Request, force: bool = False):
    """Screen 7 step 1: THREE Claude-designed hero MOCKUPS (single-file HTML) the
    client chooses between. No v0 credits are spent at this step — the mockups are
    generated by Claude and served by this backend (so the frontend can embed them).

    IDEMPOTENT: an existing mockup set is returned as-is; ?force=true regenerates.
    """
    base = str(request.base_url).rstrip("/")

    def payload(record):
        versions = []
        for key in sorted(record.get("versions", {}), key=int):
            entry = record["versions"][key]
            path = f"/companies/{company_id}/previews/{key}/html"
            versions.append({
                "version": int(key),
                "label": entry.get("label"),
                "chatId": None,
                "status": "completed" if entry.get("html") else "failed",
                "demoUrl": base + path,
                "webUrl": base + path,
            })
        return {"id": company_id, "status": "completed", "versions": versions}

    if not force:
        try:
            existing = store.get_previews(company_id)
            if (existing.get("versions") or {}) and any(
                    v.get("html") for v in existing["versions"].values()):
                return payload(existing)
        except store.NotFound:
            pass
        except Exception:
            pass

    company = store.normalize_company(_fetch_normalized(company_id))
    try:
        mockups = pipeline.generate_preview_mockups(company, n=3)
    except pipeline.BriefFlagged as e:
        raise HTTPException(422, {"flagged": True, "reason": str(e)})
    except pipeline.PipelineError as e:
        raise HTTPException(502, str(e))

    record = {"versions": {str(i + 1): {"label": m["label"], "html": m["html"]}
                           for i, m in enumerate(mockups)}}
    try:
        store.save_previews(company_id, record)
    except Exception as e:
        raise HTTPException(502, f"Storage error: {e}")
    return payload(record)


@app.get("/companies/{company_id}/previews")
def previews_status(company_id: str, request: Request):
    """Preview polling — mockups are generated synchronously, so an existing set
    is always 'completed'. Kept for frontend contract compatibility."""
    try:
        record = store.get_previews(company_id)
    except store.NotFound:
        raise HTTPException(404, f"No previews found for '{company_id}' — POST to create them")
    except Exception as e:
        raise HTTPException(502, f"Storage error: {e}")
    base = str(request.base_url).rstrip("/")
    versions = []
    for key in sorted(record.get("versions", {}), key=int):
        entry = record["versions"][key]
        path = f"/companies/{company_id}/previews/{key}/html"
        versions.append({
            "version": int(key), "label": entry.get("label"), "chatId": None,
            "status": "completed" if entry.get("html") else "failed",
            "demoUrl": base + path, "webUrl": base + path,
        })
    return {"id": company_id, "status": "completed", "versions": versions}


@app.get("/companies/{company_id}/previews/{version}/html")
def preview_html(company_id: str, version: int):
    """Serve one mockup as a real web page — embeddable in the frontend's iframes
    and openable in a new tab (unlike v0 demos, nothing blocks framing here)."""
    try:
        record = store.get_previews(company_id)
    except store.NotFound:
        raise HTTPException(404, "No previews for this company")
    except Exception as e:
        raise HTTPException(502, f"Storage error: {e}")
    entry = (record.get("versions") or {}).get(str(version)) or {}
    html = entry.get("html")
    if not html:
        raise HTTPException(404, f"No mockup stored for version {version}")
    return Response(content=html, media_type="text/html")


# ─── Client documents (brochure + portfolio PDFs) ────────────────────────────

DOC_KINDS = ("brochure", "portfolio")


@app.post("/companies/{company_id}/documents")
def generate_documents(company_id: str, force: bool = False):
    """Generate the two client-facing PDFs (brochure + portfolio) from the stored
    company data — shown to the client BEFORE the website is generated.

    IDEMPOTENT: if both documents already exist they are returned as-is; pass
    ?force=true to regenerate. Each document is one Claude call + a local render,
    so regeneration costs tokens but no v0 credits.
    """
    if not force and all(store.has_document(company_id, k) for k in DOC_KINDS):
        return {
            "id": company_id, "status": "ready", "regenerated": False,
            "documents": {k: f"/companies/{company_id}/documents/{k}" for k in DOC_KINDS},
        }

    company = store.normalize_company(_fetch_normalized(company_id))
    try:
        docs = documents.generate_documents(company)
    except documents.BriefFlagged as e:
        raise HTTPException(422, {"flagged": True, "reason": str(e)})
    except (documents.DocumentError, documents.PipelineError) as e:
        raise HTTPException(502, str(e))

    for kind, data in docs.items():
        try:
            store.save_document(company_id, kind, data)
        except Exception as e:
            raise HTTPException(502, f"Storage error: {e}")

    return {
        "id": company_id, "status": "ready", "regenerated": True,
        "documents": {k: f"/companies/{company_id}/documents/{k}" for k in DOC_KINDS},
    }


@app.get("/companies/{company_id}/documents")
def documents_status(company_id: str):
    """Which client documents exist for this company."""
    return {
        "id": company_id,
        "documents": {
            k: {"ready": store.has_document(company_id, k),
                "path": f"/companies/{company_id}/documents/{k}"}
            for k in DOC_KINDS
        },
    }


@app.get("/companies/{company_id}/documents/{kind}")
def get_document(company_id: str, kind: str):
    """Serve one PDF inline (viewable directly in the browser / an <embed>)."""
    if kind not in DOC_KINDS:
        raise HTTPException(404, f"Unknown document kind '{kind}' — use one of {list(DOC_KINDS)}")
    try:
        data = store.get_document(company_id, kind)
    except store.NotFound:
        raise HTTPException(404, f"No {kind} generated yet — POST /companies/{company_id}/documents first")
    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{kind}-{company_id}.pdf"'},
    )


@app.post("/companies/{company_id}/select-version")
def select_version(company_id: str, choice: VersionChoice):
    """Screen 7 step 2: the user picked a mockup — build the COMPLETE website on v0.

    The chosen mockup's HTML is embedded verbatim in the v0 prompt as the design
    spec ("match this exact look"), so the final site follows the approved design.
    This is the ONLY v0 build in the whole journey (one build per customer).
    """
    if choice.version not in (1, 2, 3):
        raise HTTPException(422, "version must be 1, 2, or 3")

    try:
        stored = store.get_previews(company_id)
    except store.NotFound:
        raise HTTPException(404, "No previews found for this company — call /previews first")
    except Exception as e:
        raise HTTPException(502, f"Storage error: {e}")

    chosen = (stored.get("versions") or {}).get(str(choice.version)) or {}
    mockup_html = chosen.get("html")
    if not mockup_html:
        raise HTTPException(404, f"No stored mockup for version {choice.version}")

    company = store.normalize_company(_fetch_normalized(company_id))
    try:
        prompt = pipeline.build_v0_site_prompt(company, mockup_html)
        chat = pipeline.create_chat(prompt, model_id=pipeline.V0_MODEL)
    except pipeline.PipelineError as e:
        raise HTTPException(502, str(e))

    chat_id = chat.get("id")
    # persist the final chatId on the preview record for traceability
    try:
        stored["finalChatId"] = chat_id
        stored["chosenVersion"] = choice.version
        store.save_previews(company_id, stored)
    except Exception:
        pass

    return {
        "companyId": company_id,
        "chosenVersion": choice.version,
        "status": "pending",
        "chatId": chat_id,
        "webUrl": chat.get("webUrl"),
        "demoUrl": None,
        "claimUrl": chat.get("webUrl"),
        "downloadPath": f"/builds/{chat_id}/download",
        "claimDeployPath": f"/builds/{chat_id}/claim-deploy",
        "poll": f"/builds/{chat_id}",
    }
