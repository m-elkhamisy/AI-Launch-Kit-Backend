# Real-provider integration runbook

This runbook is the manual acceptance test for OpenRouter, v0, asset storage, and
Vercel. Automated tests use fakes and mock transports and never spend provider
credits.

## Prerequisites

- Docker Desktop running Linux containers, or Python 3.12 plus PostgreSQL 17.
- Public HTTPS URLs for the API's v0 and Vercel callbacks.
- A frontend build whose `VITE_API_BASE_URL` points to the API.
- OpenRouter, v0, and Vercel credentials with access to the configured models and
  deployment team.
- Optional AWS credentials or workload identity when validating S3 storage.

Never commit `.env`, webhook tokens, transfer codes, provider IDs, or downloaded
customer assets.

## Configure and start

1. Copy `.env.example` to `.env`.
2. Set `LAUNCHKIT_FRONTEND_ORIGINS` to the exact frontend origins.
3. Set `LAUNCHKIT_SITE_URL` to the public API origin.
4. Set `LAUNCHKIT_OPENROUTER_API_KEY` and confirm the configured generation,
   utility, and image models are available to the account.
5. Set `LAUNCHKIT_V0_API_KEY`, a new high-entropy
   `LAUNCHKIT_V0_WEBHOOK_TOKEN`, and the public HTTPS
   `LAUNCHKIT_V0_WEBHOOK_CALLBACK_URL` including that token.
6. Set `LAUNCHKIT_VERCEL_TOKEN`, the optional team ID, the account webhook
   secret, and `LAUNCHKIT_CLAIM_RETURN_URL` to a frontend route.
7. For S3, set the bucket, region, and asset prefix and provide credentials
   through the normal AWS environment or role chain. Leave the bucket empty to
   validate local durable asset storage instead.
8. Start the stack and inspect health:

```powershell
docker compose config
docker compose up --build -d
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health
docker compose ps
docker compose logs --tail 100 migrate api worker
```

Compose loads `.env` into migrations, the API, and the worker, while overriding
the database host with the internal PostgreSQL service name.

## Provision callbacks

Provision one environment-level v0 hook after the public API is reachable:

```powershell
docker compose exec api python -m launchkit.hooks provision-v0
```

Run the command again and confirm it is idempotent. Configure the Vercel account
or team webhook to send deployment lifecycle events to
`https://<api-origin>/api/v1/webhooks/vercel` using the same secret stored in
`LAUNCHKIT_VERCEL_WEBHOOK_SECRET`.

The v0 callback uses an unguessable path token because v0 does not document a
signed-delivery contract. Vercel callbacks use HMAC-SHA1 over the exact request
body in `x-vercel-signature`. Do not apply one provider's verification scheme to
the other.

## Exercise the product

1. Open the frontend and complete the questionnaire, category, mood, palette,
   font, and page-layout steps.
2. Upload one supported profile document and one supported image. Confirm the
   operation completes, only empty project fields are filled, and extracted media
   appears as owned assets.
3. Generate mockups. Confirm exactly three sandboxed previews appear, refresh the
   browser, and verify the same persisted project and mockups return.
4. Select a mockup and start a build once. Record only the internal build ID.
5. Confirm the worker submits one private v0 chat. Repeating the same API request
   with the same idempotency key must return the original build.
6. Allow a `message.finished` hook to arrive. Confirm it queues reconciliation;
   it must not mark the build complete from webhook data alone.
7. Disable or delay the hook for a second build and confirm scheduled
   reconciliation still reaches the provider's authoritative terminal state.
8. Refresh or reconnect the frontend during the build. Confirm polling or SSE
   resumes from persisted state without resubmission.
9. On completion, open the preview and download the ZIP. Inspect the archive for
   the expected pages and assets. A pre-completion download must return `409`.
10. Start Vercel deployment. Confirm the UI reaches `ready_to_claim`, opens the
    Vercel claim URL only after user action, and does not claim ownership was
    accepted. Complete the claim in Vercel and verify the live URL separately.

## Failure and recovery checks

- Temporarily remove each provider credential and confirm the API returns a safe
  configuration error without secrets or upstream response bodies.
- Deliver the same v0 and Vercel webhook twice and confirm the second delivery is
  acknowledged without another transition or job.
- Send an unknown provider reference and confirm it is ignored.
- Send a valid Vercel error or cancellation event and confirm the correlated
  deployment moves to the matching terminal state.
- Restart the API and worker during an active operation. Confirm persisted jobs
  are leased again after expiry and no paid v0 submission is repeated when its
  original outcome is uncertain.

Record provider dashboard evidence, internal IDs, timestamps, and sanitized logs
for the release. Do not record secrets or raw customer content. Stop local
services with `docker compose down`; do not add `--volumes` when persistence is
part of the test evidence.
