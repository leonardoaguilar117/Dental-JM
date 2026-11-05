"""Lógica del depósito dental: entradas por lote, salidas FEFO, alertas."""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import EXPIRY_ALERT_DAYS
from ..models import Lot, Movement, Product
from ..utils import now_local, today_local


class StockError(ValueError):
    pass


def register_entry(db: Session, product: Product, qty: float, lot_code: str, expiry: date | None,
                   unit_cost: float, user_id: int, reason: str = "Compra a proveedor") -> Lot:
    if qty <= 0:
        raise StockError("La cantidad debe ser mayor a cero.")
    if product.tracks_expiry and not expiry:
        raise StockError("Este producto requiere fecha de caducidad.")
    lot = Lot(product_id=product.id, lot_code=lot_code or "S/L", quantity=qty, expiry_date=expiry,
              received_at=today_local(), unit_cost=unit_cost or product.cost_price)
    db.add(lot)
    db.flush()
    if unit_cost:
        product.cost_price = unit_cost
    db.add(Movement(product_id=product.id, lot_id=lot.id, kind="entrada", quantity=qty,
                    unit_price=unit_cost or product.cost_price, reason=reason, user_id=user_id,
                    date=now_local()))
    return lot


def register_exit(db: Session, product: Product, qty: float, kind: str, user_id: int,
                  unit_price: float = 0, reason: str = "", patient_id: int | None = None) -> list[Movement]:
    """Descuenta stock por FEFO (primero el lote que caduca antes). Rechaza lotes caducados en ventas."""
    if qty <= 0:
        raise StockError("La cantidad debe ser mayor a cero.")
    today = today_local()
    lots = [l for l in product.lots if l.quantity > 0]
    if kind in ("venta", "uso"):
        lots = [l for l in lots if not l.expiry_date or l.expiry_date >= today]
    lots.sort(key=lambda l: (l.expiry_date or date.max, l.received_at))
    available = sum(l.quantity for l in lots)
    if qty > available + 1e-9:
        raise StockError(f"Stock insuficiente (disponible vigente: {available:g} {product.unit}).")
    remaining = qty
    movs = []
    for lot in lots:
        if remaining <= 0:
            break
        take = min(lot.quantity, remaining)
        lot.quantity = round(lot.quantity - take, 4)
        remaining = round(remaining - take, 4)
        m = Movement(product_id=product.id, lot_id=lot.id, kind=kind, quantity=-take,
                     unit_price=unit_price if kind == "venta" else product.cost_price,
                     reason=reason, user_id=user_id, patient_id=patient_id, date=now_local())
        db.add(m)
        movs.append(m)
    return movs


def discard_expired(db: Session, lot: Lot, user_id: int) -> None:
    if lot.quantity <= 0:
        return
    db.add(Movement(product_id=lot.product_id, lot_id=lot.id, kind="merma", quantity=-lot.quantity,
                    unit_price=lot.unit_cost, reason="Baja por caducidad",
                    user_id=user_id, date=now_local()))
    lot.quantity = 0


def adjust(db: Session, product: Product, lot: Lot, new_qty: float, user_id: int, reason: str) -> None:
    diff = round(new_qty - lot.quantity, 4)
    if diff == 0:
        return
    lot.quantity = new_qty
    db.add(Movement(product_id=product.id, lot_id=lot.id, kind="ajuste", quantity=diff,
                    unit_price=product.cost_price, reason=reason or "Conteo físico", user_id=user_id,
                    date=now_local()))


def alerts(db: Session, owner_id: int) -> dict:
    today = today_local()
    limit = today + timedelta(days=EXPIRY_ALERT_DAYS)
    products = db.scalars(select(Product).where(Product.owner_id == owner_id, Product.active)).all()
    low = [p for p in products if p.is_low]
    expired, expiring = [], []
    for p in products:
        for l in p.lots:
            if l.quantity <= 0 or not l.expiry_date:
                continue
            if l.expiry_date < today:
                expired.append(l)
            elif l.expiry_date <= limit:
                expiring.append(l)
    expiring.sort(key=lambda l: l.expiry_date)
    expired.sort(key=lambda l: l.expiry_date)
    return {"low": low, "expiring": expiring, "expired": expired, "products": products}
