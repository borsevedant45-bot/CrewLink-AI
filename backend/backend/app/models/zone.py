from uuid import uuid4

from sqlalchemy import Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


class Zone(Base):
    __tablename__ = "zones"

    zone_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    zone_type: Mapped[str] = mapped_column(
        Enum(
            "CONCOURSE",
            "GATE",
            "SEATING_BLOCK",
            "MEDICAL_STATION",
            "GUEST_SERVICES",
            "TRANSPORT_HUB",
            "BACK_OF_HOUSE",
            "OTHER",
            name="zone_type_enum",
            create_constraint=True,
        ),
        nullable=False,
    )
    venue_code: Mapped[str] = mapped_column(String(50), nullable=False)
    capacity_estimate: Mapped[int] = mapped_column(Integer, nullable=False)

    shifts = relationship("Shift", back_populates="zone")
    incidents = relationship("Incident", back_populates="zone")
    chat_sessions = relationship("ChatSession", back_populates="zone")
    crowd_density_readings = relationship("CrowdDensityReading", back_populates="zone")
    volunteer_position_pings = relationship("VolunteerPositionPing", back_populates="zone")

    def __repr__(self) -> str:
        return f"<Zone {self.zone_id} {self.name}>"
