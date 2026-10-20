# Recovery email — live setup and remaining acceptance

Outgoing email is configured and live on 20 October 2026, using the existing
tested runtime `25374db`. Two authorised delivery checks were accepted by SMTP,
reported Delivered by Resend, and reported Forwarded to the existing Gmail by
Cloudflare. Owner confirmation of inbox receipt and the real verification/reset
journey remain pending. Do not equate these delivery records with successful
password recovery.

The public domain uses Cloudflare Email Routing for incoming mail. This does not
establish an outbound SMTP service. Preserve its current root MX/SPF records.

## Configured service

Owner confirms Gmail use and Cloudflare registration, and asks for setup help.
Cloudflare now has an active **support@zova-social.com → zova.social@gmail.com**
rule, using the same verified destination as the existing David address. That
existing rule and root DNS/catch-all settings are unchanged. The support test
was forwarded at 18:53:22 BST on 20 October; Cloudflare reports SPF and DKIM pass.

Owner has signed into the existing Resend account. Its
published allowance currently includes 3,000 emails per month, limited to 100
per day; the account UI confirms Free and paid overages off (6 monthly sends,
0 today at inspection). Keep paid overages and upgrades disabled. The existing
`auth.zova-social.com` domain is verified in Ireland with Enforced TLS and no
configured tracking subdomain. It already serves Zova Market; preserve that app's
key and configuration. Following the owner's confirmation, a separate
**Zova Social Render recovery** key was created with Sending access only,
restricted to this domain. Key ID `33e41e38-8f66-4bfa-a01a-321ba07c3497` is a
non-secret identifier; its value is stored only in Render's protected
`SMTP_PASSWORD` field. No key value is included in evidence or the repository.

Sources checked 20 October 2026:
[Resend pricing](https://resend.com/pricing) and
[SMTP setup](https://resend.com/docs/send-with-smtp).
Recheck before committing to a service because limits may change.

Use the provider's actual displayed DNS records to verify the sending domain.
Prefer a dedicated return-path/sending subdomain where the verified From address
and reply routing allow it. Do not replace incoming-mail records or add a second
SPF record at an existing hostname. Disable open/click tracking for account-security
messages. Use a sending-only credential limited to the approved domain.

The existing Zova mail implementation supports verified STARTTLS and is compatible
with Resend's documented port 587 settings:

| Render setting | Value |
|---|---|
| `SMTP_HOST` | `smtp.resend.com` |
| `SMTP_PORT` | `587` |
| `SMTP_USERNAME` | `resend` |
| `SMTP_PASSWORD` | Sending credential, entered only in the protected secret field |
| `SMTP_FROM` | `Zova <noreply@auth.zova-social.com>` on the existing verified domain |
| `PUBLIC_BASE_URL` | `https://zova-social.com` |

The production Render service successfully completed a verified STARTTLS
connection, authenticated with the restricted credential and sent the two
authorised checks. `/internal/status` returned 200 with a reachable database,
idle embedded worker, zero mail failures and zero stuck mail after activation.
The public recovery form now offers Send reset link.

Render deployment `dep-dbbqk2tpkucs73eg704g` activated these settings using
Save and deploy, retaining exact runtime
`25374dba138c8c50ebeb5b0224b7d4af55b180bd`. Billing mode remains off, checkout
false and subscription enforcement false. No DNS changes or plan upgrades
were made. Never choose Save, rebuild, and deploy from the unrelated main branch.

After confirmed provider delivery and Cloudflare forwarding, the
`SUPPORT_EMAIL=support@zova-social.com` change went live in deployment
`dep-dbbqni1jfumc73d36gr0` at 18:59:07 BST. The signed-in live Help page now
links to that address and still states free beta/no automatic charge.
Gmail Send mail as is not configured; forwarding alone
does not allow replies from that address. The current app sender is noreply and
does not add a Reply-To header.

## Delivery evidence

| Check | Resend email ID | Observed outcome |
|---|---|---|
| support@zova-social.com | `01a15a72-4a7b-727d-bc06-0253fdfbff4f` | SMTP accepted; Resend Delivered; Cloudflare Forwarded to existing Gmail |
| david@zova-social.com | `01a15a72-4ed5-7044-a7aa-1d3505ece6f3` | SMTP accepted; Resend Delivered; Cloudflare Forwarded |

Subjects identify these as Zova Social beta delivery checks. No password was
changed and no verification/reset token was included in either message.
Evidence screenshots are in ignored `social-proof/`: resend-email-delivered-checks
and support-email-forwarded, both dated 20261020. Owner inbox acknowledgement
is still outstanding. Cloudflare reports DMARC status none on the support check;
this is not evidence of a published DMARC enforcement policy.

Do not copy a credential into this document, chat, logs, screenshots or Git.
If using another provider, inspect its TLS/authentication requirements before
configuring it. Current code does not implement implicit TLS on port 465.

## Verify delivery and recovery

1. Completed: verified domain and restricted sending key; no changes to the
   separate Zova Market sender.
2. Completed: existing production service configured, billing and publishing
   configuration preserved. Confirm the owner's actual Gmail receipt.
3. Use a dedicated synthetic account whose mailbox the owner controls. Request
   one verification email through Zova and confirm receipt and verified identity.
4. Request a password reset and confirm it arrives with the correct HTTPS
   `zova-social.com` destination. Do not print or copy the one-use token into logs.
   The owner completes password entry.
5. Confirm the old password/session fails, the new sign-in works, the used reset
   link fails and a second attempt cannot replay it. Expiry/concurrent redemption
   are already covered by synthetic tests; preserve those checks.
6. Record the provider delivery ID/status, timestamps and a redacted receipt.
   A queued/accepted SMTP response is not a confirmed inbox receipt.
7. Confirm recovery readiness and mail-failure monitoring. Do not interpret an
   unrelated historical publication warning as a new email-delivery failure.

## Operational follow-through

External invitations also wait on a monitored support address, delivered and
acknowledged alerts, the real-device social-return check and Apple approval.
Do not hand a production scheduler/admin secret to an external uptime service.
Any monitor integration must have narrowly scoped access, avoid sending user
content, and be tested with an explicitly authorised synthetic alert.

Database and upload backups are visible in Render, and the synthetic recovery
drill passed. Production restoration still needs an isolated destination with
email, AI and provider dispatch disabled. No stale backup may replace live data.

## Configuration rollback

Keep the existing runtime, database, uploads and all other environment values.
If the sending credential is compromised, replace/revoke only the dedicated
Zova Social key; do not touch Zova Market's key. A provider outage should keep
recovery attempts honestly failed and preserve existing sign-in access.
Removing the SMTP settings makes recovery unavailable again; never claim the
service is ready afterwards. If the new support route fails, the previous
Help fallback is the existing Zova Gmail. Do not change incoming MX or erase
delivery records as part of rollback. No schema/data rollback is required.
