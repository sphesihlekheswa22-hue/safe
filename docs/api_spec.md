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
| GET | `/summary` | any | KPIs, risk areas, recent events, safe routes, analytics block. |

## Events — `/api/events`
| GET | `` | any | List events (`?location=` filter). |
| GET | `/<id>` | any | Single event. |
| POST | `` | any | Create event (recomputes risk). |
| PUT | `/<id>` | any | Update event. |
| DELETE | `/<id>` | any | Delete event. |

## Routes — `/api/routes`
| GET | `` | any | List saved routes. |
| POST | `/generate` | any | Generate a route → GeoJSON + risk score. |
| DELETE | `/<id>` | SYSTEM_ADMIN | Delete route. |

## AI / Risk — `/api/ai`
| GET | `/risk-areas` | any | Persisted risk areas. |
| GET | `/map-data` | any | Bundled map data (areas + incidents). |
| GET | `/score/<area>` | any | Live computed score for an area. |
| POST | `/recompute` | SYSTEM_ADMIN | Recompute all areas. |
| POST | `/score` | SYSTEM_ADMIN | Ad-hoc score for arbitrary inputs. |

## Admin — `/api/admin` (SYSTEM_ADMIN only)
| GET | `/users` | List users. |
| GET | `/roles` | Valid role names (`PUBLIC_USER`, `SYSTEM_ADMIN`). |
| PUT | `/users/<id>/role` | Assign role. |
| PUT | `/users/<id>/status` | Enable/disable. |
| DELETE | `/users/<id>` | Delete user. |
| POST | `/users` | Create user with chosen role. |
| GET | `/audit` | Audit log. |
| GET | `/system` | System health + counts. |
| POST | `/broadcast` | Emergency incident broadcast. |

## Reports — `/api/reports` (SYSTEM_ADMIN only)
| GET | `/analytics` | Totals, users-by-role, events-by-severity, top risk areas. |
| GET | `/overview` | Totals only. |
| GET | `/model-info` | AI model metadata. |

## Chat — `/api/chat`
| POST | `/message` | any | AI assistant (safety-focused). |

## Health — `/api/health`
| GET | `` | public | Liveness. |
| GET | `/ready` | public | Readiness (checks DB). |

### Example
```bash
TOKEN=$(curl -s localhost:5000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@saferoute.ai","password":"Admin#12345"}' | jq -r .access_token)

curl localhost:5000/api/dashboard/summary -H "Authorization: Bearer $TOKEN"
```
