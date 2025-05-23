# app/core/config.py
import os
from pathlib import Path

import yaml
from pydantic import BaseModel, ValidationError

# --- Path Configuration ---
# File config.py ada di app/core/, jadi naik dua level untuk root proyek
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_FILE_PATH = PROJECT_ROOT / "config.yaml"

# --- Pydantic Models for Configuration Structure ---
class DatabaseSettings(BaseModel):
    url: str

class UploadSettings(BaseModel):
    directory: str

class AppSettings(BaseModel):
    database: DatabaseSettings
    uploads: UploadSettings

# --- Load Configuration Function ---
def load_configuration(config_path: Path = CONFIG_FILE_PATH) -> AppSettings:
    print(f"Mencoba memuat konfigurasi dari: {config_path}")
    if not config_path.is_file():
        message = f"FATAL: File konfigurasi '{config_path}' tidak ditemukan. Pastikan ada di root proyek."
        print(message)
        raise FileNotFoundError(message)
    try:
        with open(config_path, 'r') as f:
            raw_config = yaml.safe_load(f)
        if not raw_config:
            message = f"FATAL: File konfigurasi '{config_path}' kosong atau tidak valid."
            print(message)
            raise ValueError(message)
        # Validasi dan parsing menggunakan model Pydantic AppSettings
        return AppSettings(**raw_config)
    except yaml.YAMLError as e:
        message = f"FATAL: Error parsing YAML dari '{config_path}': {e}"
        print(message)
        raise ValueError(message) from e
    except ValidationError as e:
        message = f"FATAL: Error validasi konfigurasi dari '{config_path}': {e.errors()}"
        print(message)
        raise ValueError(message) from e
    except Exception as e: # Tangkap error lain yang mungkin terjadi
        message = f"FATAL: Terjadi error tidak terduga saat memuat konfigurasi '{config_path}': {e}"
        print(message)
        raise RuntimeError(message) from e


# --- Global Settings Instance & Exported Variables ---
try:
    settings = load_configuration()
    DATABASE_URL: str = settings.database.url
    # UPLOAD_FILES_DIRECTORY sekarang adalah objek Path absolut
    UPLOAD_FILES_DIRECTORY: Path = PROJECT_ROOT / settings.uploads.directory
except (FileNotFoundError, ValueError, RuntimeError) as e:
    print(f"KRITIKAL: Gagal memuat konfigurasi aplikasi. Aplikasi akan berhenti. Error: {e}")
    raise SystemExit(f"Konfigurasi aplikasi error: {e}") # Hentikan aplikasi jika config gagal

# --- Ensure Upload Directory Exists ---
def _ensure_upload_dir_exists():
    try:
        UPLOAD_FILES_DIRECTORY.mkdir(parents=True, exist_ok=True)
        print(f"Direktori upload dipastikan ada/dibuat: {UPLOAD_FILES_DIRECTORY}")
    except OSError as e:
        message = f"FATAL: Gagal membuat direktori upload '{UPLOAD_FILES_DIRECTORY}': {e}"
        print(message)
        raise SystemExit(message) from e

_ensure_upload_dir_exists() # Panggil fungsi ini saat modul dimuat

print(f"OK: Konfigurasi dimuat. DB URL (awal): {DATABASE_URL[:20]}..., Uploads Dir: {UPLOAD_FILES_DIRECTORY}")
