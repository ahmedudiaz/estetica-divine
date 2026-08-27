"""
database.py - Gestión de Base de Datos SQLite para Estética Divine
Soporte Multi-Usuario, Autenticación Segura y Aislamiento de Datos por Especialista
"""
import sqlite3
import os
import secrets
import hashlib
from datetime import datetime, date, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "agenda_estetica.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ----------------------------------------------------
# SEGURIDAD & HASHING DE CONTRASEÑAS (PBKDF2-HMAC-SHA256)
# ----------------------------------------------------
def hash_password(password, salt=None):
    if not salt:
        salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
    return key.hex(), salt

def verify_password(password, stored_hash, salt):
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
    return key.hex() == stored_hash

# ----------------------------------------------------
# INICIALIZACIÓN Y MIGRACIÓN DE TABLAS
# ----------------------------------------------------
def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Tabla de Usuarios / Especialistas
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        salt TEXT NOT NULL,
        specialty TEXT DEFAULT 'Cosmetóloga',
        phone TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Tabla de Sesiones Activas
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        token TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        expires_at DATETIME,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)

    # Tabla de Configuración (por usuario)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER DEFAULT 1,
        key TEXT NOT NULL,
        value TEXT,
        UNIQUE(user_id, key)
    )
    """)

    # Tabla de Pacientes
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS patients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER DEFAULT 1,
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
        user_id INTEGER DEFAULT 1,
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
        user_id INTEGER DEFAULT 1,
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
        FOREIGN KEY (patient_id) REFERENCES patients (id) ON DELETE CASCADE,
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
        FOREIGN KEY (appointment_id) REFERENCES appointments (id) ON DELETE CASCADE,
        FOREIGN KEY (patient_id) REFERENCES patients (id) ON DELETE CASCADE
    )
    """)

    # Migración: Comprobar y agregar columna user_id en tablas si no existen
    for table in ["patients", "services", "appointments", "settings"]:
        columns = [row["name"] for row in cursor.execute(f"PRAGMA table_info({table})").fetchall()]
        if "user_id" not in columns:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN user_id INTEGER DEFAULT 1")

    # Crear Usuario Principal por Defecto si no existe ninguno
    cursor.execute("SELECT COUNT(*) as count FROM users")
    if cursor.fetchone()["count"] == 0:
        pwd_hash, salt = hash_password("divine123")
        cursor.execute("""
        INSERT INTO users (id, name, email, password_hash, salt, specialty, phone)
        VALUES (1, 'Cosmetóloga Constanza Díaz', 'constanza@esteticadivine.com', ?, ?, 'Cosmetóloga & Directora', '+56959432935')
        """, (pwd_hash, salt))

    # Configuración por defecto para usuario 1
    default_settings = {
        "clinic_name": "Estética Divine",
        "clinic_phone": "+56959432935",
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
        cursor.execute("INSERT OR IGNORE INTO settings (user_id, key, value) VALUES (1, ?, ?)", (k, v))

    # Sembrar servicios base para usuario 1 si no tiene
    cursor.execute("SELECT COUNT(*) as count FROM services WHERE user_id = 1")
    if cursor.fetchone()["count"] == 0:
        seed_default_services(cursor, 1)

    conn.commit()
    conn.close()

def seed_default_services(cursor, user_id):
    services = [
        ("Limpieza Facial Profunda con Hidrodermoabrasión", "Facial", 60, 45.0, "Venir sin maquillaje. No exfoliarse las 48h previas.", "#F472B6"),
        ("Peeling Químico Renovador Iluminador", "Facial", 45, 60.0, "Evitar exposición solar directa antes y después de la sesión.", "#FB7185"),
        ("Radiofrecuencia Facial y Cuello Efecto Lifting", "Facial", 60, 55.0, "Excelente hidratación previa recomendada.", "#EC4899"),
        ("Depilación Láser Diodo - Piernas Completas", "Depilación", 45, 40.0, "Venir rasurada 24 horas antes con cuchilla. Sin cremas corporales.", "#818CF8"),
        ("Drenaje Linfático Manual y Presoterapia", "Corporal", 60, 35.0, "Beber 1 litro de agua antes de la sesión.", "#34D399"),
        ("Masaje Reductor y Modelador con Maderoterapia", "Corporal", 50, 40.0, "No ingerir comidas pesadas 1 hora antes.", "#FBBF24"),
        ("Armonización y Aplicación de Toxina Botulínica", "Medicina Estética", 30, 180.0, "No consumir alcohol ni aspirinas las 24 horas previas.", "#A78BFA")
    ]
    for s in services:
        cursor.execute("""
        INSERT INTO services (user_id, name, category, duration_minutes, price, instructions, color)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, s[0], s[1], s[2], s[3], s[4], s[5]))

# ----------------------------------------------------
# GESTIÓN DE USUARIOS Y AUTENTICACIÓN
# ----------------------------------------------------
def create_user(name, email, password, specialty="Cosmetóloga", phone=""):
    conn = get_connection()
    cursor = conn.cursor()
    email_clean = email.strip().lower()

    # Verificar si el correo ya existe
    existing = cursor.execute("SELECT id FROM users WHERE email = ?", (email_clean,)).fetchone()
    if existing:
        conn.close()
        return None, "El correo electrónico ya está registrado."

    pwd_hash, salt = hash_password(password)
    cursor.execute("""
    INSERT INTO users (name, email, password_hash, salt, specialty, phone)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (name.strip(), email_clean, pwd_hash, salt, specialty.strip(), phone.strip()))
    new_user_id = cursor.lastrowid

    # Crear catálogo de tratamientos iniciales para este nuevo usuario
    seed_default_services(cursor, new_user_id)

    # Configuración base para el nuevo usuario
    default_settings = {
        "clinic_name": f"Estética Divine - {name.strip()}",
        "clinic_phone": phone.strip() or "+56959432935",
        "clinic_address": "Av. Principal 142, Suite 3B, Ciudad",
        "clinic_email": email_clean,
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
        )
    }
    for k, v in default_settings.items():
        cursor.execute("INSERT OR IGNORE INTO settings (user_id, key, value) VALUES (?, ?, ?)", (new_user_id, k, v))

    conn.commit()
    user = get_user_by_id(new_user_id, conn)
    conn.close()
    return user, None

def authenticate_user(email, password):
    conn = get_connection()
    email_clean = email.strip().lower()
    row = conn.execute("SELECT * FROM users WHERE email = ?", (email_clean,)).fetchone()
    if not row:
        conn.close()
        return None, "Correo o contraseña incorrectos."

    if not verify_password(password, row["password_hash"], row["salt"]):
        conn.close()
        return None, "Correo o contraseña incorrectos."

    user = {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "specialty": row["specialty"],
        "phone": row["phone"],
        "created_at": row["created_at"]
    }
    conn.close()
    return user, None

def reset_user_password(email, phone, new_password):
    conn = get_connection()
    cursor = conn.cursor()
    email_clean = email.strip().lower()
    
    def clean_digits(p):
        return "".join(c for c in (p or "") if c.isdigit())
    
    phone_digits = clean_digits(phone)
    if len(phone_digits) < 6:
        conn.close()
        return None, "Ingresa un número de teléfono o WhatsApp válido para verificar tu identidad."

    user_row = cursor.execute("SELECT * FROM users WHERE LOWER(email) = ?", (email_clean,)).fetchone()
    if not user_row:
        conn.close()
        return None, "No existe ninguna cuenta registrada con este correo electrónico."

    db_phone_digits = clean_digits(user_row["phone"])
    # Verificación de coincidencia de teléfono
    if not (phone_digits in db_phone_digits or db_phone_digits in phone_digits or (len(phone_digits) >= 8 and phone_digits[-8:] == db_phone_digits[-8:])):
        conn.close()
        return None, "El número de teléfono/WhatsApp no coincide con el registrado en esta cuenta."

    if len(new_password) < 4:
        conn.close()
        return None, "La nueva contraseña debe tener al menos 4 caracteres."

    pwd_hash, salt = hash_password(new_password)
    cursor.execute("""
    UPDATE users SET password_hash = ?, salt = ? WHERE id = ?
    """, (pwd_hash, salt, user_row["id"]))
    
    # Invalidar sesiones antiguas por seguridad
    cursor.execute("DELETE FROM sessions WHERE user_id = ?", (user_row["id"],))
    
    conn.commit()
    user = get_user_by_id(user_row["id"], conn)
    conn.close()
    return user, None

def create_session(user_id, duration_days=30):
    conn = get_connection()
    token = secrets.token_hex(32)
    expires_at = (datetime.now() + timedelta(days=duration_days)).isoformat()
    conn.execute("""
    INSERT INTO sessions (token, user_id, expires_at)
    VALUES (?, ?, ?)
    """, (token, user_id, expires_at))
    conn.commit()
    conn.close()
    return token

def get_user_by_session_token(token):
    if not token:
        return None
    conn = get_connection()
    row = conn.execute("""
    SELECT u.id, u.name, u.email, u.specialty, u.phone, u.created_at, s.expires_at
    FROM sessions s
    JOIN users u ON s.user_id = u.id
    WHERE s.token = ?
    """, (token,)).fetchone()
    
    if not row:
        conn.close()
        return None

    # Verificar si expiró
    if row["expires_at"]:
        try:
            exp = datetime.fromisoformat(row["expires_at"])
            if datetime.now() > exp:
                conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
                conn.commit()
                conn.close()
                return None
        except Exception:
            pass

    user = {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "specialty": row["specialty"],
        "phone": row["phone"],
        "created_at": row["created_at"]
    }
    conn.close()
    return user

def delete_session(token):
    conn = get_connection()
    conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
    conn.commit()
    conn.close()
    return True

def get_user_by_id(user_id, conn=None):
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True
    row = conn.execute("SELECT id, name, email, specialty, phone, created_at FROM users WHERE id = ?", (user_id,)).fetchone()
    if close_conn:
        conn.close()
    return dict(row) if row else None

# ----------------------------------------------------
# CONSULTAS Y ESTADÍSTICAS POR USUARIO
# ----------------------------------------------------
def get_settings(user_id=1):
    conn = get_connection()
    rows = conn.execute("SELECT key, value FROM settings WHERE user_id = ?", (user_id,)).fetchall()
    conn.close()
    return {r["key"]: r["value"] for r in rows}

def update_setting(key, value, user_id=1):
    conn = get_connection()
    conn.execute("INSERT OR REPLACE INTO settings (user_id, key, value) VALUES (?, ?, ?)", (user_id, key, value))
    conn.commit()
    conn.close()

def get_stats(user_id=1):
    conn = get_connection()
    today_str = date.today().strftime("%Y-%m-%d")
    tomorrow_str = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")

    # Citas hoy
    today_appts = conn.execute("""
    SELECT COUNT(*) as total, SUM(CASE WHEN status='Confirmada' THEN 1 ELSE 0 END) as confirmed 
    FROM appointments 
    WHERE user_id = ? AND appointment_date = ?
    """, (user_id, today_str)).fetchone()
    
    # Citas mañana y confirmaciones
    tomorrow_appts = conn.execute("""
    SELECT COUNT(*) as total, 
           SUM(CASE WHEN status='Confirmada' THEN 1 ELSE 0 END) as confirmed, 
           SUM(CASE WHEN status='Pendiente' OR status='Recordatorio Enviado' THEN 1 ELSE 0 END) as unconfirmed 
    FROM appointments 
    WHERE user_id = ? AND appointment_date = ?
    """, (user_id, tomorrow_str)).fetchone()

    # Total pacientes del usuario
    total_patients = conn.execute("SELECT COUNT(*) as count FROM patients WHERE user_id = ?", (user_id,)).fetchone()["count"]

    # Ingresos estimados de la semana
    week_start = (date.today() - timedelta(days=date.today().weekday())).strftime("%Y-%m-%d")
    week_end = (date.today() + timedelta(days=7)).strftime("%Y-%m-%d")
    revenue = conn.execute("""
    SELECT SUM(s.price) as total_revenue 
    FROM appointments a 
    JOIN services s ON a.service_id = s.id 
    WHERE a.user_id = ? AND a.appointment_date >= ? AND a.appointment_date <= ? AND a.status != 'Cancelada'
    """, (user_id, week_start, week_end)).fetchone()["total_revenue"] or 0

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

# ----------------------------------------------------
# GESTIÓN DE CITAS POR USUARIO
# ----------------------------------------------------
def get_appointments(user_id=1, date_from=None, date_to=None, status=None, patient_id=None):
    conn = get_connection()
    query = """
    SELECT a.*, p.name as patient_name, p.phone as patient_phone, p.email as patient_email,
           s.name as service_name, s.category as service_category, s.price as service_price,
           s.duration_minutes as service_duration, s.instructions as service_instructions, s.color as service_color
    FROM appointments a
    JOIN patients p ON a.patient_id = p.id
    JOIN services s ON a.service_id = s.id
    WHERE a.user_id = ?
    """
    params = [user_id]

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

def get_appointment_by_id(appt_id, user_id=None):
    conn = get_connection()
    query = """
    SELECT a.*, p.name as patient_name, p.phone as patient_phone, p.email as patient_email,
           s.name as service_name, s.category as service_category, s.price as service_price,
           s.duration_minutes as service_duration, s.instructions as service_instructions, s.color as service_color
    FROM appointments a
    JOIN patients p ON a.patient_id = p.id
    JOIN services s ON a.service_id = s.id
    WHERE a.id = ?
    """
    params = [appt_id]
    if user_id is not None:
        query += " AND a.user_id = ?"
        params.append(user_id)

    row = conn.execute(query, params).fetchone()
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

def create_appointment(data, user_id=1):
    conn = get_connection()
    cursor = conn.cursor()
    token = secrets.token_urlsafe(16)

    # Obtener duración del servicio si no se especifica
    duration = data.get("duration_minutes")
    if not duration:
        svc = conn.execute("SELECT duration_minutes FROM services WHERE id = ?", (data["service_id"],)).fetchone()
        duration = svc["duration_minutes"] if svc else 60

    user_info = get_user_by_id(user_id, conn)
    default_specialist = user_info["name"] if user_info else "Cosmetóloga Constanza Díaz"

    cursor.execute("""
    INSERT INTO appointments (
        user_id, patient_id, service_id, appointment_date, appointment_time,
        duration_minutes, status, specialist, notes, confirmation_token
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        data["patient_id"],
        data["service_id"],
        data["appointment_date"],
        data["appointment_time"],
        duration,
        data.get("status", "Pendiente"),
        data.get("specialist", default_specialist),
        data.get("notes", ""),
        token
    ))
    appt_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return get_appointment_by_id(appt_id)

def update_appointment(appt_id, data, user_id=None):
    conn = get_connection()
    fields = []
    values = []
    for key in ["patient_id", "service_id", "appointment_date", "appointment_time", "duration_minutes", "status", "specialist", "notes"]:
        if key in data:
            fields.append(f"{key} = ?")
            values.append(data[key])
    if fields:
        query = f"UPDATE appointments SET {', '.join(fields)} WHERE id = ?"
        values.append(appt_id)
        if user_id is not None:
            query += " AND user_id = ?"
            values.append(user_id)
        conn.execute(query, values)
        conn.commit()
    conn.close()
    return get_appointment_by_id(appt_id, user_id)

def delete_appointment(appt_id, user_id=None):
    conn = get_connection()
    conn.execute("DELETE FROM notification_logs WHERE appointment_id = ?", (appt_id,))
    query = "DELETE FROM appointments WHERE id = ?"
    params = [appt_id]
    if user_id is not None:
        query += " AND user_id = ?"
        params.append(user_id)
    conn.execute(query, params)
    conn.commit()
    conn.close()
    return True

def confirm_appointment_by_token(token, action="confirm", reason=None):
    conn = get_connection()
    if action == "confirm":
        conn.execute("""
        UPDATE appointments 
        SET status = 'Confirmada', confirmed_at = CURRENT_TIMESTAMP 
        WHERE confirmation_token = ?
        """, (token,))
    elif action in ("reschedule", "cancel"):
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
        SET status = 'Recordatorio Enviado',
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

# ----------------------------------------------------
# GESTIÓN DE PACIENTES POR USUARIO
# ----------------------------------------------------
def get_patients(user_id=1, search=""):
    conn = get_connection()
    if search:
        s = f"%{search}%"
        rows = conn.execute("""
        SELECT p.*, COUNT(a.id) as total_appointments
        FROM patients p
        LEFT JOIN appointments a ON p.id = a.patient_id
        WHERE p.user_id = ? AND (p.name LIKE ? OR p.phone LIKE ? OR p.email LIKE ?)
        GROUP BY p.id
        ORDER BY p.name ASC
        """, (user_id, s, s, s)).fetchall()
    else:
        rows = conn.execute("""
        SELECT p.*, COUNT(a.id) as total_appointments
        FROM patients p
        LEFT JOIN appointments a ON p.id = a.patient_id
        WHERE p.user_id = ?
        GROUP BY p.id
        ORDER BY p.name ASC
        """, (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_patient_by_id(patient_id, user_id=None):
    conn = get_connection()
    query = """
    SELECT p.*, COUNT(a.id) as total_appointments
    FROM patients p
    LEFT JOIN appointments a ON p.id = a.patient_id
    WHERE p.id = ?
    """
    params = [patient_id]
    if user_id is not None:
        query += " AND p.user_id = ?"
        params.append(user_id)
    query += " GROUP BY p.id"
    row = conn.execute(query, params).fetchone()
    conn.close()
    return dict(row) if row else None

def create_patient(data, user_id=1):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO patients (user_id, name, phone, email, birth_date, allergies, skin_type, notes)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        data["name"],
        data["phone"],
        data.get("email", ""),
        data.get("birth_date", ""),
        data.get("allergies", "Ninguna"),
        data.get("skin_type", "Normal"),
        data.get("notes", "")
    ))
    patient_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return get_patient_by_id(patient_id, user_id)

def update_patient(patient_id, data, user_id=None):
    conn = get_connection()
    fields = []
    values = []
    for key in ["name", "phone", "email", "birth_date", "allergies", "skin_type", "notes"]:
        if key in data:
            fields.append(f"{key} = ?")
            values.append(data[key])
    if fields:
        query = f"UPDATE patients SET {', '.join(fields)} WHERE id = ?"
        values.append(patient_id)
        if user_id is not None:
            query += " AND user_id = ?"
            values.append(user_id)
        conn.execute(query, values)
        conn.commit()
    conn.close()
    return get_patient_by_id(patient_id, user_id)

def delete_patient(patient_id, user_id=None):
    conn = get_connection()
    # Eliminar notificaciones y citas asociadas
    conn.execute("DELETE FROM notification_logs WHERE patient_id = ?", (patient_id,))
    conn.execute("DELETE FROM appointments WHERE patient_id = ?", (patient_id,))
    query = "DELETE FROM patients WHERE id = ?"
    params = [patient_id]
    if user_id is not None:
        query += " AND user_id = ?"
        params.append(user_id)
    conn.execute(query, params)
    conn.commit()
    conn.close()
    return True

# ----------------------------------------------------
# GESTIÓN DE SERVICIOS POR USUARIO
# ----------------------------------------------------
def get_services(user_id=1, active_only=True):
    conn = get_connection()
    query = "SELECT * FROM services WHERE user_id = ?"
    params = [user_id]
    if active_only:
        query += " AND is_active = 1"
    query += " ORDER BY category ASC, name ASC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_service_by_id(service_id, user_id=None):
    conn = get_connection()
    query = "SELECT * FROM services WHERE id = ?"
    params = [service_id]
    if user_id is not None:
        query += " AND user_id = ?"
        params.append(user_id)
    row = conn.execute(query, params).fetchone()
    conn.close()
    return dict(row) if row else None

def create_service(data, user_id=1):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO services (user_id, name, category, duration_minutes, price, instructions, color)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
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

def update_service(service_id, data, user_id=None):
    conn = get_connection()
    fields = []
    values = []
    for key in ["name", "category", "duration_minutes", "price", "instructions", "color", "is_active"]:
        if key in data:
            fields.append(f"{key} = ?")
            values.append(data[key])
    if fields:
        query = f"UPDATE services SET {', '.join(fields)} WHERE id = ?"
        values.append(service_id)
        if user_id is not None:
            query += " AND user_id = ?"
            values.append(user_id)
        conn.execute(query, values)
        conn.commit()
    conn.close()
    return get_service_by_id(service_id, user_id)

def delete_service(service_id, user_id=None):
    conn = get_connection()
    query = "UPDATE services SET is_active = 0 WHERE id = ?"
    params = [service_id]
    if user_id is not None:
        query += " AND user_id = ?"
        params.append(user_id)
    conn.execute(query, params)
    conn.commit()
    conn.close()
    return True

# ----------------------------------------------------
# EXPORTACIÓN E IMPORTACIÓN DE ESTADO POR USUARIO
# ----------------------------------------------------
def export_full_state(user_id=1):
    conn = get_connection()
    patients = [dict(r) for r in conn.execute("SELECT * FROM patients WHERE user_id = ?", (user_id,)).fetchall()]
    services = [dict(r) for r in conn.execute("SELECT * FROM services WHERE user_id = ?", (user_id,)).fetchall()]
    appointments = [dict(r) for r in conn.execute("SELECT * FROM appointments WHERE user_id = ?", (user_id,)).fetchall()]
    settings = {r["key"]: r["value"] for r in conn.execute("SELECT key, value FROM settings WHERE user_id = ?", (user_id,)).fetchall()}
    user = get_user_by_id(user_id, conn)
    conn.close()
    return {
        "version": "2.0",
        "user": user,
        "exported_at": datetime.now().isoformat(),
        "patients": patients,
        "services": services,
        "appointments": appointments,
        "settings": settings
    }

def import_full_state(data, user_id=1):
    conn = get_connection()
    cursor = conn.cursor()

    if "patients" in data and isinstance(data["patients"], list):
        cursor.execute("DELETE FROM notification_logs WHERE patient_id IN (SELECT id FROM patients WHERE user_id = ?)", (user_id,))
        cursor.execute("DELETE FROM appointments WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM patients WHERE user_id = ?", (user_id,))
        for p in data["patients"]:
            cursor.execute("""
            INSERT OR REPLACE INTO patients (id, user_id, name, phone, email, birth_date, allergies, skin_type, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                p.get("id"), user_id, p.get("name"), p.get("phone"), p.get("email"),
                p.get("birth_date"), p.get("allergies"), p.get("skin_type"),
                p.get("notes"), p.get("created_at")
            ))

    if "services" in data and isinstance(data["services"], list):
        cursor.execute("DELETE FROM services WHERE user_id = ?", (user_id,))
        for s in data["services"]:
            cursor.execute("""
            INSERT OR REPLACE INTO services (id, user_id, name, category, duration_minutes, price, instructions, color, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                s.get("id"), user_id, s.get("name"), s.get("category", "General"),
                s.get("duration_minutes", 60), s.get("price", 0.0),
                s.get("instructions", ""), s.get("color", "#E0A9AF"),
                s.get("is_active", 1)
            ))

    if "appointments" in data and isinstance(data["appointments"], list):
        for a in data["appointments"]:
            cursor.execute("""
            INSERT OR REPLACE INTO appointments (
                id, user_id, patient_id, service_id, appointment_date, appointment_time, duration_minutes,
                status, specialist, notes, confirmation_token, reminder_sent_at, confirmed_at, canceled_at, cancellation_reason, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                a.get("id"), user_id, a.get("patient_id"), a.get("service_id"),
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
            cursor.execute("INSERT OR REPLACE INTO settings (user_id, key, value) VALUES (?, ?, ?)", (user_id, k, str(v)))

    conn.commit()
    conn.close()
    return True
