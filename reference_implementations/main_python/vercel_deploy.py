"""
Vercel Claim Deployments: hand the generated website to the business owner as a
claimable link, with no OAuth and no integration setup.

Flow (docs: vercel.com/docs/deployments/claim-deployments):
  1. Pull the finished site's files from v0 (as a zip, converted to Vercel's
     inline-file format).
  2. Deploy them as a production project under the PLATFORM's own Vercel account
     (POST /v13/deployments) using our VERCEL_TOKEN.
  3. Create a project transfer request (POST /v9/projects/{id}/transfer-request),
     which returns a code valid for 24 hours.
  4. Hand the user the claim URL:
         https://vercel.com/claim-deployment?code=...&returnUrl=...
     They open it, sign in to Vercel, pick their team, click Transfer — and the
     whole project (deployment included) moves into THEIR account.

Notes:
  * Until claimed, the project lives under the platform account and counts against
    its billing/limits; stale unclaimed projects should be cleaned up periodically.
  * Each call creates a fresh deployment + transfer code — the frontend should call
    once and reuse the returned claimUrl, not re-call per page view.

Needs in .env:
  VERCEL_TOKEN      — the platform account's access token (vercel.com → Settings → Tokens)
  VERCEL_TEAM_ID    — optional; set if the token is scoped to a team
  CLAIM_RETURN_URL  — optional; where the claim page sends users if the link is
                      invalid/expired (defaults to localhost)
"""
import os
import io
import base64
import zipfile
from urllib.parse import urlencode

import requests
from pathlib import Path
from dotenv import load_dotenv

import pipeline

load_dotenv(Path(__file__).resolve().parent / ".env")

VERCEL_API = "https://api.vercel.com"

VERCEL_TOKEN = os.getenv("VERCEL_TOKEN")
VERCEL_TEAM_ID = os.getenv("VERCEL_TEAM_ID")
CLAIM_RETURN_URL = os.getenv("CLAIM_RETURN_URL", "http://localhost:8000/")


class DeployError(Exception):
    """Raised on any Vercel failure so the API can return a clean HTTP error."""


# ----------------------------------------------------------------------
# Files: pull the finished site from v0 and convert to Vercel's inline format
# ----------------------------------------------------------------------

_SKIP_NAMES = {".DS_Store"}
_SKIP_PREFIXES = ("__MACOSX/",)


def collect_site_files(chat_id: str) -> list:
    """Download the generated site zip from v0 and convert it to Vercel inline files.

    Text files are sent as plain data; binary files (images, fonts) as base64.
    """
    zip_bytes, _ = pipeline.download_zip(chat_id)   # raises PipelineError if not ready

    files = []
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            name = info.filename
            if name in _SKIP_NAMES or any(name.startswith(p) for p in _SKIP_PREFIXES):
                continue
            raw = zf.read(info)
            try:
                files.append({"file": name, "data": raw.decode("utf-8")})
            except UnicodeDecodeError:
                files.append({
                    "file": name,
                    "data": base64.b64encode(raw).decode("ascii"),
                    "encoding": "base64",
                })
    if not files:
        raise DeployError("The v0 archive contained no files to deploy")
    return files


def _project_name(chat_id: str) -> str:
    """A valid Vercel project name: lowercase letters, digits, hyphens."""
    slug = "".join(c if c.isalnum() else "-" for c in chat_id.lower()).strip("-")
    return f"ic-site-{slug}"[:90] or "ic-site"


def create_deployment(access_token: str, team_id, chat_id: str, files: list) -> dict:
    """Create a production deployment of the site under the given token's account/team."""
    params = {"skipAutoDetectionConfirmation": "1"}
    if team_id:
        params["teamId"] = team_id

    r = requests.post(
        f"{VERCEL_API}/v13/deployments",
        params=params,
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
        json={
            "name": _project_name(chat_id),
            "files": files,
            "target": "production",
            "projectSettings": {"framework": "nextjs"},
        },
        timeout=(10, 300),
    )
    if r.status_code not in (200, 201, 202):
        raise DeployError(f"Vercel deployment failed ({r.status_code}): {r.text[:300]}")
    return r.json()


# ----------------------------------------------------------------------
# Claim flow: transfer request + claim URL
# ----------------------------------------------------------------------

def create_transfer_code(project_id_or_name: str) -> str:
    """Create a 24h project transfer request for a project in OUR account; returns the code."""
    if not VERCEL_TOKEN:
        raise DeployError("VERCEL_TOKEN is not set — create a token at vercel.com → Settings → Tokens")

    params = {}
    if VERCEL_TEAM_ID:
        params["teamId"] = VERCEL_TEAM_ID

    r = requests.post(
        f"{VERCEL_API}/v9/projects/{project_id_or_name}/transfer-request",
        params=params,
        headers={"Authorization": f"Bearer {VERCEL_TOKEN}", "Content-Type": "application/json"},
        json={},
        timeout=(10, 60),
    )
    if r.status_code not in (200, 201):
        raise DeployError(f"Transfer request failed ({r.status_code}): {r.text[:300]}")
    code = r.json().get("code")
    if not code:
        raise DeployError("Vercel returned no transfer code")
    return code


def build_claim_url(code: str) -> str:
    return "https://vercel.com/claim-deployment?" + urlencode(
        {"code": code, "returnUrl": CLAIM_RETURN_URL}
    )


def claimable_deploy(chat_id: str) -> dict:
    """Full claim flow: deploy the site into OUR account, then mint a claim URL.

    The site runs (temporarily under our account/billing) the moment Vercel finishes
    building; ownership moves to the user the moment they claim it.
    """
    if not VERCEL_TOKEN:
        raise DeployError("VERCEL_TOKEN is not set — create a token at vercel.com → Settings → Tokens")

    try:
        files = collect_site_files(chat_id)
    except pipeline.PipelineError as e:
        raise DeployError(str(e))

    dep = create_deployment(VERCEL_TOKEN, VERCEL_TEAM_ID, chat_id, files)

    project = dep.get("projectId") or _project_name(chat_id)
    code = create_transfer_code(project)

    url = dep.get("url")
    return {
        "status": "ready_to_claim",
        "chatId": chat_id,
        "projectId": project,
        "deploymentId": dep.get("id"),
        "liveUrl": f"https://{url}" if url else None,
        "claimUrl": build_claim_url(code),
        "claimExpires": "24 hours",
        "note": "The site is building under the platform account now and goes live in 1-3 "
                "minutes. Share claimUrl with the business owner — opening it and clicking "
                "Transfer moves the whole project into THEIR Vercel account.",
    }
