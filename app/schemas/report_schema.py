from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date  # Untuk tipe data tanggal

# Impor Enum dari model database kita agar Pydantic bisa memvalidasinya
from ..models.report_model import DamageSeverityEnum, ReportStatusEnum


# Skema dasar untuk atribut inti dari sebuah laporan
# Digunakan sebagai basis untuk create dan response
class ReportBase(BaseModel):
    lat: float = Field(..., ge=-90, le=90, description="Latitude lokasi kerusakan")
    lng: float = Field(..., ge=-180, le=180, description="Longitude lokasi kerusakan")
    # Menggunakan alias 'type' karena 'type' bisa jadi kata kunci
    # Klien akan mengirim 'type', tapi di Python kita bisa pakai 'damage_type'
    damage_type: str = Field(
        ...,
        min_length=3,
        max_length=100,
        alias="type",
        description="Jenis kerusakan (misal: jalan, jembatan)",
    )
    severity: DamageSeverityEnum = Field(..., description="Tingkat keparahan kerusakan")
    description: Optional[str] = Field(
        None, max_length=500, description="Deskripsi detail kerusakan (opsional)"
    )

    # Konfigurasi Pydantic
    class Config:
        populate_by_name = (
            True  # Mengizinkan penggunaan alias ('type' menjadi 'damage_type')
        )
        from_attributes = True  # Untuk Pydantic V2 (sebelumnya orm_mode=True), memungkinkan model dibuat dari objek ORM
        use_enum_values = True  # Saat serialisasi (mengubah model ke JSON), kirim nilai string dari Enum, bukan objek Enum itu sendiri


# Skema untuk data yang dibutuhkan saat membuat laporan baru
class ReportCreate(ReportBase):
    # Saat ini tidak ada field tambahan yang spesifik untuk pembuatan,
    # karena status, photo_url, dan date_reported akan di-handle oleh backend.
    pass


# Skema untuk data yang bisa diupdate pada laporan yang sudah ada
# Semua field di sini opsional, karena klien mungkin hanya ingin update sebagian.
class ReportUpdate(BaseModel):
    lat: Optional[float] = Field(None, ge=-90, le=90)
    lng: Optional[float] = Field(None, ge=-180, le=180)
    damage_type: Optional[str] = Field(None, min_length=3, max_length=100, alias="type")
    severity: Optional[DamageSeverityEnum] = None
    description: Optional[str] = Field(None, max_length=500)
    status: Optional[ReportStatusEnum] = None  # Status bisa diupdate
    # photo_url tidak diupdate langsung via JSON di sini.
    # Update foto biasanya melibatkan unggahan file baru, yang akan ditangani terpisah.

    class Config:
        populate_by_name = True
        from_attributes = True
        use_enum_values = True


# Skema untuk data yang dikembalikan oleh API sebagai respons
# Mewarisi field dari ReportBase dan menambahkan field yang di-generate server
class ReportResponse(ReportBase):
    id: int
    status: ReportStatusEnum
    photo_url: Optional[str] = None
    date_reported: date

    # Config diwarisi dari ReportBase, tapi bisa ditimpa jika perlu.
    # Pastikan from_attributes = True agar bisa dibuat dari objek ORM Report.


# Skema untuk respons yang berisi daftar laporan dengan paginasi
class ReportPaginatedResponse(BaseModel):
    total_reports: int
    reports: List[ReportResponse]  # Daftar dari objek ReportResponse
    current_page: int
    total_pages: int
    # Anda bisa menambahkan field lain seperti 'limit' atau 'next_page_url' jika perlu

    class Config:
        from_attributes = True  # Jika 'reports' akan dibuat dari list objek ORM


print(f"OK: Skema Pydantic untuk Report didefinisikan di {__file__}")
