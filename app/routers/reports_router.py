# app/routers/reports_router.py
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    UploadFile,
    File,
    Form,
    Query,
)
from typing import Optional, List  # List dari typing

# Impor skema Pydantic yang relevan
from ..schemas.report_schema import *

# Impor service yang akan digunakan
# from ..services.report_service import ReportService
from ..services.report_services import ReportService

# Impor Enum dari model DB jika digunakan sebagai tipe di Form atau validasi
from ..models.report_model import DamageSeverityEnum

# Buat instance APIRouter
# Semua endpoint yang didefinisikan dengan router ini akan memiliki prefix "/reports"
# dan akan dikelompokkan di bawah tag "Damage Reports" di dokumentasi OpenAPI.
router = APIRouter(prefix="/reports", tags=["Damage Reports (Step-by-Step)"])


# --- Endpoint untuk Membuat Laporan Baru ---
@router.post(
    "/",  # Path relatif terhadap prefix router, jadi ini akan menjadi /reports/
    response_model=ReportResponse,  # Menentukan skema Pydantic untuk respons
    status_code=status.HTTP_201_CREATED,  # Status HTTP untuk pembuatan berhasil
    summary="Create a New Damage Report",
    description="Creates a new damage report entry. Photo upload is optional.",
)
async def create_new_report_endpoint(
    # Dependensi: FastAPI akan menginjeksi instance ReportService
    # ReportService sendiri memiliki dependensi get_db_session yang akan di-resolve FastAPI
    report_service: ReportService = Depends(ReportService),
    # Data laporan dikirim sebagai Form fields karena ada potensi unggahan file (photo)
    # Jika tidak ada file, Anda bisa menggunakan Pydantic model langsung di body request.
    lat: float = Form(
        ..., description="Latitude of the damage location", ge=-90, le=90
    ),
    lng: float = Form(
        ..., description="Longitude of the damage location", ge=-180, le=180
    ),
    # 'type' adalah alias di Pydantic model, jadi klien mengirim 'type'
    type: str = Form(
        ...,
        min_length=3,
        max_length=100,
        description="Type of damage (e.g., road, bridge)",
    ),
    severity: DamageSeverityEnum = Form(
        ..., description="Severity of the damage (low, medium, high, critical)"
    ),  # FastAPI akan memvalidasi string ke Enum
    description: Optional[str] = Form(
        None, max_length=500, description="Optional detailed description"
    ),
    photo: Optional[UploadFile] = File(
        None, description="Optional photo evidence of the damage"
    ),
):
    print(
        f"API Endpoint: Menerima request create_new_report_endpoint dengan tipe: {type}"
    )
    # Buat objek Pydantic ReportCreate dari data Form yang diterima
    report_create_schema = ReportCreate(
        lat=lat,
        lng=lng,
        type=type,  # Pydantic akan menggunakan alias ke 'damage_type' jika dikonfigurasi di skema
        severity=severity,
        description=description,
    )
    try:
        # Panggil metode service untuk memproses pembuatan laporan
        created_db_report_model = await report_service.create_report(
            report_data=report_create_schema, photo_file=photo
        )
        # Service mengembalikan model DB, FastAPI akan otomatis mengonversinya ke
        # ReportResponse (response_model) menggunakan Pydantic .model_validate() (atau .from_orm())
        print(
            f"API Endpoint: Laporan berhasil dibuat dengan ID: {created_db_report_model.id}"
        )
        return created_db_report_model
    except HTTPException as e:
        # Jika service melempar HTTPException (misalnya, validasi gagal), teruskan saja
        raise e
    except ValueError as e:  # Tangkap error validasi spesifik atau lainnya
        print(f"API Endpoint Error Validasi saat membuat laporan: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )
    except Exception as e:
        # Tangkap error tak terduga lainnya
        print(f"API Endpoint Error Internal Tidak Terduga saat membuat laporan: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Terjadi error internal saat memproses permintaan Anda.",
        )


# --- Endpoint untuk Mendapatkan Semua Laporan (Paginated) ---
@router.get(
    "/",
    response_model=ReportPaginatedResponse,
    summary="Get All Damage Reports (Paginated)",
)
async def get_all_reports_endpoint(
    report_service: ReportService = Depends(ReportService),
    page: int = Query(1, ge=1, description="Nomor halaman, dimulai dari 1"),
    limit: int = Query(10, ge=1, le=100, description="Jumlah item per halaman (1-100)"),
):
    print(
        f"API Endpoint: Menerima request get_all_reports_endpoint (page={page}, limit={limit})"
    )
    try:
        # Service sudah mengembalikan objek ReportPaginatedResponse yang sesuai
        paginated_response = report_service.get_all_reports_paginated(
            page=page, limit=limit
        )
        return paginated_response
    except Exception as e:
        print(
            f"API Endpoint Error Internal Tidak Terduga saat mengambil semua laporan: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Terjadi error internal saat mengambil daftar laporan.",
        )


# --- Endpoint untuk Mendapatkan Laporan Berdasarkan ID ---
@router.get(
    "/{report_id}",
    response_model=ReportResponse,
    summary="Get a Specific Damage Report by ID",
)
async def get_report_by_id_endpoint(
    report_id: int,  # Path parameter, FastAPI otomatis validasi sebagai integer
    report_service: ReportService = Depends(ReportService),
):
    print(
        f"API Endpoint: Menerima request get_report_by_id_endpoint untuk ID: {report_id}"
    )
    try:
        db_report_model = report_service.get_report_by_id(report_id)
        # Service akan melempar HTTPException 404 jika tidak ditemukan
        # FastAPI akan otomatis konversi model DB ke response_model
        return db_report_model
    except HTTPException as e:  # Tangkap 404 dari service
        raise e
    except Exception as e:
        print(
            f"API Endpoint Error Internal Tidak Terduga saat mengambil laporan ID {report_id}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Terjadi error internal saat mengambil laporan {report_id}.",
        )


# --- Endpoint untuk Memperbarui Laporan ---
@router.put(
    "/{report_id}",
    response_model=ReportResponse,
    summary="Update an Existing Damage Report",
)
async def update_report_endpoint(
    report_id: int,
    # Untuk PUT, kita terima semua field sebagai Form karena ada potensi update foto.
    # Ini berarti klien HARUS mengirim sebagai multipart/form-data jika ingin update foto.
    # Jika hanya teks, klien tetap bisa mengirim multipart tanpa file, atau Anda bisa buat endpoint PATCH terpisah untuk JSON.
    report_service: ReportService = Depends(ReportService),
    lat: Optional[float] = Form(None, ge=-90, le=90),
    lng: Optional[float] = Form(None, ge=-180, le=180),
    type: Optional[str] = Form(
        None, min_length=3, max_length=100, alias="type_update"
    ),  # Gunakan alias berbeda jika perlu
    severity: Optional[DamageSeverityEnum] = Form(None),
    description: Optional[str] = Form(None, max_length=500),
    status: Optional[ReportStatusEnum] = Form(None),
    new_photo: Optional[UploadFile] = File(
        None, description="New photo to replace the existing one, if any"
    ),
):
    print(
        f"API Endpoint: Menerima request update_report_endpoint untuk ID: {report_id}"
    )

    # Buat objek ReportUpdate dari Form fields yang diterima.
    # Hanya sertakan field yang nilainya bukan None untuk update parsial.
    update_data_dict = {}
    if lat is not None:
        update_data_dict["lat"] = lat
    if lng is not None:
        update_data_dict["lng"] = lng
    if type is not None:
        update_data_dict["damage_type"] = (
            type  # Pydantic akan handle alias 'type' di skema
        )
    if severity is not None:
        update_data_dict["severity"] = severity
    if description is not None:
        update_data_dict["description"] = description
    if status is not None:
        update_data_dict["status"] = status

    # Validasi dengan Pydantic model
    try:
        report_update_schema = ReportUpdate(**update_data_dict)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.errors()
        )

    try:
        updated_db_report_model = await report_service.update_report(
            report_id=report_id,
            report_update_data=report_update_schema,
            new_photo_file=new_photo,
        )
        return updated_db_report_model  # FastAPI konversi ke response_model
    except HTTPException as e:
        raise e
    except Exception as e:
        print(
            f"API Endpoint Error Internal Tidak Terduga saat mengupdate laporan ID {report_id}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Terjadi error internal saat memperbarui laporan {report_id}.",
        )


# --- Endpoint untuk Menghapus Laporan ---
@router.delete(
    "/{report_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a Damage Report by ID",
)
async def delete_report_endpoint(
    report_id: int, report_service: ReportService = Depends(ReportService)
):
    print(
        f"API Endpoint: Menerima request delete_report_endpoint untuk ID: {report_id}"
    )
    try:
        report_service.delete_report(report_id)
        # Tidak ada return body untuk status 204
    except HTTPException as e:  # Tangkap 404 dari service
        raise e
    except Exception as e:
        print(
            f"API Endpoint Error Internal Tidak Terduga saat menghapus laporan ID {report_id}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Terjadi error internal saat menghapus laporan {report_id}.",
        )


print(f"OK: Router API untuk Report didefinisikan di {__file__}")
