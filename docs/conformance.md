# TMF API Conformance Notes

This document records the TMForum standards version targeted by tmf-mock v0.1,
what is implemented, what is intentionally deferred, and how to verify conformance
against the official specifications.

---

## Target standard versions

| API    | Name                            | Version  | TMForum spec repo |
|--------|---------------------------------|----------|-------------------|
| TMF638 | Service Inventory Management    | v4.0.0   | [tmforum-apis/TMF638_ServiceInventory](https://github.com/tmforum-apis/TMF638_ServiceInventory) |
| TMF639 | Resource Inventory Management   | v4.0.0   | [tmforum-apis/TMF639_ResourceInventory](https://github.com/tmforum-apis/TMF639_ResourceInventory) |
| TMF641 | Service Ordering Management     | v4.0.0   | [tmforum-apis/TMF641_ServiceOrdering](https://github.com/tmforum-apis/TMF641_ServiceOrdering) |

The official OpenAPI/Swagger JSON specs for each API are in the `swagger/` or
`documentation/` folder of those repos. You can diff them against tmf-mock's
`/openapi.json` endpoint (served at runtime) using tools such as
[openapi-diff](https://github.com/OpenAPITools/openapi-diff) or Swagger Editor.

---

## Official Conformance Test Kits (CTKs)

TMForum publishes a Conformance Test Kit for each API. The CTK fires a sequence
of HTTP calls against a running implementation and checks mandatory fields,
HTTP status codes, pagination headers, and CRUD lifecycle.

| API    | CTK repo |
|--------|----------|
| TMF638 | [tmforum-rand/TMF638_ServiceInventory_ctk](https://github.com/tmforum-rand/TMF638_ServiceInventory_ctk) |
| TMF639 | [tmforum-rand/TMF639_ResourceInventory_ctk](https://github.com/tmforum-rand/TMF639_ResourceInventory_ctk) |
| TMF641 | [tmforum-rand/TMF641_ServiceOrdering_ctk](https://github.com/tmforum-rand/TMF641_ServiceOrdering_ctk) |

To run a CTK against a local tmf-mock instance:
```bash
tmf-mock start
# in another terminal, clone and run the CTK per its README
```

Full CTK compliance is a goal for v1.0. See the gaps section below for what
tmf-mock does not yet implement.

---

## What is implemented in v0.1

### HTTP mechanics
- ✅ Correct status codes: 200 GET/PATCH, 201 POST (with `Location` header), 204 DELETE, 404 not found
- ✅ `Content-Type: application/json` on all responses (FastAPI default)
- ✅ `X-Total-Count` header on all list endpoints
- ✅ `X-Result-Count` header on list endpoints
- ✅ `offset`, `limit`, `fields` query parameters on all list endpoints
- ✅ `resourceStatus`, `category`, `state`, `serviceType` filter parameters

### Schema
- ✅ Core entity fields for Resource (TMF639), Service (TMF638), ServiceOrder (TMF641)
- ✅ `@type`, `@baseType`, `@schemaLocation` polymorphism fields
- ✅ `relatedParty`, `note`, `serviceCharacteristic`, `resourceCharacteristic`
- ✅ `supportingResource` cross-reference from Service to Resource
- ✅ `orderItem[].service` reference in ServiceOrder

### Referential integrity (enforced at runtime)
- ✅ `DELETE /resource/{id}` → HTTP 409 if any Service has it in `supportingResource`
- ✅ `POST /service` → HTTP 422 if `supportingResource[].id` does not exist in Resource Inventory
- ✅ `PATCH /service` → HTTP 422 if new `supportingResource[].id` does not exist
- ✅ `DELETE /service/{id}` → HTTP 409 if any ServiceOrder references it
- ✅ `POST /serviceOrder` with `action=modify|delete|noChange` → HTTP 422 if service not found

### Lifecycle state machine (enforced at runtime — added v0.1.1)
- ✅ TMF639 `resourceStatus` transitions (available ↔ reserved ↔ standby → suspended)
- ✅ TMF639 `administrativeState` transitions (unlocked ↔ locked → shutdown → unlocked)
- ✅ TMF638 `state` transitions (feasibilityChecked → designed → reserved → inactive ↔ active → terminated)
- ✅ TMF641 ServiceOrder `state` transitions (acknowledged → pending|held|inProgress → completed|failed|partial|cancelled)
- ✅ TMF641 orderItem `state` transitions (same lifecycle as order)
- ✅ Terminal states are enforced — once `terminated`/`completed`/`failed`/`cancelled`, no further transitions
- ✅ Error responses include the current state, the requested state, and the set of legal transitions

### Seed data
- ✅ Realistic telecom entities: DSLAM, OLT, ONT, BTS, DSL ports
- ✅ Real-world identifiers: ONT serial numbers (HWTC prefix), IMSI (404xx format), MSISDN (+91 format)
- ✅ Realistic DSL characteristics: SNR margin, line attenuation, upstream/downstream speeds
- ✅ Cross-API integrity: seed Services reference real seed Resources; seed ServiceOrders reference real seed Services
- ✅ Lifecycle variety: mix of active/inactive services, available/reserved resources, completed/inProgress orders

---

## Known gaps vs. TMForum v4.0.0 spec (deferred to future versions)

### v0.2 targets
- ❌ `Link` headers (RFC 5988) for prev/next page navigation on list responses
- ❌ `fields` parameter on nested objects (currently top-level only)
- ❌ `405 Method Not Allowed` for explicitly unsupported HTTP methods
- ❌ Mandatory field validation beyond Pydantic's built-in required checks
  (the spec has additional semantic requirements not expressible in JSON Schema)

### v0.3 targets
- ❌ TMF688 Event Management — Hub/Listener pattern for notifications
  - All three APIs define `POST /hub` and `DELETE /hub/{id}` for event subscriptions
  - Without this, integrators cannot test their event-handler code
- ❌ `serviceOrderMilestone` on ServiceOrder (TMF641 §6.3)
- ❌ `serviceOrderJeopardy` on ServiceOrder (TMF641 §6.4)

### v1.0 target
- ❌ Full CTK pass for all three APIs
  - The CTK tests cover edge cases and error responses that tmf-mock does not
    yet validate (e.g. specific error response body schema, content negotiation)

### Out of scope for tmf-mock (by design)
- Authentication / authorisation — this is a developer mock, not a production server
- Persistent storage — in-memory by design; use `POST /admin/reset` to restore seed data
- Multi-process / distributed state — single-process in-memory store only

---

## How to verify your implementation against tmf-mock

If you are building a TMF638/639/641 implementation and want to validate it
against tmf-mock's expectations:

1. Start tmf-mock: `tmf-mock start`
2. Point your implementation at `http://localhost:8000`
3. Walk through the create → read → update → delete cycle for each entity
4. Verify that cross-API references work (create a Resource, create a Service
   referencing it, create a ServiceOrder referencing that Service)
5. Try illegal state transitions and verify your client handles 422 correctly
6. Run the official CTK against your implementation (not against tmf-mock —
   tmf-mock is not a CTK proxy)

---

## Relationship to TMForum's own tooling

| Tool | What it does | Relationship to tmf-mock |
|------|-------------|--------------------------|
| TMForum CTK | Certifies an *implementation* against the spec | Use CTK to test your BSS/OSS; use tmf-mock as the peer during integration testing |
| TMFValidator | Validates a Swagger/OpenAPI spec document | Use it to validate tmf-mock's `/openapi.json` |
| TMForum RI (Reference Implementations) | Minimal sunny-day implementations | tmf-mock provides richer seed data and stricter validation than the RIs |
| Prism / WireMock | Generic OpenAPI mock servers | tmf-mock provides domain-aware data and cross-API integrity that generic tools cannot |

---

*Last updated: v0.1.1 — state machine enforcement added*
*Maintainer: Manoj Chavan — https://linkedin.com/in/manojchavan23*
