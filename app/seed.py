"""Datos ficticios para la demo. Se cargan solo si la base está vacía (SEED_DEMO=true)."""
from __future__ import annotations

import json
import random
import secrets
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import (Appointment, ClinicalNote, Expense, ExternalSpecialist, Lot, MedicalHistory, Movement,
                     Patient, Payment, Product, Reminder, Treatment, User)
from .utils import add_months, hash_password, month_bounds, now_local, today_local

PATIENTS = [
    # nombre, apellidos, sexo, edad, doctor(0=Jimena,1=Carlos), ocupación
    ("Valeria", "Ramírez Soto", "Femenino", 15, 0, "Estudiante"),
    ("Diego", "Hernández Cruz", "Masculino", 17, 0, "Estudiante"),
    ("Sofía", "Martínez Peña", "Femenino", 24, 0, "Diseñadora"),
    ("Mateo", "López Aguirre", "Masculino", 12, 0, "Estudiante"),
    ("Camila", "Torres Ibarra", "Femenino", 29, 0, "Contadora"),
    ("Andrés", "Gómez Villalobos", "Masculino", 34, 1, "Abogado"),
    ("Mariana", "Flores Delgado", "Femenino", 41, 1, "Empresaria"),
    ("Ricardo", "Castillo Mora", "Masculino", 52, 1, "Ingeniero"),
    ("Daniela", "Vargas Ríos", "Femenino", 27, 1, "Influencer"),
    ("Fernanda", "Ruiz Contreras", "Femenino", 36, 1, "Docente"),
    ("Luis", "Mendoza Salgado", "Masculino", 22, 1, "Estudiante"),
    ("Paola", "Navarro Reyes", "Femenino", 45, 1, "Médica"),
    ("Emilio", "Ortega Luna", "Masculino", 19, 0, "Estudiante"),
    ("Regina", "Sánchez Bravo", "Femenino", 31, 1, "Arquitecta"),
    ("Jorge", "Domínguez Paz", "Masculino", 58, 1, "Comerciante"),
    ("Ximena", "Cervantes Lara", "Femenino", 14, 0, "Estudiante"),
]

UPPER = [18, 17, 16, 15, 14, 13, 12, 11, 21, 22, 23, 24, 25, 26, 27, 28]
LOWER = [48, 47, 46, 45, 44, 43, 42, 41, 31, 32, 33, 34, 35, 36, 37, 38]


def seed_if_empty(db: Session) -> None:
    if db.scalar(select(User.id).limit(1)):
        return
    rnd = random.Random(42)
    today = today_local()
    now = now_local()

    jimena = User(username="jimena", full_name="Dra. Jimena Juárez Aguilar", short_name="Dra. Jimena",
                  specialty="Ortodoncia", password_hash=hash_password("demo123"), color="#418d96",
                  phone="5512345678", can_inventory=True, shared_expense_pct=50,
                  ical_token=secrets.token_urlsafe(24))
    carlos = User(username="carlos", full_name="Dr. Juan Carlos Montaño López", short_name="Dr. Juan Carlos",
                  specialty="Estética dental", password_hash=hash_password("demo123"), color="#6c4813",
                  phone="5587654321", can_inventory=False, shared_expense_pct=50,
                  ical_token=secrets.token_urlsafe(24))
    maxilo = ExternalSpecialist(full_name="Dr. Ricardo Salinas Vega", specialty="Cirujano maxilofacial",
                                phone="5544556677", email="maxilofacial@ejemplo.com", color="#737a90",
                                availability_note="Martes y jueves por la tarde (confirmar por WhatsApp)")
    db.add_all([jimena, carlos, maxilo])
    db.flush()
    docs = [jimena, carlos]

    # ---------- Pacientes + historia clínica ----------
    patients = []
    for i, (fn, ln, sex, age, d, occ) in enumerate(PATIENTS):
        bd = today.replace(year=today.year - age) - timedelta(days=rnd.randint(10, 300))
        p = Patient(first_name=fn, last_name=ln, sex=sex, birth_date=bd,
                    phone=f"55{rnd.randint(10000000, 99999999)}",
                    email=f"{fn.lower()}.{ln.split()[0].lower()}@correo.com".replace("í", "i").replace("é", "e")
                    .replace("á", "a").replace("ó", "o").replace("ú", "u"),
                    address=f"Calle {rnd.choice(['Roble', 'Pino', 'Cedro', 'Fresno', 'Encino'])} #{rnd.randint(10, 300)}, CDMX",
                    occupation=occ, primary_doctor_id=docs[d].id,
                    emergency_contact=("Mamá / Papá · 55" + str(rnd.randint(10000000, 99999999))) if age < 18 else "",
                    referred_by=rnd.choice(["Instagram", "Recomendación", "Google Maps", "Facebook", ""]),
                    created_at=now - timedelta(days=rnd.randint(20, 200)))
        db.add(p)
        db.flush()
        odo = {}
        if d == 0:
            for t in UPPER + LOWER:
                if t not in (18, 28, 38, 48):
                    odo[str(t)] = "bracket"
            if rnd.random() < 0.5:
                odo[str(rnd.choice([16, 26, 36, 46]))] = "obturado"
        else:
            for t in rnd.sample(UPPER + LOWER, 3):
                odo[str(t)] = rnd.choice(["caries", "obturado", "corona", "endodoncia"])
        if i in (2, 10):
            odo.update({"18": "extraer", "28": "extraer", "38": "extraer", "48": "extraer"})
        db.add(MedicalHistory(
            patient_id=p.id,
            motivo_consulta=("Apiñamiento dental, desea alinear sus dientes" if d == 0
                             else rnd.choice(["Mejorar estética de la sonrisa", "Dientes amarillos",
                                              "Fractura de borde incisal", "Desea carillas"])),
            padecimiento_actual="Sin dolor. Inconformidad estética." if d else "Maloclusión clase II div. 1",
            antecedentes_heredofamiliares=rnd.choice(["Diabetes (padre)", "Hipertensión (madre)", "Niega"]),
            antecedentes_patologicos=rnd.choice(["Niega", "Asma en la infancia", "Gastritis"]),
            antecedentes_no_patologicos="Cepillado 2 veces al día, usa hilo dental ocasionalmente",
            alergias=rnd.choice(["Niega", "Niega", "Penicilina", "Látex"]),
            medicamentos=rnd.choice(["Ninguno", "Ninguno", "Loratadina ocasional"]),
            hipertension=(age > 50 and rnd.random() < 0.5), diabetes=(age > 50 and rnd.random() < 0.3),
            fumador=(d == 1 and rnd.random() < 0.2), bruxismo=rnd.random() < 0.25,
            presion_arterial=f"{rnd.randint(110, 135)}/{rnd.randint(70, 88)}",
            exploracion_extraoral="Simetría facial conservada, ATM sin ruidos",
            exploracion_intraoral="Mucosas hidratadas, encía rosa coral" + (", apiñamiento anterior" if d == 0 else ""),
            higiene_oral=rnd.choice(["Buena", "Regular", "Buena"]),
            oclusion="Clase II molar" if d == 0 else "Clase I molar",
            diagnostico=("Maloclusión clase II con apiñamiento moderado" if d == 0
                         else "Discromía dental / desgaste incisal"),
            plan_tratamiento=("Ortodoncia fija con brackets metálicos 18-24 meses" if d == 0
                              else "Blanqueamiento + carillas de disilicato en sector anterior"),
            pronostico="Favorable", odontograma_json=json.dumps(odo), consentimiento_firmado=True,
            aviso_privacidad=True, updated_by_id=docs[d].id, updated_at=p.created_at,
        ))
        patients.append((p, d))

    # ---------- Tratamientos + pagos ----------
    catalog_j = [("Ortodoncia fija brackets metálicos", 28000, 24), ("Ortodoncia con alineadores", 42000, 18),
                 ("Ortodoncia brackets estéticos (zafiro)", 35000, 24), ("Retenedores Essix", 2800, 1),
                 ("Ortopedia maxilar (niño)", 15000, 12)]
    catalog_c = [("Blanqueamiento en consultorio", 4500, 2), ("Carillas de disilicato (6 piezas)", 33000, 4),
                 ("Resinas estéticas anteriores", 3600, 2), ("Diseño de sonrisa digital", 6500, 2),
                 ("Coronas de zirconia (2)", 14000, 3), ("Limpieza + pulido", 900, 1)]
    treatments = []
    for p, d in patients:
        cat = catalog_j if d == 0 else catalog_c
        for k in range(rnd.choice([1, 1, 2])):
            name, total, sess = rnd.choice(cat)
            created = p.created_at + timedelta(days=k * 15)
            status = rnd.choice(["en proceso", "en proceso", "en proceso", "terminado", "presupuesto"])
            done = sess if status == "terminado" else (0 if status == "presupuesto" else rnd.randint(1, max(1, sess - 1)))
            t = Treatment(patient_id=p.id, doctor_id=docs[d].id, name=name, total=total,
                          discount=rnd.choice([0, 0, 0, total * 0.05]), sessions_planned=sess, sessions_done=done,
                          status=status, created_at=created,
                          description="Incluye controles mensuales" if d == 0 else "Incluye pruebas y ajustes")
            db.add(t)
            db.flush()
            treatments.append(t)
            if status == "presupuesto":
                continue
            net = t.total - t.discount
            # enganche + abonos mensuales
            target = net if status == "terminado" else net * rnd.uniform(0.3, 0.85)
            paid = 0.0
            pay_date = created.date()
            first = True
            while paid < target - 1 and pay_date <= today:
                amt = round(min(target - paid, net * (0.3 if first else rnd.uniform(0.08, 0.2))), -2) or 100
                db.add(Payment(treatment_id=t.id, patient_id=p.id, doctor_id=docs[d].id, amount=amt, date=pay_date,
                               method=rnd.choice(["Efectivo", "Transferencia", "Tarjeta débito", "Tarjeta crédito"])))
                paid += amt
                first = False
                pay_date += timedelta(days=rnd.randint(20, 35))

    # Cirugía de terceros molares con el maxilofacial
    p_cx = patients[2][0]
    t_cx = Treatment(patient_id=p_cx.id, doctor_id=jimena.id, external_id=maxilo.id,
                     name="Extracción de terceros molares (4) previo a ortodoncia", total=9500,
                     external_fee=6000, sessions_planned=2, sessions_done=0, status="en proceso",
                     created_at=now - timedelta(days=10), description="Cirugía a cargo del Dr. Salinas (maxilofacial); control post-quirúrgico con la Dra. Jimena")
    db.add(t_cx)
    db.flush()
    db.add(Payment(treatment_id=t_cx.id, patient_id=p_cx.id, doctor_id=jimena.id, amount=4000,
                   date=today - timedelta(days=9), method="Transferencia"))

    # ---------- Citas (últimos 45 días + próximos 21) ----------
    types_j = ["Ajuste de ortodoncia", "Ajuste de ortodoncia", "Valoración", "Limpieza dental"]
    types_c = ["Blanqueamiento", "Carillas / coronas", "Resinas estéticas", "Limpieza dental", "Diseño de sonrisa"]
    slots = [9, 10, 11, 12, 13, 16, 17, 18]
    for offset in range(-45, 22):
        day = today + timedelta(days=offset)
        if day.weekday() == 6:
            continue
        for di, doc in enumerate(docs):
            n = rnd.randint(1, 4) if day.weekday() < 5 else rnd.randint(0, 2)
            hours = rnd.sample(slots if day.weekday() < 5 else [9, 10, 11, 12], n)
            for h in sorted(hours):
                pool = [p for p, d in patients if d == di]
                p = rnd.choice(pool)
                typ = rnd.choice(types_j if di == 0 else types_c)
                start = datetime.combine(day, datetime.min.time()).replace(hour=h, minute=0)
                dur = 30 if typ in ("Ajuste de ortodoncia", "Valoración") else 60
                if offset < 0:
                    status = rnd.choices(["atendida", "cancelada", "no asistió"], [85, 10, 5])[0]
                elif offset == 0:
                    status = "atendida" if h < now.hour else "confirmada"
                else:
                    status = rnd.choice(["programada", "programada", "confirmada"])
                a = Appointment(patient_id=p.id, doctor_id=doc.id, start=start, end=start + timedelta(minutes=dur),
                                type=typ, status=status)
                db.add(a)
                db.flush()
                if status == "atendida" and rnd.random() < 0.6:
                    db.add(ClinicalNote(patient_id=p.id, doctor_id=doc.id, appointment_id=a.id, date=start,
                                        procedure=typ,
                                        note=("Cambio de arco NiTi 0.016, ligas elásticas. Paciente colaborador."
                                              if typ == "Ajuste de ortodoncia" else
                                              "Procedimiento sin complicaciones. Se dan indicaciones post-tratamiento."),
                                        next_step="Control en 4 semanas" if di == 0 else "Revisión en 15 días"))
    # cita de cirugía con el maxilofacial (jueves próximo, tarde)
    d_cx = today + timedelta(days=(3 - today.weekday()) % 7 or 7)
    s_cx = datetime.combine(d_cx, datetime.min.time()).replace(hour=16)
    db.add(Appointment(patient_id=p_cx.id, doctor_id=jimena.id, external_id=maxilo.id, start=s_cx,
                       end=s_cx + timedelta(minutes=120), type="Extracción / cirugía", status="confirmada",
                       notes="Extracción de 18, 28, 38, 48 bajo anestesia local. Traer radiografía panorámica."))
    p_cx2 = patients[10][0]
    s_cx2 = s_cx + timedelta(days=5, hours=1)
    if s_cx2.weekday() == 6:
        s_cx2 += timedelta(days=1)
    db.add(Appointment(patient_id=p_cx2.id, doctor_id=carlos.id, external_id=maxilo.id, start=s_cx2,
                       end=s_cx2 + timedelta(minutes=90), type="Extracción / cirugía", status="programada",
                       notes="Valoración y extracción de tercer molar inferior"))

    # ---------- Recordatorios ----------
    reminder_specs = [
        (5, 1, -3, "Limpieza semestral"), (6, 1, 0, "Limpieza semestral"), (7, 1, 2, "Revisión / retoque de blanqueamiento"),
        (9, 1, 5, "Control de carillas"), (13, 1, 12, "Limpieza semestral"), (14, 1, -1, "Seguimiento de valoración (presupuesto)"),
        (0, 0, -2, "Ajuste mensual de ortodoncia"), (1, 0, 1, "Ajuste mensual de ortodoncia"),
        (3, 0, 4, "Ajuste mensual de ortodoncia"), (12, 0, 6, "Revisión de retenedores"), (4, 0, 20, "Limpieza semestral"),
    ]
    for pi, di, off, kind in reminder_specs:
        db.add(Reminder(patient_id=patients[pi][0].id, doctor_id=docs[di].id, due_date=today + timedelta(days=off),
                        kind=kind, auto=True))
    db.add(Reminder(patient_id=patients[8][0].id, doctor_id=carlos.id, due_date=today - timedelta(days=12),
                    kind="Limpieza semestral", status="enviado", sent_at=now - timedelta(days=12)))

    # ---------- Gastos (6 meses) ----------
    for k in range(5, -1, -1):
        y, m = add_months(today.year, today.month, -k)
        s, _ = month_bounds(y, m)
        last_day = today.day if k == 0 else 28

        def d(day):
            return s.replace(day=min(day, last_day))

        shared = [("Renta del consultorio", "Renta", 14000, 1, jimena), ("Luz CFE", "Luz", rnd.randint(1100, 1600), 8, carlos),
                  ("Agua", "Agua", rnd.randint(280, 420), 10, jimena), ("Internet y teléfono", "Internet / teléfono", 649, 5, carlos),
                  ("Servicio de limpieza", "Limpieza / insumos generales", 1800, 15, jimena),
                  ("Contador", "Impuestos / contador", 1500, 17, carlos)]
        for concept, cat, amt, day, payer in shared:
            if s.replace(day=min(day, 28)) <= today:
                db.add(Expense(date=d(day), concept=concept, category=cat, amount=amt, is_shared=True,
                               owner_id=payer.id, recurring=True, created_by_id=payer.id, method="Transferencia"))
        personal = [
            (jimena, "Compra brackets y arcos (depósito)", "Compra de inventario", rnd.randint(3500, 6500), 6),
            (jimena, "Laboratorio retenedores / aparatos", "Laboratorio", rnd.randint(1200, 2800), 12),
            (jimena, "Publicidad Instagram ortodoncia", "Publicidad", 800, 20),
            (carlos, "Laboratorio dental (carillas / coronas)", "Laboratorio", rnd.randint(4500, 9000), 9),
            (carlos, "Resinas y adhesivos 3M", "Material dental", rnd.randint(1500, 3200), 14),
            (carlos, "Gel blanqueador Opalescence", "Material dental", rnd.randint(900, 1800), 22),
            (carlos, "Mantenimiento lámpara de fotocurado", "Mantenimiento de equipo", rnd.choice([0, 0, 950]), 25),
        ]
        for owner, concept, cat, amt, day in personal:
            if amt and s.replace(day=min(day, 28)) <= today:
                db.add(Expense(date=d(day), concept=concept, category=cat, amount=amt, owner_id=owner.id,
                               created_by_id=owner.id, method=rnd.choice(["Tarjeta crédito", "Transferencia"])))
    db.add(Expense(date=today - timedelta(days=9), concept="Honorarios Dr. Salinas · Extracción terceros molares",
                   category="Honorarios especialista", amount=6000, owner_id=jimena.id, created_by_id=jimena.id,
                   method="Efectivo"))

    # ---------- Inventario (depósito de la Dra. Jimena) ----------
    products = [
        # sku, nombre, cat, marca, unidad, min, costo, venta, caduca, [(qty, días a caducidad)]
        ("ORT-001", "Brackets metálicos Roth 0.022 (kit 20)", "Ortodoncia", "American Orthodontics", "kit", 5, 380, 650, False, [(14, None)]),
        ("ORT-002", "Brackets cerámicos (kit 10)", "Ortodoncia", "Morelli", "kit", 3, 950, 1500, False, [(2, None)]),
        ("ORT-003", "Arco NiTi superior 0.014", "Ortodoncia", "Ortho Technology", "paquete", 10, 45, 90, False, [(36, None)]),
        ("ORT-004", "Arco NiTi inferior 0.016", "Ortodoncia", "Ortho Technology", "paquete", 10, 45, 90, False, [(8, None)]),
        ("ORT-005", "Ligas elásticas intermaxilares 1/4\"", "Ortodoncia", "GAC", "bolsa", 15, 25, 60, True, [(40, 220), (12, 25)]),
        ("ORT-006", "Módulos elastoméricos (ligaduras) surtido", "Ortodoncia", "Dentsply", "paquete", 10, 60, 120, True, [(22, 300)]),
        ("ORT-007", "Tubos molares adheribles (kit 4)", "Ortodoncia", "American Orthodontics", "kit", 5, 210, 380, False, [(11, None)]),
        ("ADH-001", "Adhesivo Transbond XT (jeringa 4 g)", "Resinas y adhesivos", "3M", "jeringa", 3, 890, 1350, True, [(2, 40), (3, 260)]),
        ("ADH-002", "Ácido grabador 37% (jeringa)", "Resinas y adhesivos", "Ultradent", "jeringa", 4, 120, 210, True, [(6, 18)]),
        ("ADH-003", "Primer ortodóntico", "Resinas y adhesivos", "3M", "frasco", 2, 750, 1100, True, [(1, -8), (2, 190)]),
        ("ANE-001", "Lidocaína c/epinefrina 2% (caja 50)", "Anestésicos", "Zeyco", "caja", 2, 560, 780, True, [(3, 400), (1, 52)]),
        ("ANE-002", "Anestesia tópica benzocaína 20%", "Anestésicos", "Zeyco", "frasco", 2, 95, 160, True, [(1, -15)]),
        ("DES-001", "Guantes de nitrilo talla M (caja 100)", "Desechables", "Ambiderm", "caja", 6, 145, 210, True, [(9, 520)]),
        ("DES-002", "Cubrebocas tricapa (caja 50)", "Desechables", "Ambiderm", "caja", 4, 70, 110, True, [(3, 600)]),
        ("DES-003", "Eyectores de saliva (bolsa 100)", "Desechables", "Viarden", "bolsa", 3, 65, 110, False, [(5, None)]),
        ("HIG-001", "Pasta profiláctica (frasco 340 g)", "Higiene / profilaxis", "Viarden", "frasco", 2, 180, 290, True, [(2, 33)]),
        ("HIG-002", "Cepillo de ortodoncia (pieza)", "Higiene / profilaxis", "Oral-B", "pieza", 20, 28, 65, False, [(54, None)]),
        ("HIG-003", "Cera ortodóntica (caja 50)", "Higiene / profilaxis", "GUM", "caja", 2, 210, 15 * 1.0, False, [(1, None)]),
        ("IMP-001", "Alginato fraguado rápido (bolsa 454 g)", "Impresión y modelos", "Zhermack", "bolsa", 3, 160, 250, True, [(4, 75), (2, 12)]),
        ("IMP-002", "Yeso tipo III (bolsa 1 kg)", "Impresión y modelos", "Magnum", "bolsa", 3, 85, 140, False, [(6, None)]),
        ("EST-001", "Bolsas para esterilizar 90x230 (caja 200)", "Esterilización", "Medibag", "caja", 2, 190, 290, True, [(3, 700)]),
        ("BLA-001", "Kit blanqueamiento en casa 10%", "Blanqueamiento", "Opalescence", "kit", 2, 620, 1050, True, [(4, 120)]),
    ]
    prod_objs = []
    entry_movs = {}
    for sku, name, cat, brand, unit, mn, cost, sale, exp, lots in products:
        if sku == "HIG-003":
            sale = 340
        pr = Product(owner_id=jimena.id, sku=sku, name=name, category=cat, brand=brand, unit=unit, min_stock=mn,
                     cost_price=cost, sale_price=sale, tracks_expiry=exp,
                     supplier=rnd.choice(["Depósito Dental Villa de Cortés", "Dentalia Proveedores", "OrthoMex"]),
                     location=rnd.choice(["Vitrina A", "Vitrina B", "Gaveta 1", "Gaveta 2", "Almacén"]))
        db.add(pr)
        db.flush()
        for qty, days in lots:
            received = today - timedelta(days=rnd.randint(20, 120))
            lot = Lot(product_id=pr.id, lot_code=f"L{rnd.randint(10000, 99999)}", quantity=qty,
                      expiry_date=(today + timedelta(days=days)) if days is not None else None,
                      received_at=received, unit_cost=cost)
            db.add(lot)
            db.flush()
            em = Movement(product_id=pr.id, lot_id=lot.id, kind="entrada", quantity=qty, unit_price=cost,
                          reason="Compra a proveedor", user_id=jimena.id,
                          date=datetime.combine(received, datetime.min.time()).replace(hour=10) - timedelta(days=180))
            db.add(em)
            entry_movs[lot.id] = em
        prod_objs.append(pr)
    db.flush()

    # Ventas de mostrador y usos clínicos de los últimos 6 meses (para el dashboard)
    sellable = [p for p in prod_objs if p.sale_price > 0]
    for k in range(170, 0, -3):
        pr = rnd.choice(sellable)
        lot = next((l for l in pr.lots if l.quantity > 0 and (not l.expiry_date or l.expiry_date > today)), None)
        if not lot:
            continue
        qty = rnd.choice([1, 1, 2])
        when = now - timedelta(days=k, hours=rnd.randint(0, 6))
        kind = rnd.choice(["venta", "venta", "uso"])
        db.add(Movement(product_id=pr.id, lot_id=lot.id, kind=kind, quantity=-qty,
                        unit_price=pr.sale_price if kind == "venta" else pr.cost_price,
                        reason="Venta mostrador" if kind == "venta" else "Uso en consulta",
                        user_id=jimena.id, date=when))
        # el kardex cuadra: la entrada original incluía lo que después se vendió/usó
        entry_movs[lot.id].quantity += qty
    db.commit()
