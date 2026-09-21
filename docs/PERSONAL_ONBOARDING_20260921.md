# Personal onboarding and connection confirmation — 21 September 2026

## Customer journey

A newly created account starts in its own default workspace, with its own name, email and voice settings. A stale browser brand selection is cleared on login/signup; fresh password and Apple accounts initialise preferences in their own workspace. Onboarding progress is bound to the signed-in user. Social setup remains optional.

Every social callback now stages the provider's returned account for review. Zova displays the destination brand and signed-in email, exact returned handle/name and account ID. Only an explicit Connect saves the selected account. Meta results require selecting one Page/account rather than silently connecting every returned Page. Connection options remain available to add another account. Both Instagram login routes remain intact and a working direct grant is not downgraded by the linked-Page route.

Use another account discards the pending selection and gives truthful switching instructions. Instagram/Meta browser sessions are independent of Zova; Zova cannot clear their cookies or guarantee a fresh provider login. Zova-IG is the application's provider name, not the customer's handle. Cancelling in Zova does not revoke a permission already granted at the provider.

Connecting no longer automatically learns a voice from a possibly unintended account. Users can enter their own guidance and explicitly scan confirmed accounts from Account. Existing saved voices and connections are retained.

## Security and compatibility

The additive zova_pending_connections table stores hashed opaque review codes and encrypted candidate credentials, bound to owner, originating brand, authentication version and a ten-minute expiry. Only whitelisted account display fields reach the template. Atomic single-use consumption prevents duplicate confirmations. Cancel/switch/confirmation scrub the encrypted payload; expired rows are removed by the worker and opportunistically on new flows. Account erasure and synthetic restore comparisons include the new table.

Cross-origin request checks remain in force. Account IDs and credentials come from the staged server payload, never submitted identity fields. A browser check found form controls named action shadowed form.action in the workspace script; attribute access now preserves the actual form destination.

No production data, users, uploads, grants, charges or publishing changed. Subscription enforcement remains disabled. This branch starts from production main 504b617; separate Instagram Post/Story PR #7 is not included.

## Evidence and limits

135 local synthetic tests passed (17 existing dependency/deprecation warnings), including ten new tests covering owner/brand boundaries, revocation, expiry, cancellation, duplicate/concurrent confirmation, cross-origin rejection, provider-label escaping, credential secrecy, multi-Page selection, X/TikTok and new-account voice isolation. Existing Instagram and brand tests now complete explicit confirmation.

Local browser review checked desktop and 390x844 mobile, visible keyboard focus, no horizontal overflow on the confirmation screen, personalized welcome, and the Use another account transition. That transition was repeated successfully after repairing the workspace form script. Providers were mocked; the preview used disposable local data and no provider secrets. Real-provider account switching/approval and controlled acceptance remain external validation, not inferred from tests.

CI result and exact commit are recorded in the root handoff. Implementation is not production deployment.

## Release and rollback

Before any separately authorised deployment, verify current main and integration with the separate Story candidate, preserve session/encryption keys, and take managed database/upload snapshots. Do not replace the database or rotate credentials for this UI change. The table is created additively on application startup.

Prefer forward fixes for connection-review failures. A rollback to 504b617 retains existing connections and the unused additive table but restores automatic callback connection behavior. Stop new OAuth starts during rollback and ask users with pending review links to restart afterward; do not allow an old callback implementation to bypass the new review expectation silently. Pending credentials should expire/be scrubbed before disabling their cleanup worker. Do not restore an old database merely to undo this interface.
