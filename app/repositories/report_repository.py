# app/repositories/report_repository.py
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional
from fastapi import UploadFile  # Untuk tipe data file yang diunggah
import os
from uuid import uuid4  # Untuk menghasilkan nama file unik
from pathlib import Path  # Untuk manipulasi path
import shutil  # Untuk operasi file

# Impor model database (SQLAlchemy) dan skema Pydantic
from .. import models_db  # Ini akan menyediakan models_db.Report
from .. import (
    schemas,
)  # Ini akan menyediakan schemas.ReportCreate, schemas.ReportUpdate

# Impor direktori upload dari konfigurasi
from ..core.config import UPLOAD_FILES_DIRECTORY

# Ekstensi file gambar yang diizinkan (bisa juga dari config jika perlu)
VALID_IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png"]


class ReportRepository:
    def __init__(self, db: Session):
        self.db = db

    async def _save_photo_to_disk(self, photo: UploadFile) -> Optional[str]:
        """
        Internal helper method untuk menyimpan file foto yang diunggah.
        Mengembalikan path URL relatif jika berhasil, None jika gagal.
        """
        if not photo or not photo.filename:
            return None

        original_filename, file_extension = os.path.splitext(photo.filename)
        file_extension = file_extension.lower()

        if file_extension not in VALID_IMAGE_EXTENSIONS:
            print(
                f"Peringatan: Ekstensi file tidak valid '{file_extension}' untuk file '{original_filename}'."
            )
            return None

        unique_filename_stem = str(uuid4())
        unique_filename = f"{unique_filename_stem}{file_extension}"
        file_path: Path = UPLOAD_FILES_DIRECTORY / unique_filename

        try:
            with open(file_path, "wb") as buffer:
                async for chunk in photo.chunks():  # Baca dan tulis per chunk
                    buffer.write(chunk)
            await photo.close()  # Tutup stream UploadFile setelah selesai
            print(f"Foto berhasil disimpan: {file_path}")
            # Kembalikan path URL relatif yang akan digunakan untuk mengakses file
            return f"/uploads/{unique_filename}"
        except Exception as e:
            print(f"Error saat menyimpan foto '{unique_filename}': {e}")
            if file_path.exists():  # Hapus file parsial jika penyimpanan gagal
                try:
                    os.remove(file_path)
                except Exception as remove_e:
                    print(f"Error menghapus file parsial '{file_path}': {remove_e}")
            return None

    def _delete_photo_from_disk(self, photo_url_value: Optional[str]):
        """
        Internal helper method untuk menghapus file foto dari disk.
        """
        if not photo_url_value:
            return

        try:
            filename = os.path.basename(
                photo_url_value
            )  # Dapatkan nama file dari URL relatif
            if not filename or filename == photo_url_value.strip("/"):  # Keamanan dasar
                print(
                    f"Filename tidak valid dari photo_url untuk penghapusan: {photo_url_value}"
                )
                return

            file_path: Path = UPLOAD_FILES_DIRECTORY / filename
            if file_path.is_file():  # Cek apakah file ada sebelum menghapus
                os.remove(file_path)
                print(f"File foto dihapus dari disk: {file_path}")
            # else: # Opsional: log jika file tidak ditemukan
            #     print(f"File foto tidak ditemukan untuk dihapus: {file_path}")
        except Exception as e:
            print(f"Error saat menghapus file foto untuk URL '{photo_url_value}': {e}")

    async def create_report_in_db(
        self,
        report_create_data: schemas.ReportCreate,
        photo_file: Optional[UploadFile] = None,
    ) -> models_db.Report:
        """
        Membuat entri laporan baru di database dan menyimpan foto jika ada.
        """
        actual_photo_url: Optional[str] = None
        if photo_file:
            actual_photo_url = await self._save_photo_to_disk(photo_file)
            if not actual_photo_url and photo_file.filename:
                print(
                    f"Peringatan: Foto '{photo_file.filename}' gagal disimpan. Laporan akan dibuat tanpa foto."
                )

        # Pydantic model_dump dengan by_alias=True akan menggunakan alias "type" dari skema
        # untuk mengisi field "damage_type" di dictionary jika nama field di model Pydantic
        # adalah "damage_type" dan di-alias sebagai "type".
        # Jika field di Pydantic Anda adalah "damage_type", maka by_alias tidak diperlukan untuk field itu.
        # Kita asumsikan ReportCreate sudah menggunakan field yang benar (damage_type)
        # atau aliasnya (type) dikonfigurasi dengan benar di Pydantic model.
        report_dict_for_db = report_create_data.model_dump(
            by_alias=True
        )  # Gunakan by_alias jika skema menggunakan alias

        db_report_obj = models_db.Report(
            **report_dict_for_db, photo_url=actual_photo_url
        )

        self.db.add(db_report_obj)
        self.db.commit()
        self.db.refresh(db_report_obj)
        print(f"Repo: Laporan baru dibuat di DB dengan ID: {db_report_obj.id}")
        return db_report_obj

    def get_report_by_id_from_db(self, report_id: int) -> Optional[models_db.Report]:
        """
        Mengambil satu laporan dari database berdasarkan ID.
        """
        report = (
            self.db.query(models_db.Report)
            .filter(models_db.Report.id == report_id)
            .first()
        )
        if report:
            print(f"Repo: Laporan dengan ID {report_id} ditemukan.")
        else:
            print(f"Repo: Laporan dengan ID {report_id} tidak ditemukan.")
        return report

    def get_all_reports_from_db(
        self, skip: int = 0, limit: int = 10
    ) -> List[models_db.Report]:
        """
        Mengambil daftar laporan dari database dengan paginasi dan pengurutan.
        """
        reports = (
            self.db.query(models_db.Report)
            .order_by(desc(models_db.Report.id))
            .offset(skip)
            .limit(limit)
            .all()
        )
        print(
            f"Repo: Mengambil {len(reports)} laporan dari DB (skip={skip}, limit={limit})"
        )
        return reports

    def count_total_reports_in_db(self) -> int:
        """
        Menghitung total jumlah laporan di database.
        """
        total_count = self.db.query(func.count(models_db.Report.id)).scalar() or 0
        print(f"Repo: Total laporan di DB: {total_count}")
        return total_count

    async def update_report_in_db(
        self,
        report_id: int,
        report_update_data: schemas.ReportUpdate,
        new_photo_file: Optional[UploadFile] = None,
    ) -> Optional[models_db.Report]:
        """
        Memperbarui laporan yang sudah ada di database.
        """
        db_report_obj = self.get_report_by_id_from_db(report_id)
        if not db_report_obj:
            return None  # Laporan tidak ditemukan

        current_photo_url = db_report_obj.photo_url  # Simpan URL foto lama

        # Update field dari report_update_data
        update_data_dict = report_update_data.model_dump(
            exclude_unset=True, by_alias=True
        )  # Hanya update field yang dikirim
        for key, value in update_data_dict.items():
            # Pastikan nama field (setelah alias) ada di model SQLAlchemy sebelum setattr
            if hasattr(db_report_obj, key):
                setattr(db_report_obj, key, value)
            # else: # Handle jika key dari Pydantic tidak cocok dengan atribut model DB
            #     print(f"Peringatan: Atribut '{key}' tidak ditemukan di model Report saat update.")

        if new_photo_file:
            new_actual_photo_url = await self._save_photo_to_disk(new_photo_file)
            if new_actual_photo_url:  # Jika foto baru berhasil disimpan
                if current_photo_url:  # Jika ada foto lama, hapus
                    self._delete_photo_from_disk(current_photo_url)
                db_report_obj.photo_url = new_actual_photo_url  # Update dengan URL baru
            elif new_photo_file.filename:  # Jika ada usaha upload foto baru tapi gagal
                print(
                    f"Peringatan: Foto baru '{new_photo_file.filename}' gagal disimpan saat update. Foto lama (jika ada) dipertahankan."
                )

        self.db.commit()
        self.db.refresh(db_report_obj)
        print(f"Repo: Laporan dengan ID {report_id} berhasil diupdate.")
        return db_report_obj

    def delete_report_from_db(self, report_id: int) -> Optional[models_db.Report]:
        """
        Menghapus laporan dari database berdasarkan ID.
        Mengembalikan objek laporan yang dihapus jika berhasil, None jika tidak ditemukan.
        """
        db_report_obj = self.get_report_by_id_from_db(report_id)
        if db_report_obj:
            photo_url_to_delete = (
                db_report_obj.photo_url
            )  # Ambil URL foto sebelum objek dihapus dari sesi

            self.db.delete(db_report_obj)
            self.db.commit()  # Commit penghapusan dari DB dulu

            if photo_url_to_delete:  # Baru hapus file fisik setelah commit DB
                self._delete_photo_from_disk(photo_url_to_delete)

            print(f"Repo: Laporan dengan ID {report_id} berhasil dihapus dari DB.")
            return db_report_obj  # Mengembalikan objek yang sudah di-detach
        print(f"Repo: Laporan dengan ID {report_id} tidak ditemukan untuk dihapus.")
        return None


print(f"OK: Kelas ReportRepository didefinisikan di {__file__}")
