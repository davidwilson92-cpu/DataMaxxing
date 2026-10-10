"""Current-member authorization for owner-scoped web and publishing paths.

Shared-team routing remains disabled until canonical object references and RLS land.
"""
from fastapi import HTTPException
from sqlalchemy import select
from .capabilities import permits
from .tenant_migration import workspace_key


class WorkspaceDenied(RuntimeError):
    pass


def require_member(db, user_id, brand_id, capability):
    from .db import TenantWorkspace, WorkspaceMembership, User
    wid = workspace_key(user_id, brand_id)
    # Select scalar values every time: an ORM identity-map cache is not authority.
    row = db.execute(select(WorkspaceMembership.role, WorkspaceMembership.active, User.active)
        .join(TenantWorkspace,TenantWorkspace.id==WorkspaceMembership.workspace_id)
        .join(User,User.id==WorkspaceMembership.user_id)
        .where(TenantWorkspace.id==wid,TenantWorkspace.owner_user_id==user_id,
               TenantWorkspace.legacy_brand_id==brand_id,WorkspaceMembership.user_id==user_id)).first()
    if not row or not row[1] or not row[2] or not permits(row[0], capability):
        raise WorkspaceDenied('Your workspace permission is unavailable. Contact the workspace owner.')
    return wid


MUTATIONS = {
    '/api/conversation/plan':'posts.create', '/api/ai/generate':'posts.create',
    '/api/ai/rewrite':'posts.edit', '/api/ai/schedule':'posts.schedule',
    '/api/preview':'posts.read', '/api/publish-context':'posts.read',
    '/api/publish-review':'posts.publish', '/api/publish':'posts.publish', '/api/schedule':'posts.schedule',
    '/api/media':'media.create', '/api/voice/learn':'posts.edit', '/api/voice/scan-socials':'posts.edit',
    '/api/drafts':'posts.create', '/api/drafts/{draft_id}/useful':'posts.read', '/api/insights':'analytics.read',
    '/api/schedules/{schedule_id}/cancel':'posts.cancel', '/api/schedules/{schedule_id}/reschedule':'posts.schedule',
    '/drafts/{draft_id}/title':'posts.edit', '/drafts/{draft_id}/delete':'posts.delete',
    '/account/preferences':'posts.edit', '/account/connections/{connection_id}/unlink':'connections.delete',
    '/connections/review/{code}':'connections.create',
    '/brands':'workspace.edit', '/brands/switch':'workspace.enter', '/brands/{brand_id}/name':'workspace.edit',
}


def request_capability(request):
    route = getattr(request.scope.get('route'), 'path', request.url.path)
    method = request.method
    if route.startswith('/oauth/') or route in {'/callback/x','/connect/{platform}'}:
        return 'connections.create'
    if route.startswith('/connections/review/'):
        return 'connections.create'
    if route.startswith('/api/strategy'):
        if method == 'GET':return 'posts.read'
        return 'posts.edit' if route in {
            '/api/strategy/propose','/api/strategy/confirm','/api/strategy/recommend',
            '/api/strategy/actions/{action_id}/feedback','/api/strategy/actions/{action_id}/draft'} else '__deny__'
    if route.startswith('/api/series'):
        if method == 'GET':return 'posts.read'
        return {
            '/api/series':'posts.edit','/api/series/preview':'posts.edit',
            '/api/series/occurrences/{occurrence_id}/draft':'posts.edit',
            '/api/series/{series_id}/review':'posts.publish','/api/series/{series_id}/confirm':'posts.publish',
            '/api/series/{series_id}/state':'posts.cancel',
            '/api/series/occurrences/{occurrence_id}/cancel':'posts.cancel',
            '/api/series/occurrences/{occurrence_id}/time':'posts.schedule',
        }.get(route,'__deny__')
    if route == '/subscribe':return 'billing.read'
    if route.startswith('/billing/') and route != '/billing/webhook':return 'billing.manage'
    if route == '/api/drafts/{draft_id}' and method != 'GET':
        return 'posts.delete' if method=='DELETE' else 'posts.edit' if method=='PATCH' else '__deny__'
    if method not in {'GET','HEAD','OPTIONS'}:
        return MUTATIONS.get(route, '__deny__' if route.startswith('/api/') else None)
    if route.startswith('/api/analytics') or route == '/analytics':return 'analytics.read'
    if route.startswith('/api/') or route.startswith('/media/preview/') or route in {'/studio','/drafts'}:return 'posts.read'
    if route in {'/account','/onboarding/socials'}:return 'connections.read'
    return None


def authorize_request(db, request, user_id, brand_id):
    capability = request_capability(request)
    if capability is None:
        return
    try:
        wid = require_member(db,user_id,0 if capability.startswith('billing.') else brand_id,capability)
    except WorkspaceDenied as exc:
        raise HTTPException(403,str(exc)) from None
    db.info['workspace_id'] = wid
    request.state.workspace_id = wid
