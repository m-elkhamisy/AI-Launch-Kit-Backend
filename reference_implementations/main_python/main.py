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
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response, RedirectResponse
from pydantic import BaseModel
from typing import Any, Dict

import local_store as store      # DEV: filesystem store. Switch to `s3_store` when the bucket exists.
import pipeline
import vercel_deploy

app = FastAPI(title="Innovation City — License-to-Launch API")


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
            "POST /submit                    (guardrail -> store raw+normalized -> build)",
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


@app.get("/builds/{chat_id}")
def build_status(chat_id: str):
    try:
        return pipeline.check_build(chat_id)
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
