"""Cálculo de ingresos, egresos y cuentas por cobrar.

Reglas:
- Ingreso de un doctor = abonos de sus tratamientos + ventas del depósito (si tiene inventario).
- Egreso de un doctor = gastos propios + (gastos compartidos × su % de reparto).
- Vista "consultorio" (user=None) = todo sumado.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Expense, Movement, Payment, Product, Treatment, User
from ..utils import MESES_CORTOS, add_months, month_bounds


def _share_pct(db: Session, user: User | None) -> float:
    if user is None:
        return 100.0
    return user.shared_expense_pct or 0.0


def income(db: Session, user: User | None, start: date, end: date) -> dict:
    q = select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.date >= start, Payment.date < end)
    if user is not None:
        q = q.where(Payment.doctor_id == user.id)
    treatments = float(db.scalar(q) or 0)

    sq = (
        select(func.coalesce(func.sum(-Movement.quantity * Movement.unit_price), 0))
        .join(Product)
        .where(
            Movement.kind == "venta",
            Movement.date >= datetime.combine(start, datetime.min.time()),
            Movement.date < datetime.combine(end, datetime.min.time()),
        )
    )
    if user is not None:
        sq = sq.where(Product.owner_id == user.id)
    sales = float(db.scalar(sq) or 0)
    return {"tratamientos": treatments, "ventas": sales, "total": treatments + sales}


def expenses(db: Session, user: User | None, start: date, end: date) -> dict:
    base = select(Expense).where(Expense.date >= start, Expense.date < end)
    rows = db.scalars(base).all()
    pct = _share_pct(db, user) / 100
    personal = shared = 0.0
    by_cat: dict[str, float] = defaultdict(float)
    for e in rows:
        if e.is_shared:
            part = e.amount * pct
            shared += part
            by_cat[e.category] += part
        elif user is None or e.owner_id == user.id:
            personal += e.amount
            by_cat[e.category] += e.amount
    return {
        "personal": personal,
        "compartido": shared,
        "total": personal + shared,
        "por_categoria": dict(sorted(by_cat.items(), key=lambda kv: -kv[1])),
    }


def receivables(db: Session, user: User | None) -> tuple[float, list[Treatment]]:
    q = select(Treatment).where(Treatment.status.in_(["en proceso", "terminado", "presupuesto aceptado"]))
    if user is not None:
        q = q.where(Treatment.doctor_id == user.id)
    items = [t for t in db.scalars(q).all() if t.balance > 0]
    items.sort(key=lambda t: -t.balance)
    return sum(t.balance for t in items), items


def month_summary(db: Session, user: User | None, year: int, month: int) -> dict:
    start, end = month_bounds(year, month)
    inc = income(db, user, start, end)
    exp = expenses(db, user, start, end)
    py, pm = add_months(year, month, -1)
    ps, pe = month_bounds(py, pm)
    prev_inc = income(db, user, ps, pe)["total"]
    prev_exp = expenses(db, user, ps, pe)["total"]
    return {
        "ingresos": inc,
        "egresos": exp,
        "utilidad": inc["total"] - exp["total"],
        "prev_ingresos": prev_inc,
        "prev_egresos": prev_exp,
        "var_ingresos": _variation(inc["total"], prev_inc),
        "var_egresos": _variation(exp["total"], prev_exp),
    }


def _variation(cur: float, prev: float) -> float | None:
    if not prev:
        return None
    return round(100 * (cur - prev) / prev, 1)


def series(db: Session, user: User | None, year: int, month: int, n: int = 6) -> dict:
    labels, inc, exp = [], [], []
    for k in range(n - 1, -1, -1):
        y, m = add_months(year, month, -k)
        s, e = month_bounds(y, m)
        labels.append(f"{MESES_CORTOS[m - 1]} {str(y)[2:]}")
        inc.append(round(income(db, user, s, e)["total"], 2))
        exp.append(round(expenses(db, user, s, e)["total"], 2))
    return {"labels": labels, "ingresos": inc, "egresos": exp}


def shared_settlement(db: Session, year: int, month: int) -> list[dict]:
    """Quién pagó gastos compartidos vs. cuánto le correspondía: para saldar cuentas entre doctores."""
    start, end = month_bounds(year, month)
    shared = db.scalars(select(Expense).where(Expense.is_shared, Expense.date >= start, Expense.date < end)).all()
    total = sum(e.amount for e in shared)
    out = []
    for u in db.scalars(select(User).order_by(User.id)).all():
        paid = sum(e.amount for e in shared if e.owner_id == u.id)
        due = total * (u.shared_expense_pct or 0) / 100
        out.append({"user": u, "pagado": paid, "corresponde": due, "diferencia": paid - due})
    return out
