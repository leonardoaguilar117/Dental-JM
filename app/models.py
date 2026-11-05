"""Modelo de datos del consultorio."""
from __future__ import annotations

import json
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def _now() -> datetime:
    from .utils import now_local

    return now_local()


class User(Base):
    """Doctores con acceso al sistema (los únicos usuarios)."""

    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    short_name: Mapped[str] = mapped_column(String(60))
    specialty: Mapped[str] = mapped_column(String(80))
    password_hash: Mapped[str] = mapped_column(String(255))
    color: Mapped[str] = mapped_column(String(9), default="#418d96")
    phone: Mapped[str] = mapped_column(String(20), default="")
    can_inventory: Mapped[bool] = mapped_column(Boolean, default=False)
    shared_expense_pct: Mapped[float] = mapped_column(Float, default=50.0)
    ical_token: Mapped[str] = mapped_column(String(64), default="")
    gcal_calendar_id: Mapped[str] = mapped_column(String(255), default="")
    photo: Mapped[str] = mapped_column(Text, default="")  # foto del doctor (JPEG en data URL, 320×320)

    @property
    def initials(self) -> str:
        words = self.short_name.split()[1:3]
        ini = "".join(w[0] for w in words)
        if len(ini) < 2:
            ini += self.full_name.split()[2][0] if len(self.full_name.split()) > 2 else ""
        return ini.upper()


class ExternalSpecialist(Base):
    """Especialistas sin usuario (p.ej. cirujano maxilofacial) que se agendan en citas."""

    __tablename__ = "external_specialists"
    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120))
    specialty: Mapped[str] = mapped_column(String(80))
    phone: Mapped[str] = mapped_column(String(20), default="")
    email: Mapped[str] = mapped_column(String(120), default="")
    color: Mapped[str] = mapped_column(String(9), default="#737a90")
    availability_note: Mapped[str] = mapped_column(String(255), default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Patient(Base):
    __tablename__ = "patients"
    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(String(80))
    last_name: Mapped[str] = mapped_column(String(120))
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    sex: Mapped[str] = mapped_column(String(12), default="")
    phone: Mapped[str] = mapped_column(String(20), default="")
    email: Mapped[str] = mapped_column(String(120), default="")
    address: Mapped[str] = mapped_column(String(255), default="")
    occupation: Mapped[str] = mapped_column(String(80), default="")
    emergency_contact: Mapped[str] = mapped_column(String(160), default="")
    referred_by: Mapped[str] = mapped_column(String(120), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    primary_doctor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    primary_doctor: Mapped[User | None] = relationship()
    history: Mapped["MedicalHistory | None"] = relationship(back_populates="patient", uselist=False)
    notes_list: Mapped[list["ClinicalNote"]] = relationship(
        back_populates="patient", order_by="desc(ClinicalNote.date)"
    )
    treatments: Mapped[list["Treatment"]] = relationship(
        back_populates="patient", order_by="desc(Treatment.created_at)"
    )
    appointments: Mapped[list["Appointment"]] = relationship(
        back_populates="patient", order_by="desc(Appointment.start)"
    )
    reminders: Mapped[list["Reminder"]] = relationship(
        back_populates="patient", order_by="Reminder.due_date"
    )

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def initials(self) -> str:
        return (self.first_name[:1] + self.last_name[:1]).upper()

    @property
    def age(self) -> int | None:
        if not self.birth_date:
            return None
        from .utils import today_local
        t = today_local()
        b = self.birth_date
        return t.year - b.year - ((t.month, t.day) < (b.month, b.day))

    @property
    def balance(self) -> float:
        return sum(t.balance for t in self.treatments if t.status != "cancelado")

    def balance_for(self, doctor_id: int) -> float:
        """Lo que el paciente le debe a un doctor (cada doctor solo ve sus propios montos)."""
        return sum(t.balance for t in self.treatments if t.status != "cancelado" and t.doctor_id == doctor_id)

    def total_for(self, doctor_id: int) -> float:
        return sum(t.net_total for t in self.treatments if t.status != "cancelado" and t.doctor_id == doctor_id)


class MedicalHistory(Base):
    """Historia clínica odontológica (estructura basada en NOM-004-SSA3 / NOM-013-SSA2)."""

    __tablename__ = "medical_histories"
    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), unique=True)
    motivo_consulta: Mapped[str] = mapped_column(Text, default="")
    padecimiento_actual: Mapped[str] = mapped_column(Text, default="")
    antecedentes_heredofamiliares: Mapped[str] = mapped_column(Text, default="")
    antecedentes_patologicos: Mapped[str] = mapped_column(Text, default="")
    antecedentes_no_patologicos: Mapped[str] = mapped_column(Text, default="")
    alergias: Mapped[str] = mapped_column(Text, default="")
    medicamentos: Mapped[str] = mapped_column(Text, default="")
    diabetes: Mapped[bool] = mapped_column(Boolean, default=False)
    hipertension: Mapped[bool] = mapped_column(Boolean, default=False)
    cardiopatia: Mapped[bool] = mapped_column(Boolean, default=False)
    coagulacion: Mapped[bool] = mapped_column(Boolean, default=False)
    embarazo: Mapped[bool] = mapped_column(Boolean, default=False)
    fumador: Mapped[bool] = mapped_column(Boolean, default=False)
    bruxismo: Mapped[bool] = mapped_column(Boolean, default=False)
    presion_arterial: Mapped[str] = mapped_column(String(20), default="")
    exploracion_extraoral: Mapped[str] = mapped_column(Text, default="")
    exploracion_intraoral: Mapped[str] = mapped_column(Text, default="")
    higiene_oral: Mapped[str] = mapped_column(String(20), default="")
    oclusion: Mapped[str] = mapped_column(String(120), default="")
    diagnostico: Mapped[str] = mapped_column(Text, default="")
    plan_tratamiento: Mapped[str] = mapped_column(Text, default="")
    pronostico: Mapped[str] = mapped_column(String(60), default="")
    odontograma_json: Mapped[str] = mapped_column(Text, default="{}")
    # lengua y encía: hallazgos (lista JSON de opciones de config) + notas libres
    lengua_hallazgos: Mapped[str] = mapped_column(Text, default="[]")
    lengua_notas: Mapped[str] = mapped_column(Text, default="")
    encia_hallazgos: Mapped[str] = mapped_column(Text, default="[]")
    encia_notas: Mapped[str] = mapped_column(Text, default="")
    consentimiento_firmado: Mapped[bool] = mapped_column(Boolean, default=False)
    # firma autógrafa capturada en pantalla (PNG en data URL), quién firmó y cuándo
    consentimiento_firma: Mapped[str] = mapped_column(Text, default="")
    consentimiento_nombre: Mapped[str] = mapped_column(String(160), default="")
    consentimiento_fecha: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    aviso_privacidad: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    patient: Mapped[Patient] = relationship(back_populates="history")
    updated_by: Mapped[User | None] = relationship()

    @property
    def odontograma(self) -> dict:
        try:
            return json.loads(self.odontograma_json or "{}")
        except ValueError:
            return {}

    @staticmethod
    def _list(raw: str) -> list[str]:
        try:
            v = json.loads(raw or "[]")
            return [str(x) for x in v] if isinstance(v, list) else []
        except ValueError:
            return []

    @property
    def lengua_list(self) -> list[str]:
        return self._list(self.lengua_hallazgos)

    @property
    def encia_list(self) -> list[str]:
        return self._list(self.encia_hallazgos)

    @property
    def alert_flags(self) -> list[str]:
        flags = []
        if self.alergias.strip() and self.alergias.strip().lower() not in ("niega", "ninguna", "no"):
            flags.append(f"Alergias: {self.alergias}")
        for attr, label in [
            ("diabetes", "Diabetes"),
            ("hipertension", "Hipertensión"),
            ("cardiopatia", "Cardiopatía"),
            ("coagulacion", "Trastorno de coagulación"),
            ("embarazo", "Embarazo"),
        ]:
            if getattr(self, attr):
                flags.append(label)
        return flags


class ClinicalNote(Base):
    """Nota de evolución por visita."""

    __tablename__ = "clinical_notes"
    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    appointment_id: Mapped[int | None] = mapped_column(ForeignKey("appointments.id"), nullable=True)
    date: Mapped[datetime] = mapped_column(DateTime, default=_now)
    procedure: Mapped[str] = mapped_column(String(160), default="")
    teeth: Mapped[str] = mapped_column(String(80), default="")
    note: Mapped[str] = mapped_column(Text, default="")
    next_step: Mapped[str] = mapped_column(String(255), default="")

    patient: Mapped[Patient] = relationship(back_populates="notes_list")
    doctor: Mapped[User] = relationship()


class Appointment(Base):
    __tablename__ = "appointments"
    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    external_id: Mapped[int | None] = mapped_column(ForeignKey("external_specialists.id"), nullable=True)
    start: Mapped[datetime] = mapped_column(DateTime, index=True)
    end: Mapped[datetime] = mapped_column(DateTime)
    type: Mapped[str] = mapped_column(String(80), default="Valoración")
    status: Mapped[str] = mapped_column(String(20), default="programada")
    notes: Mapped[str] = mapped_column(Text, default="")
    gcal_event_id: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    patient: Mapped[Patient] = relationship(back_populates="appointments")
    doctor: Mapped[User] = relationship()
    external: Mapped[ExternalSpecialist | None] = relationship()

    @property
    def duration_min(self) -> int:
        return int((self.end - self.start).total_seconds() // 60)


class Treatment(Base):
    """Plan de tratamiento / presupuesto con control de cobros."""

    __tablename__ = "treatments"
    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    external_id: Mapped[int | None] = mapped_column(ForeignKey("external_specialists.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text, default="")
    total: Mapped[float] = mapped_column(Float, default=0)
    discount: Mapped[float] = mapped_column(Float, default=0)
    external_fee: Mapped[float] = mapped_column(Float, default=0)
    sessions_planned: Mapped[int] = mapped_column(Integer, default=1)
    sessions_done: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="presupuesto")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    patient: Mapped[Patient] = relationship(back_populates="treatments")
    doctor: Mapped[User] = relationship()
    external: Mapped[ExternalSpecialist | None] = relationship()
    payments: Mapped[list["Payment"]] = relationship(
        back_populates="treatment", order_by="desc(Payment.date)"
    )

    @property
    def net_total(self) -> float:
        return max(self.total - self.discount, 0)

    @property
    def paid(self) -> float:
        return sum(p.amount for p in self.payments)

    @property
    def balance(self) -> float:
        return round(max(self.net_total - self.paid, 0), 2)

    def balance_after(self, payment: "Payment") -> float:
        """Lo que quedó a deber justo después de ese abono (no el saldo de hoy)."""
        key = (payment.date, payment.id)
        paid = sum(p.amount for p in self.payments if (p.date, p.id) <= key)
        return round(max(self.net_total - paid, 0), 2)

    @property
    def paid_pct(self) -> int:
        return int(round(100 * self.paid / self.net_total)) if self.net_total else 100

    @property
    def progress_pct(self) -> int:
        if not self.sessions_planned:
            return 0
        return min(100, int(round(100 * self.sessions_done / self.sessions_planned)))


class Payment(Base):
    """Abono / cobro a un tratamiento."""

    __tablename__ = "payments"
    id: Mapped[int] = mapped_column(primary_key=True)
    treatment_id: Mapped[int] = mapped_column(ForeignKey("treatments.id"), index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    amount: Mapped[float] = mapped_column(Float)
    date: Mapped[date] = mapped_column(Date, index=True)
    method: Mapped[str] = mapped_column(String(30), default="Efectivo")
    reference: Mapped[str] = mapped_column(String(80), default="")
    notes: Mapped[str] = mapped_column(String(255), default="")

    treatment: Mapped[Treatment] = relationship(back_populates="payments")
    patient: Mapped[Patient] = relationship()
    doctor: Mapped[User] = relationship()


class Expense(Base):
    """Egreso. owner_id = doctor responsable; is_shared = se reparte según % configurado."""

    __tablename__ = "expenses"
    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    concept: Mapped[str] = mapped_column(String(160))
    category: Mapped[str] = mapped_column(String(60))
    amount: Mapped[float] = mapped_column(Float)
    is_shared: Mapped[bool] = mapped_column(Boolean, default=False)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    method: Mapped[str] = mapped_column(String(30), default="Transferencia")
    recurring: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str] = mapped_column(String(255), default="")
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    owner: Mapped[User | None] = relationship(foreign_keys=[owner_id])
    created_by: Mapped[User | None] = relationship(foreign_keys=[created_by_id])


class Reminder(Base):
    """Aviso para contactar manualmente al paciente (WhatsApp / llamada)."""

    __tablename__ = "reminders"
    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    due_date: Mapped[date] = mapped_column(Date, index=True)
    kind: Mapped[str] = mapped_column(String(80))
    message: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="pendiente")
    auto: Mapped[bool] = mapped_column(Boolean, default=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    patient: Mapped[Patient] = relationship(back_populates="reminders")
    doctor: Mapped[User] = relationship()


class Product(Base):
    """Producto del depósito dental (exclusivo de la Dra. Jimena)."""

    __tablename__ = "products"
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    sku: Mapped[str] = mapped_column(String(40), index=True)
    name: Mapped[str] = mapped_column(String(160))
    category: Mapped[str] = mapped_column(String(60))
    brand: Mapped[str] = mapped_column(String(80), default="")
    unit: Mapped[str] = mapped_column(String(20), default="pieza")
    min_stock: Mapped[float] = mapped_column(Float, default=0)
    cost_price: Mapped[float] = mapped_column(Float, default=0)
    sale_price: Mapped[float] = mapped_column(Float, default=0)
    supplier: Mapped[str] = mapped_column(String(120), default="")
    location: Mapped[str] = mapped_column(String(80), default="")
    tracks_expiry: Mapped[bool] = mapped_column(Boolean, default=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str] = mapped_column(String(255), default="")

    lots: Mapped[list["Lot"]] = relationship(back_populates="product", order_by="Lot.expiry_date")
    movements: Mapped[list["Movement"]] = relationship(
        back_populates="product", order_by="desc(Movement.date)"
    )

    @property
    def stock(self) -> float:
        return round(sum(l.quantity for l in self.lots), 2)

    @property
    def sellable_stock(self) -> float:
        """Existencia que se puede vender o usar: excluye lotes caducados."""
        from .utils import today_local
        t = today_local()
        return round(sum(l.quantity for l in self.lots if l.quantity > 0 and (not l.expiry_date or l.expiry_date >= t)), 2)

    @property
    def is_low(self) -> bool:
        return self.stock <= self.min_stock

    @property
    def stock_value(self) -> float:
        return round(self.stock * self.cost_price, 2)

    @property
    def next_expiry(self) -> date | None:
        dates = [l.expiry_date for l in self.lots if l.quantity > 0 and l.expiry_date]
        return min(dates) if dates else None


class Lot(Base):
    """Lote con cantidad y caducidad (permite FEFO: primero en caducar, primero en salir)."""

    __tablename__ = "lots"
    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    lot_code: Mapped[str] = mapped_column(String(60), default="")
    quantity: Mapped[float] = mapped_column(Float, default=0)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    received_at: Mapped[date] = mapped_column(Date)
    unit_cost: Mapped[float] = mapped_column(Float, default=0)

    product: Mapped[Product] = relationship(back_populates="lots")

    @property
    def days_to_expiry(self) -> int | None:
        if not self.expiry_date:
            return None
        from .utils import today_local

        return (self.expiry_date - today_local()).days


class Movement(Base):
    """Kardex: entrada, uso clínico, venta, merma o ajuste."""

    __tablename__ = "movements"
    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    lot_id: Mapped[int | None] = mapped_column(ForeignKey("lots.id"), nullable=True)
    kind: Mapped[str] = mapped_column(String(20))  # entrada | uso | venta | merma | ajuste
    quantity: Mapped[float] = mapped_column(Float)  # positivo entra, negativo sale
    unit_price: Mapped[float] = mapped_column(Float, default=0)
    date: Mapped[datetime] = mapped_column(DateTime, default=_now, index=True)
    reason: Mapped[str] = mapped_column(String(255), default="")
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    patient_id: Mapped[int | None] = mapped_column(ForeignKey("patients.id"), nullable=True)
    ticket: Mapped[str] = mapped_column(String(24), default="", index=True)  # folio de la nota de venta
    method: Mapped[str] = mapped_column(String(30), default="")  # forma de pago de la venta
    customer: Mapped[str] = mapped_column(String(120), default="")

    product: Mapped[Product] = relationship(back_populates="movements")
    lot: Mapped[Lot | None] = relationship()
    patient: Mapped[Patient | None] = relationship()

    @property
    def total(self) -> float:
        return round(abs(self.quantity) * self.unit_price, 2)

    @property
    def customer_label(self) -> str:
        return self.patient.full_name if self.patient else (self.customer or "Mostrador")
