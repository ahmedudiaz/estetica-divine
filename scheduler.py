"""
scheduler.py - Módulo de Generación de Recordatorios y Enlaces de WhatsApp
"""
import urllib.parse
from datetime import datetime, date, timedelta
from database import get_connection, get_settings, get_appointments, mark_reminder_sent

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

def generate_reminder_message(appointment, base_url="http://localhost:8000", user_id=1):
    settings = get_settings(user_id)
    template = settings.get("whatsapp_template", "")
    
    fecha_formateada = format_date_es(appointment["appointment_date"])
    token = appointment.get("confirmation_token")
    enlace_confirmacion = f"{base_url}/confirmar/{token}"

    indicaciones = ""
    if appointment.get("service_instructions"):
        indicaciones = f"💡 *Recomendaciones previas:* {appointment['service_instructions']}\n"

    message = template.format(
        nombre_paciente=appointment["patient_name"],
        centro=settings.get("clinic_name", "Estética Divine"),
        fecha=fecha_formateada,
        hora=appointment["appointment_time"],
        tratamiento=appointment["service_name"],
        especialista=appointment.get("specialist", "Especialista"),
        direccion=settings.get("clinic_address", ""),
        indicaciones=indicaciones,
        enlace_confirmacion=enlace_confirmacion
    )
    return message

def clean_phone_for_whatsapp(phone):
    # Remueve espacios, guiones y paréntesis
    cleaned = "".join(c for c in phone if c.isdigit() or c == "+")
    if cleaned.startswith("+"):
        cleaned = cleaned[1:]
    return cleaned

def generate_whatsapp_link(phone, message):
    cleaned_phone = clean_phone_for_whatsapp(phone)
    encoded_text = urllib.parse.quote(message)
    # Enlace universal wa.me
    return f"https://wa.me/{cleaned_phone}?text={encoded_text}"

def get_tomorrow_reminders(base_url="http://localhost:8000", user_id=1):
    tomorrow_str = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
    conn = get_connection()
    query = """
    SELECT a.*, p.name as patient_name, p.phone as patient_phone, p.email as patient_email,
           s.name as service_name, s.category as service_category, s.price as service_price,
           s.duration_minutes as service_duration, s.instructions as service_instructions, s.color as service_color
    FROM appointments a
    JOIN patients p ON a.patient_id = p.id
    JOIN services s ON a.service_id = s.id
    WHERE a.user_id = ? AND a.appointment_date = ? AND a.status != 'Cancelada'
    ORDER BY a.appointment_time ASC
    """
    rows = conn.execute(query, (user_id, tomorrow_str)).fetchall()
    conn.close()

    reminders = []
    for r in rows:
        appt = dict(r)
        msg = generate_reminder_message(appt, base_url, user_id)
        wa_link = generate_whatsapp_link(appt["patient_phone"], msg)
        appt["formatted_message"] = msg
        appt["whatsapp_link"] = wa_link
        appt["is_confirmed"] = (appt["status"] == "Confirmada")
        appt["is_reminder_sent"] = (appt["reminder_sent_at"] is not None)
        reminders.append(appt)

    return reminders
