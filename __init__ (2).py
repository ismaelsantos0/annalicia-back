from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime, time, date
from typing import Optional, List

# ─── Auth ───
class Token(BaseModel):
    access_token: str
    token_type: str

# ─── Users ───
class UserCreate(BaseModel):
    username: str
    password: str
    role: Optional[str] = "standard"

class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "clinica"
    professional_id: Optional[UUID] = None

class UserUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    professional_id: Optional[UUID] = None

class UserOut(BaseModel):
    id: UUID
    username: str
    role: str
    is_active: bool
    professional_id: Optional[UUID] = None

    model_config = ConfigDict(from_attributes=True)


# ─── Professional ───
class ProfessionalCreate(BaseModel):
    name: str
    profession: Optional[str] = None
    contact_number: Optional[str] = None
    notify_new: bool = True
    notify_cancelled: bool = True
    notify_rescheduled: bool = True
    notify_upcoming: bool = True
    is_active: bool = True
    slug: Optional[str] = None
    has_custom_link: bool = False

class ProfessionalUpdate(BaseModel):
    name: Optional[str] = None
    profession: Optional[str] = None
    contact_number: Optional[str] = None
    notify_new: Optional[bool] = None
    notify_cancelled: Optional[bool] = None
    notify_rescheduled: Optional[bool] = None
    notify_upcoming: Optional[bool] = None
    is_active: Optional[bool] = None
    slug: Optional[str] = None
    has_custom_link: Optional[bool] = None

class ProfessionalResponse(ProfessionalCreate):
    id: UUID
    model_config = ConfigDict(from_attributes=True)


# ─── Availability Rule ───
class AvailabilityRuleCreate(BaseModel):
    professional_id: UUID
    day_of_week: int
    start_time: time
    end_time: time

class AvailabilityRuleResponse(AvailabilityRuleCreate):
    id: UUID
    model_config = ConfigDict(from_attributes=True)


# ─── Blockouts ───
class BlockoutCreate(BaseModel):
    professional_id: UUID
    date: date
    start_time: time
    end_time: time

class BlockoutResponse(BlockoutCreate):
    id: UUID
    model_config = ConfigDict(from_attributes=True)


# ─── Appointment ───
class AppointmentCreate(BaseModel):
    professional_id: UUID
    customer_name: str
    customer_phone: str
    start_time: datetime
    notes: Optional[str] = None
    otp_code: Optional[str] = None
    service_name: Optional[str] = None

class OTPRequest(BaseModel):
    customer_phone: str
    customer_name: str
    professional_id: UUID

class AppointmentResponse(BaseModel):
    id: UUID
    professional_id: UUID
    professional_name: Optional[str] = None
    customer_name: str
    customer_phone: str
    start_time: datetime
    end_time: datetime
    status: str
    notes: Optional[str] = None
    service_name: Optional[str] = None
    clinical_notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class AppointmentStatusUpdate(BaseModel):
    status: str
    notes: Optional[str] = None

class AppointmentReschedule(BaseModel):
    start_time: datetime

class AppointmentComplete(BaseModel):
    clinical_notes: str


# ─── Settings ───
class ClinicSettingsUpdate(BaseModel):
    clinic_name: Optional[str] = None
    address: Optional[str] = None
    opening_hours: Optional[str] = None
    appointment_duration_minutes: int
    msg_created: Optional[str] = None
    msg_confirmation: Optional[str] = None
    msg_feedback_confirmed: Optional[str] = None
    msg_feedback_cancelled: Optional[str] = None
    services: Optional[str] = None
    allow_custom_links: Optional[bool] = None
    # Lembretes automáticos
    reminder_hours_before: Optional[int] = None
    reminder_message: Optional[str] = None
    # Customização visual
    primary_color: Optional[str] = None
    banner_image_url: Optional[str] = None
    logo_url: Optional[str] = None
    background_style: Optional[str] = None
    social_instagram: Optional[str] = None
    social_whatsapp: Optional[str] = None

class ClinicSettingsResponse(ClinicSettingsUpdate):
    id: str
    model_config = ConfigDict(from_attributes=True)

class ClinicServiceCreate(BaseModel):
    name: str
    duration_minutes: int
    price: Optional[str] = None
    professional_ids: Optional[List[str]] = None

class ClinicServiceResponse(BaseModel):
    id: UUID
    name: str
    duration_minutes: int
    price: Optional[str] = None
    professional_ids: Optional[List[str]] = None
    
    model_config = ConfigDict(from_attributes=True)

class TestConfirmationMessagePayload(BaseModel):
    telefone: str
    msg_confirmation: Optional[str] = None

class TestConfirmationMessageResponse(BaseModel):
    status: str
    preview: str
    appointment_id: str
    professional_name: str

class PatientResponse(BaseModel):
    name: str
    phone: str
    last_visit: Optional[datetime] = None

class ResetSystemPayload(BaseModel):
    reset_appointments: bool = False
    reset_professionals: bool = False
    reset_services: bool = False
    reset_users: bool = False
    reset_settings: bool = False
