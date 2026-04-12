# tmf-mock

**Smart TMForum Open API mock server with domain-aware seed data and cross-API referential integrity.**

Part of the TMF DevKit project — https://github.com/manojchavan23/tmf-devkit

---

Generic OpenAPI mock tools (Prism, WireMock) return random strings where you need DSLAM port IDs,
random numbers where you need VDSL2 SNR margins, and have zero awareness that a ServiceOrder must
reference a valid Service which must reference a valid Resource. `tmf-mock` fixes that.

## Supported APIs (v0.1)

| API    | Name                            | Base Path                                              |
|--------|---------------------------------|--------------------------------------------------------|
| TMF638 | Service Inventory Management    | /tmf-api/serviceInventoryManagement/v4/service         |
| TMF639 | Resource Inventory Management   | /tmf-api/resourceInventoryManagement/v4/resource       |
| TMF641 | Service Ordering Management     | /tmf-api/serviceOrdering/v4/serviceOrder               |

## Quickstart

```bash
pip install -e ".[dev]"
tmf-mock start
```

Open http://localhost:8000/docs

## CLI

```bash
tmf-mock start                          # all 3 APIs, port 8000, with seed data
tmf-mock start --apis 638,639           # only Resource + Service Inventory
tmf-mock start --port 9000              # custom port
tmf-mock start --no-seed                # empty store
tmf-mock start --reload                 # dev mode with auto-reload
```

## Key Endpoints

```
GET/POST        /tmf-api/resourceInventoryManagement/v4/resource
GET/PATCH/DELETE /tmf-api/resourceInventoryManagement/v4/resource/{id}

GET/POST        /tmf-api/serviceInventoryManagement/v4/service
GET/PATCH/DELETE /tmf-api/serviceInventoryManagement/v4/service/{id}

GET/POST        /tmf-api/serviceOrdering/v4/serviceOrder
GET/PATCH/DELETE /tmf-api/serviceOrdering/v4/serviceOrder/{id}

GET  /health
POST /admin/reset
GET  /docs
```

## Query Parameters (TMForum standard)

All list endpoints support: `?offset=0&limit=20&fields=id,name&resourceStatus=available&category=Physical`

Response headers: `X-Total-Count`, `X-Result-Count`

## Referential Integrity

```
ServiceOrder (TMF641)
    └── orderItem[].service → Service (TMF638)
                                  └── supportingResource[] → Resource (TMF639)
```

- DELETE /resource/{id} → 409 if any Service references it
- POST /service with unknown supportingResource → 422
- POST /serviceOrder with action=modify/delete on unknown service → 422

## Running Tests

```bash
pytest -v
```

## Docker

```bash
docker build -t tmf-mock .
docker run -p 8000:8000 tmf-mock

# or
docker compose up
```

## Author

Manoj Chavan — https://linkedin.com/in/manojchavan23
