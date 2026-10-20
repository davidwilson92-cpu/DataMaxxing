# Zova Social — prepared external TestFlight review

Status: review not submitted. Build 0.1.0 (10), bundle `com.zovasocial.app`, from
runtime `25374db` is processed and Ready to Submit. What to Test is saved and the
existing one-tester internal group assigned. The new Zova Social External Beta
group has zero testers. Its build10 flow requires a dedicated review login;
name/business email and the owner's supplied private telephone number are
entered but not saved in that modal. Keep the telephone number out of public
app UI, metadata and this repository.
A dedicated Zova App Review signup is prepared for the owner's existing
Gmail plus alias, zova.social+apple-review@gmail.com. The owner must complete
new password entry/signup and enter the same credentials in Apple's private
review fields. No reviewer account or review submission is confirmed yet.
Do not submit incomplete review access details.

## Beta description

Zova Social helps creators plan, draft and review social posts. Studio combines
conversation, editable captions, media and platform choices. Next move suggests
content based on a saved strategy. Drafts keeps saved posts and schedules;
Performance explains available social results; Account manages identity, privacy
and connected profiles.

This beta is free. No payment card, purchase or subscription charge is required.
AI processing asks for explicit permission before sending the user's content to
the AI service. Users can withdraw that permission in Account.

## What to test

Create an account, draft and edit a caption, attach media, and reopen the app to
check saved work. Try Next move, Drafts, Performance and the expandable Account
sections. Check keyboard behaviour, larger text and VoiceOver.

Connect an eligible social account, confirm the exact returned profile and check
that sign-in returns to the app. Review a post's caption, media, destination and
platform settings. Publishing is optional and always requires final confirmation.
Do not resend a post whose result is unconfirmed.

Please report unclear instructions, lost input, unexpected account choices,
failed connections and any navigation or accessibility difficulty through
TestFlight feedback, including the build and device/iOS version.

## Reviewer notes

The app uses the same Zova account and data as https://zova-social.com. Its native
shell presents Studio, Drafts, Performance and Account, with secure browser-based
social sign-in and a validated return to the app. Permission changes and posting
are explicit actions; opening the app does not post content.

Instagram publishing requires a Business or Creator profile. Facebook publishing
is to a managed Page. X access depends on the connected account's provider grant
and limits. The current production TikTok permission supports inbox upload for
the creator to finish in TikTok. Direct Post is not advertised as available while
the production `video.publish` permission revision remains in review.

Image and sampled video-frame inspection requires the user's AI-sharing consent.
Video audio is not inspected; source links are not silently fetched by Studio.
Performance distinguishes missing or stale data from confirmed results.

The beta has no active purchases, customer charges or subscription enforcement.
Account contains privacy controls and an account-deletion request route. Do not
describe deletion as instant erasure or claim unverified provider revocation.

## Complete before submission

1. Verify build 10 has finished Apple processing and is eligible for an external
   TestFlight group. Keep the public App Store release disabled.
2. Provide a dedicated review account with synthetic drafts and no owner's social
   connections. Record credentials only in Apple's protected reviewer fields,
   never in this repository or chat. If a credential must be created through the
   browser, the owner completes that step. Verify the account actually signs in.
3. Confirm the reviewer can inspect the product without publishing or requiring
   access to another person's social account. Explain provider account eligibility
   accurately; do not supply customer tokens, passwords or grants.
4. Fill the contact using the confirmed business email `david@zova-social.com`
   and David Wilson. Obtain the contact telephone number from the owner; do not
   invent one. Confirm the mailbox is monitored.
5. Complete the remaining password-recovery, device-return and operational gates
   in `EXTERNAL_BETA_20261020.md`. Export-compliance and legal declarations must
   match the shipped app; do not accept a new agreement on the owner's behalf
   without the required confirmation.
6. Submit Beta App Review only when all required fields and review access are
   verified. Save the visible submission receipt and distinguish In Review from
   Approved. Invite external testers only after approval and access checks.

## Delivery record

- Application CI: `39453432880`, successful.
- Native CI: `39453432747`, successful, 16 unit and 1 UI test.
- Codemagic: `6ad7907b454d2506f7ab80b9`, upload succeeded.
- Render: `dep-dbbp1k0ae00c73abch8g`, live.
- Apple processing: complete, Ready to Submit; UUID
  `49d32ac0-86d6-43bc-a0e3-8d82d9101af1`.
- Internal group: existing group assigned, 1 tester.
- External group: `f3f15099-0bec-49dc-8347-cd55beb805c0`, 0 testers.
- Beta App Review submission/approval: not completed.
- External invitations: not sent.
