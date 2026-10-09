"""Explicit grants for the currently mapped draft service, not future routes.

Do not expand automatically from ORM metadata. Additional services need their
own reviewed grants and integration tests before their routes are activated.
"""
from sqlalchemy import text


DRAFT_TABLE_GRANTS = {
    'nova_drafts': {'SELECT','DELETE'},
    'zova_workspaces': {'SELECT'},  # Canonical insert ownership check.
    'zova_content_series': {'SELECT'},
    'zova_series_occurrences': {'SELECT'},
    'zova_publish_reviews': {'DELETE'},
}
SCOPE_COLUMNS = {'user_id','brand_id','workspace_id'}
DRAFT_COLUMN_GRANTS = {
    ('nova_drafts','INSERT'): SCOPE_COLUMNS | {
        'brief','title','instruction','platforms_json','variants_json','workspace_json',
        'revision','thread_length','status','created_at','updated_at'},
    ('nova_drafts','UPDATE'): {
        'brief','title','instruction','platforms_json','variants_json','workspace_json',
        'revision','thread_length','updated_at'},
    ('nova_media_assets','SELECT'): SCOPE_COLUMNS | {'id','filename','mime_type'},
    ('nova_activity','SELECT'): SCOPE_COLUMNS | {'id','draft_id','platform','url'},
    ('zova_publications','SELECT'): SCOPE_COLUMNS | {'id','draft_id'},
    ('nova_scheduled_posts','SELECT'): SCOPE_COLUMNS | {'id','draft_id'},
    ('zova_publish_reviews','SELECT'): SCOPE_COLUMNS | {'code','draft_id'},
    ('zova_strategy_actions','SELECT'): SCOPE_COLUMNS | {'id','draft_id'},
    ('zova_strategy_actions','UPDATE'): {'draft_id','status','updated_at'},
    ('zova_series_occurrences','UPDATE'): {'draft_id','status'},
}


def verify_sequence_grants(c, *, draft_ids=False):
    """Only the draft allocator may advance; no service may reset a sequence."""
    expected = None
    if draft_ids:
        q=c.dialect.identifier_preparer.quote
        schema=q(c.scalar(text('SELECT current_schema()')))
        expected=c.scalar(text('SELECT CAST(pg_get_serial_sequence(:table,\'id\') AS regclass)::oid'),
                          {'table':f'{schema}.nova_drafts'})
        if expected is None:
            raise ValueError('Draft identifier sequence is missing')
    rows=c.execute(text('''SELECT t.oid,
        has_sequence_privilege(session_user,t.oid,'USAGE') AS usage,
        has_sequence_privilege(session_user,t.oid,'SELECT') AS read,
        has_sequence_privilege(session_user,t.oid,'UPDATE') AS reset
        FROM pg_class t JOIN pg_namespace n ON n.oid=t.relnamespace
        WHERE n.nspname=current_schema() AND t.relkind='S' ''')).mappings()
    for row in rows:
        if row['usage'] != (row['oid']==expected) or row['read'] or row['reset']:
            raise ValueError('Service sequence grants do not match the manifest')
