# LinkedIn integration setup continuation

Status: blocked on LinkedIn Page eligibility; no new developer app or runtime
integration created. Existing native build 13 remains Testing externally.

## Recovered previous work

Read chat **Start LinkedIn API integration**, ID
`01a16f89-7592-7f32-bc69-61770aadecc1`. It records:

- Owner requested starting LinkedIn API integration and authorised creating a
  Zova Social company Page.
- Developer registration was prepared with app name and verified privacy URL.
- LinkedIn blocked Page creation for insufficient connections; no app was saved.
- Owner requested renaming the signed-in member profile to Zova Social and two
  connection invitations. Those actions did not create a company Page.

Do not mistake the renamed member profile for the company Page. Do not restart
or create duplicate registrations without checking this record and live state.

## Live inspection on 28 October

- `https://www.linkedin.com/developers/apps` shows no developer applications.
- Prepared unsaved registration: **Zova Social**, privacy URL
  `https://zova-social.com/privacy`. Company search found no exact match.
- Retried the previously authorised Page setup at
  `https://www.linkedin.com/company/setup/new/`.
- Clicking Company shows **Feature not available — Please verify your workplace
  before creating a LinkedIn Page**.
- Verify opens `https://www.linkedin.com/verify/`; the available option is
  **Verify your identity — Using government ID**. No verification was started,
  no ID collected, no legal agreement accepted.
- Asked the owner to sign into the established David Wilson profile or complete the
  provider verification directly. Never collect passwords or identity documents
  in chat. No invitations or other messages sent this turn.

Proof: `C:/Users/david/AppData/Local/Temp/zova-linkedin-page-verification-20261028.png`.

## Continue after account eligibility is resolved

1. Check the existing Page/admin state first. Complete the already-authorised
   company Page registration if none exists; obtain action-time confirmation for
   any new binding agreement required by LinkedIn.
2. Register the existing prepared Zova app against the correct company Page;
   verify the Page association. No credentials currently exist to configure.
3. Confirm target access: Share on LinkedIn and OpenID Connect for member posting;
   Community Management access for company Page publishing/analytics. Do not
   promise Page access or performance data before LinkedIn grants it.
4. Implement within existing encrypted connections, owner/brand-bound OAuth state,
   staged final confirmation, native browser return, reviewed publication ledger
   and duplicate prevention. Extend both web/native platform choices consistently.
5. Validate new permissions, expiry/reconnection, publishing limits, scheduling,
   native return/cancellation, and regression coverage before deployment. A live
   test post needs explicit owner permission for its account/content.

No runtime edits, hosting/billing changes or extra customer access were made.
The earlier opening plan to complete publishing in this turn is not evidence that
implementation or provider approval has been completed.

## Official API references inspected

- [Application access](https://learn.microsoft.com/en-us/linkedin/shared/authentication/getting-access)
- [Authorization code flow](https://learn.microsoft.com/en-us/linkedin/shared/authentication/authorization-code-flow)
- [OpenID Connect](https://learn.microsoft.com/en-us/linkedin/consumer/integrations/self-serve/sign-in-with-linkedin-v2)
- [Share on LinkedIn](https://learn.microsoft.com/en-us/linkedin/consumer/integrations/self-serve/share-on-linkedin)
- [Posts API](https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/posts-api?view=li-lms-2026-09)

Use current supported versioned Posts APIs; do not infer that read/analytics or
company publishing scopes are granted from member posting access.
