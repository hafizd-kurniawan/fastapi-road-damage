# app/models/report_model.py
import enum
from typing import Optional  # Untuk type hinting kolom yang bisa NULL

from sqlalchemy import Column, Date
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy import Float, Integer, String
from sqlalchemy.sql import func  # Untuk default value seperti tanggal saat ini

from ..core.database import Base  # Impor Base dari app/core/database.py


# Definisikan Enum untuk severity dan status menggunakan Python enum
class DamageSeverityEnum(enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class ReportStatusEnum(enum.Enum):
    pending = "pending"
    in_review = "in_review"
    in_progress = "in_progress"
    completed = "completed"


class Report(Base):
    __tablename__ = "damage_reports"  # Nama tabel di database

    # Kolom-kolom tabel
    id: int = Column(Integer, primary_key=True, index=True, autoincrement=True)
    lat: float = Column(Float, nullable=False)
    lng: float = Column(Float, nullable=False)
    damage_type: str = Column(
        String(100), index=True, nullable=False
    )  # Panjang string disarankan

    severity: DamageSeverityEnum = Column(
        SQLAlchemyEnum(
            DamageSeverityEnum, name="damageseverityenum_dr", inherit_schema=True
        ),  # 'name' penting untuk tipe Enum di DB
        nullable=False,
        default=DamageSeverityEnum.medium,  # Nilai default untuk kolom ini
    )

    description: Optional[str] = Column(
        String(500), nullable=True
    )  # Kolom ini opsional

    status: ReportStatusEnum = Column(
        SQLAlchemyEnum(
            ReportStatusEnum, name="reportstatusenum_dr", inherit_schema=True
        ),
        nullable=False,
        default=ReportStatusEnum.pending,
    )

    photo_url: Optional[str] = Column(
        String(255), nullable=True
    )  # Path atau URL ke foto

    # default=func.current_date() akan menggunakan tanggal saat ini dari server DB
    # nullable=False berarti kolom ini wajib diisi (DB akan mengisinya dengan default)
    date_reported: Date = Column(Date, default=func.current_date(), nullable=False)

    def __repr__(self):
        return f"<Report(id={self.id}, type='{self.damage_type}', status='{self.status.value}')>"


print(f"OK: Model SQLAlchemy 'Report' didefinisikan di {__file__}")
