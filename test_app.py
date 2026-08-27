"""
test_app.py - Script de Pruebas Automatizadas para Estética Divine
Incluye verificación de Autenticación, Sesiones y Aislamiento Multi-Usuario
"""
import os
import sys
import unittest
from datetime import date, timedelta

import database
# Usar base de datos aislada temporal para NO modificar la base de datos real
TEST_DB_PATH = "/tmp/test_estetica_isolated.db"
if os.path.exists(TEST_DB_PATH):
    os.remove(TEST_DB_PATH)
database.DB_PATH = TEST_DB_PATH

# Importar módulos de la aplicación
from database import (
    init_db, get_stats, get_appointments, create_appointment,
    get_patients, create_patient, get_services, get_settings,
    get_appointment_by_token, confirm_appointment_by_token,
    create_user, authenticate_user, create_session, get_user_by_session_token, delete_session,
    reset_user_password, export_full_state, import_full_state
)
from scheduler import get_tomorrow_reminders, generate_reminder_message

class TestEsteticaDivine(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Inicializar base de datos de prueba
        init_db()

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(TEST_DB_PATH):
            os.remove(TEST_DB_PATH)

    def test_authentication_and_sessions(self):
        # 1. Autenticar usuario principal por defecto
        user, err = authenticate_user("constanza@esteticadivine.com", "divine123")
        self.assertIsNone(err)
        self.assertIsNotNone(user)
        self.assertEqual(user["email"], "constanza@esteticadivine.com")
        print(f"\n[TEST] Usuario principal autenticado: {user['name']} (ID: {user['id']})")

        # 2. Crear sesión
        token = create_session(user["id"])
        self.assertIsNotNone(token)
        session_user = get_user_by_session_token(token)
        self.assertIsNotNone(session_user)
        self.assertEqual(session_user["id"], user["id"])
        print(f"[TEST] Sesión creada y validada con token exitosamente.")

        # 3. Registrar un segundo usuario / especialista
        user2, err2 = create_user(
            name="Dra. Carolina Méndez",
            email="carolina@esteticadivine.com",
            password="segura1234",
            specialty="Kinesióloga Dermatofuncional",
            phone="+56911223344"
        )
        self.assertIsNone(err2)
        self.assertIsNotNone(user2)
        self.assertEqual(user2["email"], "carolina@esteticadivine.com")
        print(f"[TEST] Segundo usuario registrado: {user2['name']} (ID: {user2['id']})")

        # 4. Probar login con credenciales erróneas
        bad_user, bad_err = authenticate_user("carolina@esteticadivine.com", "clave_incorrecta")
        self.assertIsNone(bad_user)
        self.assertIsNotNone(bad_err)

        # 5. Probar recuperación de contraseña olvidada
        reset_u, reset_err = reset_user_password("carolina@esteticadivine.com", "+56911223344", "nueva_clave_2026")
        self.assertIsNone(reset_err)
        self.assertIsNotNone(reset_u)

        # Verificar que ahora entra con la nueva contraseña
        login_u, login_err = authenticate_user("carolina@esteticadivine.com", "nueva_clave_2026")
        self.assertIsNone(login_err)
        self.assertIsNotNone(login_u)
        print(f"[TEST] Recuperación y restablecimiento de contraseña verificado exitosamente.")

        # 6. Probar borrado de sesión (logout)
        delete_session(token)
        self.assertIsNone(get_user_by_session_token(token))
        print(f"[TEST] Logout de sesión verificado exitosamente.")

    def test_multi_user_data_isolation(self):
        # Usuario 1: Constanza (ID 1)
        # Usuario 2: Carolina (ID 2 con nueva_clave_2026)
        user2, _ = authenticate_user("carolina@esteticadivine.com", "nueva_clave_2026")
        self.assertIsNotNone(user2)
        user2_id = user2["id"]

        # Crear paciente exclusivo para Usuario 1
        p1 = create_patient({
            "name": "Paciente de Constanza",
            "phone": "+56911111111"
        }, user_id=1)

        # Crear paciente exclusivo para Usuario 2
        p2 = create_patient({
            "name": "Paciente de Carolina",
            "phone": "+56922222222"
        }, user_id=user2_id)

        # Comprobar que Constanza solo ve a su paciente
        patients_u1 = get_patients(user_id=1)
        names_u1 = [p["name"] for p in patients_u1]
        self.assertIn("Paciente de Constanza", names_u1)
        self.assertNotIn("Paciente de Carolina", names_u1)

        # Comprobar que Carolina solo ve a su paciente
        patients_u2 = get_patients(user_id=user2_id)
        names_u2 = [p["name"] for p in patients_u2]
        self.assertIn("Paciente de Carolina", names_u2)
        self.assertNotIn("Paciente de Constanza", names_u2)
        print(f"[TEST] ¡Aislamiento de datos multi-usuario verificado al 100%!")

    def test_create_appointment_and_whatsapp_reminder(self):
        # 1. Crear nuevo paciente para user 1
        new_patient = create_patient({
            "name": "Luciana Tester",
            "phone": "+34655443322",
            "email": "luciana.test@example.com",
            "skin_type": "Sensible",
            "allergies": "Ninguna",
            "notes": "Paciente de prueba automatizada"
        }, user_id=1)

        services = get_services(user_id=1)
        self.assertGreater(len(services), 0)
        selected_service = services[0]

        # 2. Agendar cita para mañana
        tomorrow = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        new_appt = create_appointment({
            "patient_id": new_patient["id"],
            "service_id": selected_service["id"],
            "appointment_date": tomorrow,
            "appointment_time": "14:30",
            "specialist": "Cosmetóloga Constanza Díaz",
            "status": "Pendiente",
            "notes": "Prueba de confirmación"
        }, user_id=1)
        self.assertIsNotNone(new_appt)
        self.assertIsNotNone(new_appt["confirmation_token"])

        # 3. Verificar que aparece en los recordatorios de 24h
        reminders = get_tomorrow_reminders(user_id=1)
        target_reminder = next((r for r in reminders if r["id"] == new_appt["id"]), None)
        self.assertIsNotNone(target_reminder)
        self.assertIn("https://wa.me/34655443322", target_reminder["whatsapp_link"])

        # 4. Confirmar cita desde portal
        confirmed = confirm_appointment_by_token(new_appt["confirmation_token"], action="confirm")
        self.assertEqual(confirmed["status"], "Confirmada")
        print(f"[TEST] Cita agendada, recordatorio WhatsApp y confirmación verificados.")

    def test_calendar_sync_and_mobile(self):
        from calendar_sync import get_local_ip, generate_ics_feed
        ip = get_local_ip()
        self.assertTrue(len(ip) > 0)

        appts = get_appointments(user_id=1)
        ics = generate_ics_feed(appts, "Estética Divine")
        self.assertIn("BEGIN:VCALENDAR", ics)
        print(f"[TEST] Feed iCalendar (.ics) generado exitosamente con {len(appts)} eventos.")

    def test_sync_export_import(self):
        state = export_full_state(user_id=1)
        self.assertIn("patients", state)
        self.assertIn("services", state)

        res = import_full_state(state, user_id=1)
        self.assertTrue(res)
        print(f"[TEST] Exportación e Importación de estado por usuario completada con éxito.")

if __name__ == "__main__":
    unittest.main()
