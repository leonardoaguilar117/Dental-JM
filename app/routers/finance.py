import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import config
from ..database import get_db
from ..models import Expense, Payment, Treatment, User
from ..services import finance, notifications
from ..utils import MESES, month_bounds, parse_date, to_float, today_local, whatsapp_link
from ..web import current_user, flash, redirect, render

router = APIRouter()


def _month(mes: str | None):
    t = today_local()
    try:
        y, m = (mes or "").split("-")
        return int(y), int(m)
    except ValueError:
        return t.year, t.month


@router.get("/finanzas")
def finance_home(request: Request, mes: str | None = None, vista: str = "mia", tab: str = "cobros",
                 db: Session = Depends(get_db), user: User = Depends(current_user)):
    year, month = _month(mes)
    start, end = month_bounds(year, month)
    scope = None if vista == "consultorio" else user

    pq = select(Payment).where(Payment.date >= start, Payment.date < end).order_by(Payment.date.desc())
    if scope is not None:
        pq = pq.where(Payment.doctor_id == user.id)
    payments = db.scalars(pq).all()

    eq = select(Expense).where(Expense.date >= start, Expense.date < end).order_by(Expense.date.desc())
    expenses = db.scalars(eq).all()
    if scope is not None:
        expenses = [e for e in expenses if e.is_shared or e.owner_id == user.id]

    rec_total, rec_items = finance.receivables(db, scope)
    debt_links = {t.id: whatsapp_link(t.patient.phone, notifications.balance_message(t)) for t in rec_items}
    summary = finance.month_summary(db, scope, year, month)
    doctors = db.scalars(select(User).order_by(User.id)).all()
    return render(request, "finance/index.html", db, user, payments=payments, expenses=expenses,
                  rec_total=rec_total, rec_items=rec_items, debt_links=debt_links, summary=summary,
                  year=year, month=month, month_name=MESES[month - 1], mes=f"{year}-{month:02d}",
                  vista=vista, tab=tab, doctors=doctors, categories=config.EXPENSE_CATEGORIES,
                  methods=config.PAYMENT_METHODS,
                  settlement=finance.shared_settlement(db, year, month))


# ---------- Tratamientos / presupuestos ----------
@router.post("/tratamientos/nuevo")
async def create_treatment(request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    f = await request.form()
    pid = int(f["patient_id"])
    t = Treatment(
        patient_id=pid, doctor_id=int(f.get("doctor_id") or user.id),
        external_id=int(f["external_id"]) if f.get("external_id") else None,
        name=str(f.get("name", "")).strip() or "Tratamiento", description=str(f.get("description", "")).strip(),
        total=to_float(f.get("total")), discount=to_float(f.get("discount")),
        external_fee=to_float(f.get("external_fee")), sessions_planned=int(f.get("sessions_planned") or 1),
        status=str(f.get("status") or "presupuesto"),
    )
    db.add(t)
    db.flush()
    if t.external_fee > 0 and t.external_id:
        db.refresh(t)
        db.add(Expense(date=today_local(), concept=f"Honorarios {t.external.full_name} · {t.name} ({t.patient.full_name})",
                       category="Honorarios especialista", amount=t.external_fee, owner_id=t.doctor_id,
                       is_shared=False, created_by_id=user.id, method="Efectivo"))
    db.commit()
    flash(request, f"Tratamiento «{t.name}» registrado.")
    return redirect(f"/pacientes/{pid}#tratamientos")


@router.post("/tratamientos/{tid}")
async def update_treatment(tid: int, request: Request, db: Session = Depends(get_db),
                           user: User = Depends(current_user)):
    t = db.get(Treatment, tid)
    if not t:
        raise HTTPException(404)
    f = await request.form()
    if "status" in f:
        t.status = str(f["status"])
    if "sessions_done" in f:
        t.sessions_done = int(f.get("sessions_done") or 0)
    if "total" in f:
        t.total = to_float(f.get("total"))
    if "discount" in f:
        t.discount = to_float(f.get("discount"))
    db.commit()
    flash(request, "Tratamiento actualizado.")
    return redirect(f"/pacientes/{t.patient_id}#tratamientos")


@router.get("/tratamientos/{tid}/presupuesto")
def print_quote(tid: int, request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    t = db.get(Treatment, tid)
    if not t:
        raise HTTPException(404)
    return render(request, "finance/quote.html", db, user, t=t)


# ---------- Pagos ----------
@router.post("/pagos/nuevo")
async def create_payment(request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    f = await request.form()
    t = db.get(Treatment, int(f["treatment_id"]))
    if not t:
        raise HTTPException(404)
    amount = to_float(f.get("amount"))
    if amount <= 0:
        flash(request, "El monto debe ser mayor a cero.", "error")
        return redirect(f"/pacientes/{t.patient_id}#tratamientos")
    if amount > t.balance + 0.01:
        flash(request, f"El abono ({amount:,.2f}) excede el saldo ({t.balance:,.2f}).", "error")
        return redirect(f"/pacientes/{t.patient_id}#tratamientos")
    p = Payment(treatment_id=t.id, patient_id=t.patient_id, doctor_id=t.doctor_id, amount=amount,
                date=parse_date(f.get("date")) or today_local(), method=str(f.get("method") or "Efectivo"),
                reference=str(f.get("reference", "")).strip(), notes=str(f.get("notes", "")).strip())
    if t.status == "presupuesto":
        t.status = "en proceso"
    db.add(p)
    db.commit()
    db.refresh(t)
    flash(request, f"Abono de ${amount:,.2f} registrado. Saldo restante: ${t.balance:,.2f}.")
    return redirect(str(f.get("next") or f"/pacientes/{t.patient_id}#tratamientos"))


@router.get("/pagos/{pid}/recibo")
def receipt(pid: int, request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    p = db.get(Payment, pid)
    if not p:
        raise HTTPException(404)
    return render(request, "finance/receipt.html", db, user, pay=p)


@router.post("/pagos/{pid}/eliminar")
def delete_payment(pid: int, request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    p = db.get(Payment, pid)
    if not p:
        raise HTTPException(404)
    if p.doctor_id != user.id:
        flash(request, "Solo el doctor responsable puede eliminar este abono.", "error")
        return redirect(f"/pacientes/{p.patient_id}#tratamientos")
    pid_ = p.patient_id
    db.delete(p)
    db.commit()
    flash(request, "Abono eliminado.")
    return redirect(f"/pacientes/{pid_}#tratamientos")


# ---------- Gastos ----------
@router.post("/gastos/nuevo")
async def create_expense(request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    f = await request.form()
    amount = to_float(f.get("amount"))
    if amount <= 0 or not f.get("concept"):
        flash(request, "Concepto y monto son obligatorios.", "error")
        return redirect("/finanzas?tab=gastos")
    shared = f.get("scope") == "compartido"
    e = Expense(date=parse_date(f.get("date")) or today_local(), concept=str(f["concept"]).strip(),
                category=str(f.get("category") or "Otro"), amount=amount, is_shared=shared,
                owner_id=int(f.get("paid_by") or user.id), method=str(f.get("method") or "Efectivo"),
                recurring=f.get("recurring") == "on", notes=str(f.get("notes", "")).strip(),
                created_by_id=user.id)
    db.add(e)
    db.commit()
    flash(request, f"Gasto «{e.concept}» registrado" + (" como compartido." if shared else "."))
    return redirect(f"/finanzas?tab=gastos&mes={e.date:%Y-%m}")


@router.post("/gastos/{eid}/eliminar")
def delete_expense(eid: int, request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)):
    e = db.get(Expense, eid)
    if e:
        db.delete(e)
        db.commit()
        flash(request, "Gasto eliminado.")
    return redirect("/finanzas?tab=gastos")


@router.post("/gastos/recurrentes")
def copy_recurring(request: Request, mes: str = "", db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Copia al mes indicado los gastos marcados como recurrentes del mes anterior (renta, luz, internet...)."""
    from ..utils import add_months
    year, month = _month(mes)
    py, pm = add_months(year, month, -1)
    ps, pe = month_bounds(py, pm)
    cs, ce = month_bounds(year, month)
    prev = db.scalars(select(Expense).where(Expense.recurring, Expense.date >= ps, Expense.date < pe)).all()
    existing = {(e.concept, e.owner_id) for e in db.scalars(
        select(Expense).where(Expense.date >= cs, Expense.date < ce)).all()}
    n = 0
    for e in prev:
        if (e.concept, e.owner_id) in existing:
            continue
        day = min(e.date.day, 28)
        db.add(Expense(date=cs.replace(day=day), concept=e.concept, category=e.category, amount=e.amount,
                       is_shared=e.is_shared, owner_id=e.owner_id, method=e.method, recurring=True,
                       notes="Copiado de mes anterior", created_by_id=user.id))
        n += 1
    db.commit()
    flash(request, f"{n} gasto(s) recurrente(s) copiados. Revisa y ajusta montos si cambiaron.")
    return redirect(f"/finanzas?tab=gastos&mes={year}-{month:02d}")


# ---------- Exportaciones ----------
def _csv(rows: list[list], header: list[str], filename: str) -> StreamingResponse:
    buf = io.StringIO()
    buf.write("﻿")  # BOM para que Excel respete acentos
    w = csv.writer(buf)
    w.writerow(header)
    w.writerows(rows)
    buf.seek(0)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/finanzas/exportar/{kind}.csv")
def export_csv(kind: str, mes: str | None = None, vista: str = "mia",
               db: Session = Depends(get_db), user: User = Depends(current_user)):
    year, month = _month(mes)
    start, end = month_bounds(year, month)
    if kind == "pagos":
        q = select(Payment).where(Payment.date >= start, Payment.date < end).order_by(Payment.date)
        if vista != "consultorio":
            q = q.where(Payment.doctor_id == user.id)
        rows = [[p.date.isoformat(), p.patient.full_name, p.treatment.name, p.doctor.full_name, p.method,
                 f"{p.amount:.2f}", p.reference] for p in db.scalars(q).all()]
        return _csv(rows, ["Fecha", "Paciente", "Tratamiento", "Doctor", "Método", "Monto", "Referencia"],
                    f"cobros_{year}-{month:02d}.csv")
    if kind == "gastos":
        rows = []
        for e in db.scalars(select(Expense).where(Expense.date >= start, Expense.date < end).order_by(Expense.date)):
            if vista != "consultorio" and not (e.is_shared or e.owner_id == user.id):
                continue
            rows.append([e.date.isoformat(), e.concept, e.category, "Compartido" if e.is_shared else "Propio",
                         e.owner.full_name if e.owner else "", f"{e.amount:.2f}"])
        return _csv(rows, ["Fecha", "Concepto", "Categoría", "Tipo", "Pagado por", "Monto"],
                    f"gastos_{year}-{month:02d}.csv")
    raise HTTPException(404)
