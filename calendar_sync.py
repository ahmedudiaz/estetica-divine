"""
calendar_sync.py - Generación de feeds iCalendar (.ics) y utilidades de red móvil
"""
import socket
from datetime import datetime, timedelta

def get_local_ip():
    """Detecta la IP local en la red Wi-Fi para conectar el celular"""
    s = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"
    finally:
        if s:
            s.close()

def generate_ics_feed(appointments, clinic_name="Estética Divine"):
    """
    Genera un archivo compatible con Apple Calendar, Google Calendar y Outlook (RFC 5545)
    para sincronización en tiempo real desde el celular.
    """
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//EsteticaDivine//Agenda Estetica v1.0//ES",
        f"X-WR-CALNAME:{clinic_name} - Agenda de Turnos",
        "X-WR-TIMEZONE:America/Santiago",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH"
    ]

    for appt in appointments:
        if appt.get("status") == "Cancelada":
            continue

        try:
            date_str = appt["appointment_date"]  # YYYY-MM-DD
            time_str = appt["appointment_time"]  # HH:MM
            duration = int(appt.get("duration_minutes", 60))

            start_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
            end_dt = start_dt + timedelta(minutes=duration)

            dtstart = start_dt.strftime("%Y%m%dT%H%M00")
            dtend = end_dt.strftime("%Y%m%dT%H%M00")
            uid = f"appt-{appt['id']}-{appt.get('confirmation_token', 'token')}@esteticadivine.app"

            summary = f"💆‍♀️ {appt['service_name']} - {appt['patient_name']}"
            description = (
                f"Paciente: {appt['patient_name']}\\n"
                f"Tel/WhatsApp: {appt['patient_phone']}\\n"
                f"Estado: {appt['status']}\\n"
                f"Especialista: {appt.get('specialist', 'Cosmetóloga Constanza Díaz')}\\n"
                f"Notas: {appt.get('notes', '') or 'Sin notas'}"
            )
            location = "Estética Divine - Centro de Estética"

            lines.extend([
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTAMP:{datetime.now().strftime('%Y%m%dT%H%M00Z')}",
                f"DTSTART:{dtstart}",
                f"DTEND:{dtend}",
                f"SUMMARY:{summary}",
                f"DESCRIPTION:{description}",
                f"LOCATION:{location}",
                f"STATUS:{'CONFIRMED' if appt['status'] == 'Confirmada' else 'TENTATIVE'}",
                "BEGIN:VALARM",
                "TRIGGER:-PT1H",
                "ACTION:DISPLAY",
                f"DESCRIPTION:Recordatorio de Turno: {appt['patient_name']}",
                "END:VALARM",
                "END:VEVENT"
            ])
        except Exception as e:
            print(f"Error procesando cita en ICS: {e}")

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)
