# Recovery email — remaining beta setup

No outgoing email is configured in production as of 20 October 2026. The
password-reset and verification code paths exist, but testers cannot receive
those messages yet. A configuration check is not proof of delivery.

The public domain uses Cloudflare Email Routing for incoming mail. This does not
establish an outbound SMTP service. Preserve its current root MX/SPF records.

## Proposed minimal-cost option

Owner choice is pending: reuse an existing outgoing provider or prepare Resend's
Free plan. Its published allowance currently includes 3,000 emails per month,
limited to 100 per day. Keep paid overages and all paid upgrades disabled.

Sources checked 20 October 2026:
[Resend pricing](https://resend.com/pricing) and
[SMTP setup](https://resend.com/docs/send-with-smtp).
Recheck before committing to a service because limits may change.

If selected, verify a dedicated sending subdomain through the provider's actual
displayed DNS records. Do not replace incoming-mail records or add a second SPF
record at an existing hostname. Disable open/click tracking for account-security
messages. Use a sending-only credential limited to the approved domain.

The existing Zova mail implementation supports verified STARTTLS and is compatible
with Resend's documented port 587 settings:

| Render setting | Value |
|---|---|
| `SMTP_HOST` | `smtp.resend.com` |
| `SMTP_PORT` | `587` |
| `SMTP_USERNAME` | `resend` |
| `SMTP_PASSWORD` | Sending credential, entered only in the protected secret field |
| `SMTP_FROM` | Sender on the domain actually verified by the owner |
| `PUBLIC_BASE_URL` | `https://zova-social.com` |

Do not copy a credential into this document, chat, logs, screenshots or Git.
If using another provider, inspect its TLS/authentication requirements before
configuring it. Current code does not implement implicit TLS on port 465.

## Verify delivery and recovery

1. Owner completes account/terms and credential entry where required. Record the
   exact permitted sending domain; verify it in the provider dashboard.
2. Configure the existing production service, keeping billing and publishing
   configuration unchanged. Restart only through the normal reviewed deployment.
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
