# v0 Hook Operations

AI Launch Kit keeps one environment-level v0 hook subscribed to `message.finished`.
The callback correlates the event to a private chat reference and queues authoritative
reconciliation. It does not complete a build directly from webhook data.

## Configuration

Generate a separate high-entropy token for each environment and configure:

```text
LAUNCHKIT_V0_API_KEY=...
LAUNCHKIT_V0_WEBHOOK_TOKEN=...
LAUNCHKIT_V0_WEBHOOK_CALLBACK_URL=https://api.example.com/api/v1/webhooks/v0/<same-token>
```

The callback must use HTTPS outside local development. Do not place the token in logs,
client code, screenshots, or source control. The implementation uses a path token
because the documented v0 hook API does not define a signed-delivery verification
contract. It intentionally does not accept invented v0 signature headers.

## Provisioning

After deploying API configuration, reconcile the environment hook:

```powershell
.venv\Scripts\python.exe -m launchkit.hooks provision-v0
```

The command lists existing hooks, preserves one exact `message.finished` callback,
creates it when absent, and deletes duplicate or replaced Launch Kit callbacks. Run it
once per local, staging, and production environment after callback changes or token
rotation. It does not create a permanent hook per build.

For local webhook testing, expose the API through an HTTPS tunnel, update
`LAUNCHKIT_V0_WEBHOOK_CALLBACK_URL`, then rerun provisioning. Restore the environment's
normal callback afterward.

## Delivery Handling

The endpoint limits request size, requires JSON object payloads, accepts only
`message.finished`, and searches bounded nested payload data for a chat ID. Each provider
delivery ID is persisted; when no ID exists, a SHA-256 hash of the raw body is used.
Duplicate deliveries are acknowledged without another job. Unknown chat IDs and events
for terminal builds are safely ignored.

Every accepted active-build event queues `build.reconcile`. Reconciliation fetches the
latest v0 state by private chat ID, persists status events, downloads the completed ZIP,
and stores the archive in configured local or S3 asset storage. The normal scheduled
reconciliation path remains active when hooks are delayed or absent.

## Rotation And Recovery

1. Set a new token and callback URL in the target environment.
2. Deploy or restart the API and worker with the new settings.
3. Run `python -m launchkit.hooks provision-v0` for that environment.
4. Confirm there is one matching hook and remove the old secret from the environment.

If provisioning or delivery is unavailable, active builds continue through scheduled
reconciliation. Do not manually resubmit a build whose original v0 submission outcome
is uncertain; create a new build only after confirming no paid chat was created.
