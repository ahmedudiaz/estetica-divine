"""
server.py - Servidor HTTP, API REST y Sincronización Móvil para Estética Divine
Soporte de Autenticación Multi-Usuario y Cuentas de Especialistas
"""
import http.server
import socketserver
import json
import os
import sys
import mimetypes
import urllib.parse
from datetime import datetime, date, timedelta
from database import (
    init_db, get_stats, get_appointments, get_appointment_by_id,
    create_appointment, update_appointment, delete_appointment,
    get_patients, get_patient_by_id, create_patient, update_patient, delete_patient,
    get_services, get_service_by_id, create_service, update_service, delete_service,
    get_settings, update_setting, mark_reminder_sent,
    get_appointment_by_token, confirm_appointment_by_token,
    export_full_state, import_full_state,
    create_user, authenticate_user, create_session, get_user_by_session_token, delete_session
)
from scheduler import get_tomorrow_reminders, generate_reminder_message, generate_whatsapp_link
from calendar_sync import get_local_ip, generate_ics_feed
from tunnel import get_saved_public_url, start_ssh_tunnel, set_public_url

PORT = int(os.environ.get("PORT", 8000))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

class EsteticaRequestHandler(http.server.BaseHTTPRequestHandler):
    
    def log_message(self, format, *args):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {args[0]} {args[1]} -> {args[2]}")

    def get_base_url(self):
        pub_url = get_saved_public_url()
        if pub_url and (pub_url.startswith("http://") or pub_url.startswith("https://")):
            return pub_url.rstrip("/")
        host = self.headers.get("Host", f"localhost:{PORT}")
        return f"http://{host}"

    def send_json(self, data, status_code=200):
        response_bytes = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()
        self.wfile.write(response_bytes)

    def serve_file(self, filepath, content_type=None):
        if not os.path.exists(filepath):
            self.send_error(404, "Archivo no encontrado")
            return
        if not content_type:
            content_type, _ = mimetypes.guess_type(filepath)
            if not content_type:
                content_type = "application/octet-stream"
        
        with open(filepath, "rb") as f:
            content = f.read()

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def get_session_token(self):
        # 1. Header Authorization: Bearer <token>
        auth_header = self.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:].strip()
        # 2. Cookie session_token=<token>
        cookie_header = self.headers.get("Cookie", "")
        if "session_token=" in cookie_header:
            for part in cookie_header.split(";"):
                part = part.strip()
                if part.startswith("session_token="):
                    return part.split("=")[1].strip()
        # 3. Query Param ?token=<token>
        parsed_url = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed_url.query)
        if "token" in params:
            return params["token"][0]
        return None

    def get_authenticated_user(self):
        token = self.get_session_token()
        if not token:
            return None
        return get_user_by_session_token(token)

    def parse_body_json(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length > 0:
                raw_body = self.rfile.read(content_length).decode("utf-8")
                return json.loads(raw_body)
            return {}
        except Exception as e:
            print(f"Error parsing JSON: {e}")
            return {}

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query_params = urllib.parse.parse_qs(parsed_url.query)

        # Rutas Web Frontend & PWA
        if path == "/" or path == "/index.html":
            return self.serve_file(os.path.join(STATIC_DIR, "index.html"), "text/html; charset=utf-8")
        
        if path.startswith("/confirmar/"):
            return self.serve_file(os.path.join(STATIC_DIR, "confirm.html"), "text/html; charset=utf-8")

        if path == "/manifest.json":
            return self.serve_file(os.path.join(STATIC_DIR, "manifest.json"), "application/manifest+json")

        if path == "/sw.js":
            return self.serve_file(os.path.join(STATIC_DIR, "sw.js"), "application/javascript")

        if path.startswith("/static/"):
            rel_path = path[len("/static/"):]
            file_path = os.path.join(STATIC_DIR, rel_path)
            return self.serve_file(file_path)

        # ----------------------------------------------------
        # AUTENTICACIÓN: OBTENER USUARIO ACTUAL (/api/auth/me)
        # ----------------------------------------------------
        if path == "/api/auth/me":
            user = self.get_authenticated_user()
            if user:
                return self.send_json({"success": True, "data": user})
            return self.send_json({"success": False, "error": "No autenticado"}, 401)

        # Sincronización con Calendarios Móviles (Público con token de cita o feed general)
        if path == "/api/calendar.ics":
            user = self.get_authenticated_user()
            user_id = user["id"] if user else 1
            appts = get_appointments(user_id=user_id)
            settings = get_settings(user_id=user_id)
            clinic_name = settings.get("clinic_name", "Estética Divine")
            ics_content = generate_ics_feed(appts, clinic_name)
            ics_bytes = ics_content.encode("utf-8")
            
            self.send_response(200)
            self.send_header("Content-Type", "text/calendar; charset=utf-8")
            self.send_header("Content-Disposition", 'attachment; filename="estetica_divine_agenda.ics"')
            self.send_header("Content-Length", str(len(ics_bytes)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(ics_bytes)
            return

        # Información de Red Local y Acceso por Internet
        if path == "/api/network-info":
            local_ip = get_local_ip()
            local_url = f"http://{local_ip}:{PORT}"
            public_url = get_saved_public_url()
            effective_url = public_url if public_url else local_url
            
            ical_url = f"{effective_url}/api/calendar.ics"
            webcal_url = ical_url.replace("http://", "webcal://").replace("https://", "webcal://")
            
            return self.send_json({
                "success": True,
                "data": {
                    "local_ip": local_ip,
                    "port": PORT,
                    "local_url": local_url,
                    "public_url": public_url,
                    "effective_url": effective_url,
                    "has_public_url": bool(public_url),
                    "ical_url": ical_url,
                    "webcal_url": webcal_url
                }
            })

        # Portal de Confirmación de Pacientes (Público mediante Token)
        if path.startswith("/api/confirm-info/"):
            token = path.split("/")[-1]
            appt = get_appointment_by_token(token)
            if appt:
                user_id = appt.get("user_id", 1)
                settings = get_settings(user_id=user_id)
                return self.send_json({
                    "success": True,
                    "data": {
                        "appointment": appt,
                        "clinic": {
                            "name": settings.get("clinic_name", "Estética Divine"),
                            "phone": settings.get("clinic_phone", ""),
                            "address": settings.get("clinic_address", ""),
                            "email": settings.get("clinic_email", "")
                        }
                    }
                })
            return self.send_json({"success": False, "error": "Token inválido o cita no encontrada"}, 404)

        # ----------------------------------------------------
        # RUTAS PRIVADAS (REQUIEREN SESIÓN ACTIVA)
        # ----------------------------------------------------
        user = self.get_authenticated_user()
        if not user:
            return self.send_json({"success": False, "error": "Inicia sesión para continuar"}, 401)
        
        user_id = user["id"]

        if path == "/api/stats":
            stats = get_stats(user_id=user_id)
            return self.send_json({"success": True, "data": stats})

        if path == "/api/appointments":
            date_from = query_params.get("date_from", [None])[0]
            date_to = query_params.get("date_to", [None])[0]
            status = query_params.get("status", [None])[0]
            patient_id = query_params.get("patient_id", [None])[0]
            appts = get_appointments(user_id=user_id, date_from=date_from, date_to=date_to, status=status, patient_id=patient_id)
            return self.send_json({"success": True, "data": appts})

        if path.startswith("/api/appointments/"):
            appt_id = int(path.split("/")[-1])
            appt = get_appointment_by_id(appt_id, user_id=user_id)
            if appt:
                return self.send_json({"success": True, "data": appt})
            return self.send_json({"success": False, "error": "Cita no encontrada"}, 404)

        if path == "/api/patients":
            search = query_params.get("search", [""])[0]
            patients = get_patients(user_id=user_id, search=search)
            return self.send_json({"success": True, "data": patients})

        if path.startswith("/api/patients/"):
            patient_id = int(path.split("/")[-1])
            patient = get_patient_by_id(patient_id, user_id=user_id)
            if patient:
                return self.send_json({"success": True, "data": patient})
            return self.send_json({"success": False, "error": "Paciente no encontrado"}, 404)

        if path == "/api/services":
            services = get_services(user_id=user_id)
            return self.send_json({"success": True, "data": services})

        if path.startswith("/api/services/"):
            svc_id = int(path.split("/")[-1])
            svc = get_service_by_id(svc_id, user_id=user_id)
            if svc:
                return self.send_json({"success": True, "data": svc})
            return self.send_json({"success": False, "error": "Tratamiento no encontrado"}, 404)

        if path == "/api/reminders/tomorrow":
            base_url = self.get_base_url()
            reminders = get_tomorrow_reminders(base_url, user_id=user_id)
            return self.send_json({"success": True, "data": reminders})

        if path == "/api/settings":
            settings = get_settings(user_id=user_id)
            return self.send_json({"success": True, "data": settings})

        if path == "/api/sync/state":
            state = export_full_state(user_id=user_id)
            return self.send_json({"success": True, "data": state})

        # Si no coincide
        self.send_error(404, "Ruta no encontrada")

    def do_POST(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        body = self.parse_body_json()

        # ----------------------------------------------------
        # AUTENTICACIÓN PÚBLICA: REGISTRO Y LOGIN
        # ----------------------------------------------------
        if path == "/api/auth/register":
            name = body.get("name", "").strip()
            email = body.get("email", "").strip()
            password = body.get("password", "")
            specialty = body.get("specialty", "Cosmetóloga").strip()
            phone = body.get("phone", "").strip()

            if not name or not email or not password:
                return self.send_json({"success": False, "error": "Nombre, correo y contraseña son obligatorios"}, 400)

            if len(password) < 4:
                return self.send_json({"success": False, "error": "La contraseña debe tener al menos 4 caracteres"}, 400)

            user, err = create_user(name, email, password, specialty, phone)
            if err:
                return self.send_json({"success": False, "error": err}, 400)

            token = create_session(user["id"])
            return self.send_json({"success": True, "data": {"token": token, "user": user}}, 201)

        if path == "/api/auth/login":
            email = body.get("email", "").strip()
            password = body.get("password", "")

            if not email or not password:
                return self.send_json({"success": False, "error": "Ingresa tu correo y contraseña"}, 400)

            user, err = authenticate_user(email, password)
            if err:
                return self.send_json({"success": False, "error": err}, 401)

            token = create_session(user["id"])
            return self.send_json({"success": True, "data": {"token": token, "user": user}})

        if path == "/api/auth/logout":
            token = self.get_session_token()
            if token:
                delete_session(token)
            return self.send_json({"success": True, "message": "Sesión cerrada"})

        # Confirmación de Pacientes (Público con Token)
        if path.startswith("/api/confirm/"):
            token = path.split("/")[-1]
            action = body.get("action", "confirm")
            reason = body.get("reason", "")
            
            updated_appt = confirm_appointment_by_token(token, action=action, reason=reason)
            if updated_appt:
                return self.send_json({
                    "success": True,
                    "data": {
                        "appointment": updated_appt,
                        "action": action
                    }
                })
            return self.send_json({"success": False, "error": "Token inválido o cita no encontrada"}, 404)

        # Control del Túnel Público
        if path == "/api/tunnel/start":
            res = start_ssh_tunnel(PORT)
            return self.send_json(res)

        if path == "/api/tunnel/set-url":
            url = body.get("url", "")
            set_public_url(url)
            return self.send_json({"success": True, "url": url})

        # ----------------------------------------------------
        # RUTAS PRIVADAS (REQUIEREN SESIÓN ACTIVA)
        # ----------------------------------------------------
        user = self.get_authenticated_user()
        if not user:
            return self.send_json({"success": False, "error": "Inicia sesión para continuar"}, 401)
        
        user_id = user["id"]

        if path == "/api/sync/state":
            if not body or not isinstance(body, dict):
                return self.send_json({"success": False, "error": "Datos de sincronización inválidos"}, 400)
            import_full_state(body, user_id=user_id)
            return self.send_json({"success": True, "message": "Datos sincronizados correctamente"})

        if path == "/api/appointments":
            if not body.get("patient_id") or not body.get("service_id") or not body.get("appointment_date") or not body.get("appointment_time"):
                return self.send_json({"success": False, "error": "Faltan campos obligatorios"}, 400)
            appt = create_appointment(body, user_id=user_id)
            return self.send_json({"success": True, "data": appt}, 201)

        if path == "/api/patients":
            if not body.get("name") or not body.get("phone"):
                return self.send_json({"success": False, "error": "Nombre y teléfono son obligatorios"}, 400)
            patient = create_patient(body, user_id=user_id)
            return self.send_json({"success": True, "data": patient}, 201)

        if path == "/api/services":
            if not body.get("name") or not body.get("price"):
                return self.send_json({"success": False, "error": "Nombre y precio son obligatorios"}, 400)
            svc_id = create_service(body, user_id=user_id)
            return self.send_json({"success": True, "data": {"id": svc_id}}, 201)

        if path.startswith("/api/reminders/send/"):
            appt_id = int(path.split("/")[-1])
            base_url = self.get_base_url()
            appt = get_appointment_by_id(appt_id, user_id=user_id)
            if not appt:
                return self.send_json({"success": False, "error": "Cita no encontrada"}, 404)
            
            msg = generate_reminder_message(appt, base_url, user_id=user_id)
            wa_link = generate_whatsapp_link(appt["patient_phone"], msg)
            updated = mark_reminder_sent(appt_id, msg)
            return self.send_json({
                "success": True,
                "data": {
                    "appointment": updated,
                    "message": msg,
                    "whatsapp_link": wa_link
                }
            })

        if path == "/api/settings":
            for k, v in body.items():
                update_setting(k, str(v), user_id=user_id)
            return self.send_json({"success": True, "data": get_settings(user_id=user_id)})

        self.send_error(404, "Ruta no encontrada")

    def do_PUT(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        body = self.parse_body_json()

        user = self.get_authenticated_user()
        if not user:
            return self.send_json({"success": False, "error": "Inicia sesión para continuar"}, 401)
        
        user_id = user["id"]

        if path.startswith("/api/appointments/"):
            appt_id = int(path.split("/")[-1])
            appt = update_appointment(appt_id, body, user_id=user_id)
            if appt:
                return self.send_json({"success": True, "data": appt})
            return self.send_json({"success": False, "error": "Cita no encontrada"}, 404)

        if path.startswith("/api/patients/"):
            patient_id = int(path.split("/")[-1])
            patient = update_patient(patient_id, body, user_id=user_id)
            if patient:
                return self.send_json({"success": True, "data": patient})
            return self.send_json({"success": False, "error": "Paciente no encontrado"}, 404)

        if path.startswith("/api/services/"):
            svc_id = int(path.split("/")[-1])
            svc = update_service(svc_id, body, user_id=user_id)
            if svc:
                return self.send_json({"success": True, "data": svc})
            return self.send_json({"success": False, "error": "Tratamiento no encontrado"}, 404)

        self.send_error(404, "Ruta no encontrada")

    def do_DELETE(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        user = self.get_authenticated_user()
        if not user:
            return self.send_json({"success": False, "error": "Inicia sesión para continuar"}, 401)
        
        user_id = user["id"]

        if path.startswith("/api/appointments/"):
            appt_id = int(path.split("/")[-1])
            delete_appointment(appt_id, user_id=user_id)
            return self.send_json({"success": True, "message": "Cita eliminada correctamente"})

        if path.startswith("/api/patients/"):
            patient_id = int(path.split("/")[-1])
            delete_patient(patient_id, user_id=user_id)
            return self.send_json({"success": True, "message": "Paciente eliminado correctamente"})

        if path.startswith("/api/services/"):
            svc_id = int(path.split("/")[-1])
            delete_service(svc_id, user_id=user_id)
            return self.send_json({"success": True, "message": "Tratamiento eliminado correctamente"})

        self.send_error(404, "Ruta no encontrada")

def run_server():
    init_db()
    server_address = ("", PORT)
    httpd = socketserver.TCPServer(server_address, EsteticaRequestHandler)
    httpd.allow_reuse_address = True
    print(f"✨ Servidor Estética Divine corriendo en el puerto {PORT}...")
    print(f"👉 Acceso local: http://localhost:{PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nDeteniendo servidor...")
        httpd.server_close()

if __name__ == "__main__":
    run_server()
