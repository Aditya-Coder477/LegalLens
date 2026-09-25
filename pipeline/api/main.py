"""
pipeline/api/main.py
====================
Main FastAPI application entrypoint for LegalLens.
Sets up CORS, middleware, security headers, and routes.
"""

from __future__ import annotations

import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .routes import router

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("legallens.api")

app = FastAPI(
    title="LegalLens API",
    description="India-first, Evidence-first GenAI Legal Information Assistant REST API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS for local Next.js frontend (default 3000, 3001)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3001", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["X-LegalLens-Corpus"] = "SYNTHETIC"
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled API error on {request.url.path}: {exc}")
    # Never expose internal database stack traces to the client
    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "message": "We couldn't complete this analysis. Your document is safe. No changes were made.",
            "status": "ERROR",
        },
    )


app.include_router(router)


@app.get("/")
def root():
    return {
        "message": "Welcome to LegalLens Evidence-first API",
        "documentation": "/docs",
        "health": "/api/v1/health",
        "synthetic": True,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("pipeline.api.main:app", host="0.0.0.0", port=8000, reload=True)
