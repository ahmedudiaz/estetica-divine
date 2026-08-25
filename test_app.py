"""
test_app.py - Script de Pruebas Automatizadas para GlowAura Estética
"""
import os
import sys
import unittest
from datetime import date, timedelta

# Importar módulos de la aplicación
from database import (
    init_db, get_stats, get_appointments, create_appointment,
    get_patients, create_patient, get_services, get_settings,
    get_appointment_by_token, confirm_appointment_by_token
)
from scheduler import get_tomorrow_reminders, generate_reminder_message

class TestGlowAuraEstetica(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Inicializar base de datos
        init_db()

    def test_database_and_stats(self):
        stats = get_stats()
        print(f"\n[TEST] Estadísticas iniciales: {stats}")
        self.assertIn("today_total", stats)
        self.assertIn("tomorrow_unconfirmed", stats)
        self.assertGreaterEqual(stats["total_patients"], 1)

    def test_create_patient_and_appointment(self):
        # 1. Crear nuevo paciente
        new_patient = create_patient({
            "name": "Luciana Tester",
            "phone": "+34655443322",
            "email": "luciana.test@example.com",
            "skin_type": "Sensible",
            "allergies": "Ninguna",
            "notes": "Paciente de prueba automatizada"
        })
        self.assertIsNotNone(new_patient)
        self.assertEqual(new_patient["name"], "Luciana Tester")
        print(f"[TEST] Paciente creado: {new_patient['name']} (ID: {new_patient['id']})")

        # 2. Obtener servicios
        services = get_services()
        self.assertGreater(len(services), 0)
        selected_service = services[0]

        # 3. Agendar cita para mañana
        tomorrow = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        new_appt = create_appointment({
            "patient_id": new_patient["id"],
            "service_id": selected_service["id"],
            "appointment_date": tomorrow,
            "appointment_time": "14:30",
            "specialist": "Cosmetóloga Constanza Díaz",
            "status": "Pendiente",
            "notes": "Prueba de confirmación"
        })
        self.assertIsNotNone(new_appt)
        self.assertIsNotNone(new_appt["confirmation_token"])
        print(f"[TEST] Cita para mañana agendada: ID {new_appt['id']} - Token: {new_appt['confirmation_token']}")

        # 4. Verificar que aparece en los recordatorios de 24h
        reminders = get_tomorrow_reminders()
        target_reminder = next((r for r in reminders if r["id"] == new_appt["id"]), None)
        self.assertIsNotNone(target_reminder)
        self.assertIn("https://wa.me/34655443322", target_reminder["whatsapp_link"])
        self.assertIn(new_appt["confirmation_token"], target_reminder["formatted_message"])
        print(f"[TEST] Recordatorio de WhatsApp generado exitosamente:\n{target_reminder['formatted_message']}")

        # 5. Simular confirmación por parte de la paciente desde el portal web
        confirmed_appt = confirm_appointment_by_token(new_appt["confirmation_token"], action="confirm")
        self.assertIsNotNone(confirmed_appt)
        self.assertEqual(confirmed_appt["status"], "Confirmada")
        self.assertIsNotNone(confirmed_appt["confirmed_at"])
        print(f"[TEST] ¡Confirmación exitosa! Estado de la cita actualizado a: {confirmed_appt['status']}")

    def test_calendar_sync_and_mobile(self):
        from calendar_sync import get_local_ip, generate_ics_feed
        ip = get_local_ip()
        self.assertTrue(len(ip) > 0)
        print(f"\n[TEST] IP local detectada para conectar celular: {ip}")

        appts = get_appointments()
        ics = generate_ics_feed(appts, "Estética Divine")
        self.assertIn("BEGIN:VCALENDAR", ics)
        self.assertIn("END:VCALENDAR", ics)
        self.assertIn("BEGIN:VEVENT", ics)
        print(f"[TEST] Feed iCalendar (.ics) generado exitosamente con {ics.count('BEGIN:VEVENT')} eventos.")

    def test_patient_crud(self):
        from database import update_patient, delete_patient, get_patient_by_id
        # 1. Crear
        p = create_patient({
            "name": "Paciente Para Eliminar",
            "phone": "+34699887766",
            "email": "eliminar@example.com",
            "skin_type": "Grasa",
            "allergies": "Ninguna",
            "notes": "Prueba temporal"
        })
        p_id = p["id"]
        self.assertIsNotNone(p_id)

        # 2. Actualizar
        updated = update_patient(p_id, {"name": "Paciente Editado", "skin_type": "Mixta"})
        self.assertEqual(updated["name"], "Paciente Editado")
        self.assertEqual(updated["skin_type"], "Mixta")
        print(f"[TEST] Paciente actualizado con éxito: {updated['name']}")

        # 3. Eliminar
        deleted = delete_patient(p_id)
        self.assertTrue(deleted)
        self.assertIsNone(get_patient_by_id(p_id))
        print(f"[TEST] Paciente ID {p_id} eliminado con éxito.")

    def test_service_crud_and_weekly_calendar(self):
        from database import create_service, get_service_by_id, update_service, delete_service
        # 1. Crear Tratamiento
        svc_id = create_service({
            "name": "Peeling Ultrasonico Test",
            "category": "Facial",
            "duration_minutes": 45,
            "price": 65.0,
            "instructions": "Sin maquillaje",
            "color": "#10b981"
        })
        self.assertIsNotNone(svc_id)
        svc = get_service_by_id(svc_id)
        self.assertEqual(svc["name"], "Peeling Ultrasonico Test")

        # 2. Actualizar Tratamiento
        updated_svc = update_service(svc_id, {"price": 75.0, "duration_minutes": 50})
        self.assertEqual(updated_svc["price"], 75.0)
        self.assertEqual(updated_svc["duration_minutes"], 50)
        print(f"[TEST] Tratamiento actualizado con éxito: {updated_svc['name']} ($ {updated_svc['price']})")

        # 3. Consultar Citas en Rango Semanal para el Calendario
        today_str = date.today().strftime("%Y-%m-%d")
        next_week_str = (date.today() + timedelta(days=7)).strftime("%Y-%m-%d")
        week_appts = get_appointments(date_from=today_str, date_to=next_week_str)
        self.assertIsInstance(week_appts, list)
        print(f"[TEST] Consulta de calendario semanal para el rango {today_str} a {next_week_str}: {len(week_appts)} citas encontradas.")

        # 4. Eliminar Tratamiento
        deleted = delete_service(svc_id)
        self.assertTrue(deleted)
        print(f"[TEST] Tratamiento ID {svc_id} eliminado/desactivado con éxito.")

    def test_sync_export_import(self):
        from database import export_full_state, import_full_state, create_patient, get_patients
        # 1. Exportar
        state = export_full_state()
        self.assertIn("patients", state)
        self.assertIn("services", state)
        self.assertIn("appointments", state)
        self.assertIn("settings", state)
        print(f"[TEST] Exportación de estado completa: {len(state['patients'])} pacientes, {len(state['services'])} servicios.")

        # 2. Modificar y Re-importar
        state["patients"].append({
            "id": 999,
            "name": "Paciente Sync Persistente",
            "phone": "+34699999999",
            "skin_type": "Grasa",
            "allergies": "Ninguna",
            "notes": "Test de sincronización"
        })
        import_full_state(state)
        patients = get_patients(search="Paciente Sync Persistente")
        self.assertTrue(len(patients) > 0)
        self.assertEqual(patients[0]["name"], "Paciente Sync Persistente")
        print("[TEST] Importación y auto-restauración de estado completada con éxito.")

if __name__ == "__main__":
    unittest.main()
