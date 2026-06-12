"""RBAC middleware.

Builds on ``utils.rbac.require_roles`` and adds a declarative permission matrix
so access rules are documented in one place. The decorator here is the one the
route layer imports.
"""
from utils.rbac import Role, require_roles, current_user  # re-exported

# Capability -> roles allowed. Documented centrally; mirrored in docs/rbac_matrix.md
PERMISSION_MATRIX = {
    "event:read": Role.all(),
    "event:write": Role.all(),
    "route:read": Role.all(),
    "route:generate": Role.all(),
    "route:delete": [Role.SYSTEM_ADMIN],
    "ai:recompute": [Role.SYSTEM_ADMIN],
    "analytics:read": [Role.SYSTEM_ADMIN],
    "user:manage": [Role.SYSTEM_ADMIN],
    "chat:use": Role.all(),
}


def roles_for(capability: str):
    return PERMISSION_MATRIX.get(capability, [Role.SYSTEM_ADMIN])


def require_permission(capability: str):
    """Decorator that enforces the roles configured for ``capability``."""
    return require_roles(*roles_for(capability))


__all__ = ["Role", "require_roles", "require_permission", "roles_for",
           "current_user", "PERMISSION_MATRIX"]
