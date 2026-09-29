# Private media delivery candidate

Browser responses and saved review snapshots use `/media/preview/{id}`. That
endpoint checks the signed-in owner/workspace before creating a five-minute
download URL. Local downloads require an unmodified HMAC signature bound to the
filename and expiry. Unsigned/permanent URLs no longer grant access. The URL is
a temporary bearer capability: its recipient can download until expiry, so
the application filters query strings from Uvicorn access logs. Verify the same
redaction in hosting/proxy logs and do not put these links in analytics.

Provider adapters create fresh URLs immediately before publishing, valid for at
most one hour. S3 uses presigned GetObject URLs; the app no longer returns an
existing permanent public URL or populates one for new uploads. Local filesystem
URLs can only be signed for files in the configured upload directory. This does
not make ephemeral disk a durable store.

Before rollout, verify bucket policies deny anonymous access and block public
ACLs; revoke old public object access and review CDN/cache copies. Updating this
code cannot revoke an already public bucket. Run provider fetch tests with
approved synthetic media and confirm the expiry supports their processing time.
Refresh old browser reviews that contain permanent URLs. Do not change or rotate
production secrets to deploy this code. Local signatures use the existing
session signing secret with a media-specific message prefix; a separately
managed signing key/rotation workflow remains future assurance work.

No storage policy, production service or customer object was changed during
implementation. Staging rollout remains deferred. Retention, erasure across
secondary stores and infrastructure access logs remain open guardrails.
