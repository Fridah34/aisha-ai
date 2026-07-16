import app.models
from app.config import settings
from app.conversations.router import router as conversations_router
from app.database import Base, engine
from app.knowledge_base.router import router as knowledge_base_router
from app.products.router import router as products_router

# --- MOVE ALL ROUTER IMPORTS TO THE TOP HERE ---
from app.routes.auth import router as auth_router
from app.settings.router import router as settings_router
from app.webhook.router import router as webhook_router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

# --- APPLICATION SETUP ---
#Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AISHA AI",
    description="AI-powered Whatsapp sales assistant for African SMBs",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS,
    allow_origin_regex=settings.CORS_ALLOW_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- CUSTOM OPENAPI SCHEMALESS LOGIC ---
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    print("\n--- Generating OpenAPI Schema docs ---")
    for route in app.routes:
        if hasattr(route, "endpoint"):
            print(f"Inspecting Route: {route.path} -> [Function: {route.endpoint.__name__}]")
            
    app.openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    return app.openapi_schema

app.openapi = custom_openapi


# ======== ENDPOINTS =============

@app.get("/", tags=["Info"])
def root():
    return {
        "message": "AISHA AI API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }

@app.get("/health", tags=["Info"])
def health():
    return {"status": "healthy"}


# ========== ROUTE ISOLATION TESTING ===============

# 1. Activate Auth Router (Let's see if this one works first)
app.include_router(auth_router)

# 2. Keep these commented out! Turn them on one at a time to test them.
app.include_router(products_router)
app.include_router(conversations_router)
app.include_router(settings_router)
app.include_router(knowledge_base_router)
app.include_router(webhook_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        reload=True,
        port=8000,
    )