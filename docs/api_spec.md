# API Specification

Base URL: `/api`. All protected endpoints expect `Authorization: Bearer <jwt>`.
Responses are JSON. Errors use `{ "error": "..." }` with an appropriate status
(`400` validation, `401` unauthenticated, `403` forbidden, `404` not found,
`409` conflict, `429` rate-limited).

## Auth — `/api/auth`
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/register` | public | Create account (always `PUBLIC_USER`). Returns token + user. |
| POST | `/login` | public | Returns `access_token` + user. |
| GET | `/me` | any | Current user. |
| POST | `/logout` | any | Stateless logout (client discards token). |

## Dashboard — `/api/dashboard`
| GET | `/summary` | any | KPIs, risk areas, alerts, recent events, safe routes (role-scoped). |

## Events — `/api/events`
| GET | `` | any | List events (`?location=` filter). |
| GET | `/<id>` | any | Single event. |
| POST | `` | write* | Create event (recomputes risk). |
| PUT | `/<id>` | write* | Update event. |
| DELETE | `/<id>` | write* | Delete event. |

`write*` = INSTITUTION_ADMIN, TRANSPORT_OPERATOR, GOVERNMENT_AUTHORITY, SYSTEM_ANALYST, SYSTEM_ADMIN.

## Routes — `/api/routes`
| GET | `` | any | List saved routes. |
| POST | `/generate` | any | Generate a route → GeoJSON + risk score. |
| DELETE | `/<id>` | TRANSPORT_OPERATOR, SYSTEM_ANALYST, SYSTEM_ADMIN | Delete route. |

## Alerts — `/api/alerts`
| GET | `` | any | List alerts (scoped to ALL/own role; analysts+admins see all). |
| POST | `` | INSTITUTION_ADMIN, GOVERNMENT_AUTHORITY, SYSTEM_ANALYST, SYSTEM_ADMIN | Create + dispatch alert. |
| DELETE | `/<id>` | same as POST | Delete alert. |

## AI / Risk — `/api/ai`
| GET | `/risk-areas` | any | Persisted risk areas. |
| GET | `/score/<area>` | any | Live computed score for an area. |
| POST | `/recompute` | SYSTEM_ANALYST, GOVERNMENT_AUTHORITY, SYSTEM_ADMIN | Recompute all areas. |
| POST | `/score` | same | Ad-hoc score for arbitrary inputs. |

## Institutions — `/api/institutions`
| GET | `` | SYSTEM_ADMIN, INSTITUTION_ADMIN, GOVERNMENT_AUTHORITY | List. |
| GET | `/<id>` | same | Single. |
| POST | `` | SYSTEM_ADMIN | Create. |
| DELETE | `/<id>` | SYSTEM_ADMIN | Delete. |

## Admin — `/api/admin` (SYSTEM_ADMIN only)
| GET | `/users` | List users. |
| GET | `/roles` | Valid role names. |
| PUT | `/users/<id>/role` | Assign role (+ optional institution). |
| PUT | `/users/<id>/status` | Enable/disable. |
| DELETE | `/users/<id>` | Delete user. |
| GET | `/audit` | Audit log. |

## Reports — `/api/reports` (SYSTEM_ANALYST, GOVERNMENT_AUTHORITY, SYSTEM_ADMIN)
| GET | `/analytics` | Totals, users-by-role, events-by-severity, top risk areas. |
| GET | `/overview` | Totals only. |
| GET | `/model-info` | AI model metadata. |

## Health — `/api/health`
| GET | `` | public | Liveness. |
| GET | `/ready` | public | Readiness (checks DB). |

## Realtime — `/api/realtime`
| GET | `/stream` | public | Server-Sent-Events feed of latest alerts. |

### Example
```bash
TOKEN=$(curl -s localhost:5000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@saferoute.ai","password":"Admin#12345"}' | jq -r .access_token)

curl localhost:5000/api/dashboard/summary -H "Authorization: Bearer $TOKEN"
```
