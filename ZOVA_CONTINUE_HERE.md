# Tester remediation candidate — 25 October 2026

Current work is on `codex/ios-beta-20261019` in the existing iOS beta checkout.
Read **docs/beta/QA_REMEDIATION_20261025.md** for all 57 tester cases, seven bugs,
five UX observations and seven owner requests. The workbook is unchanged.

Implemented: Schedule calendar/saved posts with guarded reschedule/cancel/edit;
separate immediate Next Move and saved description-based Strategy; corrected
voice persistence and consent-gated approved-caption memory; public Help/auth
spacing; native tab ownership/save guards and browser connection progress;
conditional Instagram Reel music and private media export for finishing
Story/photo music inside Instagram. A new iPhone binary is required for native
navigation/export changes. This candidate is not yet installed by testers.

No live social publication, grant change, deletion, charge or migration in this
remediation. Keep Render, billing/checkout/enforcement off and the paid monitor
inactive. Do not change Apple's reviewer credentials. All 79 commercial findings
remain; do not revive the unfinished broad RLS/service migration.

Local browser checks use disposable accounts, blocked external providers and a
worker-disabled fixture. They cover calendar time changes/cancellation, pausing
all destinations before caption edit, reload persistence, saved Strategy and
pottery-to-restaurant replacement. Tests exposed and fixed a transient stale-card
flash. Mocked search/AI evidence is not live-provider or model-quality evidence.

Still external: true erasure processing/deadline; Facebook's recorded provider
login; an eligible Meta audio grant and actual delivery; original tester schedule
cleanup; replacement iPhone acceptance. Tester source recording contains an
exposed test credential: restrict/redact it and rotate it; no value is retained
in this report. Original scores stay baseline until the tester reassesses.

Rollback: revert this code without restoring old production data. Retain new
nullable/defaulted voice-memory/audio-grant columns, encryption keys, uploads,
existing sessions and immutable publication ledgers. Roll back native and server
separately; existing builds/routes remain supported. Never replay unknown posts.
The previously verified live server is bcd260e, TestFlight 0.1.0 (10); records below
are historical live evidence, not proof this candidate has shipped.

Code candidate 1a77f43 passed application CI 40177854317 and PR CI 40177859348:
652 SQLite / 653 PostgreSQL, 29 client checks/groups plus Studio and real-browser
viewport checks, synthetic recovery, image smoke, exact scope and clean package
audits. Native source at bf6cc07 passed CI 40177228592 (20 unit/WebKit + 1 UI,
iPhone Release compilation); ios/ is identical in 1a77f43. Final native PR CI
40177859386 also passed on 1a77f43: 20 unit/WebKit tests, 1 UI test and iPhone
Release compilation. Screenshots and full test/provider boundaries
are in the remediation report. No new deployment/TestFlight release yet.

The final small-screen review found and fixed nested composer height caps that
hid Send. Text/Send now remain visible at 350/500/844px with long text, attachments
and four platforms, with reachable formats. The regression is required in CI.
A full operations-only deletion queue and health count are available, but no
automated notification/erasure or owner-approved completion deadline is claimed.

---

# Approved TestFlight beta and security update — 22 October 2026

**TestFlight invitation is now active:**
https://testflight.apple.com/join/BxawFPCu

At approximately 22:09 UTC, the owner's fresh Apple sign-in was observed. Build
**0.1.0 (10)** remains **Testing**, assigned to **Zova Social External Beta**.
The requested public link was saved with a **10-tester maximum**, currently 0/10,
and its public landing page was verified as **Join the Zova Social beta**.
No direct invitations were sent and no tester was enrolled by the agent.
The separate live password-reset/session-revocation check remains unresolved;
creating the invitation does not mark it passed or certify commercial readiness.

Apple approved **0.1.0 (10)**: its external group was observed as **Testing** on
21 October, with zero external testers. The app source is unchanged; no new
binary is needed for this server dependency patch. This is TestFlight approval,
not a public App Store release or commercial certification.

Fresh dependency checks found newly disclosed problems in the live image's
Pillow 12.3.0 and pip 25.0.1. Exact reviewed candidate
**bcd260e25d92b41101f31073e2a626588195c65d** pins Pillow 13.0.0 and pip 26.2.0,
tests image orientation/decoding and now audits the actual hosting-image package
inventory as well as the test runner. It is **live on Render**, deploy
**dep-dbcj1pvb9u1s73bree8g**, instance **n7s4s**, since 21:39:52 UTC on 21 October.
Effective runtime confirms patched versions, billing off, checkout false and
subscription enforcement false. No schema, keys, grants or customer data change.

Required CI **39679616727** passed: **590 SQLite tests / 2 skipped,
591 PostgreSQL tests / 1 skipped**, client groups/Studio, synthetic restore,
hosting-image smoke/audit and exact scope. Native CI **39679616901** passed
**16 unit tests / 1 UI test / iPhone release compilation**. The fresh test and
hosting-image dependency audits report no known vulnerabilities. The previous
day's clean scan does not supersede the new findings or this patch.

Live readiness on 22 October at 09:02 UTC: database/schema available, embedded
worker idle, no overdue/stuck jobs, failed/stuck mail, old reservations or recent
AI failures. Full status correctly remains attention for one historical unknown
Instagram publication and **49 unpriced AI calls**. Do not invent outcomes/costs.
The reviewer session survived deployment. The owner's new isolated recovery
account has its own identity, no connections and no drafts; draft36 is not leaked.

Owner decisions on 22 October:

- Reports build 10 draft/attachment reload and Facebook/X/TikTok cancellation/
  return checks passed. Phone/iOS details were not supplied. Instagram return
  was separately confirmed earlier. Keep device reports distinct from CI proof.
- **Leave the paid monitor inactive.** No cron, recurring hosting cost or new
  monitor key was created. Independent automatic monitoring remains a beta
  limitation; do not request the same approval again or claim alert automation.
- Use **david@zova-social.com** for beta operational contact. Authorised manual
  test alert `01a162d9-354b-7cb1-9a8a-dd7ef6080e8d` is Delivered in Resend;
  the owner now confirms receipt in the forwarded inbox. Manual delivery and
  receipt are verified; automatic monitoring remains inactive by choice.
  Existing support forwarding remains intact.
- Created the separate **Zova Recovery Check** account. Its actual reset email
  `01a162d7-4bb8-7bf3-bf53-0efa41c37ad5` is Delivered. After the first completion
  reply, database/UI evidence still showed an unused reset/auth_version 0 and a
  valid old session. Owner was asked to finish the password submission. Do not
  mark reset/revocation passed until evidenced; never reset Apple's reviewer.

Follow-up at **21:57 UTC on 22 October**: the owner reports seeing "Password
updated" and signing back into Apple. A fresh read of the live PostgreSQL account
still finds auth_version 0 and its sole reset token unused (expired at 09:15 UTC).
A newly opened Account page still accepts that account's existing session. The
accessible Apple tabs were still signed out, including after direct navigation to
the external group. The subsequent sign-in is resolved and the invitation is now
saved as recorded above. The recovery account discrepancy remains: reconcile the
account/browser used before repeating credential steps or marking revocation passed.
Live bcd260e readiness still passes, billing/checkout/enforcement remain off,
worker idle and no overdue/stuck jobs or failed/stuck mail. The historical unknown
publication and 49 unpriced AI calls remain visible, unchanged.

The earlier link save returned to login after session expiry; the later successful
save supersedes that blocker. Screenshot receipts are in ignored social-proof:
`testflight-public-link-20261022.png` and `testflight-invitation-page-20261022.png`.
Finish the separate live recovery acceptance without changing Apple's reviewer.

See **docs/beta/BETA_ACCEPTANCE_20261021.md** for exact evidence and limits.
Retain all 79 commercial findings and the four historical missing August uploads.
No AWS migration or customer charges. Keep data, disk, keys and publication
receipts during rollback. Prefer a code revert that retains patched dependencies;
old `7048c35` is an outage fallback with known dependency findings, not an equivalent
security release. Never replay unknown posts or restore stale production data.

---

# Beta checks published; owner acceptance gates remain — 20 October 2026

The owner asked to finish beta checks while Apple reviews build 10. The bounded
follow-up is **live on Render** at exact
**7048c353d2833a24076bde99a8a09a4c2e7a286f**,
deploy **dep-dbbt0mjncjis73c1hcv0**, instance **r9986**, at 21:35 BST.
Do not deploy main or the unfinished broad migration. Customer billing mode is
off, checkout false and subscription enforcement false, verified through effective
runtime functions after deployment. No provider grant, real post or tester invite.

Changes: optional separate read-only monitor access (cannot dispatch or read
customer cohort reports); bounded safe monitor requests; stored attachment
availability/size checks before review and dispatch. Missing media after review
now fails before sending, releasing its reservation instead of becoming an unknown
provider outcome. Missing previews fail safely; draft/media records are retained.
There is no schema migration and native application source is unchanged.

Required CI **39492645799** passed for that exact candidate: **584 SQLite tests /
2 skipped, 585 PostgreSQL tests / 1 skipped**, 18 client tests/groups plus Studio,
dependency audit with no known findings, synthetic restore, hosting-image smoke
and the exact beta scope. Native CI **39492645584** passed **16 unit tests, 1 UI
test and iPhone release compilation**. An earlier native run failed only on the
5-second cold listener setup deadline, while the handshake checks completed;
the bounded 30-second setup allowance fixes that test without removing assertions.
Do not count the earlier failed run as passing. Build **0.1.0 (10)** remains the
submitted binary; no new TestFlight build is required for these server changes.

Live checks: dependency readiness 200, schema/database available, embedded worker
idle with progress advancing from 20:38:21 to 20:39:22 UTC, zero overdue/stuck
publications, failed/stuck mail or old reservations. The
full status correctly remains attention for **one historical unknown Instagram
publication** and **47 unpriced AI calls**; neither was hidden or marked resolved.
Reviewer stays signed in as the same account; Studio draft 36 and its pending idea
survive deployment/reload. Drafts, Performance, Account and Help load. Help confirms
free beta/no card and support@zova-social.com. A temporary 502 during Render's
disk-backed restart cleared when the new service became Live.

Recovery: a consistent read-only production snapshot was restored into a private,
disposable local PostgreSQL 18 instance with no network listener or app/providers.
All **44 tables / 401 rows** matched; **39 encrypted values** decrypted correctly and
rejected the wrong key; **16 files / 6,187,895 bytes** passed copy/restore hashes.
Temporary copies, local server and extracted official tools were removed.
Overall media recovery is **incomplete**: four uploads from 29–30 August are missing
on disk, with no current draft, conversation, review or schedule references found.
Local workspace upload folders had no matching originals. Records remain intact.
Do not call this a full media recovery or a managed PITR/independent-key recovery.
Receipt: `docs/beta/restore-receipt-20261020.json`.

Outstanding owner inputs already requested asynchronously; do not duplicate them:

- Create the prepared separate **Zova Recovery Check** account with controlled
  alias **zova.social+beta-recovery@gmail.com** in tab 64. Owner enters/submits its
  password and terms. Then conduct live reset/login, old-session and used-link
  rejection. **Do not change Apple's reviewer password.**
- Confirm build 10 on the physical phone: attachment/draft reload and Facebook/X/
  TikTok sign-in cancellation/return, with phone/iOS details. Instagram return was
  confirmed previously; do not infer every provider or current-device scenario.
- Approve or decline the prepared **zova-beta-monitor** Render cron: every 10 minutes,
  runtime capped 30 seconds, auto-deploy off, smallest instance, **$1/month minimum**.
  Separate read-only credential creation is also pending approval. Tab 65 is the
  unsubmitted form; **no new service or credential was created**. Keep the
  health-only token distinct from scheduler/admin/database/provider/billing keys.
  Prove alert delivery/acknowledgement and address historical attention/noise
  explicitly; do not silently suppress uncertainty or missing cost coverage.
- Confirm support/alert inbox ownership (support@ or david@). Existing delivery
  and forwarding were confirmed in Gmail; ongoing coverage has not been confirmed.

Apple was rechecked: **Waiting for Review**, external group still **0 testers**.
No external invitations yet. Remain on Render; AWS and customer charges unchanged.
See **docs/beta/BETA_CHECKS_20261020.md** for evidence and remaining limits,
**EXTERNAL_BETA_20261020.md** for invitation gates and **TESTER_BRIEF.md** for the
ready-to-use tester guide. All 79 deferred commercial findings remain retained.
Rollback for this bounded update: runtime **b131f23**, preserving data/disk/keys and
all publication receipts; pause any subsequently activated monitor if rolling back.
Never replay unknown posts or restore stale production data as a code rollback.
Screenshot: ignored **social-proof/beta-checks-render-live-20261020.png**.

---

# External TestFlight build submitted — 20 October 2026

The owner completed Apple's private reviewer fields. On resuming, the existing
Apple tab already showed **Zova Social 0.1.0 (10) — Waiting for Review** in
**Zova Social External Beta**. Submission had therefore completed through the
owner's browser interaction; do not attribute a second submission to the agent.
This is Beta App Review submission, not approval or a public App Store release.
Verified status on 20 October; record checked at 19:47 UTC / 20:47 BST.

App ID **6824416979**, bundle **com.zovasocial.app**, build UUID
**49d32ac0-86d6-43bc-a0e3-8d82d9101af1**, external group
**f3f15099-0bec-49dc-8347-cd55beb805c0**. Build 10 is assigned to that external
group and the existing one-tester internal group. No external invitations were
sent; the external group has no testers.

The private contact and review username are now saved in Apple. Credential
readback is redacted by the browser tools; it must not be treated as the real
password or evidence that a password is wrong. The owner performed a fresh
login using the same password entered in Apple and confirmed success. Browser
checks then observed Studio, the exact reviewer email in Account and the saved
synthetic draft 36. No credential is retained in chat, evidence or Git.

Apple's previously empty Review Notes are now saved with reviewer navigation,
optional provider connection/publishing, explicit AI sharing, free-beta status,
accurate Instagram/Facebook/X eligibility and production TikTok inbox limits.
Replaced the leftover "internal beta" description with external-beta copy and
set Feedback Email to the already delivery-tested **support@zova-social.com**.
Each save reached Saved. What to Test is present and accurately covers account,
draft/edit/media/reload, AI permission, social return/cancellation, final review,
keyboard/larger text/VoiceOver and safe feedback. No legal terms were accepted.

Screenshot receipt: ignored
**social-proof/apple-external-beta-waiting-review-20261020.png**. See
**docs/beta/APPLE_REVIEW_NOTES_20261020.md** for submission details.
Render remains on tested **b131f23**, native build 10 is unchanged, charges and
subscription enforcement remain off. No real post, provider grant or password
change occurred. Keep the remaining live reset/session-invalidation, device,
alert-delivery and isolated production-restore gates in the external-beta
checklist; Apple approval and those gates are still needed before invitations.

---

# Security-form fix live; Apple reviewer password still missing — 20 October 2026

Owner requested checks and Beta App Review submission after creating the reviewer
account. Account creation is confirmed. Zova App Review,
zova.social+apple-review@gmail.com, has no social connections and one harmless
pending idea, draft 36, which survives reload and the new server deployment.
No AI-sharing permission or real AI request, connection grant or social post was
made during this check.

Found and reproduced the live no-referrer/Origin-null form defect described
below. Bounded fix **b131f23af2dbd95c0609da5b18944753daaac3bc** passed all
required CI in **39482173393**: SQLite 564 passed/2 skipped, PostgreSQL 565
passed/ 1 skipped, 18 client tests/groups plus Studio harness, synthetic restore,
container smoke, dependency checks and exact scope. Native binary is unchanged.
The earlier local full run's scope-manifest failure is not claimed as a pass.

Render **dep-dbbruo5pkucs73dudgv0** became Live at **20:23 BST on 20 October**.
Post-deploy shell readback confirms that exact commit, readiness 200, database and
schema ready, embedded worker idle, billing off, checkout false and subscription
enforcement false. Zero overdue jobs, stuck publications, failed mail or stuck
mail. The historical uncertain Instagram publication remains preserved.

Actual reviewer verification email was Delivered by Resend, its link confirmed
ownership and reuse was rejected inline. Actual password-reset request was
Delivered and its link opened the reset form, with the token removed from the
address bar. No password was entered or changed. A completed live reset and
old-session revocation still require owner credential entry; synthetic checks
pass. See **docs/beta/SECURITY_FORM_ACCEPTANCE_20261020.md** for exact receipts,
screenshots and rollback limits. No passwords or link tokens are stored here.

**Apple submission remains blocked on private reviewer credentials.** Original
Test Information modal contains the private contact and reviewer username,
but its Password field has no value and Next is disabled. A fresh second tab
confirmed no saved TestFlight review details; the separate App Store review
form also has no username or password. Only field-presence booleans were printed.
The owner has a pending request to enter the existing Zova review password into
Apple's Sign-In Information. Do not use the owner's Apple password, invent a
credential or bypass the required new-password handoff with a server change.

Next: once the owner fills the Apple field, verify the review login privately,
finish the review notes and submit build0.1.0 (10) to Beta App Review. Record the
actual Apple receipt; do not equate submission with approval. Build 10 remains
Ready to Submit; the external group has no submitted build or invited testers.
Customer charges stay off and Render stays in place. The external-invitation
gates in EXTERNAL_BETA_20261020.md (live reset, remaining device/provider checks,
alert delivery and isolated production recovery) are still open.

---

# Reviewer account created; security-form correction in validation — 20 October 2026

Owner created Zova App Review at zova.social+apple-review@gmail.com and requests
checks followed by Beta App Review submission. Verified onboarding identity and
all four socials Not connected. Created one harmless pending idea, draft 36;
saved state survived reload, Drafts shows one item and Performance shows the
unconnected state. No AI consent granted, AI request, social connection or post.

Apple's visible Test Information modal still had empty username/password despite
the owner reporting entry. Filled the review email and asked the owner to enter
the existing password in Apple's private Sign-In Information field. Next remains
disabled until entered. Do not share the private contact phone or password.

Live verification attempt reproduced HTTP403 "Open Zova directly and try again."
before any mail send. Root cause: no-referrer pages' native form POSTs supply
Origin null, correctly rejected by existing middleware. Implemented a bounded
client helper for verification/recovery forms using CORS-mode same-origin fetch,
keeping no-referrer and every backend Origin/token/session check unchanged.
Errors remain inline with input retained and duplicate submission suppressed.
See docs/beta/SECURITY_FORM_ACCEPTANCE_20261020.md.

Focused Python: 24 passed. Client: 18 groups/tests plus Studio harness passed,
including five new security-form regressions. Real local browser verification
request/confirmation succeeded with valid Origin and no Referer; replay rejected
inline. Full suite running; its first pass preceded the refreshed exact-scope
manifest and hit that expected scope-drift check. New manifest now reviewed and
validates, but fresh required application/PostgreSQL CI must pass before deployment.
Runtime remains 25374db; native build 10 is unchanged. No Apple submission yet.

---

# Recovery email live; Apple reviewer handoff remains — 20 October 2026

Owner confirmed the prepared restricted Resend key/configuration and two delivery
checks. Created **Zova Social Render recovery**, key ID
33e41e38-8f66-4bfa-a01a-321ba07c3497, Sending access only, restricted to the existing
verified `auth.zova-social.com` domain. Stored its value only in Render's protected
SMTP_PASSWORD; no plaintext credentials in Git, chat, screenshots or evidence.
Resend remains Free with paid overages off, Ireland/Enforced TLS and no configured
tracking subdomain. The separate Zova Market key and root DNS are unchanged.

SMTP_HOST=smtp.resend.com, SMTP_PORT=587, SMTP_USERNAME=resend,
SMTP_FROM=Zova <noreply@auth.zova-social.com> are now live. PUBLIC_BASE_URL remains
https://zova-social.com. Mail activation deployment dep-dbbqk2tpkucs73eg704g
reused exact existing runtime **25374dba138c8c50ebeb5b0224b7d4af55b180bd**.
No rebuild from the service's unrelated main branch. Recovery readiness true,
internal status 200, database reachable, embedded worker idle, zero mail failures
and stuck mail; billing off, checkout false and subscription enforcement false.

The authorised support and David delivery checks returned SMTP accepted; Resend
reports Delivered. IDs: 01a15a72-4a7b-727d-bc06-0253fdfbff4f (support) and
01a15a72-4ed5-7044-a7aa-1d3505ece6f3 (David). Cloudflare reports Forwarded for both.
The support detail confirms the existing zova.social@gmail.com destination and
SPF/DKIM pass at 18:53:22 BST. Owner explicitly confirmed **"Both emails arrived"**
in Gmail on 20 October. This completes the two delivery checks through to the
owner's inbox. They contain no reset/verification token and do not prove the
complete recovery journey.

Set SUPPORT_EMAIL=support@zova-social.com after forwarding evidence. Deployment
**dep-dbbqni1jfumc73d36gr0** is Live at 18:59:07 BST on the same runtime.
The signed-in live Help page now shows Contact Zova support → that mailto address
and free beta/no automatic charge. Existing browser session survived.
Gmail Send mail as is not configured, and app mail does not add a Reply-To header;
incoming forwarding is distinct from sending replies as support@.

Owner supplied the private review-contact telephone number. It is entered in
Apple tab38's still-unsaved required review form; never put that personal number
in app UI, public metadata, repository or this document. Prepared a separate
signup in tab60 for **Zova App Review**, zova.social+apple-review@gmail.com.
Owner asked to enter a unique new password, accept the app's terms and submit,
skip social connections, then fill the same existing credentials into Apple's
review fields without clicking Next. New password entry is an owner handoff.
Do not share the owner's personal account or attach their social profiles.
Reviewer password/signup and Apple's username/password fields remain incomplete.
Rechecked after the inbox confirmation: signup is still open and Apple's Next
is disabled, with the private reviewer login fields blank.
The owner's generic Yes approved the mail-key action; do not treat it as evidence
of completed reviewer signup. Never bypass the password-entry handoff through
another tool or backend route.

After these inputs: verify reviewer access and only synthetic content; test
real delivered email/verification/single-use recovery; finish review notes and
submit Beta App Review with a visible receipt. External invitations still wait
on Apple approval and the other documented acceptance gates. Runtime25374db and
build 10 are unchanged. No reviewer account or review submission is confirmed.
The two approved delivery tests are the only new emails. No social posts/grants,
customer charges, AWS upgrade or cloud migration.
Evidence in ignored social-proof: resend-social-sending-key-created,
resend-email-delivered-checks, support-email-forwarded, support-email-render-live
and support-email-help-live, all dated 20261020. Read
docs/beta/RECOVERY_EMAIL_SETUP.md and APPLE_REVIEW_NOTES_20261020.md.
Apple tab38 remains on the unsaved reviewer form; signup tab60 is the owner
handoff. Resend58, Cloudflare57 and Render54 hold mail configuration evidence.

---

# Owner confirms Instagram return; external Apple group prepared — 20 October 2026

Owner answered the build9 phone check: **"Returns automatically to Zova"** after
Instagram's final profile confirmation. Record this as owner-reported physical
Instagram acceptance. Do not generalise it to Facebook/X/TikTok, cancellation,
account switching or publishing. Build 10 retains the same native social-return code.

Owner signed back into App Store Connect. Build 10 has finished processing and
shows Ready to Submit; UUID 49d32ac0-86d6-43bc-a0e3-8d82d9101af1. Saved focused
What to Test notes and assigned the existing Zova Social Internal Beta group
(1 existing tester). Created **Zova Social External Beta**, group
f3f15099-0bec-49dc-8347-cd55beb805c0, with zero testers. Its Add Builds flow selects
10 but requires contact phone and a dedicated reviewer account before proceeding.
No Beta App Review submission, public invitation link or external invitations.
Contact name/email prepared in the unsaved modal; owner asked for review phone.
Never share the owner's personal Zova account as reviewer credentials.

Email: owner uses Gmail and Cloudflare domain registration, requests setup help.
Owner signed into Cloudflare. Existing active david@zova-social.com rule routes
to the verified destination zova.social@gmail.com. Created **support@zova-social.com**
using that same verified destination and confirmed Active in the rules table.
Existing David rule, root DNS and catch-all unchanged. This is configured
forwarding, not a proven new-message inbox receipt or an outbound sender.
Resend signup is open in tab58. Owner asked to create/sign into Resend, completing
credentials/account terms directly. No Resend account creation, sending DNS record,
sender grant or paid upgrade performed. Configure SUPPORT_EMAIL only after the
support route's delivery check; application mail remains unconfigured.
Production Render successfully negotiates verified STARTTLS with
smtp.resend.com:587 and advertises AUTH. This proves network/TLS connectivity only;
no credentials used and no email sent. Preserve incoming Cloudflare MX/SPF.

Continue at Apple tab38's contact/reviewer form after owner information arrives.
Cloudflare57/Resend58 are handoffs. Proofs in social-proof:
testflight10-notes-saved-20261020.png,
testflight-external-group-created-20261020.png,
resend-signup-handoff-20261020.png and support-email-routing-active-20261020.png.
Cloudflare account5fb2d0270682efea2d06d7809b84fad9, domain
87fec50363781ebe0388782b3a5606ed; Email Routing path is
/email-service/routing/87fec50363781ebe0388782b3a5606ed/routing-rules.
Operational alert delivery and production
recovery rehearsal remain open; no score uplift or readiness certification.

---

# External beta update live; TestFlight 10 uploaded — 20 October 2026

Owner explicitly requests fixing/testing/reviewing, publishing validated updates on
Render and preparing external TestFlight. Keep charges disabled; keep AWS Free
unchanged. Read docs/beta/EXTERNAL_BETA_20261020.md and TESTER_BRIEF.md. This is not
commercial certification or permission to publish real social posts.

Runtime **25374dba138c8c50ebeb5b0224b7d4af55b180bd** is LIVE on Render service
srv-d9rqg6navr4c739thoeg, deploy dep-dbbp1k0ae00c73abch8g (20 October, 17:03 BST).
Live dependency readiness and database/schema checks return 200. Embedded worker
has a real idle heartbeat; no overdue/stuck publications. Runtime billing mode is
off, checkout false and subscription enforcement false. Existing signed-in web
session remained usable; Account shows free beta, retained Facebook/X/TikTok
connections and the explicit AI-sharing choice. No real posts or grants changed.

Bounded follow-up to 45d4d3b: verified-mailbox requirement for the allowlisted staff
directory (unverified access reproduced before fixing); local unlink cancels only
unsent jobs/publications and unused reviews, leaving pending/in-flight/unknown
provider receipts intact; cancelled review gives a clear conflict even after
reconnection. Embedded scheduler now records progress; monitor rejects stale or
incomplete documents and flags worker failure, old reservations and missing mail
configuration. External-eligible TestFlight export uses existing signing/workflow
counter, minimum build 10, no public App Store submission. Two tracked bytecode
files removed; local virtual environment excluded from Docker context.

Exact application CI 39453432880 passed: SQLite 563 passed/2 PostgreSQL-only skips;
PostgreSQL 564 passed/1 SQLite-backup skip; 13 client tests/groups and Studio harness;
dependency audit 0 known findings; container, synthetic PostgreSQL/key/password/
session/media/AI-consent recovery and exact beta scope all passed. Native CI
39453432747 passed 16 unit tests, 1 UI test and release compilation. Local final
suite also 563 passed/2 skipped. These are synthetic tests, not real provider or
managed production restore evidence. Browser check at 393px verified AI decline
retains the sent message, reload and retry. The synthetic model failure also kept
the message; this is not proof of real-model answer quality.

Codemagic build 6ad7907b454d2506f7ab80b9 archived exact 25374db and uploaded
**0.1.0 (10)**, com.zovasocial.app. Apple upload log says UPLOAD SUCCEEDED with no
errors. Signing log explicitly shows Test Flight Internal Testing Only: False.
Apple processing, external group assignment and Beta App Review remain unverified:
App Store Connect tab38 is signed out and owner has been asked to sign back in.
Do not say build 10 is installable or externally approved yet. Native code is the
same as build9; current-device sign-in/return acceptance is still pending.

Production has no SMTP host/from, no configured AI cost rates/threshold, one old
unknown publication and 47 unpriced AI calls this month. Read-only reconciliation
left publication-2 (Instagram, 22 September) unknown: no stored provider receipt
identifier exists. Never resend or mark it published/failed without evidence.
Uploads have an existing 1 GB disk at /app/uploads with daily snapshots through
20 October. Managed PostgreSQL UI shows 3-day point-in-time recovery and a
19 October 09:03 BST export. No production restore was performed.

TikTok portal's Live version currently has user.info.basic+video.upload and Direct
Post disabled; video.publish revision remains In review. Production inbox=true and
verified media prefix absent. Owner's earlier audit approval is separate evidence,
not proof that this scope is live. Preserve inbox until provider approval and
controlled activation; do not advertise all-social Direct Post as completed.

Open gates: outgoing recovery/verification email with a delivered single-use reset;
renewed Apple sign-in/reviewer access/external approval; real iPhone social-return
acceptance; delivered operational alerts and isolated production recovery rehearsal.
Public DNS shows Cloudflare Email Routing for the company domain, not evidence of
outbound sending. Owner asked whether to prepare Resend Free or use an existing
outgoing provider. No email account, paid plan, DNS change or credential was created.
Use docs/beta/APPLE_REVIEW_NOTES_20261020.md for the prepared review content.

Evidence: social-proof/external-beta-validation-20261020.json;
social-proof/external-beta-ci-25374db; render-external-beta-live-25374db.png;
testflight10-uploaded-20261020.png; beta-ai-declined-20261020.png.
These local proofs are ignored by Git; the CI runs and deployment/build IDs above
are durable remote receipts. Update the final review state when owner actions
arrive. Do not rebuild an identical iPhone binary or repeat completed tests.
All 79 historical gaps remain recorded; no unsupported score uplift.

---

# AWS account created; owner retains Free plan — 20 October 2026

Owner supplied company email david@zova-social.com and said "No credit history for the company (new company)." Self-funded and August2026 product start remain confirmed. Preserve that wording; borrowing history is distinct from earlier AWS/Azure/Google promotional credits, so confirm the precise award-history question before attesting on an application. Updated facts, prepared answers and remaining unknowns are in docs/architecture/CLOUD_MIGRATION_20261019.md.

Owner completed the missing profile and product fields directly, responding Done twice. Reopened both saved steps and verified: founded12August2026, employee band1–10 (not an exact headcount), AWS experience0–2years, job titleCEO, target launch1December2026, fundingNo Funding and No Valuation. Preserve those owner entries. Aligned the duplicate founder-role field with the owner's CEO choice and saved. Founders package; consumers/businesses; web/mobile; launched initial product and iterating; uses AI to improve product; AWS spend share I'm not sure. Product description explicitly says web/iPhone beta, Python/PostgreSQL, planned container/S3/workers and OpenAI captions. Both profile and product steps are now confirmed saved.

Owner completed AWS signup directly. Signup displayed Congratulations/activating, then the console opened successfully as Zova Social. Console explicitly shows Free plan, $100 USD starter credit and 183 days remaining (20 April 2027). This is NOT an Activate award. Opened the upgrade review: AWS says the Paid plan enables Activate eligibility, preserves remaining credit and bills uncovered usage. Owner explicitly answered **Keep the Free plan for now**. Did NOT click Upgrade plan. Do not upgrade, provision paid resources or cut over hosting without a new owner decision. Returned to Console home and verified Free plan/$100 remains; existing tab52 (providerTabId b1597260-fe77-4851-a3a3-a6e619f980dc) remains the signed-in account. Screenshots social-proof/aws-paid-plan-review-20261020.png and social-proof/aws-free-plan-retained-20261020.png record the reviewed terms and retained plan; signup preparation screenshot is historical.

Application tab51 remains at https://startups.aws.com/credits/apply/link-aws-account with all previous profile/product fields saved. Clicked Link my AWS account once to open its review, but the control returned to its initial state with no new tab or verified link/consent. No final linking confirmation, application submission or Activate award. The account's Free plan currently fails the published Activate paid-tier requirement; leave the saved application for later rather than submit an ineligible declaration. Promotional-credit history still needs precise confirmation before any final attestation. No AWS services provisioned, customer data copied or hosting migration. Render stays live.

AWS's limited-rollout new signup can use Builder ID to own project accounts, so absence of card/phone verification alone is not proof that no account exists. The completed signup used the application's observed root-email route. Reuse the now-established Zova account; do not create another. Do not ask again for saved profile/product dates or reset the form.

Owner also asked to update TestFlight0.1.0(9), fully close/reopen and complete one social connection through Zova's final account confirmation, then report whether it returns automatically to the app. No post or disconnect/reset requested. Physical-device acceptance remains pending; no score uplift. Build9 was already verified Testing in the existing internal group. Runtime45d4d3b is tested but NOT deployed; live419d452 is unchanged. This turn only updates documentation/application preparation, not application code or commercial release status.

---

# Commercial candidate validated; TestFlight9 available — 19 October 2026,21:49 BST

Latest owner request: assess commercial readiness across product/design/iOS/engineering/security; iteratively improve and then pursue credit-supported cloud migration. Current work is a bounded candidate, not a commercial launch. Baseline db7fc42 / live server419d452 is preserved. Read docs/COMMERCIAL_READINESS_20261019.md (13 dimensions, 5.6→6.3 judgement), docs/architecture/CLOUD_MIGRATION_20261019.md and docs/beta/current-reconciliation-20261019.json. All 79 original areas retained; historical RLS/service claims are not assumed active.

Candidate: account-bound explicit AI sharing with server enforcement, version/revocation/export/erasure and first-use dialog; Performance7/30-day answers, incomplete metrics/no fabricated winner, stale refresh/late answer protection, safer links and larger mobile typography; saved Next move/recurring drafts open without generating again or demanding a new AI permission; simpler Account/Drafts/current Help; safe correlated request failures and provider-error/review-URL redaction. Two additive tables only. Portable worker/runtime controls remain INACTIVE: embedded scheduler/default pool retained, no hosting/env/grants/customer-data change. Invalid external mode refuses before DB preparation; explicit offline target preparation, pool budget, private shared-storage config requirement and PG worker lock/heartbeat prepared. No unfinished broad migration merged.

Local full run540 passed/2 PostgreSQL-only skips before the final import-order safeguard; focused safeguard/diagnostics11 passed/1 PG skip. Existing Studio client harness and13 node tests/groups passed. Desktop plus393px synthetic phone screenshots reviewed; initial spacing, tiny metrics, misleading comparison bars and dark-dialog contrast were corrected. Permission cancel/allow/result verified with synthetic account and no real provider request. Candidate7e6a7fe passed hosted SQLite541/2 skipped, PostgreSQL542/ 1 skipped, dependency/restore/container and exact-scope checks (39319457603). Final saved-draft refinement passes the client failure/save/workspace tests and requires new exact-candidate validation. Save final receipt in social-proof/commercial-validation-20261019.json and PR34 checks; do not treat the earlier run as validation of later changes. No new real posts, charges or deployment.

Owner confirmed self-funded, started August2026. Existing Apple developer organisation is ZOVA SOCIAL LIMITED; previous startup credits/company-domain email remain pending. Owner signed back into Apple: build0.1.0(9), UUIDe309aeb4-126e-48bb-a4eb-fc4a4d1a21d2, is now verified Testing in existing Zova Social Internal Beta group a74d0ba7-0d28-4f11-bfb3-c77e75986ba8 with1 tester at21:41BST. Focused What to Test notes saved; screenshot social-proof/testflight9-testing-20261019.png. Owner asked to update9 and verify automatic return after final social confirmation; answer pending. No duplicate build, new signing grants, tester or public release. Existing8 fallback. No new Swift code in this increment. Build9/server419d452 do not yet include this commercial candidate.

Do not cut over to a cloud, claim credits awarded or enable paid plans. Start with eligible AWS Activate application vs Microsoft comparison once owner facts arrive; all advertised credit maxima conditional. Require approved cost/award/staging restore/canary/rollback before live migration. Render stays live. A full code rollback before AI consent would remove the permission boundary: retain this gate or pause new AI processing before reverting. Preserve all data, keys and publication ledgers; never resend unknown outcomes. See assessment for concrete release gates and next iteration.


Final recovery iteration: scripts/synthetic_recovery.py seeds only a loopback CI database before pg_dump, then checks passwords, token decryption/wrong key rejection, live and revoked sessions, unknown publication, withdrawn AI permission and checksum-verified media restoration after pg_restore. New local guard/corruption tests6 passed. Await final exact-candidate hosted receipt; never claim cloud/production restore or RPO/RTO from this synthetic drill. All operator decisions and commercial gates remain open.

Final implementation45d4d3b passed required PR application39321607637: SQLite547 passed/2 PostgreSQL-only skips; PostgreSQL548 passed/1 separate SQLite-backup skip;13 Node tests/groups and Studio harness; dependencies0 reported vulnerabilities; synthetic restore/recovery, container smoke and exact beta scope passed. Native39321607625 passed 16 unit/1 UI tests plus release compilation. Final structured receipt: social-proof/commercial-validation-20261019.json; CI artifacts and PR34 carry remote evidence. The two owned loopback preview services8793/8794 are stopped and temporary review tabs closed; Apple38 is retained as a deliverable. These commercial changes are NOT deployed; live419d452 and delivered native9 remain separate. Final documentation receipts do not change the validated runtime.

---

# Native9 accepted by Apple; App Store Connect sign-in required — 19 October2026,16:25 BST

Codemagic6ad634947550aed810902dd4 FINISHED3m29s. Apple upload succeeded16:25:19 BST, delivery/build UUID e309aeb4-126e-48bb-a4eb-fc4a4d1a21d2, Zova0.1.0(9), com.zovasocial.app, source419d452. Existing signing profile/certificate/workflow only. Server419d452 is already LIVE (Render dep-dbb3804s728c73a8jaug); application513/ 1 skipped each database and native16 unit/1 UI/release checks passed. Shared Studio/Account inspected live, screenshots saved below. User-facing update already explains shared UI is live.

Refreshing App Store Connect tab38 redirected to Apple login authResult=FAILED. This is an expired browser session, not a rejected build. Asked owner to sign in to existing App Store Connect tab, including verification, and tell us when in; answer pending. Do not enter/ask for passwords or codes. Apple processing, build9 What to Test notes and assignment to existing Zova Social Internal Beta group a74d0ba7-0d28-4f11-bfb3-c77e75986ba8 remain TO DO. Do not claim9 can be installed until status Testing/group confirmed. Existing8 remains delivered fallback; avoid duplicate signed builds. Native phone automatic dismissal remains unverified until owner updates and accepts profile in a fresh flow. No real social posts or grant changes authorised/tested here.

Next: after owner signs in, refresh/read /apps/6824416979/testflight/ios, find9 (UUID above), wait for processing if needed, set concise notes covering all four social returns after final profile confirmation/cancel plus slim header/Account rows/no raw IDs, add existing internal group and verify Testing/1 tester. No new app, identifier, key, certificate, tester or public release. Then tell owner update0.1.0(9), fully close/reopen, retry one connection without deleting existing ones and report whether browser dismisses. Keep all79 wider gaps, existing identity/data/attachments/connections, explicit publishing approvals, unknown-outcome protection and disabled charges. Rollback server8846cbc/native8; no stale data restore/resend.

Browser handoffs: Codemagic tab37 (new build receipt) and Apple tab38 (login) marked for continuation; browserID2. Temporary local preview31502 STOPPED; preview/live-review/Render tabs closed. User's pre-existing Studio7 and provider tabs left unchanged. Local visual proofs retained under ignored social-proof; do not recreate a test service in production.

---

# Shared slimmer UI live; native9 uploading — 19 October2026,16:23 BST

Runtime419d4520fb76a357f007a6c95c274f78c26625d1 is LIVE on Render dep-dbb3804s728c73a8jaug, started16:15:12 BST,1m17s; service live16:16:29. Public health/login/native-config200; public studio-layout.css, zova-night.css and studio-publish.js hash-match reviewed source. Existing signed-in browser Studio/Account inspected without submitting posts/settings; Studio weekly summary absent, plain Account rows present. Evidence social-proof/studio-slim-live-20261019.png and account-rows-live-20261019.png. No provider grants or customer data changed.

Exact candidate application39275914996 SUCCEEDED513/ 1 skipped each SQLite/PostgreSQL, dependencies/restore/container/exact-scope guards. Native39275915374 SUCCEEDED16 unit tests, 1 UI test and iPhone release compilation. First application attempt had two obsolete tests expecting the weekly summary in Studio; moved assertions to Drafts and assert absence in Studio, preserving pending/overdue visibility there. Older duplicate/outdated checks cancelled to avoid needless work; no failed gate waived.

Codemagic6ad634947550aed810902dd4 is PUBLISHING Zova0.1.0(9), com.zovasocial.app, exact source419d452, correct branch codex/ios-beta-20261019, index8, existing workflow/profile/certificate. Machine started16:21 BST. No new signing permissions, credentials, billing or other-app changes. Apple upload acceptance/processing/internal-group availability still pending; do NOT yet tell owner9 can be installed. Build8 remains latest delivered. Hold runtime changes; finish this delivery before new work. All 79 wider gaps retained; rollback server8846cbc and native8 without restoring stale data or replaying uncertain posts.

---

# Social return and slimmer UI candidate — 19 October 2026

Owner confirms Instagram CONNECTS on the iPhone after converting to an eligible professional account. This supersedes earlier pending connection acceptance; no real publishing acceptance is inferred. New request: return to app after every social connection, fewer steps, aligned slim header, remove Studio weekly summary, hide raw account IDs, plain Account rows.

Candidate combines the native identity handoff and provider choice into one screen while retaining cookie-bound explicit confirmation, correct Zova email, both Instagram routes and final exact-profile confirmation. New native client uses Apple ASWebAuthenticationSession HTTPS return on the EXISTING associated /mobile/callback route for all four providers. Per-attempt SHA256 state, exact platform, host/path/query validation; server return requires a signed 20-minute receipt AND the same live native device cookie. Receipt is navigation only; app refreshes server connections, never authenticates from URL. Consumed browser receipts retained at most20 minutes beyond original expiry during sign-in cleanup; unused ticket60-second expiry unchanged. Review binds return receipt to its staged grant; switched parallel attempt cannot capture another review's return. Existing build8 keeps its browser flow (no return opt-in); a replacement TestFlight binary is required for automatic dismissal. Instagram #weblink, scopes and provider callback URLs unchanged.

Shared UI: header controls share a44px aligned baseline; mobile workspace sits below; Your week removed only from Studio, retained in Drafts. Account categories are flat icon/label/chevron rows; all forms/save-error/hash behavior retained. Raw destination IDs removed from review presentation, internal immutable target binding unchanged. Core screens remain white; Account/bridges near-black. Synthetic393px browser preview inspected for Studio, typing and Account expansion; social-proof/studio-header-slim-20261019.png and account-rows-20261019.png. Required full application/PostgreSQL/native checks, deployment and replacement TestFlight delivery still pending. No real grants or posts changed; no charges. All 79 wider gaps retained. Rollback server8846cbc and prior native8, preserving data and ledgers.

---

# Browser confirmation recovery live — 19 October 2026,15:39 BST

Server8846cbc3ef9aa389dabded81e07936e3e021a714 is Live on Render dep-dbb2mmfbtjjs7394qmi0, started15:38:17 BST,50.4s. Public health/login/native-config200. Application39270163640 succeeded490/ 1 skipped each SQLite/PostgreSQL plus dependency/restore/container/exact-scope checks. New repeated-form/device-isolation regressions passed. Native code is unchanged from shipped8; PR native39270163584 also SUCCEEDED. Recovery HTML visually inspected using a loopback-only disposable-account preview; no production auth bypass or test data installed.

Verified public callback settings on live instance using only whitelisted nonsecret environment reads: Instagram redirect is https://zova-social.com/oauth/instagram/callback, client configured, scopes default. No credentials accessed or changed. Rejected repeat-submit matches owner Safari screenshot and production303→403→401 sequence. Recovery removes raw JSON for these browser requests without issuing new cookies or reviving authority. Owner asked for a fresh attempt on8 and whether Instagram shows Allow/permissions versus only its feed. Provider return and final account confirmation remain UNVERIFIED; last inspected hour has no direct Instagram callback. Do not claim the Instagram integration is fully repaired from the browser-recovery tests alone. No new TestFlight build required.

Rollback to39d0d17 / dep-dbb28fc9v7es73aec6sg preserves the browser-only weblink marker but restores the repeat-form expiry defect. No schema/data/connection changes; do not erase records or replay posts. All 79 wider gaps retained.

---

# Browser confirmation replay reproduced; recovery candidate — 19 October 2026

Owner reports progress: can sign into Instagram but stays there; returning/retrying shows Safari raw JSON Browser confirmation expired (15:27 screenshot). Production last-hour logs show native browser POST303 at15:26:22, then POST403 and GET401 at15:26:23. Instagram start302 at15:25:39 but NO Instagram callback in the inspected hour. Do not conflate the proved Zova resubmission defect with an already-solved provider return; no final grant acceptance observed. Asked owner whether Allow/permissions or exact-account Zova review appeared; answer pending.

Reproduced the same403 with a synthetic accepted handoff then resubmitted pre-cookie-change form. Candidate only lets the same already-authenticated active iOS device session resume the used browser ticket by303 to its bounded original connection page. It never redeems again, issues cookies, authorises a different device/user, revives a revoked session or connects/publishes anything. Changed-cookie unused requests remain403 and get a readable account-review link; expired/missing browser GET/POST get readable recovery instead of JSON. Studio/bootstrap one-use semantics unchanged. Tests cover repeat GET/POST, expired consumed tickets, no new cookie, same-user different-session rejection, revocation and unchanged fresh-ticket CSRF. Initial regressions failed against old code; corrected focused3 cases pass. Full required application checks/deployment remain pending. Use build8; no new native build for this server fix. All 79 wider gaps and existing data/grants preserved.

---

# Instagram browser-only authorization link live — 19 October 2026,15:08 BST

Server39d0d17bac09261764ff08e04003d13ddc37f666 is Live: Render dep-dbb28fc9v7es73aec6sg, started15:07:57 BST,53.0s, service live15:08:50. Public health/login/native-config200. Application39265783737 succeeded488/ 1 skipped each SQLite/PostgreSQL plus restore/container/dependency/scope gates. Focused73 tests passed. No new native binary: use installed8 and start a FRESH connection after closing old Instagram/browser attempt.

Only runtime change adds #weblink to the existing direct Instagram authorize URL. Both Instagram's primary AASA and Apple's cached association explicitly exclude this fragment from app launch; captured ignored social-proof/instagram-aasa-20261019.json and instagram-aasa-apple-cache-20261019.json. State, scopes, reauthentication, callback, final exact-account confirmation and both login routes preserved. No account/grant/upload/data/billing changes. Owner says the remaining provider message is “unable to log in, unexpected error occurred”; whether Safari appeared first was not established. Fresh phone/provider acceptance requested and still pending. Do not claim end-to-end success until owner confirms.

Later docs-only native CI39262180007 failed waiting5s for synthetic loopback listener readiness (Cookie listener ready), despite shipped8's earlier39259002240 success. Investigated log; not waived or described as passing. Fresh unchanged-native validation39265906012 SUCCEEDED, including simulator tests and release compilation. No Swift runtime/tests modified in this server correction. Intermittent listener readiness remains a test-harness follow-up; do not claim it was repaired by a rerun. Native8 is already Testing; avoid another signed build solely for this server change. Rollback server to0cb83b2 / dep-dbb1h0ss728c73a2t3m0 preserves all data but removes the browser-only marker.

---

# Build8 phone failure confirmed; Instagram web-link correction in validation — 19 October 2026

Owner confirms updated8 still launches Instagram with the error. Mark normal-browser-only remedy unsuccessful for the actual phone; do not repeat it as a proved fix. Asked whether Safari shows the Zova confirmation/connect page before the app opens; answer pending. No new signup request.

Primary evidence from https://www.instagram.com/.well-known/apple-app-site-association (captured social-proof/instagram-aasa-20261019.json): Instagram's modern components first excludes fragment weblink. OAuth /oauth/authorize/* is excluded but exact no-slash /oauth/authorize is not in that modern list; legacy paths separately exclude the exact path. Current Zova URL lacks fragment. Hypothesis: app-link resolution can send exact OAuth URL to Instagram's broken native page. This is evidence for a targeted correction, not proof of every redirect on the phone.

Candidate adds only #weblink to Instagram's existing authorization URL, preserving endpoint, scope, reauthentication, state and callback. Fragment is separate from HTTP query; no grants changed. iPhone/desktop route tests verify fragment and unchanged permissions/callback; existing mocked callback, ownership, confirmation and native handoff tests retained. No new iPhone binary should be needed for this server URL correction. Full required application gates and deployment must pass; owner device/provider retest remains required. No phone-success claim before acceptance. Previous0cb83b2 is rollback, with the known failing app handoff.

---

# Replacement iPhone beta8 released — 19 October 2026,14:39 BST

Zova Social0.1.0(8) is now **Testing** in the existing Zova Social Internal Beta group with1 tester. Apple build4c7fd194-4007-4da5-b766-b23639c4375f. Signed source0cb83b2; Codemagic6ad61b167550aed81090246d finished3m21s, upload accepted14:36:31 BST. Apple processing completed and group assigned around14:39 BST. Focused What to Test notes saved for browser Instagram return, exact Zova email, account switching, light core/dark Account and typing layout. Owner told to update to8 and retry Instagram. **Physical Instagram acceptance is still pending**; do not claim the provider loop is fixed on the phone merely because build8 is available.

Native validation39259002240 succeeded16 unit tests, 1 UI test and release compilation. Application39258328505 succeeded487/ 1 skipped on both SQLite/PostgreSQL plus restore/container/scope/dependencies. Server0cb83b2 was already live; no new server/data/schema/grant/publishing/billing changes for this native release. Both Instagram routes and existing account separation preserved. Other social providers keep their previous browser flow. Separate Zova Market remains untouched.

Rollback native by making prior7 available from the existing group if needed; it restores the known failing embedded Instagram flow, so keep the Safari workaround. Do not erase user data or replay unknown posts. All 79 broader beta gaps retained. The historical delivery-blocker notes below are superseded by this receipt.

---

# Replacement iPhone signing request accepted — 19 October 2026,14:29 BST

Owner's “See now” showed the actual branch list in Codemagic. Selected codex/ios-beta-20261019 and Zova Social internal TestFlight workflow, started the build under existing authorisation. Receipt: https://codemagic.io/app/6ad5cbbeadaac76a4f1f8525/build/6ad61b167550aed81090246d. Overview confirms index7, Mac mini M2, correct branch and exact validated commit0cb83b2. Build finished3m21s; publishing log confirms Zova0.1.0(8), com.zovasocial.app, UPLOAD SUCCEEDED with no errors at14:36:31 BST, delivery4c7fd194-4007-4da5-b766-b23639c4375f. Apple Build Uploads shows8 Processing. Do not start duplicates. No new credentials/permissions/paid resources. Still must observe Apple processing and internal group assignment before telling owner to update. Build7 remains latest available to test until new evidence.

---

# Instagram still fails after new signup — 19 October 2026

Owner's14:22 screenshot shows Instagram's native loading skeleton and “Something went wrong” after a successful new Zova signup. The account mismatch does not explain this remaining failure. Do not ask for another signup or claim switching email fixes Instagram. New account identity has not been supplied.

Exact native candidate0cb83b2 passed39259002240:16 unit tests,1 welcome UI test and release iPhone compilation. Normal-browser Instagram routing is implemented but still NOT delivered to the phone. Application39258328505 passed487/ 1 skipped on each database plus release gates. Server0cb83b2 remains live; TestFlight7 remains latest delivered binary.

Codemagic still cannot load branches/workflows. Refreshed same public repo using equivalent URL without .git, with no improvement; restored original URL. No signing/access/billing changes or new signed build. Asked owner to try Start new build in normal laptop browser and select codex/ios-beta-20261019, never main; answer pending. This may distinguish a side-browser failure; do not assume it will resolve the service error.

Interim owner path: normal Safari on iPhone, zova-social.com, intended Zova login, Account / Social accounts / Connect Instagram. Earlier owner tests succeeded there, but current provider retest is still required. If it fails there too, investigate provider request/account/logs rather than assuming embedded browser alone. Preserve all users/data/uploads/grants and both Instagram routes.

---

# Latest owner correction and iPhone account mismatch — 19 October 2026

**Theme source of truth:** Studio, Drafts and Performance must be plain light/white. Account and connection/sign-in intermediary pages stay near-black/violet. This overrides earlier global dark entries below. Live server72ad0573da850fb472c6b47bea6966f9e06d7223, Render dep-dbb1a7ff3r2c73fth8j0,14:03:25 BST. Live core3 white and connection page dark inspected. Application39256612072 passed485/ 1 skipped on both databases plus release checks. Native light/dark conditional source is committed; validation39256385114 pending at this entry.

**New owner evidence:** native handoff offers an email the owner says is not theirs. The prompt obtains it from the bearer device session's User record, never the browser cookie. Do not presume this establishes cross-account leakage or a typo. Owner confirmed the correct Zova email is david.wilson92@hotmail.com. The displayed .org address is not theirs. Read-only production lookup confirmed two distinct active records: .com created29 August, no active native sessions; .org created14 September with active native sessions and19 October sign-in. Neither email is verified. This confirms the phone is authenticated to the .org record, but does NOT prove who created it. No identity/data/grant changes made; asked owner to sign out and authenticate .com. Never rename/merge without verified ownership. Do not change emails, merge accounts, transfer drafts/connections or approve this identity. Instagram screenshot shows native Instagram loading skeleton before callback; phone still runs7 with the old embedded browser route. Normal-browser Instagram fix remains undelivered because existing Codemagic cannot load branches/workflows. No successful new binary upload. Do not tell owner to install8.

**Latest candidate:**0cb83b2f539f57eeec0fddfa19293fa52445f20e (account description only after10e73e1); application39258328505 SUCCESS (exact0cb83b2); duplicate39258321150 status not used. Native39258138958 cancelled by PR concurrency, not a pass; clean exact-candidate manual run39259002240 started0cb83b2; older39256385114 cancelled, not a pass. Codemagic apps/start-build retry still shows loading branches/workflow plus generic service error; no signed upload. Account preview inspected with synthetic creator@example.test; email and sign-out visible above all groups. Evidence social-proof/account-identity-local.png. Identity changes0cb83b2 are LIVE: Render dep-dbb1h0ss728c73a2t3m0 at14:17:55 BST,55.7s. Internal/live succeeded14:18:50; brief routing502 during startup resolved, public health/login/native-config200 and signed-in Account reloaded successfully. Email/Sign out visible above groups, existing browser test account david1@gmail.com and social statuses unchanged. This is not acceptance of owner phone .com sign-in. Correct email confirmed by owner: david.wilson92@hotmail.com; no credential or identity changes authorised by this confirmation.

**Bounded account recovery candidate:** browser handoff explicitly distinguishes Zova from Instagram identity; wrong-account action consumes only this one-use ticket without accepting it, issuing a cookie, changing browser/native identity or revoking grants. Instructions return to app Account/sign out. Account email and existing Sign out moved outside collapsed categories. Future native login requests an ephemeral auth browser so Safari's remembered Zova identity is not inherited. Existing browser proof, owner/purpose/session/replay protections retained. Focused synthetic tests42 passed, including two-account cancellation/no-cookie/replay and wrong-purpose cases. Native validation and full application checks must finish before release claims. User's real account identity and actual phone/provider flow remain unverified.

**Rollback:** previous72ad057 retains light-core preference and is the rollback for current0cb83b2. Account recovery candidate has no migrations; revert its bounded code changes to72ad057 if necessary. Never restore stale customer data or resend unknown publications. All 79 wider beta gaps remain. TestFlight7 is still the only delivered beta. Preserve separate Zova Market, all users/data/uploads/grants, both Instagram routes, explicit posting approvals and disabled charges.

---

# Dark product UI live; iPhone Instagram update validated but signing blocked — 19 October 2026

**Website/shared screens:** a4070430496338c70b44d8132fb4a2023ef6049d is deployed. Render dep-dbb0ipijnfac739e8dug,19 October13:13:26 BST,51.9s. Earlier9b13289 deployment dep-dbb0gjff3r2c73fqkv10 also succeeded. Public health/login/native-config200; deployed night CSSv20261019-3 and Account JS match the reviewed files. Live signed-in Studio, Account, Drafts and Performance inspected; no messages, posts, grants or customer settings submitted. Auto-Deploy remains off; main is older.

**Delivered UI:** black/violet product palette replaces pale/pink gradients; Account is five expandable categories (details, voice, socials, security/privacy, plan/help). Hash links and save errors open the correct category; voice saves return to open preferences; native socials-only refresh still preserves unsaved settings. Studio has + New post beside Zova, smaller Next move, compact workspace/header, clearer composer prompt. Welcome hides on focus; mobile weekly summary hides while typing. Existing conversation, drafts, uploads, approvals and billing testing settings preserved.

**Phone acceptance:** owner screenshots show Studio loaded in build7, so the earlier bootstrap blocker is accepted as repaired on the phone. Do not ask again whether7 opens Studio. Instagram remains unverified: direct connection starts302 at11:14,11:31,11:42 BST, with no direct callback in the inspected four-hour logs. Asked owner for the stopping screen/error. No token exchange failure was observed. New native implementation opens the same bounded, purpose/session-bound Instagram handoff in the normal browser, where the owner previously reported success, and refreshes connection presentation when the app becomes active. Other platforms keep their existing sheet. No grant reset, reauthentication removal or approval bypass.

**Native candidate:**8d602a5674592c0625e9ca8e62a6d04fcc0a0146 adds the normal-browser route and dark native canvas/status appearance with readable violet links. CI39250881721 **success**:16 unit tests,1 welcome UI test, release compilation. New Instagram routing test passed; real WebKit cookie bootstrap/error/export tests retained. Simulator welcome screenshot reviewed; its build1 label is a simulator build, NOT a new TestFlight release. Application39250888058 success485 passed/ 1 skipped each SQLite/PostgreSQL, plus backup restore/container/dependencies/exact scope. Deployed a407043 also passed39250027919 with the same counts; native-only palette tweak does not require another web deployment. Superseded/duplicate native jobs were cancelled, not counted as passes.

**Remaining delivery blocker:** Codemagic's existing app6ad5cbbeadaac76a4f1f8525 cannot load branches/workflows and shows “Oh no! Looks like something broke down.” Reproduced via settings, last build and Applications/start-build after refresh. No new signed build was started/uploaded. **0.1.0(7) remains the latest delivered TestFlight build**; do not tell the owner to install8. Resume in existing Codemagic app when service recovers; select codex/ios-beta-20261019/current reviewed source, reuse zova-social-testflight profile, existing distribution certificate and zova-testflight Apple integration. No secrets exported, new auth grants or paid resources created to bypass this. Upload/internal group assignment and real iPhone Instagram/keyboard retest remain. Interim owner option: connect through the regular browser on zova-social.com and reopen the app; do not claim this has just been retested.

Evidence under ignored social-proof/: instagram-precallback-attempts.txt, codemagic-branch-loading-block.png, dark-release-preflight.json, account-dark-live.png, studio-dark-live-focused.png, drafts-dark-live.png, performance-dark-live.png, ios-dark-validation/ios-test-attachments/. Updated feature matrix and docs/IOS_BETA_READINESS_20261019.md distinguish implementation, tests and delivery. PR34 remains draft; not commercial certification. All 79 wider beta gaps retained.

**Rollback:** redeploy pre-update2bce283476563ef399f1afe413aee40abe2e65c2 / dep-dbaulsrrjlhs73aorpsg and keep build7. No migrations in this update; do not drop tables, restore stale writes or replay pending/unknown publications. Existing users, PostgreSQL, uploads, encrypted connections, both Instagram routes, explicit approvals and disabled charges remain.

---

# iPhone feedback: dark product theme and grouped Account — 19 October 2026

Owner screenshots now show Studio loaded on the phone: build7 bootstrap acceptance is observed. This does not verify social connections or every native feature. New bounded candidate: shared near-black/violet product theme, grouped Account settings with deep-link/save-error reveal, + New post beside the brand, compact Next move/header, hero hidden on composer focus and mobile weekly summary hidden while typing. Native shell/background/status appearance also changes to dark; needs a replacement TestFlight binary. Existing forms, workspace links, native socials-only refresh, drafts and immutable approvals preserved.

Instagram remains an open provider journey defect, not falsely resolved. Production logs show /connect/instagram200 then /oauth/instagram/start302 at11:14,11:31 and11:42 BST, **no callback** in the four-hour inspected window. This narrows the observed failure to before return to Zova; no token-exchange failure is evidenced. Asked owner where it stops and the displayed message. Do not disconnect accounts, change grants, remove reauthentication or weaken state/session protections to guess at a fix. Real phone/provider retest still needed.

Validation in progress:45 focused Python tests passed;5 Node native/account/focus cases passed, syntax and diff checks clean. Synthetic loopback phone previews used disposable SQLite/users and no provider keys. Preview helper under ignored social-proof is local only, not product source. Exact application/PostgreSQL and native CI, deployment and new TestFlight status must be recorded before release claims. All 79 broader gaps remain tracked. Rollback runtime to2bce283 / dep-dbaulsrrjlhs73aorpsg; build7 remains previous native binary. No migrations or customer data changes.

---

# Replacement iPhone beta7 released; phone acceptance pending — 19 October 2026

Owner confirmed build5 installed and failing. Do not repeat the version5 question or claim its origin-header patch fixed the phone. Production logs confirmed /mobile/web-session403 after build5. Exact device header mismatch was not captured; the new implementation removes the failing WebKit POST rather than claiming the simulator reproduced every phone condition.

**Zova Social0.1.0(7) is now Testing** in the existing private group with1 invitation. Apple UUIDdf822ba2-979a-4de9-aa56-481774dbab71, uploaded11:06 BST. Signed source2bce283476563ef399f1afe413aee40abe2e65c2; Codemagic6ad5ea777550aed81090148a uploaded successfully. Build6 failed compilation before upload;7 is the intended replacement. Owner asked to Update, fully close/reopen and confirm Studio. Actual phone acceptance is still pending; no unsupported working-device or commercial-ready claim.

Production2bce283 is Live on Render dep-dbaulsrrjlhs73aorpsg (11:03 BST,1m09s). Native URLSession redeems an owned, active, one-use ticket with bearer at /api/v1/native-web-session; receives one Secure/HttpOnly session cookie and a bounded destination. Swift validates and installs the cookie in WKHTTPCookieStore before a plain GET /studio. No access/refresh token enters WebKit or a URL. Existing session/purpose/owner/version/expiry/replay/revocation checks and browser origin protections remain. Legacy clients/browser handoffs preserved. Actual Coordinator rejects generic/HTTP JSON error documents without hiding JSON file exports; welcome shows build number.

Validation: application39234304434 and test-only39235234636 green,483 passed/ 1 skipped each SQLite/PostgreSQL plus restore/container/dependencies/scope. Native39235234656 **success**,15 unit tests including real cookie-first GET and production error/export policy,1 welcome UI test and release compilation. Test-onlyb10bd55e701dd03b4acdab13b86ce579fef37fe6 corrected the URLProtocol harness to read streamed bodies; production Swift and project settings exactly match build7 source2bce283. Earlier harness crash was not waived. Public health/login/signup/config200; native-web-session without bearer401/no cookie. Proof: social-proof/ios-native-cookie-live-preflight.json, native-cookie-ci-tests.txt, native-cookie-bootstrap-live.png, testflight-build7-testing.png.

No customer/profile/draft/upload/social grant changes or real posts/charges. Existing79 beta gaps retained; separate Zova Market app untouched. Draft PR34 remains pending physical acceptance. Read docs/IOS_BETA_READINESS_20261019.md. Rollback server to a9398b2 / dep-dbau7ce1egvs73c5jfsg if needed (preserves data but new app bootstrap route then unavailable); no schema rollback. Auto-Deploy remains off while main is older. Do not deploy broad PR28.

---

# Confirmed build5 device blocker; native cookie bootstrap in validation — 19 October 2026

Owner explicitly confirms0.1.0(5) installed and still sees raw origin-protection JSON. Do not ask for the build number again. Production logs show POST /mobile/web-session403 at10:46:07,10:46:31 and10:49:22 BST after the first repair. Exact device header mismatch is not captured, so do not pretend the simulator reproduced every phone condition. Existing build5 is not accepted as working.

New candidate2bce283476563ef399f1afe413aee40abe2e65c2 replaces the app's WebKit POST bootstrap: native URLSession uses bearer+one-use owned ticket to redeem /api/v1/native-web-session, parses the one Secure/HttpOnly cookie, installs it in WKHTTPCookieStore, then loads ordinary GET /studio. Access/refresh tokens never enter WebKit. Cookie remains bound to the originating revocable session; endpoint rejects web-cookie-only authority, wrong session/purpose, expired/reused tickets and cross-origin requests. Legacy WebKit/browser handoffs remain compatible; no origin protections removed. Actual Coordinator now rejects JSON even if response is not HTTPURLResponse, and cannot mark /mobile/web-session ready. Visible welcome build label added.

Local38 handoff/lifecycle tests passed before final single-cookie header adjustment. Application39234304434 passed483/ 1 skipped on both databases plus release checks. Native39234291707 exposed a forced unwrap in the new test harness reading URLProtocol.httpBody (iOS supplies httpBodyStream), not product code; corrected test-onlyb10bd55. New native39235234656 is running; application39235234636 is green. Production iOS source is unchanged between2bce283 andb10bd55. Earlier native compile caught a SwiftUI version-label type-check error, fixed4b03567; export attachment compatibility protected2bce283. Replacement signed iPhone build started in existing Codemagic account; capture actual new build URL/status before claims. Production2bce283 is now Live, Render11:03 BST/1m09s, public health/login/signup/config healthy; native-web-session without bearer returns401 with no cookie. See social-proof/ios-native-cookie-live-preflight.json. The first signed replacement attempt6 failed on the version-label compile error before upload. Corrected signed build7 uploaded successfully (Codemagic6ad5ea777550aed81090148a), Apple UUIDdf822ba2-979a-4de9-aa56-481774dbab71, Ready to Test but not assigned while the final native run is pending. Build7 code is2bce283; test-onlyb10bd55 does not require another binary. Need full native cookie-first GET and production Coordinator tests, exact application/PostgreSQL/restore/container/dependency checks, then deploy and assign processed replacement to private group. Owner phone retest required; no unsupported success claim.

---

# iPhone Studio handoff repair released — 19 October 2026

Owner's build4 screenshot exposed a real initial-navigation403, not an installation failure. **Replacement Zova Social0.1.0(5) is now Testing**, manually assigned to Zova Social Internal Beta with1 invitation. Apple build UUID77e6529f-aefc-4d7c-bb30-441e60f069ff; signed source671bbdd8df5e1324158391db63053d6be84b9149. Production native sources are identical in latest test-onlyb9dcd32. Ask owner to Update in TestFlight, fully close/reopen and confirm Studio. Physical-device confirmation is still pending; do not claim it already works on the phone.

Backend a9398b2f8a7718f372c7bdfdffc4534aa9d60f6e is Live on existing Render service (10:32 BST,53.4s). Scoped fix: non-simple native header on initial one-use ticket POST; opaque origin allowed only for this exact marked exchange. Hostile concrete origins, unmarked opaque requests and unrelated mutations remain blocked. No CORS grant. Ticket expiry/purpose/ownership/revocation/replay checks preserved. iPhone intercepts HTTP errors instead of rendering raw JSON.

Required checks completed: native39231451448 **success**,12 unit tests including actual WebKit network POST/header/body/303/session-cookie (4.401s),1 welcome UI test and release iPhone compilation. Application39231451464 **success**,480 passed/ 1 skipped each SQLite/PostgreSQL; restore/container/dependency/scope gates passed. Earlier loopback compile/timeout attempts failed and were corrected, not waived. Live probes in social-proof/ios-webkit-origin-live-fix.json; actual WebKit evidence ios-webkit-ci-network.txt; Apple release screenshot testflight-build5-testing.png. No user/social/upload data changes, no posts/grants/charges. All 79 broader gaps retained. Draft PR34 remains pending device acceptance.

Read docs/IOS_BETA_READINESS_20261019.md for full matrix/history. Rollback server to f47e1be preserves data but restores the known old-client origin blocker; no schema rollback. Do not deploy broad PR28 or enable Auto-Deploy while main remains old. Do not overwrite separate Zova Market app.

---

# iPhone beta first-device blocker — 19 October 2026, 10:24 BST

Owner installed build4 and reported all tabs showing JSON403: Open Zova directly and try again. This is a confirmed release blocker; build4 availability was not proof of working Studio. Reproduced public POST /mobile/web-session with opaque Origin:null; SecurityMiddleware blocks the initial WebKit navigation before consuming the one-use ticket. Fix541ca62 adds a non-simple X-Zova-Native-Handoff:1 header to the native request and allows opaque origin only on the exact POST ticket exchange with this marker. Explicit hostile origins and all other routes stay protected; CORS not enabled; actual one-use,60s, purpose/session/owner checks remain required. Native now intercepts HTTP errors instead of rendering raw JSON.

Candidate671bbdd8df5e1324158391db63053d6be84b9149 adds a real WebKit loopback POST/redirect-cookie integration test. Local35 native handoff/lifecycle tests pass, including reproduced failure, fixed exchange, replay and hostile-origin boundaries. Required hosted validation39230191672/application and39230191657/native is running. New signing/upload job https://codemagic.io/app/6ad5cbbeadaac76a4f1f8525/build/6ad5e2be7550aed81090123e started. Do not distribute a new build until actual WebKit test and release checks pass; do not call the device issue fixed until owner retests the updated build. Production is now a9398b2 / Render Live,53.4s; public synthetic probes verify marked opaque-origin exchange reaches401 ticket validation, unmarked/hostile remain403 and no CORS grant. Apple processed build5 UUID77e6529f-aefc-4d7c-bb30-441e60f069ff (native source671bbdd; later commits change tests only). It is Ready to Test but not assigned to the group yet. Actual WebKit loopback test compiled but timed out during cold startup; timeout/diagnostics corrected in test-only252a1c3/b9dcd32. Await latest native run before distribution. Do not treat incomplete loopback checks as passing.

---

# iPhone internal beta available — 19 October 2026

Zova Social 0.1.0 (4) is uploaded, processed and **Testing** in App Store Connect. Private group Zova Social Internal Beta has one tester, David Wilson, invited at 10:08 BST. Apple app ID6824416979 / bundle com.zovasocial.app / team7B4W8RN6GX. This is separate from Zova Market: never overwrite that app. Native binary source16fbb9a8e168d774a130f5cecfcc266928960141; build UUIDe5b9c889-61cb-463a-b0b0-fb3cdfe744ef. Build3 is not distributed. Owner authorised registration, signing and internal upload; no public App Store submission.

Current worktree: C:/Users/david/.codex/.chatgpt-projects/g-p-6a8a0aa881c88191a2835a8d53316369/zova-ios-beta, branch codex/ios-beta-20261019, draft PR34. Read docs/IOS_BETA_READINESS_20261019.md first for evidence, feature matrix and rollback. Backend candidate f47e1be540f167f6bf6594318dde56f3a107d822 includes the final native Account refresh preserving unsaved edits; Render deployment dep-dbats96q1p3s73d3c2ig reports Deploy succeeded | Live, duration46.9s, verified at10:11 BST. Its native tree matches build4. Main remains older; specific-commit deployment disabled Auto-Deploy deliberately. Do not enable it blindly or deploy broad PR28.

Exact f47 checks green: application CI39225907537 and39225914327, native CI39225914321. Application476 passed/ 1 skipped on SQLite and PostgreSQL; synthetic backup/restore, container, dependencies and release guardrails passed. Native11 unit tests,1 welcome UI test and release compilation passed; JS native refresh3 tests passed. Initial Apple upload exposed an iPad orientation mismatch; fixed explicit target family and added actual IPA metadata regression gate. Later build4 is Apple's accepted final build.

Production native flag, exact callback and Associated Domains are configured. Verified existing web account and Facebook/TikTok/X connections remained intact; Instagram is not connected in that checked account. No social grant or post changed. Render database recovery shows3-day PITR and a completed logical export created09:03 BST; no production restore or data download. Physical iPhone sign-in, Studio/media/keyboard/VoiceOver/provider-return checks remain pending user installation. All 79 wider beta gaps retained; no commercial certification, charges or subscription enforcement.

---

# TikTok public-access audit submitted — 18 October 2026

Owner approved the final Direct Post audit declarations. Accepted the three displayed declarations and submitted the prepared audit for app7672846663509215253 with the reviewed3m51s/4.65MB merged video. TikTok explicitly confirmed: “Your Application to request access to Content Posting API has been submitted!” It states an expected response in2-4weeks and directs checking Manage apps for status. Evidence: social-proof/tiktok-final-1810/audit-submitted.png and audit-submitted.txt. This is submission confirmation, not approval.

Both outstanding requests are now submitted: app revision/video.publish is In review; separate Content Posting API public-access audit is submitted. Await TikTok decisions. Production remains inbox-only; do not activate Direct Post or infer scope upgrade from submission. After both required approvals, verify live permissions, reconnect for video.publish with the account owner's consent, and run a specifically authorised public publishing test before controlled rollout. No real post, production deployment, grant change, billing or iOS rollout occurred in this submission step. All 79 broader gaps retained.

---

# TikTok review package and app submission — 18 October 2026

Owner authorised merging/trimming/compressing the main v2 recording and the commercial-content addendum, final review, and submission. Final video: C:/Users/david/Videos/Zova TikTok Direct Post - review package 1810.mp4; 231.37 seconds, 4,648,050 bytes, 1920x960 at15fps, AAC audio retained. SHA256 eb082a3f43bcf0338a8ed96f379acd979af713e822f2aacd798c9c5ca2097a72. Full video/audio decoding passed; key scenes and boundaries visually reviewed. Kept main0-112s,123-190s,202-221.166633s;4s labelled supplement transition; addendum49-78.207979s. Cuts remove waiting/repeated drafting; no fabricated provider outcome. New recording supplement starts3:22. Local evidence/manifest under social-proof/tiktok-final-1810/.

App7672846663509215253 production revision successfully SUBMITTED and portal shows In review. New combined video attached; old approved inbox recording retained to evidence existing video.upload. Notes explain video.publish, Login Kit/user.info.basic, separate test host, private test outcome, commercial controls, production inbox-only until approval and no native iOS submission. Callback, existing scopes and production service were not changed. Website/legal pages and sandbox signup/login each returned200. No new real post. Actual reviewer-account login and reviewer TikTok sandbox allowlisting have not been tested; notes truthfully state that Direct Post testing requires a registered sandbox tester and do not invent credentials or claim unrestricted reviewer access.

Separate Content Posting API public-access AUDIT is fully populated with the new video and code-checked database field description, but NOT SUBMITTED. Browser tab13 is at Review with all three legal declarations unchecked. Owner has been asked for action-time approval to accept Developer Terms/Production-use compliance, exemption of TikTok reviewer access from Zova terms/policies, and truthful facts declaration. Await reply; do not claim audit submitted or TikTok approved. Draft form persistence across closing/reloading is not guaranteed; local audit-review.txt and audit-declarations.png preserve answers. Existing app review tab12 shows In review. Maintain those tabs for continuation.

After owner approves declarations: tick the three checkboxes on the audit Review page, continue submission, verify an explicit receipt/success state, capture screenshot and update this handoff. If another legal declaration or CAPTCHA appears, use the required action-time confirmation. No charges, public posting, production-mode switch or iOS rollout authorised by submission. All 79 beta gaps remain tracked.

---

# Sandbox publication verified — 18 October 2026, 21:17 BST

Owner requested “Publish updates”. Deployed exact tested runtime 1bd3b9486ea79c82413978c07e7d82a4c26ef52c to zova-tiktok-sandbox only (srv-d9u4joad0e5s73afpu10). Render deployment dep-dbaiictg1s2s73c85sf0 reports Deploy succeeded | Live, duration37.6s. Independent release preflight confirmed exact-commit CI39161889443 green, documentation-only HEAD and all79 known gaps retained. No production deployment, real social post, grant, billing change or native rollout.

Before restart, saved read-only draft1/publication-1 UI text and screenshot under social-proof/sandbox-publication-1-before-1bd3b94.{txt,png}. It still showed Outcome unconfirmed; no authoritative receipt was recoverable from this UI. This preserves visible evidence, not a database/uploads backup. Do not resend or reinterpret that submission. Sandbox SQLite/uploads remain ephemeral.

Post-deploy checks: /health and /login return200; all four versioned Studio assets (studio.js, studio-state.js, studio-publish.js, studio-design.css?v=20261018-media) match the exact tested candidate after newline normalization. Browser refresh of sandbox Studio returns the sign-in screen, so no new signed-in/model/provider result is claimed. Prior tests:440 passed/ 1 skipped each SQLite/PostgreSQL plus restore/container/dependency/frontend and scope gates; synthetic desktop/mobile attachment evidence retained. Local release evidence: social-proof/sandbox-release-1bd3b94.png and sandbox-release-1bd3b94-checks.json.

Next: owner signs in again and tests a fresh caption/video draft; sent video should appear on the user conversation turn with an empty composer. Sandbox permits private Only me testing; third-party paid partnerships remain unavailable pending TikTok approval. Do not resend old unknown publication1. Keep production inbox-only unchanged. Operational callback-query log redaction and all79 wider gaps remain tracked.

Rollback: manually deploy exact2fa13f72009fa4629129070c14b8e15fa9f73631 to this sandbox only. No schema rollback; older code ignores additive message/retry metadata. Preserve durable receipts and unknown outcomes; never replay submissions. A sandbox restart can reset temporary users/uploads/connections again.

---

# Sent media, first-caption creation and TikTok outcome repair — 18 October 2026 (pre-release evidence)

Branch codex/studio-media-tiktok-results-20261018 builds on deployed sandbox 2fa13f7. Owner reported publication-1 unconfirmed after commercial disclosure and video remaining in composer. Live sandbox draft1 remains needs_review/unconfirmed; the old adapter discarded the underlying exception and receipt details, so its exact cause cannot be recovered from the existing result. Never reclassify it as failed or resend without authoritative evidence. No provider post was sent during this work. Owner subsequently signed in: live draft2 showed “Post this shlop” followed by “Create a draft first…”, reproduced and now handled by proposing a first caption (never implicit publication or agreement).

Sent attachments now live on the user turn with playable previews, while workspace active media remains the authority for AI/review/publishing. Server rebuilds previews from owned same-brand records; client URLs are ignored. Removal from the active post retains historical preview; deleted uploads show unavailable. Additive conversation/retry metadata only; no migration. Changed media/source link blocks retrying an old request silently against new content. Synthetic desktop1280x720 and mobile390x844 showed no composer video after send/reload, retained playback, no horizontal overflow; mobile composer196px. Screenshots: social-proof/studio-sent-attachment-desktop-20261018.png and studio-sent-attachment-mobile-20261018.png.

TikTok adapter now records pre-send, requested, rejected and accepted receipt stages. Documented explicit init rejection becomes Failed with an allowlisted explanation; timeouts/ambiguous responses stay unknown. Receipt-bearing interrupted work is reconciled without resend. Conditional updates bind checkpoints, recovery and poll completion to the exact reviewed attempt; late workers/status responses cannot overwrite or send a replacement attempt. Worker recovery preserves receipts and does not let old receiptless unknowns starve pending work. Known processing failure reasons are safe mapped messages; raw provider errors/tokens are not retained.

ZOVA_ENV=sandbox now makes its private-only restriction explicit in settings and server validation, even when creator_info lists wider choices. Own-brand promotion differs from third-party paid partnership: the latter requires Everyone/Friends and cannot be sent from this unaudited test app. Provider options remain displayed without a default; unavailable test choices are disabled. Approval remains external; no grant/audit/production changes. Production stays inbox-only; native branch remains undeployed. All 79 wider beta gaps retained. Live access logs still include OAuth callback query strings; preserve the operational redaction follow-up without copying credentials into evidence.

Runtime candidate 1bd3b9486ea79c82413978c07e7d82a4c26ef52c is pushed. Hosted CI39161889443 passed all required jobs:440 passed/ 1 skipped each on SQLite and PostgreSQL, synthetic backup restore, container build/smoke, frontend planning/lifecycle checks, dependency audit (no known vulnerabilities) and exact beta scope. Independent review caught and closed three publication concurrency races; their interleaving regressions pass. The exact “Post this shlop” owned-video API/client case creates a caption with zero review/publication/schedule records. A final extra browser screenshot for that phrase was unavailable because CUA returned no browsers; the earlier attachment desktop/mobile visual evidence remains valid. No new live-model/provider result is claimed.

At validation time sandbox remained2fa13f7 / production unchanged; see the release record above for deployment. Sandbox SQLite/uploads are ephemeral. Rollback for this candidate is exact2fa13f72009fa4629129070c14b8e15fa9f73631; older code ignores additive message-media and retry snapshot JSON. Preserve receipts and never replay unknown submissions.

---

# Sandbox release verified — 18 October 2026

Owner requested publish. Deployed exact runtime 2fa13f72009fa4629129070c14b8e15fa9f73631 to the existing Free TikTok sandbox only. Render deployment dep-dbai30rrjlhs73akkom0 reports Deploy succeeded | Live (18 October, 20:44 BST). Required hosted CI39146945668 passed on that exact commit: 359 passed / 1 skipped each on SQLite and PostgreSQL, synthetic restore, container build/smoke, dependency audit and exact beta scope. Independent release review confirmed the bounded change set and all 79 known gaps retained.

Post-deploy checks: /health and /login return 200; versioned studio-state.js and studio-design.css match the tested candidate after newline normalization. Browser /studio correctly redirects to sign-in with no active sandbox session; the signed-in/provider path was not repeated after deployment. Pre-release synthetic desktop/mobile/reload/retry/keyboard/fork checks remain the functional evidence. Local evidence: social-proof/sandbox-release-2fa13f7.png and sandbox-release-2fa13f7-checks.json.

Production zova-social.com remains unchanged and TikTok inbox-only. No real social post, grant, billing change or native rollout. Sandbox remains isolated and ephemeral, auto-deploy Off; it may need a fresh Zova login and TikTok connection. Public Direct Post approval/audit remains pending; private sandbox cannot publish a paid partnership. Do not resend old test drafts. Next: owner signs into the sandbox and retries the paid-partnership caption/review demonstration with a new draft; acceptance/public posting restrictions remain in place.

Rollback: manually redeploy sandbox 89e7cf716d82f358d52515b58313862f0258c7eb. No schema migration; older code ignores pending_message metadata. Preserve any receipts/evidence before a restart, never point sandbox at production storage or replay posts. Source branch is codex/studio-send-recovery-20261018; the Render configured branch remains codex/tiktok-recording-sandbox-20261016 with auto-deploy Off, so future releases must select the intended exact tested commit.

---

# Studio sent-message and TikTok drafting correction — 18 October 2026 (pre-deployment evidence)

Branch codex/studio-send-recovery-20261018 addresses two owner-reported defects: sent ideas remaining in the composer and TikTok-only sponsor/paid-partnership drafting incorrectly demanding an X version. Planner targets now follow the actual selected/active caption and create a first version when no caption exists; sponsor URLs are content, not destination changes. Sent text moves into the conversation before planning; failed requests have a separate Retry message control, retain attachments and unsent new input, survive reload, and do not duplicate the user turn. Initial save failure keeps input in place. Late replies remain workspace-bound. Pending-message metadata is additive; no schema migration.

Synthetic browser checks: exact screenshot request produced a TikTok caption, empty composer persisted after reload; 390px mobile failed generation/reload/keyboard retry succeeded with one user turn, no horizontal overflow. Evidence locally under social-proof/studio-sent-tiktok-20261018.png and studio-retry-mobile-20261018.png. Model/providers mocked; no real post, grant, charge or production data changed. Local full suite: 359 passed / 1 skipped. Client lifecycle and planning/scheduling suites passed. Successful generation now clears pending metadata atomically; new-draft forks preserve source state and copy transcript/media/link/composer into the new row, guarded by ownership, status and revision. Synthetic browser verified reopening the old draft does not offer a stale retry. Runtime candidate 2fa13f72009fa4629129070c14b8e15fa9f73631 is pushed; hosted CI39146945668 passed all required jobs: synthetic tests, PostgreSQL tests, synthetic restore, container build/smoke, dependency audit and exact beta guardrails. Not deployed; sandbox and production remain unchanged.

Commercial-disclosure tests verify existing own-brand/paid selection, label/declaration changes, consent reset, private-paid rejection and immutable options. Sandbox remains unaudited/Only me; an actual paid-partnership post cannot use Only me. Demonstrate controls without publishing; public-access audit approval remains required. Production stays inbox-only, Instagram unchanged, native branch not deployed. All 79 broader beta findings retained.

Rollback: revert this bounded candidate or redeploy sandbox runtime 89e7cf716d82f358d52515b58313862f0258c7eb. Preserve data, uploads, sessions, connections and publication receipts; never resend prior tests. Old code ignores pending_message JSON. Free sandbox storage remains ephemeral; no deployment was requested in this update.

---

# Sandbox release verified — 16 October 2026

Owner requested publish. Deployed exact89e7cf716d82f358d52515b58313862f0258c7eb to existing Free TikTok sandbox only. Render dep-db9819ff3r2c73afr1p0 reports Deploy succeeded|Live. CI38957921987 passed all gates:319passed/1skipped each on SQLite/PostgreSQL, synthetic backup restore, image build/smoke, dependency audit and exact beta scope. Public health/login200; deployed studio-publish.js, studio-state.js, readiness.js, studio-design.css and studio.js match local candidate byte-for-byte after newline normalization. Evidence social-proof/sandbox-release-89e7cf7.png.

Production zova-social.com unchanged and inbox-only. No real social post, new grant, billing change, or native deployment. Owner may need fresh sandbox login/TikTok connection because SQLite/uploads are ephemeral. Never resend previously published draft1. Sandbox rollback is7fdec1573a004bd28d79ee0e54c0628461969247, without restoring production data or replaying posts. Next: owner can record the cleaner caption/review flow, verify the actual private TikTok post, then prepare truthful approval evidence. Public Direct Post approval still pending;79 wider beta gaps remain.

---

# Studio clarity and TikTok result refresh — 16 October 2026

Current local changes address the owner's recording feedback: caption-first creation/rewrite without media-observation narration, explicit Edit caption (Story retains Edit planning notes), compact composer and collapsed composer during review, readable TikTok privacy labels, automatic read-only publication checks every15seconds for up to10minutes, and public TikTok links when the provider returns a real public post ID. Private sandbox posts accurately show Published without manufacturing a public link. Polls are draft/workspace-bound, terminal results stop polling, and background checks do not move focus. Backend GET and worker share throttled receipt reconciliation; unknown outcomes are never resent. Existing Instagram logic is unchanged.

Validation: full local SQLite suite319passed/1skipped; Node lifecycle/polling/media-summary checks passed; exact beta scope verified. PostgreSQL/remote release gates not run for this candidate. Validated synthetic desktop1280x720 and phone390x844: no horizontal overflow; caption edit/save/final snapshot verified; review composer56px and phone review feed627px. Normal composer252px desktop/291px phone with a video attachment; no-attachment composer is smaller. Local screenshot social-proof/studio-caption-20261016.png. No real post, grant, or production change. NOT DEPLOYED. Before deployment rerun required remote PostgreSQL/restore/container/dependency gates on exact candidate; sandbox is ephemeral and redeploy may require reconnecting. Broad79 gaps remain open; no commercial certification.

Rollback: revert this bounded change set; no schema migration. Reconciliation adds optional status_checked_at/url fields only to existing result JSON; old code tolerates these. Preserve publication receipts and never resend earlier tests. Production TikTok remains inbox-only pending approval. Prior sandbox publication must not be repeated.

---

# Saved stopping point - 16 October 2026

Owner will return tonight; no scheduled reminder or background posting requested. TikTok Direct Post works in the isolated sandbox: draft1 returned Published after refreshing provider status, for @davidwilson493 with Only me visibility. Do not resend this draft. Independent viewing of the private video in TikTok remains unconfirmed.

Next session: read this handoff, check sandbox availability/session first, and have owner verify the private video on TikTok. Prepare a NEW draft for the recorded demonstration: connect account, upload original media, edit caption, show privacy/interactions/disclosures and consent, final review, owner-authorised private publication, refresh status, then show the actual TikTok post. Review recording before submitting TikTok production video.publish revision and separate public-access audit. Neither is submitted/approved yet. Production stays inbox-only; approval enables eligible customers to publish publicly from the main site. No further implementation or production activation is implied by the successful private test.

Sandbox https://zova-tiktok-sandbox.onrender.com is FREE with ephemeral SQLite/uploads; restart/spindown/redeploy can lose test state and require a fresh test login/reconnection. Auto-deploy is Off. Do not reconnect its database to production. Code/configuration evidence and recording plan are saved in docs/TIKTOK_DIRECT_POST_20261016.md; screenshots and synthetic video remain locally under social-proof/. Do not expose credentials or upload the whole proof folder. Preserve all79 known beta gaps and existing connections.

---

# TikTok private Direct Post confirmed by refreshed provider status - 16 October 2026

On return to sandbox draft1, UI was already Waiting for platform processing (dispatch occurred outside this agent turn). Agent only clicked Refresh results, never Confirm publish. Refreshed publication result and sidebar both show Published. Reviewed destination @davidwilson493, Only me, exact test caption and6second video described below. Evidence social-proof/tiktok-private-published.png. This establishes Zova provider-status confirmation of private Direct Post; independent viewing in TikTok still needed for recording. Do not resend. Public approval/audit remains pending. Production unchanged.

---

# TikTok final private review verified - 16 October 2026

Owner explicitly approved accepting TikTok Music Usage Confirmation and opening final review only. Accepted agreement and generated server-owned final snapshot successfully for sandbox draft1, David Wilson @davidwilson493, six-second zova-beta-test.mp4, exact caption: Zova Direct Post integration test — checking our reviewed publishing flow. Final review displays SELF_ONLY; comments/Duet/Stitch off; own brand/partnership/AI-generated media no; video preview and processing notice. Confirm publish was NOT clicked. No provider publication outcome claimed. Evidence social-proof/tiktok-final-review-ready.png. Await exact separate private-test publication approval or owner recording; do not resend previous tests. Production unchanged. Cosmetic follow-ups: raw SELF_ONLY and opaque provider ID appear in review; mixed create + do-not-publish intent quirk remains.

---

# Live TikTok sandbox account and media verified - 16 October 2026

Owner signed into sandbox in side browser. Account shows David Wilson connected; live publish context identifies @davidwilson493. Uploaded existing synthetic6-second ZOVA BETA TEST video into new draft1. Browser preview readyState4/duration6; unauthenticated media GET200 video/mp4 20834bytes under verified sandbox prefix. AI inspected8frames. Initial mixed create + Do not publish message stopped generation; simpler drafting request succeeded. Record that intent-handling defect; do not silently call resolved.

Edited exact caption: Zova Direct Post integration test — checking our reviewed publishing flow. Live privacy options Followers/Friends/Only me, no default; comments unchecked; Duet/Stitch disabled by provider. Selected Only me. Agreement checkbox remains UNTICKED and Review final post disabled. Asked owner at-action permission to accept TikTok Music Usage Confirmation and open final review ONLY. No TikTok post sent, no final snapshot/provider outcome yet. Screenshot social-proof/tiktok-live-private-review.png. Next: await agreement answer, open final review, obtain exact separate private publication approval before sending. Sandbox ephemeral; avoid restarts. Production unchanged.

---

# TikTok recording sandbox ready for account connection - 16 October 2026

Reused existing FREE Render service zova-tiktok-sandbox (srv-d9u4joad0e5s73afpu10). Discovered it previously shared the production PostgreSQL database; changed this test service ONLY to sqlite:////tmp/zova-tiktok-recording.db, verified saved. Production users/data/keys/service unchanged. This temporary database and local uploads may be lost on restart/spindown/redeploy. Do not promise durable staging; record in one session and keep external evidence. Auto-deploy is Off to avoid branch updates resetting recording state.

Owner explicitly approved copying existing TikTok Sandbox client key/secret into this existing Render service. Configured those credentials, PUBLIC_BASE_URL and callback to https://zova-tiktok-sandbox.onrender.com, TIKTOK_SEND_TO_INBOX=false, SELF_ONLY default config (user must still explicitly select privacy), REQUIRE_SUBSCRIPTION=false, ZOVA_ENV=sandbox, and TIKTOK_VERIFIED_MEDIA_PREFIX=https://zova-tiktok-sandbox.onrender.com/media/raw/. Verified saved nonsecret values after deployment. No public post or new user grant sent.

Sandbox7672854716816082965 under TikTok app7672846663509215253 already has Direct Post and video.publish. Existing target user davidwilson493. Updated sandbox website to recording host. TikTok verified https://zova-tiktok-sandbox.onrender.com/ URL prefix using downloaded signature file; screenshot social-proof/tiktok-sandbox-prefix-verified.png. Production TikTok draft/live settings were not changed in this increment.

Dedicated branch codex/tiktok-recording-sandbox-20261016 pinned on test service, Live7fdec1573a004bd28d79ee0e54c0628461969247, deploy dep-db91mlcvk9tc73ea9df0. Only runtime change versus PR33 is static sandbox verification route. Initial CI caught CRLF digest mismatch; corrected normalised digest, CI38901929057 passes all required jobs:315 tests/ 1 skipped on SQLite AND PostgreSQL, restore/container/dependencies/guardrails. Local Direct Post tests16passed. Verification endpoint200 with exact signature; signup rendered and no subscription charge. Production remains cc093687 inbox-only; no broad native branch deployment.

User has been asked to create a SEPARATE Zova login at https://zova-tiktok-sandbox.onrender.com/signup then connect registered TikTok tester davidwilson493, or identify another account to add as sandbox target. Do not share passwords. Real OAuth, creator restrictions, uploaded media fetch, final review and private Direct Post outcome remain pending their connection; no ready-to-record end-to-end claim yet. Before sending anything obtain exact post/account/privacy approval. Complete provider verification, then recording; do not submit old inbox recording as Direct Post evidence. No iOS device validation performed. All 79 broader beta gaps retained.

Rollback: keep test DB isolated; do not point sandbox back to production. Set only sandbox TIKTOK_SEND_TO_INBOX=true to disable Direct Post or suspend test service if requested. Keep production unchanged. Preserve any publish receipts before restarting disposable sandbox.

---

# Direct Post deployment evidence - 16 October 2026

PR33 is merged as cc093687bc92f5600283918d330ef70691e4216e and verified Live on Render dep-db91bkvavr4c739qd50g. Public /health and versioned Studio publishing script return200; the script contains the new Direct Post controls and policy declaration. Required hosted checks passed:315 tests / 1 skipped on SQLite and PostgreSQL plus restore, container, dependency and release checks.

Production remains inbox-only. Direct Post is NOT enabled or provider-validated. TikTok production draft contains video.publish and Direct Post. Updated notes were entered and Save clicked; subsequent reload and Manage apps navigation returned Request aborted, so persistence of the latest notes could not be reverified. Earlier draft save was verified. Separate audit at Supporting documents is unsubmitted. Verified URL prefix is https://zova-social.com/; TIKTOK_VERIFIED_MEDIA_PREFIX still needs configuring and validating against hosted storage before direct testing. Do not change delivery mode or resend previous test posts.

Native PR28 includes the same server implementation. Its contract was regenerated for the additive connection_ids field (05e2c93);40 focused tests pass / 1 skipped. All required hosted native checks passed in38900036915 and38900044596. Native remains disabled and undeployed. Desktop synthetic UI inspected; attempted mobile viewport override did not take effect, so mobile visual validation is still outstanding.

Remaining: isolated real Direct Post authorisation and exact-approved private test, new provider recording, reviewer access check, app revision plus public-access audit submission and approval, then reconnect for video.publish and controlled feed rollout. Existing inbox recording is insufficient. All 79 broader beta gaps retained. Rollback and recording script: docs/TIKTOK_DIRECT_POST_20261016.md.

---

# TikTok Direct Post preparation - 16 October 2026

See docs/TIKTOK_DIRECT_POST_20261016.md. Production remains inbox-only. TikTok draft revision saved with video.publish and Direct Post; not submitted. Existing URL prefix https://zova-social.com/ verified. Separate audit form at Supporting documents, not submitted, browser answers may be ephemeral. New real Direct Post recording and provider validation required. Local implementation includes consent/disclosure/fresh creator/duration/verified-media controls and tests; no live Direct Post or native rollout claimed. All 79 gaps retained.

---

# Facebook live publication verified - 16 October 2026

Owner explicitly approved the exact single public text-only Facebook test. Published once through draft28 immutable final review to Zova Social Page1232370066628887. Zova returned Published and receipt122119807485439972. Independently opened Facebook and verified the exact text, Zova Social author and Public audience at https://www.facebook.com/61593199172836/posts/122119807485439972/ . Leave the post in place; do not resend or remove without owner request. Screenshot social-proof/facebook-provider-verified.png is local evidence.

Facebook app-role connection and text publication now verified. General customer access remains blocked on the separate unsubmitted Meta Page-permission review; do not equate this test with approval. X text test verified; TikTok inbox received per owner, not publicly published. Instagram unchanged. Image/thread/scheduling and native device validation are not established by these live text/inbox tests. All 79 broader gaps retained.

---

# Provider validation update - 16 October 2026

Owner explicitly approved the narrowed Facebook grant and six-second TikTok inbox test. Saved Meta grant for Zova Social Page1232370066628887 only, then confirmed the exact Page in david1@gmail.com / My brand. Zova Account shows Connected. No Facebook post sent yet; draft28 is being prepared for separate exact publication approval.

Submitted synthetic video from reviewed TikTok draft27 once. Zova returned pending/complete in TikTok, without error. Owner independently confirmed "Video received in TikTok" on16 October2026. This verifies inbox delivery, not public publication. Do not resend. UI still says Waiting for platform processing even after confirmed inbox receipt; improve delivered-to-inbox labelling as a follow-up without marking it publicly published. Instagram unchanged. Facebook public-customer permissions review remains unsubmitted/unapproved. Shared native integration head93af22c passed all required CI38888696671/38888702089, remains disabled/undeployed.

---

# Live social review fix - 16 October 2026

PR32 is Live (8ef1230, Render dep-db8vtgjrjlhs73betts0); all required checks passed; health200 and real TikTok draft27 final inbox review verified. X approved test already published once: https://x.com/DataMaxxingUK/status/2111033940157055189 . Do not resend. Pending owner answers: final narrowed Facebook grant for Zova Social only; exact six-second synthetic TikTok inbox send. Do not treat elapsed time as approval. No Facebook/TT delivery receipt yet. Shared native branch93af22c integrates all fixes, remains disabled/undeployed. See docs/SOCIAL_BETA_COMPLETION_20261016.md and feature matrix.

---

# Social beta integration work - 16 October 2026

Read docs/SOCIAL_BETA_COMPLETION_20261016.md for evidence and rollback. Instagram preserved. PR30 live; X authorised test published once and verified: https://x.com/DataMaxxingUK/status/2111033940157055189 . Do not resend. TikTok connected; draft27 holds an unsent synthetic video. Facebook three-permission review draft saved, not submitted. PR31 least-privilege Facebook change merged with required checks; hosting verification pending. Current cache-version follow-up has20 focused tests passing but is not yet deployed. Verify inbox review after rollout before requesting exact video-send approval. Restart stale Facebook consent without business_management before asking for Page grant. Native PR28 remains draft/disabled; shared fixes integrated through PR31, final checks pending. All 79 gaps retained.

---

# Next Move always-visible sections — 12 October 2026 (not deployed)

Branch codex/next-move-open-sections-20261012 replaces the Details and Change this idea dropdowns with always-visible, labelled sections and bold16px headings. No collapse controls on either section. Source evidence retains its separate disclosure. See steps now focuses the visible Details heading. Existing draft/feedback behavior preserved. Node journey/onboarding suites and4 beta scope tests passed. Synthetic desktop1280x720 and mobile390x844 reviewed; feedback input directly accessible, no horizontal panel overflow. No provider, schema, account or billing changes; all79 gaps retained. Rollback live db9a4ff6daff2735b48ff989771c9ae8c91e866c. Hosting checks required before publication.

---

# Creator Studio refinement is live — 12 October 2026

PR26 merged as db9a4ff6daff2735b48ff989771c9ae8c91e866c. Render dep-db6cikc9v7es739ubsbg is Live (56.6s rollout). Final candidate83fb222 passed all required checks in PR38244952639 and push38244944763. Brief startup HTTP errors recovered; health200 and exact deployed studio-design.css, studio-state.js and studio-experience.js matches verified. Signed-in live Studio starts with a blank composer/welcome and no recommendation card; saved history and personal workspace label render; recommendations load inside Next Move with existing Open draft, Details and Change this idea controls. No real post, grant or charge performed. Owner screenshot is local only: docs/validation/creator-studio-live.jpg. No schema change. Rollback798796b86168b68aa1e9993ca3a028991b3eee49 preserves data, uploads, sessions and connections. All 79 broader beta findings remain open.

---

# Creator Studio refinement — 12 October 2026 (not deployed)

Branch codex/creator-studio-20261012 implements the creator critique with the owner's overriding preference: Studio starts with a blank chat; recommendations stay ONLY in Next Move. No home recommendation card or background generation. Refined purple identity/controls, saved brand/profile label, owned attachment thumbnails with safe fallbacks, readable two-line history, natural creator-hook guidance and consistent New chat welcome. Four visual review passes, including compact mobile navigation; desktop390px/320px mobile, keyboard-to-draft, media reopening and clean reset verified on synthetic localhost. Local274passed/1skipped; Node suites passed; ownership/brand/URL preview regressions added. See docs/CREATOR_STUDIO_REVIEW_20261012.md for the executed prompt, heuristic scores and evidence limits. All 79 broader gaps retained; no migration, real posts, grants or charges. PR26 implementation2ec749a passed all required checks in38244715161 and38244710412. Await explicit publication; not merged. Rollback live798796b86168b68aa1e9993ca3a028991b3eee49.

---

# Studio design coherence is live — 12 October 2026

PR25 merged as 798796b86168b68aa1e9993ca3a028991b3eee49. Required synthetic, PostgreSQL and production guardrail checks passed on final candidate 282ee8e in CI38241265879 and push38241259549. Live health returned200; studio-design.css, studio.js, studio-experience.js and strategy.js matched the tested files. Signed-in live draft24 and the loaded Next Move panel visually verified: compact composer, conditional Post/Story, primary Review & publish, consistent navigation icons, restrained branding and Details/Change this idea. No real social posts, grants or billing changes. Render dashboard connection closed during verification, so deployment ID was not recorded; live application and asset verification succeeded. No schema migration. Rollback to1998cec03762931a362c17705b8a04081c5cdb94 preserves data. All 79 broader beta gaps remain open. Owner screenshots are local only. See docs/STUDIO_DESIGN_REVIEW_20261012.md.

---
# Studio design coherence candidate — 12 October 2026 (not deployed)

Branch codex/studio-design-coherence-20261012 completes three visual review passes against the six cosmetic criteria. See docs/STUDIO_DESIGN_REVIEW_20261012.md for recommendations, benchmark sources, measured layouts, scores and limits. Primary draft action, composer grouping, restrained branding, shared navigation icons, readable controls, compact Next Move and plain-language recommendation guidance implemented. Local SQLite272passed/1skipped; Node suites and synthetic desktop/mobile/keyboard/edit/reload review passed. PR25 implementation checks passed in CI38240968536 and38240961652, including PostgreSQL and beta safeguards. Not merged or deployed; use normal protected release flow when publishing. All 79 broader beta findings retained; design8/10 scores are heuristic, not commercial readiness. No real provider actions or schema migration. Rollback1998cec.

---

# Details-only Next move is live — 12 October 2026

PR24 merged as1998cec03762931a362c17705b8a04081c5cdb94. Render dep-db6bf3k9v7es739t2iag is Live. All required checks passed in PR CI38236867250 and push38236860942. Brief startup502 recovered; health200 and exact strategy.css/strategy.js matches verified. Signed-in live Next move shows only Details and Change this idea beneath the card/carousel; planning controls remain accessible via Post options. Purple gradient launcher shipped. No real posts or account/billing mutations performed. Rollback to1c978a1401427246bfe57ad230faa2f475ae54f9 preserves data. Broader beta gaps remain open.

---

# Next move details-only refinement — 12 October 2026 (not deployed)

Branch codex/next-move-details-only-20261012: recommendation view exposes only Details and Change this idea beneath the card/carousel. Removed More options wrapper and reminder UI. Plan/settings/recurring controls are hidden from Next move and remain accessible in the separate Your plan view through Post options or Plan my socials. New accounts see Set your goal; confirming the plan returns to recommendations. Launcher retains white text/shimmer with a near-black plum-to-violet gradient. No backend/data/auth/publication changes. All 79 broader beta findings retained.

Validated synthetic browser setup-to-plan-confirm-to-recommendation flow, clean panel and separate Post options planning access; Node onboarding, journey, schedule and Studio checks pass. Regression asserts planning/recommendation visibility separation. Hosted release checks/deployment remain pending. Rollback to1c978a1 preserves data.

---

# Next move focus release is live — 12 October 2026

PR23 merged as1c978a1401427246bfe57ad230faa2f475ae54f9. Render dep-db6b7poae00c73afn09g is Live. Required synthetic, PostgreSQL and production guardrails checks passed in CI38235232320 (also push38235226889). Health200 and exact deployed strategy CSS/JS, shared icon helper and X/Facebook/TikTok SVG matches verified. Signed-in Studio displays the larger black/white launcher and all four platform icons. No real social posts, grants or billing changes. Broader beta gaps remain open. Rollback to b82b04715c7c48efaa22d0a21d41d90021121cb4, preserving data.

---

# Next move focus and platform icons — 12 October 2026 (local, not deployed)

Branch codex/next-move-focus-icons-20261012 simplifies the card to one More options disclosure, retaining feedback, reminders, context and keyboard navigation. Studio launcher is larger black/white with two gentle shimmer cycles; reduced-motion disables animation. Shared locally hosted X/Facebook/TikTok SVG marks replace text approximations across composer, strategy, draft/review/results, analytics, account and landing controls. Names remain in accessible labels and prose. No backend, auth, billing or publication changes. All broader beta gaps remain open.

Validation: desktop and390px browser review, icon accessible names, secondary disclosure; existing Node journey/onboarding/schedule/Studio suites pass. Full local SQLite suite:271 pass/one skip with only stale scope manifest failure; refreshed exact scope after review and all4 beta gate tests passed. PostgreSQL hosted checks and deployment have not been run for this candidate. Rollback to b82b047 preserves all data. Screenshot docs/validation/next-move-focus-studio.jpg is synthetic and local.

---

# Next move carousel is live — 12 October 2026

One recommendation at a time with previous/next, Details, optional Change this idea, and Remind me (tomorrow/next week/custom browser-local date converted to UTC). This is idea deferral, not post scheduling. Removed Made for your plan/Quick check/Behind the idea/You’ll need labels; review instructions now use readable dark text. Official Instagram artwork sourced from Meta’s brand page is shared across composer, draft/platform controls, account connections and analytics. Prose/legal names remain readable. No schema migration; feedback fits existing80-character column. PR22 merged as b82b04715c7c48efaa22d0a21d41d90021121cb4. Render deployment dep-db68tbjrjlhs73bfl820 is Live. CI38218780881 passed all required checks: 272 passed/one skipped on both SQLite and PostgreSQL; client interaction checks passed. Live home returned200 and four deployed assets exactly matched. Live signed-in carousel navigation, Instagram glyph, readable review steps and reminder choices verified without changing owner recommendations or publishing posts. Local synthetic feedback, reminder, draft/reload and keyboard/mobile journeys passed. See docs/NEXT_MOVE_CAROUSEL_20261012.md. Broader beta gaps remain open.

---

# Next move brand update is live — 12 October 2026

PR21 merged as562d7a9404dead17ce5fac77279f155544037365. Render deployment dep-db68joek1f9s73f2g5dg succeeded, live at07:20:05UTC. GitHub Actions had been disabled (enabled:false); re-enabled existing workflow and ran normal PR checks. No branch protection bypass. CI38216870312 passed all required checks,271 passed/one skipped for each SQLite and PostgreSQL.

Live health200 and exact strategy.js/strategy.css content match verified. Existing signed-in draft22 opened and the new dark Next move card, Skip and compact disclosures rendered. Existing stale-source warning remained accurate. No ideas were dismissed, real social posts sent, grants changed or charges made for this release verification. Screenshot is local only and contains owner context. Broader beta/security gaps remain open in docs/beta/KNOWN_GAPS.md and deferred-register.json. Rollback to4d86fe7 while preserving data, drafts and sessions.

---

# Next move visual refinement ready for release checks — 11 October 2026

Candidate15bd98e in PR21. Local browser design/interaction checks passed at desktop,390px and320px widths; see docs/NEXT_MOVE_BRAND_20261011.md. Hosted workflow38174288031 remains queued without started jobs. This design has NOT been merged or deployed. Finish required checks before publishing; do not bypass them. Broader beta gaps remain open.

---

# Next move brand refinement — 11 October 2026

Reworked the recommendation panel with a dark Zova card, original translucent Z asset, stronger type, Draft/Skip actions, compact evidence and icon refresh. Removed reason questionnaire and duplicated approval text. Skip advances to the next saved idea and requests more when exhausted, preserving visible cards on save failure. Local desktop/mobile and keyboard journey reviewed; candidate awaits release checks. No backend/model/schema changes. Broader beta defects remain open.

---

# Next move published and verified — 10 October 2026

Live commit 4d86fe76eb5c2fc2bfe7388b7b3a6f8491cf5789, Render dep-db588kn40ujc73c8cp90, service live at 18:31:51 UTC. PR19 delivers the compact recommendation-to-draft journey; PR20 corrects invalid model response handling found during live verification. CI38075939402: 271 passed / one skipped on SQLite and PostgreSQL, required beta scope/restore/image/dependency checks passed.

Live authenticated verification: empty saved plan automatically generated three recommendations; Draft post created an actual AI-written draft, navigated to Studio, retained Instagram-only selection and content on reload; reopening Next move offers Open draft. Draft23 is the retained unapproved validation draft in workspace0. No real social publication, scheduling, charge or grant change occurred. Health/login/signup returned200; PR19 client asset matched the reviewed source. Desktop/mobile390x844 and keyboard/failure/late-response testing used isolated synthetic data. Saved screenshots include owner data and must not be committed publicly.

Read docs/NEXT_MOVE_SIMPLE_20261010.md and docs/validation/next-move-live-20261010.json. Remaining limitations: live generation was verified for one saved strategy/account, not every provider/model outcome. Invalid output gets one repair; provider outages still require retry. Broader commercial/security backlog remains open in docs/beta/KNOWN_GAPS.md and deferred-register.json and must be prioritised on future updates. No schema migration; rollback to ebb6f48 for the repair or4c0b041 for the full Next move update, preserving drafts/data.

---

# Next move live-model follow-up — 10 October 2026

PR19 is live as ebb6f48. The compact UI and synthetic journey passed, but live recommendations failed strict validation. Current follow-up supplies the exact schema/platform constraints and one bounded repair; awaiting full CI and live verification. Read docs/NEXT_MOVE_SIMPLE_20261010.md. Broader beta gaps remain open.

---

# Next move simplification candidate — 10 October 2026

Read docs/NEXT_MOVE_SIMPLE_20261010.md. Current update responds to the owner-reported empty/cluttered Next move journey. Implements automatic missing/stale recommendations, one featured post, compact disclosures, explicit draft platform/title, save failure and late-navigation protection. Local synthetic browser end-to-end setup/draft/reload and two design review passes completed. Broader security gaps remain required follow-up in docs/beta/KNOWN_GAPS.md. Await CI and live verification before calling this update published.

---

# Beta is live — 10 October 2026

Verified Render deployment dep-db52dg3rjlhs73abnrr0, commit 4c0b0419beb6944bd8e0db3189432d259e9efded, live at 11:52:45 UTC. PR 17 merged after all three required checks passed. CI 38049756412: SQLite 265 passed / one skip; PostgreSQL 265 passed / one skip; restore/image/dependency and exact-scope beta gate passed. Health/login/signup returned 200; live Studio asset matched candidate and browser retained existing session/draft21. Transient 502 during startup recovered. No real post/charge/provider grant or secret change was used for validation.

Known gaps and next-update requirements: docs/beta/KNOWN_GAPS.md and docs/beta/deferred-register.json. Commercial readiness remains unapproved. Broader PR18 security migration is deferred and must not be deployed wholesale. When the owner next requests updates, address/reconcile the saved defects and security gaps first. Local screenshot contains the owner's draft: do not commit or share it publicly. Sanitised release evidence: docs/validation/beta-live-20261010.json.

---

# Limited beta authorisation — 10 October 2026

Owner requested publication as a beta for personal testing and deferral of the remaining commercial work. This supersedes the all-sections-complete requirement for this focused beta only. Read docs/beta/KNOWN_GAPS.md and docs/beta/deferred-register.json on every future update and address the recorded issues before unrelated expansion.

Use focused UX PR 17; do not publish the broad unfinished security/service migration in PR 18. The beta excludes later optional MFA and account/usage hardening, which remain next-update priorities. Required application/PostgreSQL/migration/restore/image and scoped beta checks must pass. Deployment has not yet been confirmed; append actual revision and evidence after verification. Existing billing test settings, data, sessions and publishing approvals must remain intact.

---

# Publication blocked by enforced production gate — 8 October 2026

User authorised publication. A focused release was prepared in the sibling `zova-ux-release` worktree, branch `codex/ux-release-20261008`, PR #17 (https://github.com/davidwilson92-cpu/DataMaxxing/pull/17), candidate `1398c7ececae2de5ab9370e7c43fa9021ba4c11d`. It is NOT merged or deployed. Production remains `38f1c265`.

Both push and PR CI passed synthetic-tests and postgres-release. Final suites: 261 passed / one expected skip on SQLite; 261 passed / one expected skip on PostgreSQL (SQLite-only backup test). PostgreSQL old-schema title migration DID pass, as did dump/restore, Docker smoke and all three frontend harnesses. Dependency audit is clean after oauthlib 4.0.0 and direct OAuth1 signing for the legacy X text path. No real post was sent. Render export was created 8 October 2026 20:35 UTC; three-day point-in-time recovery is available. Backup stayed in Render.

GitHub refused merge because active ruleset `Zova production guardrails` (24140009) requires `Production guardrails`, synthetic-tests and postgres-release. No bypass actors. The missing gate exists in separate unmerged PR #16 and intentionally blocks until its open requirements/evidence are resolved. Do not remove the rule, fabricate a green check, force-merge or manually deploy around it. The prior broader candidate is still local and must not be deployed wholesale. No infrastructure or billing changes were made.

Release manifest: `../zova-ux-release/docs/UX_RELEASE_20261008.md`; remote evidence: Actions run 37841005196; local downloaded artifacts: `../zova-ux-release/docs/validation/ux-release-ci-final/`. Next step is reconcile the focused UX release with the enforced guardrail release process and resolve its required evidence. The owner MFA and paid-staging deferrals in PR #16 remain relevant; they are not release waivers.

---

# Focused UX release candidate — 8 October 2026

Publication authorised. Read `docs/UX_RELEASE_20261008.md` for exact scope and rollback. This separate release excludes the broader September authentication, recovery, storage and newsletter candidate. Remote release checks and live verification are required before marking it live.

---

# Next move top-right and current-topic search — LOCAL CANDIDATE, 27 September 2026

Current increment is NOT deployed. Branch `codex/next-move-sources` in the existing `zova-strategy` workspace, based on production-equivalent 653528a / 021aad7. Read `docs/NEXT_MOVE_SOURCES_20260927.md` for details, evidence, limitations and rollback. Sources under the mirrored project remain read-only.

Implemented: top-right branded Next move; compact expandable source cards; bounded web/public-social search using public content themes; cited URLs and 14-day reported-date checks; strategy-ranked recommendations; 24-hour source expiry; explicit evergreen fallback and existing draft/approval continuity. No schema changes. Full suite 224 passed; final focused suite 43 passed including 2 additional tests. Desktop and 390/320px mobile, keyboard and generated-draft reload reviewed locally. Provider/model acceptance remains unvalidated: no local OpenAI key. No live posts, grants, charges, settings or production changes. Fresh CI/PostgreSQL and a synthetic provider search are release gates.

Rollback this increment to production-equivalent 653528a / 021aad7, retaining all data. Prior live strategy release details below remain valid; this increment does not supersede production until separately published.

---

# Strategy and Next move LIVE — 27 September 2026

User explicitly approved repository upload and deployment. PR #13 merged as 021aad77292abc95c499191789bc50c5cda69436, identical tree to validated 653528a02a53b1575509bcc05c3f8adafaaac7a3. Both candidate CI runs 36347400542 and 36347397624 passed (SQLite/PostgreSQL, synthetic restore, dependency audit and hosting image checks). PostgreSQL validation found a pre-existing concurrent-first-request limiter race; corrected without changing limits, with 22 focused local tests passing.

Render deployment dep-dasnmcc9v7es73f7jvrg confirmed Deploy succeeded / Live; service-live log at 21:24:02 BST. Fresh managed PostgreSQL export available at 21:18 BST; three-day point-in-time recovery available. Production backup was not downloaded/restored. Public health and homepage return 200; all four changed Studio JS/CSS assets match tested files. Existing signed-in browser session and saved draft 9 remained visible; Next move opens without error and purple sparkle renders in both heading and composer. Opening panel initialized an empty strategy row for the existing session; no preferences confirmed, AI calls, posts, grants or charges. No credentials/settings changed.

Release evidence: docs/validation/strategy-release-20260927.json and strategy-live-20260927.png in the local zova-strategy checkout. Provider/real-model quality and verified live trends remain unproven; rollout does not close these gaps. Rollback: retain additive tables; cancel pending series jobs before code rollback to b746bad, preserve unknown/completed outcomes and all user/media/auth/social records. Earlier candidate-only statements below are historical.

---

# Zova continuation — local strategy candidate, 27 September 2026

This candidate is NOT deployed. Current production base: b746bada82965baa8f3bf55bf04a921683134b35. Branch: codex/strategy-next-move. Workspace: C:/Users/david/.codex/.chatgpt-projects/g-p-6a8a0aa881c88191a2835a8d53316369/zova-strategy.

Read docs/STRATEGY_NEXT_MOVE_20260927.md first for the iteration log, scores, limitations and rollback, and docs/ZOVA_FEATURE_MATRIX.md for current feature status. Earlier live history remains in the original root handoff under Documents/Codex/2026-08-29/referenced-chatgpt-conversation-this-is-an.

Implemented: confirmed brand strategy separate from proposals; up to three compact Next moves; generated idempotent linked drafts; feedback; finite recurring plans; exact repeat batch approvals; fresh drafts separately reviewed; pause/cancel/time edits; privacy lifecycle and usage integration. Existing users/data/auth/media/social connections and explicit publishing approval preserved. Testing billing flags unchanged.

Validation: 203 automated tests passed (17 existing warnings), JavaScript syntax/whitespace checks passed. Local synthetic browser journey and 390x844 responsive check, no horizontal overflow; Escape returns focus to Next move. Mocked AI/providers, no live posts. Final targeted subscription-guard regression: 21 passed (2 existing warnings).

Before release: run staging PostgreSQL concurrency and worker recovery; real-model usefulness evaluations; approved provider scheduling/Story validation. Live trends are unavailable with explicit evergreen fallback. Batch TikTok settings use individual Studio review. Future content changes require an edited new series; one/future time changes are supported. Do not claim whole-product 8/10 or deploy without authorization.

Rollback: cancel pending series deliveries before returning code to b746bad; do not automatically cancel sending/unknown outcomes. Keep additive tables and completed history. Restore-test a database backup before any release.

Local git origin points to the original local checkout, not GitHub. Do not push to it. No PR or deployment created in this task.

WebKit regression outcome: latest test-only b9dcd32 / native run39231451448 completed the12 unit tests (including real WebKit POST/header/body/303 redirect/session-cookie) and welcome UI test successfully; release compilation was running at this entry. Actual network test passed4.401s. Earlier15s timeout is recorded as a failed attempt, not a passing result. Evidence: social-proof/ios-webkit-ci-network.txt. Application39231451464 passed480/ 1 skipped on both SQLite/PostgreSQL with restore/container/dependency/scope gates. Final build5 source671bbdd has identical production native sources to b9dcd32; test-only changes require no new binary.
