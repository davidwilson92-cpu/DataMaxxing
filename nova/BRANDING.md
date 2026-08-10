# Nova branding implementation

All visible product naming is **Nova**. The application contains no previous-product branding.

The visual system lives in:

```text
nova/static/nova.css
```

Top-level variables at the start of that file control the product theme:

```css
--ink
--paper
--violet
--violet2
--mint
--pink
```

The current UI uses a premium dark-ink / violet / mint placeholder system and a text wordmark so the backend can ship independently of final asset files.

The referenced Zova/Nova brand-profile attachment was not present in the accessible file set at build time. Upload the actual profile to apply its exact colours, typography, spacing and logo rules. No product logic needs to change.
