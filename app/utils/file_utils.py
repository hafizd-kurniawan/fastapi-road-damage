# app/utils/file_utils.py
import os
from uuid import uuid4  # Untuk menghasilkan nama file unik
from pathlib import Path  # Untuk manipulasi path yang lebih baik
from fastapi import UploadFile  # Tipe data untuk file yang diunggah
import shutil  # Untuk operasi file level tinggi seperti copy
from typing import Optional

# Impor direktori upload dari konfigurasi
from ..core.config import UPLOAD_FILES_DIRECTORY

# Ekstensi file gambar yang diizinkan (bisa juga ditaruh di config.yaml jika sering berubah)
VALID_IMAGE_EXTENSIONS = [
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
]  # Tambahkan .gif sebagai contoh


async def save_upload_file_to_disk(
    upload_file: UploadFile,
    destination_dir: Path = UPLOAD_FILES_DIRECTORY,  # Menggunakan path dari config
) -> Optional[str]:
    """
    Menyimpan file yang diunggah ke direktori tujuan.
    Mengembalikan path URL relatif jika berhasil, None jika gagal atau tipe file tidak valid.
    """
    if not upload_file or not upload_file.filename:
        return None  # Tidak ada file atau tidak ada nama file

    original_filename, file_extension = os.path.splitext(upload_file.filename)
    file_extension = file_extension.lower()  # Normalisasi ke huruf kecil

    if file_extension not in VALID_IMAGE_EXTENSIONS:
        print(
            f"Peringatan: Ekstensi file tidak valid '{file_extension}' untuk file '{original_filename}'. File tidak disimpan."
        )
        return None  # Atau bisa raise HTTPException(400, "Invalid file type")

    # Buat nama file yang unik untuk menghindari konflik
    unique_filename_stem = str(uuid4())  # Bagian nama file tanpa ekstensi
    unique_filename_with_ext = f"{unique_filename_stem}{file_extension}"

    file_save_path: Path = destination_dir / unique_filename_with_ext

    try:
        # Cara modern dan direkomendasikan untuk menyimpan UploadFile di FastAPI (async)
        # FastAPI akan menangani pembacaan stream secara efisien.
        with open(file_save_path, "wb") as buffer:
            # shutil.copyfileobj(upload_file.file, buffer) # Ini untuk file-like object sinkron
            # Untuk UploadFile async, kita baca per chunk
            async for chunk in upload_file.chunks():  # Default chunk size 64KB
                buffer.write(chunk)

        # Penting: Tutup stream file setelah selesai, terutama jika Anda membuka secara manual.
        # Namun, jika Anda hanya mengiterasi upload_file.chunks() dan FastAPI menangani
        # pembukaan stream awal, FastAPI juga yang akan menutupnya.
        # Untuk UploadFile, .close() disarankan setelah selesai berinteraksi dengannya.
        await upload_file.close()

        print(
            f"File '{unique_filename_with_ext}' berhasil disimpan ke '{file_save_path}'"
        )
        # Kembalikan path URL relatif yang akan digunakan untuk mengakses file via StaticFiles
        # Jika StaticFiles di-mount pada "/uploads", maka URL akan menjadi "/uploads/namafile.jpg"
        return f"/uploads/{unique_filename_with_ext}"
    except IOError as e:
        print(f"IOError saat menyimpan file '{unique_filename_with_ext}': {e}")
    except Exception as e:
        print(
            f"Error tidak terduga saat menyimpan file '{unique_filename_with_ext}': {e}"
        )
        # Jika penyimpanan gagal, coba hapus file yang mungkin sudah terbuat sebagian
        if file_save_path.exists():
            try:
                os.remove(file_save_path)
                print(f"File parsial '{file_save_path}' dihapus setelah error.")
            except Exception as remove_e:
                print(
                    f"Gagal menghapus file parsial '{file_save_path}' setelah error: {remove_e}"
                )
    return None  # Gagal menyimpan file


print(f"OK: Utilitas file didefinisikan di {__file__}")
