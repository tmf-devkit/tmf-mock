"""
FastAPI application factory for tmf-mock.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import tmf638_router, tmf639_router, tmf641_router
from .store import get_store, set_store, Store

API_VERSION = "0.1.0"


def create_app(
    apis: list[int] | None = None,
    seed: bool = True,
    base_url: str = "http://localhost:8000",
    store: Store | None = None,
) -> FastAPI:
    enabled = set(apis or [638, 639, 641])
    _seed, _store, _base_url = seed, store, base_url

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if _store:
            set_store(_store)
        if _seed:
            s = get_store()
            if s.stats()["resources"] == 0:
                from .seed import seed_store
                seed_store(s, _base_url)
        yield

    app = FastAPI(
        title="TMF Mock Server",
        description=(
            "Smart TMForum Open API mock server with domain-aware seed data "
            "and cross-API referential integrity.\n\n"
            "Part of the **TMF DevKit** project by Manoj Chavan.\n\n"
            "Supported APIs in this instance: "
            + ", ".join(f"TMF{n}" for n in sorted(enabled))
        ),
        version=API_VERSION,
        contact={"name": "Manoj Chavan", "email": "manoj.chavan23@gmail.com"},
        license_info={"name": "Apache 2.0", "url": "https://www.apache.org/licenses/LICENSE-2.0"},
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    if 639 in enabled:
        app.include_router(tmf639_router)
    if 638 in enabled:
        app.include_router(tmf638_router)
    if 641 in enabled:
        app.include_router(tmf641_router)

    @app.get("/", tags=["Health"])
    def root():
        return {
            "name": "tmf-mock",
            "version": API_VERSION,
            "enabled_apis": sorted(enabled),
            "docs": "/docs",
            "health": "/health",
        }

    @app.get("/health", tags=["Health"])
    def health():
        s = get_store()
        return {"status": "ok", "store": s.stats()}

    @app.post("/admin/reset", tags=["Admin"])
    def reset_store():
        s = get_store()
        s.reset()
        if _seed:
            from .seed import seed_store
            result = seed_store(s, _base_url)
            return {"status": "reset", **result}
        return {"status": "reset", "seeded": False}

    return app
