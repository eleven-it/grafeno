from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.logging import setup_logging
from app.api.routers import lists, items, offers, alerts, recommendations

setup_logging()

app = FastAPI(
    title="Grafeno API",
    description="Plataforma de seguimiento inteligente de compras multi-canal",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(lists.router)
app.include_router(items.router)
app.include_router(offers.router)
app.include_router(alerts.router)
app.include_router(recommendations.router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "grafeno"}
