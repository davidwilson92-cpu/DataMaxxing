"""Capability policy foundation. Routes must opt into enforcement before team rollout."""
READ = frozenset({'workspace.enter', 'posts.read', 'connections.read', 'analytics.read'})
WRITE = frozenset({'posts.create', 'posts.edit', 'posts.delete', 'media.create', 'media.delete'})
PUBLISH = frozenset({'posts.publish', 'posts.schedule', 'posts.cancel'})
MANAGE = frozenset({'connections.create', 'connections.delete', 'members.read', 'members.invite', 'members.remove', 'members.role', 'workspace.edit', 'automation.pause'})
ROLE_CAPABILITIES = {
    'viewer': READ,
    'analyst': frozenset({'workspace.enter','analytics.read'}),
    'creator': READ | WRITE,
    'publisher': READ | WRITE | PUBLISH,
    'admin': READ | WRITE | PUBLISH | MANAGE,
    'owner': READ | WRITE | PUBLISH | MANAGE | frozenset({'billing.read', 'billing.manage', 'workspace.delete', 'workspace.transfer'}),
}


def permits(role, capability, *, active=True):
    return bool(active and capability in ROLE_CAPABILITIES.get(role, frozenset()))
