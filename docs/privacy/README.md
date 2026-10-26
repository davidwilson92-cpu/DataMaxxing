# Zova commercial assurance pack

Prepared 26 October 2026 for **Zova Social Limited**, confirmed by David in chat.
Owner/contact: David, david@zova-social.com. Business/service address and company
number have not been supplied or independently verified. Do not invent them or
publish a private address. The current instruction authorises preparation and
engineering, not signature of a supplier contract or purchase of a security test.

Public support email: **support@zova-social.com**, confirmed by David on
26 October. This confirms an email contact, not a business postal address or
whether the receiving Gmail account is personal Gmail or Google Workspace.
Security quote replies remain directed to david@zova-social.com as authorised.

## Owner's short version

| Work | Deliverable | Closure requirement |
| --- | --- | --- |
| Retention/deletion | [Policy and data inventory](RETENTION_AND_DATA_INVENTORY.md) | Owner approved 26 October; expired-token cleanup completed. Other retention controls need implementation and privacy review before a public promise |
| Suppliers | [Supplier register](SUPPLIER_REGISTER.md) | Confirm account-specific contracts, settings, transfers and the support-mailbox arrangement; privacy review |
| Recovery | [Exercise and response procedure](RECOVERY_EXERCISE.md) | Fresh rehearsal: 44 tables/623 rows and 25 available files restored; four historical files missing. Managed backup and independent key recovery still need evidence |
| Independent testing | [Testing brief](INDEPENDENT_SECURITY_TEST_BRIEF.md) | Quote enquiries delivered to Cobalt and Kobalt; await quotes, select a tester, resolve findings and obtain their retest |

See the [dated implementation record](IMPLEMENTATION_STATUS_20261026.md) for
receipts, exact test results and the remaining work. This is not a commercial
security sign-off.

These are not four government certificates. This pack is engineering preparation,
not an external legal opinion or independent security assessment. David owns the
business decisions. A fixed-scope UK privacy review should cover the inventory,
lawful bases, supplier/transfer arrangements, customer notice and any business
customer processing agreement. Do not describe an internal code review as a pen test.

## Owner decisions and remaining actions

1. David approved policy version `2026-10-26-v1` and expired-token cleanup on
   26 October. One bounded cleanup removed 88 expired authentication records;
   a subsequent read-only audit found zero eligible records. Active content and
   native sessions were outside the allowlist. Other purges are not enabled.
2. Proposed recovery objectives: restore usable service within one business day;
   no more than 24 hours of lost content. These are planning targets, not measured
   service guarantees. DB and uploaded-media recovery must be compatible.
3. Confirm a business/service address for disclosures and a dedicated business
   support mailbox arrangement. Existing Cloudflare forwarding remains unchanged.
4. A separate web/API/iOS quote enquiry including retesting was sent to each of
   Cobalt and Kobalt with David's explicit approval. Resend reports both delivered;
   replies go to david@zova-social.com. Neither has been appointed, paid or given
   access. A fixed-scope privacy review still needs an adviser and owner approval.

Customer charges remain disabled, Stripe stays test-only, paid monitoring remains
inactive and Render is retained. There is no public legal-policy change merely
because these internal documents exist. The 79-item register remains open where
its evidence is incomplete; completing this pack does not close it wholesale.

## Review checklist for a privacy adviser

- Confirm legal entity, contact details, controller/processor roles and business
  customer Article 28 terms where Zova acts on customers' instructions.
- Validate purpose-specific lawful bases, the legitimate-interests assessment for
  security/measurement, AI permission wording and withdrawal behaviour. A product
  toggle alone is not a complete lawful-basis analysis.
- Review children/age positioning, incidental third-party people in uploaded media,
  and whether a DPIA is required; do not assume all uploads are non-sensitive.
- Review international transfers using the actual contracting entities and current
  mechanisms, not server location alone. Confirm supplier acceptance evidence.
- Check subject rights/export/erasure, exceptions/holds, retention, complaints and
  ICO registration/fee applicability. Avoid an unsupported claim of certification.
- Produce a dated, version-specific opinion and an explicit unresolved-actions list.

Maintain this pack on material changes and at least quarterly during beta. Keep
signed agreements, sensitive recovery evidence and deletion journals in restricted
business storage, not the source repository or public tester brief.
