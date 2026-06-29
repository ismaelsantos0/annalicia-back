from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, Time, DateTime, Date
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
import uuid
import datetime

from app.database import Base

class User(Base):
    __tablename__ = "usuarios"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="standard")
    is_active = Column(Boolean, default=True)
    
    professional_id = Column(PG_UUID(as_uuid=True), ForeignKey("profissionais.id"), nullable=True)
    professional = relationship("Professional")


class Professional(Base):
    __tablename__ = "profissionais"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    profession = Column(String, nullable=True)
    contact_number = Column(String, nullable=True)
    notify_new = Column(Boolean, default=True)
    notify_cancelled = Column(Boolean, default=True)
    notify_rescheduled = Column(Boolean, default=True)
    notify_upcoming = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    slug = Column(String, unique=True, index=True, nullable=True)
    has_custom_link = Column(Boolean, default=False)

    availability_rules = relationship("AvailabilityRule", back_populates="professional", cascade="all, delete-orphan")
    appointments = relationship("Appointment", back_populates="professional")
    services = relationship("ClinicService", secondary="profissionais_servicos_clinica", back_populates="professionals")


from sqlalchemy import Table

class ClinicService(Base):
    __tablename__ = "servicos_clinica"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    duration_minutes = Column(Integer, nullable=False, default=60)
    price = Column(String, nullable=True)

    professionals = relationship("Professional", secondary="profissionais_servicos_clinica", back_populates="services")

professional_clinic_services = Table(
    "profissionais_servicos_clinica",
    Base.metadata,
    Column("professional_id", PG_UUID(as_uuid=True), ForeignKey("profissionais.id"), primary_key=True),
    Column("clinic_service_id", PG_UUID(as_uuid=True), ForeignKey("servicos_clinica.id"), primary_key=True)
)

class AvailabilityRule(Base):
    __tablename__ = "regras_disponibilidade"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    professional_id = Column(PG_UUID(as_uuid=True), ForeignKey("profissionais.id"), nullable=False)
    day_of_week = Column(Integer, nullable=False)  # 0=Dom, 1=Seg...
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)

    professional = relationship("Professional", back_populates="availability_rules")

class ClinicSettings(Base):
    __tablename__ = "configuracoes_clinica"

    id = Column(String, primary_key=True, default="default")
    clinic_name = Column(String, nullable=True)
    address = Column(String, nullable=True)
    opening_hours = Column(String, nullable=True)
    appointment_duration_minutes = Column(Integer, default=60, nullable=False)
    msg_created = Column(String, nullable=True)
    msg_confirmation = Column(String, nullable=True)
    msg_feedback_confirmed = Column(String, nullable=True)
    msg_feedback_cancelled = Column(String, nullable=True)
    services = Column(String, nullable=True)
    allow_custom_links = Column(Boolean, default=False)
    # Lembretes automáticos
    reminder_hours_before = Column(Integer, nullable=True)  # None = desativado, ex: 2 ou 24
    reminder_message = Column(String, nullable=True)
    # Customização da página pública
    primary_color = Column(String, nullable=True)  # ex: '#007bff'
    banner_image_url = Column(String, nullable=True)
    logo_url = Column(String, nullable=True)
    background_style = Column(String, default="minimalist")
    social_instagram = Column(String, nullable=True)
    social_whatsapp = Column(String, nullable=True)


class Blockout(Base):
    __tablename__ = "bloqueios"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    professional_id = Column(PG_UUID(as_uuid=True), ForeignKey("profissionais.id"), nullable=False)
    date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)

    professional = relationship("Professional")

class Appointment(Base):
    __tablename__ = "agendamentos"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    professional_id = Column(PG_UUID(as_uuid=True), ForeignKey("profissionais.id"), nullable=False)
    
    customer_name = Column(String, nullable=False)
    customer_phone = Column(String, nullable=False)
    
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    
    status = Column(String, default="pending") # pending, confirmed, cancelled, completed, pending_reschedule
    notes = Column(String, nullable=True)
    service_name = Column(String, nullable=True)
    clinical_notes = Column(String, nullable=True)
    reminder_sent = Column(Boolean, default=False)

    professional = relationship("Professional", back_populates="appointments")

class OTPVerification(Base):
    __tablename__ = "verificacoes_otp"

    phone = Column(String, primary_key=True)
    code = Column(String, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
