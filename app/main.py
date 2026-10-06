from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.uploads import UPLOAD_URL_PREFIX, ensure_upload_dir
from app.routers import admin, auth, members, public

# The interactive docs publish the whole API surface - every route, every field name, every
# validation rule - which is exactly the map you would want before attacking it. Useful in
# development, so they stay on there and come off in production.
_docs_enabled = not settings.is_production

app = FastAPI(
    title="SGN Backend",
    docs_url="/docs" if _docs_enabled else None,
    redoc_url="/redoc" if _docs_enabled else None,
    openapi_url="/openapi.json" if _docs_enabled else None,
)

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


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    """Return `detail` as a readable string rather than FastAPI's list of error objects.

    sbn-website surfaces server errors with `errorData.detail || '<fallback>'`, so the
    default shape - a list of dicts - is truthy and gets rendered straight into the UI as
    "[object Object]". Flattening it to one sentence means a mistyped email or a missing
    field tells the user what is actually wrong, everywhere, without touching each form.
    """
    errors = exc.errors()
    if errors:
        first = errors[0]
        # Drop the leading "body"/"query" segment: the field name is the useful part.
        location = [str(part) for part in first.get("loc", ()) if part not in ("body", "query")]
        field = " ".join(location).replace("_", " ")
        message = first.get("msg", "Invalid input")
        detail = f"{field}: {message}" if field else message
    else:
        detail = "Invalid input"

    # Literal 422 rather than the status constant, which starlette has renamed between
    # versions (UNPROCESSABLE_ENTITY -> UNPROCESSABLE_CONTENT).
    return JSONResponse(status_code=422, content={"detail": detail})


app.include_router(auth.router, prefix="/api")
app.include_router(public.router, prefix="/api")
app.include_router(members.router, prefix="/api/members")
app.include_router(admin.router, prefix="/api/admin")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
