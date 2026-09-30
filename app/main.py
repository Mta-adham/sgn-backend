from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.uploads import UPLOAD_URL_PREFIX, ensure_upload_dir
from app.routers import admin, auth, members, public

app = FastAPI(title="SGN Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Uploaded artwork is served straight from disk. The directory is created on startup so
# a fresh deployment does not 500 on the first request for an image.
app.mount(UPLOAD_URL_PREFIX, StaticFiles(directory=str(ensure_upload_dir())), name="uploads")

app.include_router(auth.router, prefix="/api")
app.include_router(public.router, prefix="/api")
app.include_router(members.router, prefix="/api/members")
app.include_router(admin.router, prefix="/api/admin")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
