# 🌸 Estética Divine - Sistema de Agenda y Confirmación de Citas

Una solución completa y moderna diseñada específicamente para el centro **Estética Divine** (Directora: Cosmetóloga Constanza Díaz), con un módulo inteligente de **recordatorios y confirmación de citas 24 horas antes por WhatsApp** y **sincronización móvil en tiempo real**.

---

## 🚀 Inicio Rápido

Para iniciar la aplicación en tu computadora:

1. Abre tu terminal y ve al directorio del proyecto:
   ```bash
   cd /Users/ahmediaz/.gemini/antigravity/scratch/estetica-agenda
   ```

2. Inicia el servidor ejecutando:
   ```bash
   python3 server.py
   # o bien: ./start.sh
   ```

3. Abre en tu navegador favorito:
   👉 **[http://localhost:8000](http://localhost:8000)**

---

## ✨ Características Principales

### 1. 📅 Agenda & Calendario de Turnos
- Visualización interactiva por día con timeline de horarios.
- Navegación rápida entre fechas (Hoy, Anterior, Siguiente y selector de calendario).
- Filtro por estados: `Pendiente`, `Recordatorio Enviado`, `Confirmada`, `Completada`, `Cancelada`.
- Creación y edición ágil de citas vinculando paciente, servicio/tratamiento, hora y profesional a cargo.

### 2. 📲 Módulo de Confirmación 24 Horas Antes (WhatsApp)
- **Detección Automática**: Identifica todas las citas agendadas para el día siguiente.
- **Mensaje Personalizado Inteligente**: Redacta un mensaje con el nombre de la paciente, tratamiento, fecha, hora, lugar, indicaciones previas y un enlace único de confirmación.
- **Acción Directa por WhatsApp**: Botón *"Abrir WhatsApp Web / App"* con el enlace universal `wa.me` y texto pre-rellenado listo para enviar en 1 toque.
- **Botón de Copiado Rápido**: Para pegar en WhatsApp Business o SMS.
- **Portal Móvil para la Paciente**: La paciente abre su enlace exclusivo (`/confirmar/{token}`) y confirma o solicita reprogramación con un solo clic. Al confirmar, el estado en la agenda cambia inmediatamente a **Confirmada** con indicador verde.

### 3. 👤 Fichas Clínicas y Directorio de Pacientes
- Base de datos de pacientes con número de WhatsApp, email y fecha de nacimiento.
- Registro estético: Tipo de piel, alergias y notas de contraindicaciones.
- Historial completo de tratamientos y sesiones realizadas por cada paciente.
- Botón de agendado directo desde la ficha.

### 4. 💆‍♀️ Catálogo de Tratamientos y Servicios
- Configuración de servicios con precio, duración en minutos y color identificador en la agenda.
- Indicaciones previas personalizadas (ej. *"Asistir sin maquillaje", "Evitar exposición solar 48h antes", "Beber 1L de agua"*).

### 5. ⚙️ Personalización de la Clínica y Plantilla WhatsApp
- Configura el nombre del centro, dirección física, teléfono y correo.
- Editor de plantilla de WhatsApp con etiquetas dinámicas (`{nombre_paciente}`, `{tratamiento}`, `{fecha}`, `{hora}`, `{centro}`, `{enlace_confirmacion}`, etc.).

---

## 📂 Estructura del Proyecto

```
estetica-agenda/
├── server.py              # Servidor HTTP y API REST en Python (Sin dependencias externas)
├── database.py            # Gestión SQLite3 (tablas, modelos y datos iniciales)
├── scheduler.py           # Generador de recordatorios y enlaces de WhatsApp
├── test_app.py            # Suite de pruebas automatizadas
├── start.sh               # Script ejecutable de inicio
├── agenda_estetica.db     # Base de datos SQLite (se genera automáticamente)
└── static/
    ├── index.html         # Panel de Control principal de la clínica
    ├── confirm.html       # Portal web responsive para que la paciente confirme
    ├── css/
    │   └── style.css      # Estilos visuales con estética luxury medical spa
    └── js/
        ├── app.js         # Lógica del frontend, agenda y WhatsApp
        └── confirm.js     # Lógica del portal de confirmación de la paciente
```

---

## 🧪 Ejecución de Pruebas Automatizadas

Puedes verificar que todos los módulos y la base de datos funcionan correctamente ejecutando:

```bash
python3 test_app.py
```
