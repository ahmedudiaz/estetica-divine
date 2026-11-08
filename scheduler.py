"""
scheduler.py - Módulo de Generación de Recordatorios y Enlaces de WhatsApp
"""
import urllib.parse
import secrets
from datetime import datetime, date, timedelta, timezone
from database import (
    get_connection, get_settings, get_appointments, mark_reminder_sent,
    encode_appointment_payload
)

def get_local_today():
    # Ajuste a zona horaria Chile (UTC-3) para evitar saltos de día en servidores UTC (como Render)
    chile_tz = timezone(timedelta(hours=-3))
    return datetime.now(chile_tz).date()

def format_date_es(date_str):
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        dia_semana = dias[dt.weekday()]
        dia = dt.day
        mes = meses[dt.month - 1]
        return f"{dia_semana} {dia} de {mes}"
    except Exception:
        return date_str

def build_confirmation_url(appointment, base_url="http://localhost:8000", user_id=1):
    token = appointment.get("confirmation_token")
    if not token or token == "None":
        token = secrets.token_urlsafe(16)
    encoded_d = encode_appointment_payload(appointment, user_id=user_id)
    if encoded_d:
        return f"{base_url}/confirmar/{token}?d={encoded_d}"
    return f"{base_url}/confirmar/{token}"

def generate_reminder_message(appointment, base_url="http://localhost:8000", user_id=1):
    settings = get_settings(user_id)
    template = settings.get("whatsapp_template", "")
    
    fecha_formateada = format_date_es(appointment["appointment_date"])
    enlace_confirmacion = build_confirmation_url(appointment, base_url, user_id)

    indicaciones = ""
    if appointment.get("service_instructions"):
        indicaciones = f"💡 *Recomendaciones previas:* {appointment['service_instructions']}\n"

    try:
        message = template.format(
            nombre_paciente=appointment.get("patient_name", "Paciente"),
            centro=settings.get("clinic_name", "Estética Divine"),
            fecha=fecha_formateada,
            hora=appointment.get("appointment_time", ""),
            tratamiento=appointment.get("service_name", "Tratamiento"),
            especialista=appointment.get("specialist", "Especialista"),
            direccion=settings.get("clinic_address", ""),
            indicaciones=indicaciones,
            enlace_confirmacion=enlace_confirmacion
        )
    except Exception:
        message = (
            f"✨ *¡Hola, {appointment.get('patient_name', 'Paciente')}!* Te saludamos de *{settings.get('clinic_name', 'Estética Divine')}*.\n\n"
            f"Te recordamos tu cita:\n"
            f"📅 *Fecha:* {fecha_formateada}\n"
            f"⏰ *Hora:* {appointment.get('appointment_time', '')} hrs\n"
            f"💆‍♀️ *Tratamiento:* {appointment.get('service_name', 'Tratamiento')}\n"
            f"Por favor confirma tu asistencia aquí:\n👉 {enlace_confirmacion}"
        )
    return message

def clean_phone_for_whatsapp(phone):
    # Remueve espacios, guiones y paréntesis
    cleaned = "".join(c for c in (phone or "") if c.isdigit() or c == "+")
    if cleaned.startswith("+"):
        cleaned = cleaned[1:]
    return cleaned

def generate_whatsapp_link(phone, message):
    cleaned_phone = clean_phone_for_whatsapp(phone)
    encoded_text = urllib.parse.quote(message)
    # Enlace universal wa.me
    return f"https://wa.me/{cleaned_phone}?text={encoded_text}"

def get_tomorrow_reminders(base_url="http://localhost:8000", user_id=1):
    tomorrow_str = (get_local_today() + timedelta(days=1)).strftime("%Y-%m-%d")
    conn = get_connection()
    query = """
    SELECT a.*,
           COALESCE(p.name, 'Paciente') as patient_name,
           COALESCE(p.phone, '') as patient_phone,
           COALESCE(p.email, '') as patient_email,
           COALESCE(s.name, 'Tratamiento Estético') as service_name,
           COALESCE(s.category, 'Estética') as service_category,
           COALESCE(s.price, 0) as service_price,
           COALESCE(s.duration_minutes, a.duration_minutes, 60) as service_duration,
           COALESCE(s.instructions, '') as service_instructions,
           COALESCE(s.color, '#E0A9AF') as service_color
    FROM appointments a
    LEFT JOIN patients p ON a.patient_id = p.id
    LEFT JOIN services s ON a.service_id = s.id
    WHERE a.user_id = ? AND a.appointment_date = ? AND a.status != 'Cancelada'
    ORDER BY a.appointment_time ASC
    """
    rows = conn.execute(query, (user_id, tomorrow_str)).fetchall()

    reminders = []
    for r in rows:
        appt = dict(r)
        if not appt.get("confirmation_token") or appt.get("confirmation_token") == "None":
            new_tok = secrets.token_urlsafe(16)
            conn.execute("UPDATE appointments SET confirmation_token = ? WHERE id = ?", (new_tok, appt["id"]))
            conn.commit()
            appt["confirmation_token"] = new_tok
        msg = generate_reminder_message(appt, base_url, user_id)
        wa_link = generate_whatsapp_link(appt["patient_phone"], msg)
        appt["formatted_message"] = msg
        appt["whatsapp_link"] = wa_link
        appt["confirmation_url"] = build_confirmation_url(appt, base_url, user_id)
        appt["is_confirmed"] = (appt["status"] == "Confirmada")
        appt["is_reminder_sent"] = (appt["reminder_sent_at"] is not None)
        reminders.append(appt)

    conn.close()
    return reminders
