# Zova V6.2 refinement release

## Included

- Drafts are saved automatically while a creator edits generated content.
- Drafts can be reopened, edited and deleted from the new Drafts workspace.
- Analytics now has its own workspace with a seven-day cross-platform summary, platform comparisons, top posts and practical recommendations.
- Creators can ask Zova questions about their connected-account data. If `OPENAI_API_KEY` is configured, Zova provides an AI analysis grounded in the available metrics; otherwise the page provides deterministic recommendations without inventing data.
- Terms of Service, Privacy Policy and Refund Policy are live pages linked in the public footer and signed-in navigation.

## Deployment

Deploy using the existing service settings and start command. No database migration is required because drafts use the existing `Draft` model.

Recommended environment variables:

- `LEGAL_ENTITY_NAME=Zova Social Limited`
- `PRIVACY_CONTACT_EMAIL=privacy@zova-social.com`
- `LEGAL_CONTACT_EMAIL=legal@zova-social.com`
- `REFUND_CONTACT_EMAIL=billing@zova-social.com`
- `BILLING_CONTACT_EMAIL=billing@zova-social.com`
- `OPENAI_API_KEY` enables conversational analytics and recommendations.

All existing social OAuth, database, encryption and platform credentials remain unchanged. Subscription enforcement remains off unless explicitly enabled through the existing configuration.

## Release checks

- Python compilation
- JavaScript syntax validation
- Zova onboarding/application test suite
- Browser review at desktop and responsive layout widths

The legal pages are product-ready drafts and should be reviewed by a qualified lawyer before a broad commercial launch.
