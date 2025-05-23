# app/main.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles  # Untuk menyajikan file yang diunggah
from fastapi.middleware.cors import (
    CORSMiddleware,
)  # Untuk Cross-Origin Resource Sharing
from sqlalchemy import text  # Untuk query SQL literal di health check

# Impor konfigurasi dan router
from .core.config import UPLOAD_FILES_DIRECTORY  # Path direktori upload dari config
from .routers import reports_router  # Impor router laporan kita
from .core import database  # Untuk fungsi get_db_session di health check

# Inisialisasi aplikasi FastAPI
app = FastAPI(
    title="Damage Reporter API (Step-by-Step)",
    description="API for reporting damages, built incrementally.",
    version="0.0.2",  # Naikkan versi karena ada fitur baru
)

# --- Middleware ---
# CORS Middleware (sesuaikan origins dengan kebutuhan frontend Anda)
origins = [
    "http://localhost",  # Jika frontend Anda berjalan secara lokal
    "http://localhost:3000",  # Contoh port frontend umum (React, Vue)
    "http://localhost:8080",  # Contoh port frontend lain
    "http://127.0.0.1",
    # Tambahkan domain frontend produksi Anda di sini nanti
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Daftar origin yang diizinkan
    allow_credentials=True,  # Izinkan cookies/authorization header
    allow_methods=["*"],  # Izinkan semua metode HTTP (GET, POST, PUT, DELETE, dll.)
    allow_headers=["*"],  # Izinkan semua header
)

# --- Mounting Static Files ---
# Ini akan menyajikan file dari direktori UPLOAD_FILES_DIRECTORY
# pada path URL /uploads. Misalnya, file di UPLOAD_FILES_DIRECTORY/gambar.jpg
# akan bisa diakses di http://localhost:8000/uploads/gambar.jpg
if UPLOAD_FILES_DIRECTORY.is_dir():  # Pastikan direktori ada
    app.mount(
        "/uploads",  # Path URL tempat file akan disajikan
        StaticFiles(directory=str(UPLOAD_FILES_DIRECTORY)),  # Konversi Path ke string
        name="uploaded_files_static",  # Nama unik untuk static route ini
    )
    print(f"OK: Static files dari '{UPLOAD_FILES_DIRECTORY}' di-mount pada '/uploads'.")
else:
    print(
        f"Peringatan: Direktori upload '{UPLOAD_FILES_DIRECTORY}' tidak ditemukan atau bukan direktori. File statis untuk uploads tidak akan disajikan."
    )


# --- Include API Routers ---
# Semua endpoint yang didefinisikan di reports_router
# akan memiliki prefix "/api" secara keseluruhan.
# Karena reports_router sudah memiliki prefix "/reports",
# maka endpoint create akan menjadi POST /api/reports/
app.include_router(reports_router.router, prefix="/api")


# --- Root Endpoint (Opsional, untuk cek status dasar aplikasi) ---
@app.get(
    "/", tags=["Root Health Check"], include_in_schema=False
)  # Sembunyikan dari docs jika mau
async def read_root():
    return {
        "message": "Welcome to the Damage Reporter API. API documentation available at /docs"
    }


# --- Health Check Endpoint yang Lebih Detail ---
@app.get("/health", tags=["Health Check"])
async def health_check_endpoint():
    # Coba dapatkan sesi DB menggunakan dependensi FastAPI secara manual untuk endpoint ini
    # Ini cara alternatif jika tidak ingin menginjeksi `db: Session = Depends(get_db_session)`
    # Namun, cara standar adalah dengan Depends di parameter fungsi.
    db_conn_status = "unknown"
    try:
        db = next(database.get_db_session())  # Dapatkan sesi
        db.execute(text("SELECT 1"))  # Jalankan query sederhana
        db_conn_status = "healthy"
    except Exception as e:
        db_conn_status = f"unhealthy: {str(e)}"
    finally:
        if "db" in locals() and db:  # Pastikan db terdefinisi dan ada sebelum close
            db.close()

    return {
        "application_status": "ok",
        "config_loaded": True,  # Asumsi sudah termuat jika aplikasi berjalan
        "database_connection": db_conn_status,
    }


print(f"OK: Aplikasi FastAPI utama (main.py) dikonfigurasi dengan router di {__file__}")
