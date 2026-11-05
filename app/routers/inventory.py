"""Depósito dental: solo visible para usuarios con can_inventory (Dra. Jimena)."""
import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import config
from ..database import get_db
from ..models import Expense, Lot, Movement, Patient, Product, User
from ..services import inventory as inv
from ..utils import MESES, month_bounds, now_local, parse_date, to_float, today_local
from ..services import finance
from ..web import flash, inventory_user, redirect, render

router = APIRouter(prefix="/inventario")

FIELDS = ["sku", "name", "category", "brand", "unit", "supplier", "notes"]


def _purchase_expense(db: Session, user: User, p: Product, qty: float, unit_cost: float, method: str) -> float:
    """Una compra que entra al depósito se registra también como egreso de quien administra el depósito."""
    amount = round(qty * (unit_cost or p.cost_price), 2)
    if amount > 0:
        db.add(Expense(date=today_local(), concept=f"Compra depósito: {qty:g} {p.unit} · {p.name}"[:200],
                       category="Compra de inventario", amount=amount, is_shared=False, owner_id=user.id,
                       method=method or "Efectivo", notes="Entrada al depósito", created_by_id=user.id))
    return amount


def _product(db: Session, pid: int, user: User) -> Product:
    p = db.get(Product, pid)
    if not p or p.owner_id != user.id:
        raise HTTPException(404)
    return p


@router.get("")
def index(request: Request, filtro: str = "todos", q: str = "", categoria: str = "",
          db: Session = Depends(get_db), user: User = Depends(inventory_user)):
    alerts = inv.alerts(db, user.id)
    products = alerts["products"]
    expiring_ids = {l.product_id for l in alerts["expiring"]}
    expired_ids = {l.product_id for l in alerts["expired"]}
    if filtro == "bajo":
        products = [p for p in products if p.is_low]
    elif filtro == "caducar":
        products = [p for p in products if p.id in expiring_ids]
    elif filtro == "caducados":
        products = [p for p in products if p.id in expired_ids]
    if q:
        ql = q.lower()
        products = [p for p in products if ql in p.name.lower() or ql in p.sku.lower() or ql in p.brand.lower()]
    if categoria:
        products = [p for p in products if p.category == categoria]
    products = sorted(products, key=lambda p: (p.category, p.name))
    total_value = sum(p.stock_value for p in alerts["products"])
    recent = db.scalars(select(Movement).join(Product).where(Product.owner_id == user.id)
                        .order_by(Movement.date.desc()).limit(8)).all()
    return render(request, "inventory/index.html", db, user, products=products, alerts=alerts,
                  filtro=filtro, q=q, categoria=categoria, total_value=total_value, recent=recent,
                  expiring_ids=expiring_ids, expired_ids=expired_ids, categories=config.PRODUCT_CATEGORIES)


@router.get("/producto/nuevo")
def new_product(request: Request, db: Session = Depends(get_db), user: User = Depends(inventory_user)):
    return render(request, "inventory/product_form.html", db, user, p=None,
                  categories=config.PRODUCT_CATEGORIES, units=config.PRODUCT_UNITS)


@router.post("/producto/nuevo")
async def create_product(request: Request, db: Session = Depends(get_db), user: User = Depends(inventory_user)):
    f = await request.form()
    p = Product(owner_id=user.id, **{k: str(f.get(k, "")).strip() for k in FIELDS})
    if not p.name:
        flash(request, "El nombre es obligatorio.", "error")
        return redirect("/inventario/producto/nuevo")
    if not p.sku:
        p.sku = f"JJ-{len(db.scalars(select(Product.id)).all()) + 1:04d}"
    p.min_stock = to_float(f.get("min_stock"))
    p.cost_price = to_float(f.get("cost_price"))
    p.sale_price = to_float(f.get("sale_price"))
    p.tracks_expiry = f.get("tracks_expiry") == "on"
    db.add(p)
    db.flush()
    qty = to_float(f.get("initial_qty"))
    if qty > 0:
        try:
            inv.register_entry(db, p, qty, str(f.get("lot_code", "")), parse_date(f.get("expiry_date")),
                               p.cost_price, user.id, "Compra a proveedor" if f.get("as_expense") == "on" else "Inventario inicial")
            if f.get("as_expense") == "on":
                _purchase_expense(db, user, p, qty, p.cost_price, str(f.get("method") or ""))
        except inv.StockError as e:
            db.rollback()
            flash(request, str(e), "error")
            return redirect("/inventario/producto/nuevo")
    db.commit()
    flash(request, f"Producto «{p.name}» agregado.")
    return redirect(f"/inventario/producto/{p.id}")


@router.get("/producto/{pid}")
def product_detail(pid: int, request: Request, db: Session = Depends(get_db), user: User = Depends(inventory_user)):
    p = _product(db, pid, user)
    patients = db.scalars(select(Patient).where(Patient.active).order_by(Patient.first_name)).all()
    return render(request, "inventory/product_detail.html", db, user, p=p, patients=patients,
                  categories=config.PRODUCT_CATEGORIES, units=config.PRODUCT_UNITS,
                  alert_days=config.EXPIRY_ALERT_DAYS)


@router.post("/producto/{pid}/editar")
async def update_product(pid: int, request: Request, db: Session = Depends(get_db),
                         user: User = Depends(inventory_user)):
    p = _product(db, pid, user)
    f = await request.form()
    for k in FIELDS:
        setattr(p, k, str(f.get(k, "")).strip())
    p.min_stock = to_float(f.get("min_stock"))
    p.cost_price = to_float(f.get("cost_price"))
    p.sale_price = to_float(f.get("sale_price"))
    p.tracks_expiry = f.get("tracks_expiry") == "on"
    db.commit()
    flash(request, "Producto actualizado.")
    return redirect(f"/inventario/producto/{pid}")


@router.post("/producto/{pid}/entrada")
async def entry(pid: int, request: Request, db: Session = Depends(get_db), user: User = Depends(inventory_user)):
    p = _product(db, pid, user)
    f = await request.form()
    try:
        qty, cost = to_float(f.get("quantity")), to_float(f.get("unit_cost"))
        inv.register_entry(db, p, qty, str(f.get("lot_code", "")).strip(),
                           parse_date(f.get("expiry_date")), cost, user.id,
                           str(f.get("reason") or "Compra a proveedor"))
        spent = _purchase_expense(db, user, p, qty, cost, str(f.get("method") or "")) if f.get("as_expense") == "on" else 0
        db.commit()
        flash(request, f"Entrada registrada. Egreso de ${spent:,.2f} agregado a tus finanzas." if spent else "Entrada registrada.")
    except inv.StockError as e:
        db.rollback()
        flash(request, str(e), "error")
    return redirect(f"/inventario/producto/{pid}")


@router.post("/producto/{pid}/salida")
async def exit_(pid: int, request: Request, db: Session = Depends(get_db), user: User = Depends(inventory_user)):
    p = _product(db, pid, user)
    f = await request.form()
    kind = str(f.get("kind") or "uso")
    if kind not in ("uso", "venta", "merma"):
        raise HTTPException(400)
    try:
        inv.register_exit(db, p, to_float(f.get("quantity")), kind, user.id,
                          unit_price=to_float(f.get("unit_price")) or p.sale_price,
                          reason=str(f.get("reason", "")).strip(),
                          patient_id=int(f["patient_id"]) if f.get("patient_id") else None)
        db.commit()
        flash(request, {"uso": "Uso clínico registrado.", "venta": "Venta registrada (suma a tus ingresos).",
                        "merma": "Merma registrada."}[kind])
    except inv.StockError as e:
        db.rollback()
        flash(request, str(e), "error")
    return redirect(str(f.get("next") or f"/inventario/producto/{pid}"))


@router.post("/lote/{lid}/baja")
def discard_lot(lid: int, request: Request, db: Session = Depends(get_db), user: User = Depends(inventory_user)):
    lot = db.get(Lot, lid)
    if not lot or lot.product.owner_id != user.id:
        raise HTTPException(404)
    inv.discard_expired(db, lot, user.id)
    db.commit()
    flash(request, "Existencia caducada dada de baja.")
    return redirect(f"/inventario/producto/{lot.product_id}")


@router.post("/lote/{lid}/ajuste")
async def adjust_lot(lid: int, request: Request, db: Session = Depends(get_db), user: User = Depends(inventory_user)):
    lot = db.get(Lot, lid)
    if not lot or lot.product.owner_id != user.id:
        raise HTTPException(404)
    f = await request.form()
    inv.adjust(db, lot.product, lot, to_float(f.get("quantity")), user.id, str(f.get("reason", "")))
    db.commit()
    flash(request, "Ajuste por conteo físico registrado.")
    return redirect(f"/inventario/producto/{lot.product_id}")


@router.get("/movimientos")
def movements(request: Request, tipo: str = "", db: Session = Depends(get_db), user: User = Depends(inventory_user)):
    q = select(Movement).join(Product).where(Product.owner_id == user.id).order_by(Movement.date.desc())
    if tipo:
        q = q.where(Movement.kind == tipo)
    items = db.scalars(q.limit(300)).all()
    return render(request, "inventory/movements.html", db, user, items=items, tipo=tipo)


@router.get("/exportar.csv")
def export(db: Session = Depends(get_db), user: User = Depends(inventory_user)):
    buf = io.StringIO()
    buf.write("﻿")
    w = csv.writer(buf)
    w.writerow(["SKU", "Producto", "Categoría", "Marca", "Unidad", "Stock", "Mínimo", "Costo", "Precio venta",
                "Valor", "Próxima caducidad", "Proveedor"])
    for p in db.scalars(select(Product).where(Product.owner_id == user.id).order_by(Product.name)):
        w.writerow([p.sku, p.name, p.category, p.brand, p.unit, p.stock, p.min_stock, p.cost_price, p.sale_price,
                    p.stock_value, p.next_expiry.isoformat() if p.next_expiry else "", p.supplier])
    buf.seek(0)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": f'attachment; filename="inventario_{today_local()}.csv"'})


# ---------- Ventas del depósito ----------
@router.get("/venta")
def sale_form(request: Request, db: Session = Depends(get_db), user: User = Depends(inventory_user)):
    products = sorted(db.scalars(select(Product).where(Product.owner_id == user.id, Product.active)).all(),
                      key=lambda p: p.name)
    patients = db.scalars(select(Patient).where(Patient.active).order_by(Patient.first_name)).all()
    return render(request, "inventory/sale.html", db, user, products=products, patients=patients,
                  month_name=MESES[today_local().month - 1])


@router.post("/venta")
async def create_sale(request: Request, db: Session = Depends(get_db), user: User = Depends(inventory_user)):
    f = await request.form()
    pids, qtys, prices = f.getlist("product_id"), f.getlist("qty"), f.getlist("price")
    lines = [(int(a), to_float(b), to_float(c)) for a, b, c in zip(pids, qtys, prices) if str(a).isdigit() and to_float(b) > 0]
    if not lines:
        flash(request, "Agrega al menos un producto con cantidad.", "error")
        return redirect("/inventario/venta")
    now = now_local()
    prefix = f"V{now:%y%m%d}-"
    n = len(set(db.scalars(select(Movement.ticket).where(Movement.ticket.like(prefix + "%"))).all()))
    ticket = f"{prefix}{n + 1:03d}"
    pid_patient = int(f["patient_id"]) if str(f.get("patient_id") or "").isdigit() else None
    customer = str(f.get("customer", "")).strip()[:120]
    method = str(f.get("method") or "Efectivo")
    total = 0.0
    try:
        for prod_id, qty, price in lines:
            p = _product(db, prod_id, user)
            for m in inv.register_exit(db, p, qty, "venta", user.id, unit_price=price,
                                       reason="Venta" + (f" · {customer}" if customer else ""), patient_id=pid_patient):
                m.ticket, m.method, m.customer = ticket, method, customer
            total += qty * price
        db.commit()
    except inv.StockError as e:
        db.rollback()
        flash(request, f"{p.name}: {e}", "error")
        return redirect("/inventario/venta")
    flash(request, f"Venta {ticket} por ${total:,.2f} registrada y sumada a tus ingresos.")
    return redirect(f"/inventario/ventas/{ticket}")


@router.get("/ventas")
def sales_list(request: Request, mes: str | None = None, db: Session = Depends(get_db),
               user: User = Depends(inventory_user)):
    t = today_local()
    try:
        y, m = (int(x) for x in (mes or "").split("-"))
    except ValueError:
        y, m = t.year, t.month
    start, end = month_bounds(y, m)
    tickets = finance.sales_tickets(db, user, start, end)
    purchases = sum(e.amount for e in db.scalars(select(Expense).where(
        Expense.owner_id == user.id, Expense.category == "Compra de inventario",
        Expense.date >= start, Expense.date < end)).all())
    return render(request, "inventory/sales.html", db, user, tickets=tickets, year=y, month=m,
                  month_name=MESES[m - 1], mes=f"{y}-{m:02d}", total=sum(x["total"] for x in tickets),
                  cost=sum(x["cost"] for x in tickets), purchases=purchases)


@router.get("/ventas/{ticket}")
def sale_ticket(ticket: str, request: Request, db: Session = Depends(get_db), user: User = Depends(inventory_user)):
    items = db.scalars(select(Movement).join(Product).where(Movement.ticket == ticket, Product.owner_id == user.id)
                       .order_by(Movement.id)).all()
    if not items:
        raise HTTPException(404)
    m0 = items[0]
    tk = {"code": ticket, "date": m0.date, "method": m0.method, "customer": m0.customer_label,
          "lines": items, "total": sum(m.total for m in items)}
    return render(request, "inventory/ticket.html", db, user, tk=tk)
