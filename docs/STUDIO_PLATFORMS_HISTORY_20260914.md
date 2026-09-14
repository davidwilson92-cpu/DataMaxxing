# Zova composer and account history — 14 September 2026

User direction: keep the simple conversation, but make it recognisably Zova. Bring platforms and format into the composer; dim unselected platforms; offer connection when a disconnected platform is selected; keep account-owned posts in the sidebar; add a very translucent Zova Z backdrop.

Implemented: platform chips within the composer, purple selected state and muted unselected state, connected indicator, conditional X format, contextual Connect/Keep drafting dialog. Connection navigation saves first and uses the existing /connect/{platform} entry point, preserving both Instagram routes. Nothing connects or publishes automatically.

Recent work: 20 recent posts/conversations in a desktop sidebar and the mobile navigation drawer, with search/all-drafts links. Existing PostgreSQL workspace storage preserves conversation, unsent text, variants, attachments, source and selected platforms. Draft-list titles fall back to the first user message or composer text, bounded to 100 characters. Ownership filtering remains unchanged and is covered by a regression test. Old drafts are not deleted; the sidebar is a display limit. Existing per-conversation limit is 200 messages. Saved conversation context is available when that conversation is reopened; this is not a claim of automatic cross-conversation AI memory.

Verification: full baseline suite 76 passed; updated targeted tests 17 passed, including new title persistence/ownership coverage. JavaScript syntax checks passed. Local synthetic browser checks cover desktop/mobile layout, visible/muted selection, conditional X format, connection prompt and draft-only continuation, history after reload, and reopening saved content. CI will run the full updated suite on SQLite and PostgreSQL plus dependency audit and Docker/restore checks before release. No real posts, grants, charges or provider calls during tests.

Rollback: revert this PR and redeploy 1fd5a371a049ed8c72e48b24c565b09297800255. No schema change or data restore is needed. Preserve data, uploads and existing session/encryption secrets. Device emulation is not physical-device validation.
