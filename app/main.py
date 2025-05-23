# app/main.py
from fastapi import (
    FastAPI,
    Request,
    Depends,
)  # Pastikan Request dan Depends diimpor jika digunakan
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from pathlib import Path

from .core.config import UPLOAD_FILES_DIRECTORY
from .routers import reports_router
from .core import database

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

app = FastAPI(
    title="Damage Reporter API (Step-by-Step with Templates)",
    description="API and Web Interface for reporting damages.",
    version="0.0.3",
)

# ... (Middleware CORS seperti sebelumnya) ...
origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:8080",
    "http://127.0.0.1",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = BASE_DIR / "static"
if not STATIC_DIR.exists():
    STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static_custom")

if UPLOAD_FILES_DIRECTORY.is_dir():
    app.mount(
        "/uploads",
        StaticFiles(directory=str(UPLOAD_FILES_DIRECTORY)),
        name="uploaded_files_static",
    )
else:
    print(f"Peringatan: Direktori upload '{UPLOAD_FILES_DIRECTORY}' tidak ditemukan.")

app.include_router(reports_router.router, prefix="/api")


# --- Endpoint untuk Menyajikan Halaman Utama ---
# TAMBAHKAN name="read_root" DI SINI
@app.get("/", tags=["Web Interface"], include_in_schema=False, name="read_root")
async def serve_homepage(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# --- Health Check Endpoint (seperti sebelumnya) ---
@app.get(
    "/health", tags=["Health Check"], name="health_check"
)  # Beri nama juga untuk health check jika perlu
async def health_check_endpoint():
    db_conn_status = "unknown"
    try:
        db = next(database.get_db_session())
        db.execute(text("SELECT 1"))
        db_conn_status = "healthy"
    except Exception as e:
        db_conn_status = f"unhealthy: {str(e)}"
    finally:
        if "db" in locals() and db:
            db.close()

    return {
        "application_status": "ok",
        "config_loaded": True,
        "database_connection": db_conn_status,
    }


print(
    f"OK: Aplikasi FastAPI utama (main.py) dikonfigurasi dengan router dan templates di {__file__}"
)
