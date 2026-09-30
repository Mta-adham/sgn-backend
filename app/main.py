from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import admin, auth, members, public

app = FastAPI(title="SGN Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(public.router, prefix="/api")
app.include_router(members.router, prefix="/api/members")
app.include_router(admin.router, prefix="/api/admin")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
