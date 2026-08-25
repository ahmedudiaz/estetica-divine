"""
database.py - Gestión de Base de Datos SQLite para Estética Divine
"""
import sqlite3
import os
import secrets
from datetime import datetime, date, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "agenda_estetica.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Tabla de Configuración
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)

    # Tabla de Pacientes
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS patients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT NOT NULL,
        email TEXT,
        birth_date TEXT,
        allergies TEXT,
        skin_type TEXT,
        notes TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Tabla de Servicios / Tratamientos
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS services (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        duration_minutes INTEGER NOT NULL,
        price REAL NOT NULL,
        instructions TEXT,
        color TEXT DEFAULT '#E0A9AF',
        is_active INTEGER DEFAULT 1
    )
    """)

    # Tabla de Citas
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS appointments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER NOT NULL,
        service_id INTEGER NOT NULL,
        appointment_date TEXT NOT NULL, -- YYYY-MM-DD
        appointment_time TEXT NOT NULL, -- HH:MM
        duration_minutes INTEGER NOT NULL,
        status TEXT DEFAULT 'Pendiente', -- 'Pendiente', 'Recordatorio Enviado', 'Confirmada', 'Cancelada', 'Completada', 'No Asistió'
        specialist TEXT DEFAULT 'Cosmetóloga Constanza Díaz',
        notes TEXT,
        confirmation_token TEXT UNIQUE,
        reminder_sent_at DATETIME,
        confirmed_at DATETIME,
        canceled_at DATETIME,
        cancellation_reason TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (patient_id) REFERENCES patients (id),
        FOREIGN KEY (service_id) REFERENCES services (id)
    )
    """)

    # Tabla de Registro de Notificaciones / Mensajes
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS notification_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        appointment_id INTEGER NOT NULL,
        patient_id INTEGER NOT NULL,
        channel TEXT DEFAULT 'whatsapp',
        message_body TEXT NOT NULL,
        status TEXT DEFAULT 'sent',
        sent_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (appointment_id) REFERENCES appointments (id),
        FOREIGN KEY (patient_id) REFERENCES patients (id)
    )
    """)

    # Configuración por defecto
    default_settings = {
        "clinic_name": "Estética Divine",
        "clinic_phone": "+34 600 123 456",
        "clinic_address": "Av. Principal 142, Suite 3B, Ciudad",
        "clinic_email": "contacto@esteticadivine.com",
        "whatsapp_template": (
            "✨ *¡Hola, {nombre_paciente}!* Te saludamos de *{centro}*.\n\n"
            "Te recordamos tu cita programada para *mañana*:\n"
            "📅 *Fecha:* {fecha}\n"
            "⏰ *Hora:* {hora} hrs\n"
            "💆‍♀️ *Tratamiento:* {tratamiento}\n"
            "👩‍⚕️ *Especialista:* {especialista}\n"
            "📍 *Lugar:* {direccion}\n"
            "{indicaciones}\n"
            "Por favor, ayúdanos confirmando tu asistencia en el siguiente enlace:\n"
            "👉 {enlace_confirmacion}\n\n"
            "_Si necesitas reprogramar, hazlo mediante el enlace o respóndenos a este mensaje._ ¡Te esperamos!"
        ),
        "reminder_hours_before": "24",
        "auto_send_simulation": "1"
    }

    for k, v in default_settings.items():
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))

    # Poblar con datos de prueba si está vacío
    cursor.execute("SELECT COUNT(*) as count FROM patients")
    if cursor.fetchone()["count"] == 0:
        seed_sample_data(cursor)

    conn.commit()
    conn.close()

def seed_sample_data(cursor):
    # Pacientes de ejemplo
    patients = [
        ("Valentina Mendoza", "+34612345678", "valentina.m@email.com", "1994-05-12", "Ninguna", "Mixta con tendencia a acné", "Prefiere citas por la tarde"),
        ("Camila Fernández", "+34698765432", "camila.f@email.com", "1988-11-23", "Alergia al látex", "Sensible / Rosácea", "Tratamiento despigmentante previo"),
        ("Mariana Ruiz", "+34634567890", "mariana.ruiz@email.com", "1997-02-18", "Ninguna", "Grasa", "Primera vez en el centro"),
        ("Lucía Gómez", "+34687654321", "lucia.gomez@email.com", "1991-08-30", "Aspirina", "Normal a seca", "Clienta habitual mensual"),
        ("Isabella Rojas", "+34645678901", "isabella.r@email.com", "1985-04-14", "Ninguna", "Madura", "Seguimiento de rejuvenecimiento con toxina botulínica"),
        ("Sofía Albarracín", "+34656789012", "sofia.a@email.com", "1999-10-05", "Ninguna", "Joven / Mixta", "Interesada en perfilado de labios")
    ]
    cursor.executemany("""
    INSERT INTO patients (name, phone, email, birth_date, allergies, skin_type, notes)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, patients)

    # Servicios de ejemplo
    services = [
        ("Limpieza Facial Profunda con Hidrodermoabrasión", "Facial", 60, 45.0, "Venir sin maquillaje. No exfoliarse las 48h previas.", "#F472B6"),
        ("Peeling Químico Renovador Iluminador", "Facial", 45, 60.0, "Evitar exposición solar directa antes y después de la sesión.", "#FB7185"),
        ("Radiofrecuencia Facial y Cuello Efecto Lifting", "Facial", 60, 55.0, "Excelente hidratación previa recomendada.", "#EC4899"),
        ("Depilación Láser Diodo - Piernas Completas", "Depilación", 45, 40.0, "Venir rasurada 24 horas antes con cuchilla. Sin cremas corporales.", "#818CF8"),
        ("Drenaje Linfático Manual y Presoterapia", "Corporal", 60, 35.0, "Beber 1 litro de agua antes de la sesión.", "#34D399"),
        ("Masaje Reductor y Modelador con Maderoterapia", "Corporal", 50, 40.0, "No ingerir comidas pesadas 1 hora antes.", "#FBBF24"),
        ("Armonización y Aplicación de Toxina Botulínica", "Medicina Estética", 30, 180.0, "No consumir alcohol ni aspirinas las 24 horas previas.", "#A78BFA")
    ]
    cursor.executemany("""
    INSERT INTO services (name, category, duration_minutes, price, instructions, color)
    VALUES (?, ?, ?, ?, ?, ?)
    """, services)

    today = date.today()
    tomorrow = today + timedelta(days=1)
    day_after = today + timedelta(days=2)
    yesterday = today - timedelta(days=1)

    today_str = today.strftime("%Y-%m-%d")
    tomorrow_str = tomorrow.strftime("%Y-%m-%d")
    day_after_str = day_after.strftime("%Y-%m-%d")
    yesterday_str = yesterday.strftime("%Y-%m-%d")

    # Citas para probar: Ayer (completada), Hoy (confirmada/pendiente), Mañana (pendientes de confirmación para el sistema de recordatorios!)
    appointments = [
        # Ayer
        (1, 1, yesterday_str, "10:00", 60, "Completada", "Cosmetóloga Constanza Díaz", "Sesión completada con éxito. Buena tolerancia al tratamiento.", secrets.token_urlsafe(16), yesterday_str + " 09:00:00", yesterday_str + " 11:30:00", None, None),
        
        # Hoy
        (2, 3, today_str, "11:00", 60, "Confirmada", "Cosmetóloga Constanza Díaz", "Paciente confirmó telefónicamente.", secrets.token_urlsafe(16), yesterday_str + " 10:00:00", today_str + " 08:30:00", None, None),
        (3, 5, today_str, "16:00", 60, "Pendiente", "Lic. Carolina Méndez", "Recordatorio manual enviado por la mañana.", secrets.token_urlsafe(16), yesterday_str + " 15:00:00", None, None, None),

        # Mañana (Citas clave para enviar recordatorio 24h)
        (4, 1, tomorrow_str, "09:30", 60, "Pendiente", "Cosmetóloga Constanza Díaz", "Recordatorio pendiente de enviar para confirmar.", secrets.token_urlsafe(16), None, None, None, None),
        (5, 7, tomorrow_str, "12:00", 30, "Pendiente", "Cosmetóloga Constanza Díaz", "Tratamiento de toxina. Requiere confirmación obligatoria.", secrets.token_urlsafe(16), None, None, None, None),
        (6, 4, tomorrow_str, "15:30", 45, "Recordatorio Enviado", "Lic. Carolina Méndez", "Se le envió WhatsApp a las 09:00. Esperando que abra el enlace.", secrets.token_urlsafe(16), today_str + " 09:00:00", None, None, None),
        (1, 2, tomorrow_str, "17:00", 45, "Confirmada", "Cosmetóloga Constanza Díaz", "Confirmó su cita mediante el enlace web.", secrets.token_urlsafe(16), today_str + " 08:30:00", today_str + " 10:15:00", None, None),

        # Pasado mañana
        (2, 6, day_after_str, "11:00", 50, "Pendiente", "Lic. Carolina Méndez", "Cita programada para esta semana.", secrets.token_urlsafe(16), None, None, None, None),
        (3, 1, day_after_str, "14:00", 60, "Pendiente", "Cosmetóloga Constanza Díaz", "Segunda sesión de limpieza.", secrets.token_urlsafe(16), None, None, None, None)
    ]

    cursor.executemany("""
    INSERT INTO appointments (
        patient_id, service_id, appointment_date, appointment_time, duration_minutes,
        status, specialist, notes, confirmation_token, reminder_sent_at, confirmed_at, canceled_at, cancellation_reason
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, appointments)

# Funciones de consulta
def get_settings():
    conn = get_connection()
    rows = conn.execute("SELECT key, value FROM settings").fetchall()
    conn.close()
    return {r["key"]: r["value"] for r in rows}

def update_setting(key, value):
    conn = get_connection()
    conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

def get_stats():
    conn = get_connection()
    today_str = date.today().strftime("%Y-%m-%d")
    tomorrow_str = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")

    # Citas hoy
    today_appts = conn.execute("SELECT COUNT(*) as total, SUM(CASE WHEN status='Confirmada' THEN 1 ELSE 0 END) as confirmed FROM appointments WHERE appointment_date = ?", (today_str,)).fetchone()
    
    # Citas mañana y confirmaciones
    tomorrow_appts = conn.execute("SELECT COUNT(*) as total, SUM(CASE WHEN status='Confirmada' THEN 1 ELSE 0 END) as confirmed, SUM(CASE WHEN status='Pendiente' OR status='Recordatorio Enviado' THEN 1 ELSE 0 END) as unconfirmed FROM appointments WHERE appointment_date = ?", (tomorrow_str,)).fetchone()

    # Total pacientes
    total_patients = conn.execute("SELECT COUNT(*) as count FROM patients").fetchone()["count"]

    # Ingresos estimados de la semana
    week_start = (date.today() - timedelta(days=date.today().weekday())).strftime("%Y-%m-%d")
    week_end = (date.today() + timedelta(days=7)).strftime("%Y-%m-%d")
    revenue = conn.execute("""
    SELECT SUM(s.price) as total_revenue 
    FROM appointments a 
    JOIN services s ON a.service_id = s.id 
    WHERE a.appointment_date >= ? AND a.appointment_date <= ? AND a.status != 'Cancelada'
    """, (week_start, week_end)).fetchone()["total_revenue"] or 0

    conn.close()
    return {
        "today_total": today_appts["total"] or 0,
        "today_confirmed": today_appts["confirmed"] or 0,
        "tomorrow_total": tomorrow_appts["total"] or 0,
        "tomorrow_confirmed": tomorrow_appts["confirmed"] or 0,
        "tomorrow_unconfirmed": tomorrow_appts["unconfirmed"] or 0,
        "total_patients": total_patients,
        "week_estimated_revenue": round(revenue, 2)
    }

def get_appointments(date_from=None, date_to=None, status=None, patient_id=None):
    conn = get_connection()
    query = """
    SELECT a.*, p.name as patient_name, p.phone as patient_phone, p.email as patient_email,
           s.name as service_name, s.category as service_category, s.price as service_price,
           s.duration_minutes as service_duration, s.instructions as service_instructions, s.color as service_color
    FROM appointments a
    JOIN patients p ON a.patient_id = p.id
    JOIN services s ON a.service_id = s.id
    WHERE 1=1
    """
    params = []
    if date_from:
        query += " AND a.appointment_date >= ?"
        params.append(date_from)
    if date_to:
        query += " AND a.appointment_date <= ?"
        params.append(date_to)
    if status:
        query += " AND a.status = ?"
        params.append(status)
    if patient_id:
        query += " AND a.patient_id = ?"
        params.append(patient_id)

    query += " ORDER BY a.appointment_date ASC, a.appointment_time ASC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_appointment_by_id(appt_id):
    conn = get_connection()
    row = conn.execute("""
    SELECT a.*, p.name as patient_name, p.phone as patient_phone, p.email as patient_email,
           s.name as service_name, s.category as service_category, s.price as service_price,
           s.duration_minutes as service_duration, s.instructions as service_instructions, s.color as service_color
    FROM appointments a
    JOIN patients p ON a.patient_id = p.id
    JOIN services s ON a.service_id = s.id
    WHERE a.id = ?
    """, (appt_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def get_appointment_by_token(token):
    conn = get_connection()
    row = conn.execute("""
    SELECT a.*, p.name as patient_name, p.phone as patient_phone, p.email as patient_email,
           s.name as service_name, s.category as service_category, s.price as service_price,
           s.duration_minutes as service_duration, s.instructions as service_instructions, s.color as service_color
    FROM appointments a
    JOIN patients p ON a.patient_id = p.id
    JOIN services s ON a.service_id = s.id
    WHERE a.confirmation_token = ?
    """, (token,)).fetchone()
    conn.close()
    return dict(row) if row else None

def create_appointment(data):
    conn = get_connection()
    token = secrets.token_urlsafe(16)
    
    # Obtener duración del servicio si no se especifica
    duration = data.get("duration_minutes")
    if not duration:
        svc = conn.execute("SELECT duration_minutes FROM services WHERE id = ?", (data["service_id"],)).fetchone()
        duration = svc["duration_minutes"] if svc else 60

    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO appointments (
        patient_id, service_id, appointment_date, appointment_time, duration_minutes,
        status, specialist, notes, confirmation_token
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data["patient_id"],
        data["service_id"],
        data["appointment_date"],
        data["appointment_time"],
        duration,
        data.get("status", "Pendiente"),
        data.get("specialist", "Cosmetóloga Constanza Díaz"),
        data.get("notes", ""),
        token
    ))
    appt_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return get_appointment_by_id(appt_id)

def update_appointment(appt_id, data):
    conn = get_connection()
    fields = []
    values = []
    
    for key in ["patient_id", "service_id", "appointment_date", "appointment_time", "duration_minutes", "status", "specialist", "notes"]:
        if key in data:
            fields.append(f"{key} = ?")
            values.append(data[key])

    if "status" in data:
        if data["status"] == "Confirmada":
            fields.append("confirmed_at = CURRENT_TIMESTAMP")
        elif data["status"] == "Cancelada":
            fields.append("canceled_at = CURRENT_TIMESTAMP")
            if "cancellation_reason" in data:
                fields.append("cancellation_reason = ?")
                values.append(data["cancellation_reason"])

    if fields:
        values.append(appt_id)
        conn.execute(f"UPDATE appointments SET {', '.join(fields)} WHERE id = ?", values)
        conn.commit()
    conn.close()
    return get_appointment_by_id(appt_id)

def delete_appointment(appt_id):
    conn = get_connection()
    conn.execute("DELETE FROM appointments WHERE id = ?", (appt_id,))
    conn.commit()
    conn.close()
    return True

def confirm_appointment_by_token(token, action="confirm", reason=""):
    conn = get_connection()
    appt = get_appointment_by_token(token)
    if not appt:
        conn.close()
        return None

    if action == "confirm":
        conn.execute("""
        UPDATE appointments 
        SET status = 'Confirmada', confirmed_at = CURRENT_TIMESTAMP 
        WHERE confirmation_token = ?
        """, (token,))
    elif action == "reschedule" or action == "cancel":
        conn.execute("""
        UPDATE appointments 
        SET status = 'Cancelada', canceled_at = CURRENT_TIMESTAMP, cancellation_reason = ?
        WHERE confirmation_token = ?
        """, (reason or "Solicitud de reprogramación desde portal de confirmación", token))

    conn.commit()
    conn.close()
    return get_appointment_by_token(token)

def mark_reminder_sent(appt_id, message_body=""):
    conn = get_connection()
    appt = get_appointment_by_id(appt_id)
    if appt:
        conn.execute("""
        UPDATE appointments 
        SET status = CASE WHEN status = 'Pendiente' THEN 'Recordatorio Enviado' ELSE status END,
            reminder_sent_at = CURRENT_TIMESTAMP 
        WHERE id = ?
        """, (appt_id,))

        conn.execute("""
        INSERT INTO notification_logs (appointment_id, patient_id, channel, message_body, status)
        VALUES (?, ?, 'whatsapp', ?, 'sent')
        """, (appt_id, appt["patient_id"], message_body))

        conn.commit()
    conn.close()
    return get_appointment_by_id(appt_id)

def get_patients(search=""):
    conn = get_connection()
    if search:
        s = f"%{search}%"
        rows = conn.execute("""
        SELECT p.*, COUNT(a.id) as total_appointments
        FROM patients p
        LEFT JOIN appointments a ON p.id = a.patient_id
        WHERE p.name LIKE ? OR p.phone LIKE ? OR p.email LIKE ?
        GROUP BY p.id
        ORDER BY p.name ASC
        """, (s, s, s)).fetchall()
    else:
        rows = conn.execute("""
        SELECT p.*, COUNT(a.id) as total_appointments
        FROM patients p
        LEFT JOIN appointments a ON p.id = a.patient_id
        GROUP BY p.id
        ORDER BY p.name ASC
        """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_patient_by_id(patient_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM patients WHERE id = ?", (patient_id,)).fetchone()
    if not row:
        conn.close()
        return None
    patient = dict(row)
    # Historial de citas del paciente
    appts = conn.execute("""
    SELECT a.*, s.name as service_name, s.color as service_color, s.price as service_price
    FROM appointments a
    JOIN services s ON a.service_id = s.id
    WHERE a.patient_id = ?
    ORDER BY a.appointment_date DESC, a.appointment_time DESC
    """, (patient_id,)).fetchall()
    patient["history"] = [dict(a) for a in appts]
    conn.close()
    return patient

def create_patient(data):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO patients (name, phone, email, birth_date, allergies, skin_type, notes)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        data["name"],
        data["phone"],
        data.get("email", ""),
        data.get("birth_date", ""),
        data.get("allergies", "Ninguna"),
        data.get("skin_type", ""),
        data.get("notes", "")
    ))
    patient_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return get_patient_by_id(patient_id)

def update_patient(patient_id, data):
    conn = get_connection()
    fields = []
    values = []
    for key in ["name", "phone", "email", "birth_date", "allergies", "skin_type", "notes"]:
        if key in data:
            fields.append(f"{key} = ?")
            values.append(data[key])
    if fields:
        values.append(patient_id)
        conn.execute(f"UPDATE patients SET {', '.join(fields)} WHERE id = ?", values)
        conn.commit()
    conn.close()
    return get_patient_by_id(patient_id)

def delete_patient(patient_id):
    conn = get_connection()
    # Eliminar notificaciones de sus citas
    conn.execute("DELETE FROM notification_logs WHERE patient_id = ?", (patient_id,))
    # Eliminar citas asociadas
    conn.execute("DELETE FROM appointments WHERE patient_id = ?", (patient_id,))
    # Eliminar paciente
    conn.execute("DELETE FROM patients WHERE id = ?", (patient_id,))
    conn.commit()
    conn.close()
    return True

def get_services(active_only=True):
    conn = get_connection()
    query = "SELECT * FROM services"
    if active_only:
        query += " WHERE is_active = 1"
    query += " ORDER BY category ASC, name ASC"
    rows = conn.execute(query).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_service_by_id(service_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM services WHERE id = ?", (service_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def create_service(data):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO services (name, category, duration_minutes, price, instructions, color)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (
        data["name"],
        data.get("category", "General"),
        int(data.get("duration_minutes", 60)),
        float(data.get("price", 0.0)),
        data.get("instructions", ""),
        data.get("color", "#E0A9AF")
    ))
    svc_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return svc_id

def update_service(service_id, data):
    conn = get_connection()
    fields = []
    values = []
    for key in ["name", "category", "duration_minutes", "price", "instructions", "color", "is_active"]:
        if key in data:
            fields.append(f"{key} = ?")
            values.append(data[key])
    if fields:
        values.append(service_id)
        conn.execute(f"UPDATE services SET {', '.join(fields)} WHERE id = ?", values)
        conn.commit()
    conn.close()
    return get_service_by_id(service_id)

def delete_service(service_id):
    conn = get_connection()
    conn.execute("UPDATE services SET is_active = 0 WHERE id = ?", (service_id,))
    conn.commit()
    conn.close()
    return True

def export_full_state():
    conn = get_connection()
    patients = [dict(r) for r in conn.execute("SELECT * FROM patients").fetchall()]
    services = [dict(r) for r in conn.execute("SELECT * FROM services").fetchall()]
    appointments = [dict(r) for r in conn.execute("SELECT * FROM appointments").fetchall()]
    settings = {r["key"]: r["value"] for r in conn.execute("SELECT * FROM settings").fetchall()}
    conn.close()
    return {
        "version": "1.0",
        "exported_at": datetime.now().isoformat(),
        "patients": patients,
        "services": services,
        "appointments": appointments,
        "settings": settings
    }

def import_full_state(data):
    conn = get_connection()
    cursor = conn.cursor()

    if "patients" in data and isinstance(data["patients"], list):
        cursor.execute("DELETE FROM notification_logs")
        cursor.execute("DELETE FROM appointments")
        cursor.execute("DELETE FROM patients")
        for p in data["patients"]:
            cursor.execute("""
            INSERT OR REPLACE INTO patients (id, name, phone, email, birth_date, allergies, skin_type, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                p.get("id"), p.get("name"), p.get("phone"), p.get("email"),
                p.get("birth_date"), p.get("allergies"), p.get("skin_type"),
                p.get("notes"), p.get("created_at")
            ))

    if "services" in data and isinstance(data["services"], list):
        cursor.execute("DELETE FROM services")
        for s in data["services"]:
            cursor.execute("""
            INSERT OR REPLACE INTO services (id, name, category, duration_minutes, price, instructions, color, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                s.get("id"), s.get("name"), s.get("category", "General"),
                s.get("duration_minutes", 60), s.get("price", 0.0),
                s.get("instructions", ""), s.get("color", "#E0A9AF"),
                s.get("is_active", 1)
            ))

    if "appointments" in data and isinstance(data["appointments"], list):
        for a in data["appointments"]:
            cursor.execute("""
            INSERT OR REPLACE INTO appointments (
                id, patient_id, service_id, appointment_date, appointment_time, duration_minutes,
                status, specialist, notes, confirmation_token, reminder_sent_at, confirmed_at, canceled_at, cancellation_reason, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                a.get("id"), a.get("patient_id"), a.get("service_id"),
                a.get("appointment_date"), a.get("appointment_time"),
                a.get("duration_minutes", 60), a.get("status", "Pendiente"),
                a.get("specialist", "Cosmetóloga Constanza Díaz"),
                a.get("notes"), a.get("confirmation_token") or secrets.token_urlsafe(16),
                a.get("reminder_sent_at"), a.get("confirmed_at"),
                a.get("canceled_at"), a.get("cancellation_reason"),
                a.get("created_at")
            ))

    if "settings" in data and isinstance(data["settings"], dict):
        for k, v in data["settings"].items():
            cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (k, str(v)))

    conn.commit()
    conn.close()
    return True


