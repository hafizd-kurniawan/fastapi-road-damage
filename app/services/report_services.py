# app/services/report_service.py
from fastapi import Depends, HTTPException, status, UploadFile
from sqlalchemy.orm import Session  # Untuk type hinting dan dependency injection
from typing import Optional, List

# Impor repositori, skema Pydantic, dan model SQLAlchemy
from ..repositories.report_repository import ReportRepository
from .. import (
    schemas,
)  # Ini akan menyediakan schemas.ReportCreate, schemas.ReportResponse, dll.
from .. import models_db  # Ini akan menyediakan models_db.Report untuk tipe return
from ..core.database import get_db_session  # Dependency untuk mendapatkan sesi DB


class ReportService:
    def __init__(self, db: Session = Depends(get_db_session)):
        """
        Konstruktor Service, menginjeksi sesi database dan membuat instance ReportRepository.
        FastAPI akan menangani `Depends(get_db_session)` saat ReportService di-inject ke router.
        """
        self.report_repo = ReportRepository(db=db)

    async def create_report(
        self, report_data: schemas.ReportCreate, photo_file: Optional[UploadFile] = None
    ) -> models_db.Report:  # Mengembalikan model SQLAlchemy
        """
        Memproses pembuatan laporan kerusakan baru.
        Menerapkan logika bisnis jika ada, lalu memanggil repositori.
        """
        # --- Contoh Logika Bisnis Sebelum Pembuatan (Opsional) ---
        # Misalnya, validasi tambahan yang tidak bisa dilakukan oleh Pydantic saja,
        # atau normalisasi data.
        # if some_complex_validation_fails(report_data):
        #     raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Complex validation failed.")

        print(
            f"Service: Memproses pembuatan laporan untuk tipe '{report_data.damage_type}'"
        )

        try:
            created_db_report = await self.report_repo.create_report_in_db(
                report_create_data=report_data, photo_file=photo_file
            )
            # --- Contoh Logika Bisnis Setelah Pembuatan (Opsional) ---
            # Misalnya, mengirim notifikasi
            # send_notification(f"Laporan baru dibuat: ID {created_db_report.id}")
            return created_db_report
        except (
            Exception
        ) as e:  # Menangkap error umum dari repositori atau proses penyimpanan file
            print(f"Service Error saat membuat laporan: {e}")
            # Anda bisa memilih untuk melempar HTTPException yang lebih spesifik di sini
            # atau membiarkan error asli naik (jika router bisa menanganinya dengan baik).
            # Untuk sekarang, kita lempar HTTPException generik.
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Terjadi error internal saat menyimpan laporan: {str(e)}",
            )

    def get_report_by_id(
        self, report_id: int
    ) -> models_db.Report:  # Mengembalikan model SQLAlchemy
        """
        Mengambil satu laporan berdasarkan ID.
        Melempar HTTPException 404 jika tidak ditemukan.
        """
        print(f"Service: Mencari laporan dengan ID {report_id}")
        db_report = self.report_repo.get_report_by_id_from_db(report_id)
        if not db_report:
            print(f"Service: Laporan ID {report_id} tidak ditemukan.")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Laporan dengan ID {report_id} tidak ditemukan.",
            )
        return db_report

    def get_all_reports_paginated(
        self, page: int = 1, limit: int = 10
    ) -> schemas.ReportPaginatedResponse:
        """
        Mengambil semua laporan dengan paginasi.
        Mengembalikan objek skema Pydantic ReportPaginatedResponse.
        """
        # Validasi parameter paginasi dasar
        current_page = max(1, page)
        items_per_page = max(1, min(100, limit))  # Batasi limit untuk keamanan/performa

        offset = (current_page - 1) * items_per_page

        print(
            f"Service: Mengambil semua laporan, page={current_page}, limit={items_per_page}"
        )

        db_report_list: List[models_db.Report] = (
            self.report_repo.get_all_reports_from_db(skip=offset, limit=items_per_page)
        )
        total_item_count: int = self.report_repo.count_total_reports_in_db()

        total_page_count: int = (
            (total_item_count + items_per_page - 1) // items_per_page
            if total_item_count > 0
            else 0
        )

        # Konversi setiap model DB Report ke skema Pydantic ReportResponse
        # Pydantic V2 menggunakan model_validate, V1 menggunakan from_orm
        reports_for_api_response = [
            schemas.ReportResponse.model_validate(db_report)
            for db_report in db_report_list
        ]

        return schemas.ReportPaginatedResponse(
            total_reports=total_item_count,
            reports=reports_for_api_response,
            current_page=current_page,
            total_pages=total_page_count,
        )

    async def update_report(
        self,
        report_id: int,
        report_update_data: schemas.ReportUpdate,
        new_photo_file: Optional[UploadFile] = None,
    ) -> models_db.Report:  # Mengembalikan model SQLAlchemy yang sudah diupdate
        """
        Memproses pembaruan laporan yang sudah ada.
        Melempar HTTPException 404 jika laporan tidak ditemukan.
        """
        print(f"Service: Memproses update untuk laporan ID {report_id}")
        # Pertama, pastikan laporan yang akan diupdate ada (akan melempar 404 jika tidak)
        existing_report = self.get_report_by_id(
            report_id
        )  # Menggunakan metode get_report_by_id dari service ini

        # --- Contoh Logika Bisnis Sebelum Update (Opsional) ---
        # Misalnya, cek apakah status laporan memungkinkan untuk diupdate
        # if existing_report.status == models_db.ReportStatusEnum.completed:
        #     if report_update_data.status and report_update_data.status != models_db.ReportStatusEnum.completed:
        #         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
        #                             detail="Tidak dapat mengubah status laporan yang sudah 'completed'.")

        try:
            updated_db_report = await self.report_repo.update_report_in_db(
                report_id=existing_report.id,  # atau report_id
                report_update_data=report_update_data,
                new_photo_file=new_photo_file,
            )
            # Repositori akan mengembalikan None jika gagal karena suatu hal (meskipun tidak diharapkan jika objek sudah ada)
            if not updated_db_report:
                # Ini seharusnya tidak terjadi jika get_report_by_id berhasil dan repo update tidak error
                print(
                    f"Service Error: Gagal mengupdate laporan ID {report_id} di repositori meskipun ada."
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Terjadi kesalahan saat memperbarui laporan.",
                )

            # --- Contoh Logika Bisnis Setelah Update (Opsional) ---
            # Misalnya, kirim notifikasi jika status berubah
            # if report_update_data.status and report_update_data.status != existing_report.status:
            #     send_status_change_notification(updated_db_report.id, updated_db_report.status.value)
            return updated_db_report
        except Exception as e:
            print(f"Service Error saat mengupdate laporan ID {report_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Terjadi error internal saat memperbarui laporan: {str(e)}",
            )

    def delete_report(self, report_id: int) -> None:  # Tidak mengembalikan apa-apa
        """
        Memproses penghapusan laporan.
        Melempar HTTPException 404 jika laporan tidak ditemukan.
        """
        print(f"Service: Memproses penghapusan untuk laporan ID {report_id}")
        # Pertama, pastikan laporan yang akan dihapus ada
        report_to_delete = self.get_report_by_id(
            report_id
        )  # Akan melempar 404 jika tidak ada

        try:
            deleted_report_obj = self.report_repo.delete_report_from_db(
                report_id=report_to_delete.id
            )  # atau report_id
            # Repositori mengembalikan objek yang dihapus atau None jika tidak ditemukan lagi (seharusnya tidak terjadi)
            if not deleted_report_obj:
                print(
                    f"Service Error: Gagal menghapus laporan ID {report_id} di repositori meskipun ada."
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Terjadi kesalahan saat menghapus laporan.",
                )

            # --- Contoh Logika Bisnis Setelah Penghapusan (Opsional) ---
            # Misalnya, log penghapusan
            # log_deletion_event(f"Laporan ID {report_id} telah dihapus.")
            print(
                f"Service: Laporan ID {report_id} berhasil diproses untuk penghapusan."
            )
        except Exception as e:
            print(f"Service Error saat menghapus laporan ID {report_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Terjadi error internal saat menghapus laporan: {str(e)}",
            )


print(f"OK: Kelas ReportService didefinisikan di {__file__}")
