"""Bitácora del expediente: quién vio, imprimió o modificó información clínica."""
from __future__ import annotations

from fastapi import Request
from sqlalchemy.orm import Session

from ..models import AuditLog, User


def log(db: Session, request: Request, user: User | None, action: str, patient_id: int | None = None,
        detail: str = "") -> None:
    """Agrega un renglón a la bitácora (se confirma junto con la transacción en curso)."""
    ip = request.client.host if request.client else ""
    db.add(AuditLog(user_id=user.id if user else None, patient_id=patient_id, action=action[:40],
                    detail=detail[:400], ip=ip[:45]))
