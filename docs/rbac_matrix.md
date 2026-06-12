# RBAC Matrix

Roles are stored in the `users.role` column and validated server-side on every
protected request. Clients cannot set or change their own role.

Legend: ✅ allowed · — denied (HTTP 403)

| Capability | PUBLIC_USER | SYSTEM_ADMIN |
|---|:--:|:--:|
| View dashboard | ✅ | ✅ |
| Read/create/edit/delete events | ✅ | ✅ |
| Generate route | ✅ | ✅ |
| Delete route | — | ✅ |
| Read risk areas | ✅ | ✅ |
| Recompute risk | — | ✅ |
| View analytics / reports | — | ✅ |
| Use AI chat | ✅ | ✅ |
| **Manage users & assign roles** | — | ✅ |
| View audit log | — | ✅ |
| Emergency broadcast | — | ✅ |

## Enforcement

- `utils/rbac.require_roles(*roles)` and `middleware/rbac_middleware.require_permission(capability)`
  wrap every protected view.
- The decorator runs `verify_jwt_in_request()` then loads the user from the DB
  and checks the **persisted** role — never a value sent by the client.
- Missing/invalid token → `401`. Authenticated but insufficient role → `403`.
- The capability → roles mapping is defined once in
  `backend/middleware/rbac_middleware.py::PERMISSION_MATRIX`.
