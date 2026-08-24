// Estética Divine - App Logic SPA & Sincronización Móvil
let state = {
  currentDate: new Date(),
  activeTab: "agenda",
  appointments: [],
  patients: [],
  services: [],
  settings: {},
  stats: {},
  network: {}
};

// Inicialización
document.addEventListener("DOMContentLoaded", () => {
  initServiceWorker();
  initDateTime();
  initNavigation();
  initEventListeners();
  loadAllData();
});

function initServiceWorker() {
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/sw.js")
      .then(() => console.log("✨ Service Worker PWA registrado exitosamente"))
      .catch(err => console.warn("Service worker no disponible:", err));
  }
}

function initDateTime() {
  const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
  const dateStr = new Date().toLocaleDateString('es-ES', options);
  document.getElementById("current-datetime-display").textContent = dateStr.charAt(0).toUpperCase() + dateStr.slice(1);
}

function formatDateISO(date) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

function formatDisplayDate(date) {
  const options = { weekday: 'short', month: 'short', day: 'numeric' };
  return date.toLocaleDateString('es-ES', options);
}

// Navegación entre pestañas (Escritorio + Móvil)
function initNavigation() {
  // Sidebar items
  const navItems = document.querySelectorAll(".nav-item");
  navItems.forEach(item => {
    item.addEventListener("click", () => {
      const tab = item.getAttribute("data-tab");
      switchTab(tab);
    });
  });

  // Mobile Bottom Bar items
  const mobileNavBtns = document.querySelectorAll(".mobile-nav-btn");
  mobileNavBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      const tab = btn.getAttribute("data-tab");
      switchTab(tab);
    });
  });

  // Mobile Center FAB Button (+ Cita)
  const mobileFab = document.getElementById("mobile-btn-quick-schedule");
  if (mobileFab) {
    mobileFab.addEventListener("click", () => {
      openAppointmentModal();
    });
  }

  // Header quick sync button
  const btnHeaderSync = document.getElementById("btn-header-sync");
  if (btnHeaderSync) {
    btnHeaderSync.addEventListener("click", () => {
      switchTab("sync");
    });
  }
}

function switchTab(tabName) {
  state.activeTab = tabName;

  // Actualizar Sidebar
  document.querySelectorAll(".nav-item").forEach(n => {
    if (n.getAttribute("data-tab") === tabName) {
      n.classList.add("active");
    } else {
      n.classList.remove("active");
    }
  });

  // Actualizar Mobile Bottom Bar
  document.querySelectorAll(".mobile-nav-btn").forEach(btn => {
    if (btn.getAttribute("data-tab") === tabName) {
      btn.classList.add("active");
    } else {
      btn.classList.remove("active");
    }
  });

  // Mostrar panel correspondiente
  document.querySelectorAll(".tab-pane").forEach(pane => pane.style.display = "none");
  const activePane = document.getElementById(`tab-${tabName}`);
  if (activePane) activePane.style.display = "block";

  const titles = {
    agenda: "Agenda & Turnos",
    reminders: "Confirmaciones 24h (WhatsApp)",
    sync: "Sincronizar con el Celular",
    patients: "Directorio de Pacientes & Fichas",
    services: "Catálogo de Tratamientos",
    settings: "Configuración & Plantilla WhatsApp"
  };
  document.getElementById("view-title").textContent = titles[tabName] || "Estética Divine";

  if (tabName === "agenda") loadAppointmentsForDate();
  if (tabName === "reminders") loadTomorrowReminders();
  if (tabName === "sync") loadNetworkInfo();
  if (tabName === "patients") loadPatients();
  if (tabName === "services") loadServices();
  if (tabName === "settings") loadSettings();
}

function initEventListeners() {
  // Navegación de Fecha en Agenda
  document.getElementById("btn-prev-day").addEventListener("click", () => {
    state.currentDate.setDate(state.currentDate.getDate() - 1);
    loadAppointmentsForDate();
  });

  document.getElementById("btn-next-day").addEventListener("click", () => {
    state.currentDate.setDate(state.currentDate.getDate() + 1);
    loadAppointmentsForDate();
  });

  document.getElementById("btn-today").addEventListener("click", () => {
    state.currentDate = new Date();
    loadAppointmentsForDate();
  });

  document.getElementById("agenda-date-picker").addEventListener("change", (e) => {
    if (e.target.value) {
      const parts = e.target.value.split("-");
      state.currentDate = new Date(parts[0], parts[1] - 1, parts[2]);
      loadAppointmentsForDate();
    }
  });

  document.getElementById("filter-status").addEventListener("change", () => {
    renderAgendaAppointments();
  });

  // Botón Agendar Cita Rápida
  document.getElementById("btn-quick-new-appointment").addEventListener("click", () => {
    openAppointmentModal();
  });

  // Botones de Modales
  document.getElementById("btn-modal-new-patient").addEventListener("click", () => {
    document.getElementById("form-patient").reset();
    document.getElementById("patient-id").value = "";
    openModal("modal-patient");
  });

  document.getElementById("btn-add-patient-quick").addEventListener("click", () => {
    document.getElementById("form-patient").reset();
    document.getElementById("patient-id").value = "";
    openModal("modal-patient");
  });

  document.getElementById("btn-modal-new-service").addEventListener("click", () => {
    document.getElementById("form-service").reset();
    openModal("modal-service");
  });

  // Buscador de Pacientes
  document.getElementById("input-search-patients").addEventListener("input", (e) => {
    loadPatients(e.target.value);
  });

  // Enviar todos los recordatorios
  document.getElementById("btn-send-all-reminders").addEventListener("click", async () => {
    await sendAllPendingReminders();
  });

  // Activar Túnel Online
  const btnActivateTunnel = document.getElementById("btn-activate-tunnel");
  if (btnActivateTunnel) {
    btnActivateTunnel.addEventListener("click", async () => {
      btnActivateTunnel.disabled = true;
      btnActivateTunnel.innerHTML = `<span>⏳ Conectando...</span>`;
      showToast("🌐 Iniciando enlace público seguro... Por favor espera unos segundos");
      
      try {
        await fetch("/api/tunnel/start", { method: "POST" });
        // Polling para detectar la URL pública
        let attempts = 0;
        const interval = setInterval(async () => {
          attempts++;
          const res = await fetch("/api/network-info");
          const json = await res.json();
          if (json.success && json.data && json.data.public_url) {
            clearInterval(interval);
            btnActivateTunnel.disabled = false;
            btnActivateTunnel.innerHTML = `<span>✅ Enlace Online Activo</span>`;
            showToast("🎉 ¡Enlace público global activo! Puedes abrirlo con 4G/5G");
            loadNetworkInfo();
          }
          if (attempts > 15) {
            clearInterval(interval);
            btnActivateTunnel.disabled = false;
            btnActivateTunnel.innerHTML = `<span>🌐 Activar Acceso por Internet (4G/5G)</span>`;
          }
        }, 1500);
      } catch (e) {
        console.error(e);
        btnActivateTunnel.disabled = false;
        btnActivateTunnel.innerHTML = `<span>🌐 Activar Acceso por Internet (4G/5G)</span>`;
      }
    });
  }

  // Guardar Custom Public URL
  const btnSaveCustomUrl = document.getElementById("btn-save-custom-url");
  if (btnSaveCustomUrl) {
    btnSaveCustomUrl.addEventListener("click", async () => {
      const url = document.getElementById("input-custom-public-url").value.trim();
      try {
        const res = await fetch("/api/tunnel/set-url", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url })
        });
        const json = await res.json();
        if (json.success) {
          showToast("URL pública guardada exitosamente ✨");
          loadNetworkInfo();
        }
      } catch (e) {
        console.error(e);
      }
    });
  }

  // Form Handlers
  document.getElementById("form-appointment").addEventListener("submit", handleAppointmentSubmit);
  document.getElementById("form-patient").addEventListener("submit", handlePatientSubmit);
  document.getElementById("form-service").addEventListener("submit", handleServiceSubmit);
  document.getElementById("form-settings").addEventListener("submit", handleSettingsSubmit);
}

// Carga de Datos Global
async function loadAllData() {
  await Promise.all([
    loadStats(),
    loadPatients(),
    loadServices(),
    loadSettings(),
    loadAppointmentsForDate()
  ]);
}

async function loadStats() {
  try {
    const res = await fetch("/api/stats");
    const json = await res.json();
    if (json.success) {
      state.stats = json.data;
      document.getElementById("stat-today-total").textContent = state.stats.today_total;
      document.getElementById("stat-tomorrow-unconfirmed").textContent = state.stats.tomorrow_unconfirmed;
      document.getElementById("stat-tomorrow-confirmed").textContent = state.stats.tomorrow_confirmed;
      document.getElementById("stat-total-patients").textContent = state.stats.total_patients;
      document.getElementById("badge-tomorrow-unconfirmed").textContent = state.stats.tomorrow_unconfirmed;
    }
  } catch (err) {
    console.error("Error al cargar estadísticas:", err);
  }
}

// ----------------------------------------------------
// TAB: SINCRONIZACIÓN MÓVIL & QR
// ----------------------------------------------------
async function loadNetworkInfo() {
  try {
    const res = await fetch("/api/network-info");
    const json = await res.json();
    if (json.success && json.data) {
      state.network = json.data;
      const effectiveUrl = json.data.effective_url || json.data.local_url;
      const icalUrl = json.data.ical_url;
      const isOnline = json.data.has_public_url;

      document.getElementById("sync-mobile-url").value = effectiveUrl;
      document.getElementById("sync-ical-url").value = icalUrl;
      if (document.getElementById("input-custom-public-url")) {
        document.getElementById("input-custom-public-url").value = json.data.public_url || "";
      }

      // Actualizar Status UI
      const badge = document.getElementById("sync-status-badge");
      const statusText = document.getElementById("sync-status-text");
      const qrDesc = document.getElementById("qr-desc-text");

      if (isOnline) {
        badge.className = "status-badge status-Confirmada";
        statusText.textContent = "Online Global (4G / 5G)";
        qrDesc.textContent = "✨ Escanea para acceder desde cualquier lugar con datos móviles 4G/5G o cualquier Wi-Fi.";
      } else {
        badge.className = "status-badge status-Recordatorio.Enviado";
        statusText.textContent = "Wi-Fi Local";
        qrDesc.textContent = "Asegúrate de que tu celular esté en la misma red Wi-Fi o presiona 'Activar Acceso por Internet'.";
      }

      // Renderizar QR Code
      const qrContainer = document.getElementById("qr-code-container");
      qrContainer.innerHTML = createQRCodeSVG(effectiveUrl, 200);
    }
  } catch (e) {
    console.error("Error cargando network info:", e);
  }
}

function copyInput(inputId) {
  const input = document.getElementById(inputId);
  input.select();
  navigator.clipboard.writeText(input.value).then(() => {
    showToast("Enlace copiado al portapapeles 📋");
  });
}

// ----------------------------------------------------
// TAB 1: AGENDA & TURNOS
// ----------------------------------------------------
async function loadAppointmentsForDate() {
  const dateStr = formatDateISO(state.currentDate);
  document.getElementById("agenda-date-picker").value = dateStr;
  document.getElementById("agenda-date-display").textContent = formatDisplayDate(state.currentDate);

  try {
    const res = await fetch(`/api/appointments?date_from=${dateStr}&date_to=${dateStr}`);
    const json = await res.json();
    if (json.success) {
      state.appointments = json.data;
      renderAgendaAppointments();
    }
  } catch (err) {
    console.error("Error al cargar citas:", err);
  }
}

function renderAgendaAppointments() {
  const container = document.getElementById("agenda-appointments-list");
  const filterStatus = document.getElementById("filter-status").value;

  let list = state.appointments;
  if (filterStatus) {
    list = list.filter(a => a.status === filterStatus);
  }

  if (list.length === 0) {
    container.innerHTML = `
      <div style="text-align: center; padding: 40px 20px; color: var(--text-muted);">
        <p style="font-size: 1.1rem; font-weight: 500;">No hay citas agendadas para este día.</p>
        <button class="btn btn-primary btn-sm" style="margin-top: 12px;" onclick="openAppointmentModal()">
          + Agendar Primera Cita
        </button>
      </div>
    `;
    return;
  }

  container.innerHTML = list.map(appt => `
    <div class="appointment-row" style="border-left-color: ${appt.service_color || '#c97a8e'};">
      <div class="appt-time">
        <span class="time-val">${appt.appointment_time}</span>
        <span class="duration-val">${appt.duration_minutes} min</span>
      </div>

      <div class="appt-patient">
        <h4>${appt.patient_name}</h4>
        <p>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/></svg>
          ${appt.patient_phone}
        </p>
      </div>

      <div class="appt-service">
        <span class="service-tag" style="background: ${appt.service_color}20; color: ${appt.service_color};">
          ${appt.service_category || 'Estética'}
        </span>
        <strong style="display: block; font-size: 0.9rem; color: var(--text-main);">${appt.service_name}</strong>
        <p>Prof: ${appt.specialist} • $${appt.service_price}</p>
      </div>

      <div style="min-width: 140px; text-align: center;">
        <span class="status-badge status-${appt.status.replace(/\s+/g, '.')}">
          <span class="status-dot"></span>
          ${appt.status}
        </span>
      </div>

      <div class="appt-actions">
        <button class="btn btn-secondary btn-sm" onclick="editAppointment(${appt.id})" title="Editar Cita">
          ✏️
        </button>
        <button class="btn btn-whatsapp btn-sm" onclick="sendIndividualReminder(${appt.id})" title="Enviar WhatsApp">
          💬 WhatsApp
        </button>
        <button class="btn btn-danger btn-sm" onclick="deleteAppointmentConfirm(${appt.id})" title="Eliminar Cita">
          🗑️
        </button>
      </div>
    </div>
  `).join("");
}

// ----------------------------------------------------
// TAB 2: RECORDATORIOS 24H (WHATSAPP)
// ----------------------------------------------------
async function loadTomorrowReminders() {
  const container = document.getElementById("tomorrow-reminders-list");
  container.innerHTML = `<p style="padding: 20px; color: var(--text-muted);">Cargando citas de mañana...</p>`;

  try {
    const res = await fetch("/api/reminders/tomorrow");
    const json = await res.json();
    if (!json.success || json.data.length === 0) {
      container.innerHTML = `
        <div class="card" style="text-align: center; padding: 40px 20px;">
          <h4>✨ No hay citas pendientes de confirmación para mañana</h4>
          <p style="color: var(--text-muted); font-size: 0.875rem; margin-top: 6px;">Todas las pacientes están al día o no hay turnos programados.</p>
        </div>
      `;
      return;
    }

    container.innerHTML = json.data.map(item => `
      <div class="reminder-card ${item.status === 'Confirmada' ? 'confirmed-card' : 'pending-card'}">
        <div class="reminder-details">
          <div style="display: flex; align-items: center; justify-content: space-between;">
            <h4>${item.patient_name}</h4>
            <span class="status-badge status-${item.status.replace(/\s+/g, '.')}">
              <span class="status-dot"></span>
              ${item.status}
            </span>
          </div>

          <div class="meta">
            <div class="meta-item">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
              <strong>${item.appointment_time} hrs</strong> (${item.duration_minutes} min)
            </div>
            <div class="meta-item">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
              ${item.service_name}
            </div>
            <div class="meta-item">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/></svg>
              ${item.patient_phone}
            </div>
          </div>

          <label style="font-size: 0.775rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase;">
            Vista Previa del Mensaje de WhatsApp:
          </label>
          <div class="message-preview-box">${item.formatted_message}</div>
        </div>

        <div class="reminder-action-panel">
          <div>
            <span style="font-size: 0.8rem; color: var(--text-muted); display: block; margin-bottom: 8px;">
              ${item.reminder_sent_at ? `Último envío: ${item.reminder_sent_at.slice(11, 16)} hrs` : 'Aún no se ha enviado recordatorio'}
            </span>
            ${item.status === 'Confirmada' ? `
              <div style="color: #065f46; background: #d1fae5; padding: 8px 12px; border-radius: var(--radius-sm); font-size: 0.8rem; font-weight: 600;">
                ✅ ¡Paciente confirmó su asistencia!
              </div>
            ` : `
              <div style="color: #92400e; background: #fef3c7; padding: 8px 12px; border-radius: var(--radius-sm); font-size: 0.8rem; font-weight: 600;">
                ⏳ Esperando confirmación
              </div>
            `}
          </div>

          <div style="display: flex; flex-direction: column; gap: 8px; margin-top: 12px;">
            <a href="${item.whatsapp_link}" target="_blank" class="btn btn-whatsapp" onclick="markSentAndReload(${item.id})">
              <span>Abrir WhatsApp Web / App</span>
            </a>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 6px;">
              <button class="btn btn-secondary btn-sm" onclick="copyToClipboard(\`${item.formatted_message.replace(/`/g, "\\`")}\`)">
                📋 Copiar
              </button>
              <a href="/confirmar/${item.confirmation_token}" target="_blank" class="btn btn-secondary btn-sm" style="text-decoration: none;">
                🔗 Ver Portal
              </a>
            </div>
          </div>
        </div>
      </div>
    `).join("");
  } catch (err) {
    console.error("Error al cargar recordatorios:", err);
  }
}

async function markSentAndReload(apptId) {
  try {
    await fetch(`/api/reminders/send/${apptId}`, { method: "POST" });
    showToast("Recordatorio registrado como enviado.");
    setTimeout(() => {
      loadStats();
      if (state.activeTab === "reminders") loadTomorrowReminders();
    }, 1000);
  } catch (e) {
    console.error(e);
  }
}

async function sendIndividualReminder(apptId) {
  try {
    const res = await fetch(`/api/reminders/send/${apptId}`, { method: "POST" });
    const json = await res.json();
    if (json.success && json.data.whatsapp_link) {
      window.open(json.data.whatsapp_link, "_blank");
      showToast("Mensaje de WhatsApp abierto");
      loadStats();
      loadAppointmentsForDate();
    }
  } catch (e) {
    console.error(e);
  }
}

async function sendAllPendingReminders() {
  try {
    const res = await fetch("/api/reminders/tomorrow");
    const json = await res.json();
    if (json.success && json.data.length > 0) {
      const pending = json.data.filter(a => a.status !== "Confirmada" && a.status !== "Cancelada");
      if (pending.length === 0) {
        showToast("No hay recordatorios pendientes de confirmación.");
        return;
      }
      for (const item of pending) {
        await fetch(`/api/reminders/send/${item.id}`, { method: "POST" });
      }
      showToast(`Se prepararon ${pending.length} recordatorios.`);
      loadTomorrowReminders();
      loadStats();
    }
  } catch (e) {
    console.error(e);
  }
}

function copyToClipboard(text) {
  navigator.clipboard.writeText(text).then(() => {
    showToast("Mensaje copiado al portapapeles ✅");
  });
}

// ----------------------------------------------------
// TAB 3: PACIENTES & FICHAS
// ----------------------------------------------------
async function loadPatients(search = "") {
  try {
    const res = await fetch(`/api/patients?search=${encodeURIComponent(search)}`);
    const json = await res.json();
    if (json.success) {
      state.patients = json.data;
      renderPatientsTable();
      populatePatientSelect();
    }
  } catch (err) {
    console.error("Error al cargar pacientes:", err);
  }
}

function renderPatientsTable() {
  const tbody = document.getElementById("patients-table-body");
  if (state.patients.length === 0) {
    tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding: 30px; color: var(--text-muted);">No se encontraron pacientes.</td></tr>`;
    return;
  }

  tbody.innerHTML = state.patients.map(p => `
    <tr style="border-bottom: 1px solid var(--border-color); font-size: 0.9rem;">
      <td style="padding: 16px 20px;">
        <div style="font-weight: 700; color: var(--text-main);">${p.name}</div>
        <div style="font-size: 0.775rem; color: var(--text-muted);">${p.email || 'Sin email registrado'}</div>
      </td>
      <td style="padding: 16px 20px;">
        <span style="font-weight: 600; color: var(--text-main);">${p.phone}</span>
      </td>
      <td style="padding: 16px 20px;">
        <div style="font-size: 0.85rem;"><strong>Piel:</strong> ${p.skin_type || 'No especificado'}</div>
        <div style="font-size: 0.775rem; color: #ef4444;"><strong>Alergias:</strong> ${p.allergies || 'Ninguna'}</div>
      </td>
      <td style="padding: 16px 20px;">
        <span class="service-tag" style="background: #f1f5f9; color: #475569;">
          ${p.total_appointments} sesiones
        </span>
      </td>
      <td style="padding: 16px 20px; text-align: right; white-space: nowrap;">
        <button class="btn btn-secondary btn-sm" onclick="viewPatientHistory(${p.id})">
          📄 Ficha
        </button>
        <button class="btn btn-primary btn-sm" onclick="quickScheduleForPatient(${p.id})">
          + Cita
        </button>
      </td>
    </tr>
  `).join("");
}

async function viewPatientHistory(patientId) {
  try {
    const res = await fetch(`/api/patients/${patientId}`);
    const json = await res.json();
    if (json.success && json.data) {
      const p = json.data;
      document.getElementById("history-patient-name").textContent = `Ficha Estética: ${p.name}`;
      document.getElementById("history-patient-details").innerHTML = `
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; font-size: 0.85rem;">
          <div><strong>WhatsApp:</strong> ${p.phone}</div>
          <div><strong>Email:</strong> ${p.email || 'N/A'}</div>
          <div><strong>Tipo de Piel:</strong> ${p.skin_type || 'Sin registrar'}</div>
          <div><strong>Alergias:</strong> <span style="color: #ef4444;">${p.allergies || 'Ninguna'}</span></div>
        </div>
        ${p.notes ? `<div style="margin-top: 10px; font-size: 0.825rem; color: var(--text-muted);"><strong>Notas:</strong> ${p.notes}</div>` : ''}
      `;

      const listContainer = document.getElementById("history-appointments-list");
      if (!p.history || p.history.length === 0) {
        listContainer.innerHTML = `<p style="color: var(--text-muted); font-size: 0.85rem;">No hay citas registradas para este paciente.</p>`;
      } else {
        listContainer.innerHTML = p.history.map(a => `
          <div class="appointment-row" style="padding: 10px 14px;">
            <div>
              <strong>${a.appointment_date}</strong> a las ${a.appointment_time} hrs
              <div style="font-size: 0.8rem; color: var(--text-muted);">${a.service_name} • Prof: ${a.specialist}</div>
            </div>
            <div>
              <span class="status-badge status-${a.status.replace(/\s+/g, '.')}">${a.status}</span>
            </div>
          </div>
        `).join("");
      }

      document.getElementById("btn-schedule-from-history").onclick = () => {
        closeModal("modal-patient-history");
        quickScheduleForPatient(p.id);
      };

      openModal("modal-patient-history");
    }
  } catch (e) {
    console.error(e);
  }
}

function quickScheduleForPatient(patientId) {
  openAppointmentModal({ patient_id: patientId });
}

// ----------------------------------------------------
// TAB 4: TRATAMIENTOS & SERVICIOS
// ----------------------------------------------------
async function loadServices() {
  try {
    const res = await fetch("/api/services");
    const json = await res.json();
    if (json.success) {
      state.services = json.data;
      renderServicesGrid();
      populateServiceSelect();
    }
  } catch (err) {
    console.error("Error al cargar servicios:", err);
  }
}

function renderServicesGrid() {
  const container = document.getElementById("services-grid");
  if (state.services.length === 0) {
    container.innerHTML = `<p style="color: var(--text-muted);">No hay tratamientos registrados.</p>`;
    return;
  }

  container.innerHTML = state.services.map(s => `
    <div class="card" style="border-top: 4px solid ${s.color};">
      <div class="card-body">
        <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 8px;">
          <span class="service-tag" style="background: ${s.color}25; color: ${s.color};">
            ${s.category}
          </span>
          <span style="font-size: 1.15rem; font-weight: 700; color: var(--text-main);">$${s.price}</span>
        </div>
        <h4 style="font-size: 1rem; font-weight: 700; margin-bottom: 6px; color: var(--text-main);">${s.name}</h4>
        <p style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 12px;">
          ⏱️ Duración: <strong>${s.duration_minutes} minutos</strong>
        </p>
        ${s.instructions ? `
          <div style="background: #fdf2f4; border-radius: var(--radius-sm); padding: 8px 10px; font-size: 0.775rem; color: #831843;">
            💡 <strong>Indicaciones:</strong> ${s.instructions}
          </div>
        ` : ''}
      </div>
    </div>
  `).join("");
}

// ----------------------------------------------------
// TAB 5: CONFIGURACIÓN
// ----------------------------------------------------
async function loadSettings() {
  try {
    const res = await fetch("/api/settings");
    const json = await res.json();
    if (json.success) {
      state.settings = json.data;
      document.getElementById("setting-clinic-name").value = state.settings.clinic_name || "";
      document.getElementById("setting-clinic-phone").value = state.settings.clinic_phone || "";
      document.getElementById("setting-clinic-address").value = state.settings.clinic_address || "";
      document.getElementById("setting-clinic-email").value = state.settings.clinic_email || "";
      document.getElementById("setting-whatsapp-template").value = state.settings.whatsapp_template || "";
    }
  } catch (err) {
    console.error("Error al cargar configuración:", err);
  }
}

async function handleSettingsSubmit(e) {
  e.preventDefault();
  const payload = {
    clinic_name: document.getElementById("setting-clinic-name").value,
    clinic_phone: document.getElementById("setting-clinic-phone").value,
    clinic_address: document.getElementById("setting-clinic-address").value,
    clinic_email: document.getElementById("setting-clinic-email").value,
    whatsapp_template: document.getElementById("setting-whatsapp-template").value
  };

  try {
    const res = await fetch("/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      showToast("Configuración guardada correctamente ✨");
    }
  } catch (err) {
    console.error(err);
  }
}

// ----------------------------------------------------
// MODALES & FORMULARIOS
// ----------------------------------------------------
function openModal(id) {
  document.getElementById(id).classList.add("active");
}

function closeModal(id) {
  document.getElementById(id).classList.remove("active");
}

function populatePatientSelect() {
  const sel = document.getElementById("appt-patient-select");
  sel.innerHTML = state.patients.map(p => `
    <option value="${p.id}">${p.name} (${p.phone})</option>
  `).join("");
}

function populateServiceSelect() {
  const sel = document.getElementById("appt-service-select");
  sel.innerHTML = state.services.map(s => `
    <option value="${s.id}">${s.name} - $${s.price} (${s.duration_minutes} min)</option>
  `).join("");
}

function openAppointmentModal(initialData = {}) {
  document.getElementById("form-appointment").reset();
  document.getElementById("appt-id").value = initialData.id || "";
  document.getElementById("modal-appointment-title").textContent = initialData.id ? "Editar Cita" : "Agendar Nueva Cita";

  if (initialData.patient_id) {
    document.getElementById("appt-patient-select").value = initialData.patient_id;
  }
  if (initialData.service_id) {
    document.getElementById("appt-service-select").value = initialData.service_id;
  }

  const defaultDate = initialData.appointment_date || formatDateISO(state.currentDate);
  document.getElementById("appt-date").value = defaultDate;
  document.getElementById("appt-time").value = initialData.appointment_time || "10:00";
  document.getElementById("appt-specialist").value = initialData.specialist || "Cosmetóloga Constanza Díaz";
  document.getElementById("appt-status").value = initialData.status || "Pendiente";
  document.getElementById("appt-notes").value = initialData.notes || "";

  openModal("modal-appointment");
}

async function editAppointment(apptId) {
  try {
    const res = await fetch(`/api/appointments/${apptId}`);
    const json = await res.json();
    if (json.success && json.data) {
      openAppointmentModal(json.data);
    }
  } catch (e) {
    console.error(e);
  }
}

async function deleteAppointmentConfirm(apptId) {
  if (confirm("¿Estás seguro de que deseas eliminar esta cita?")) {
    try {
      await fetch(`/api/appointments/${apptId}`, { method: "DELETE" });
      showToast("Cita eliminada.");
      loadAppointmentsForDate();
      loadStats();
    } catch (e) {
      console.error(e);
    }
  }
}

async function handleAppointmentSubmit(e) {
  e.preventDefault();
  const id = document.getElementById("appt-id").value;
  const payload = {
    patient_id: parseInt(document.getElementById("appt-patient-select").value),
    service_id: parseInt(document.getElementById("appt-service-select").value),
    appointment_date: document.getElementById("appt-date").value,
    appointment_time: document.getElementById("appt-time").value,
    specialist: document.getElementById("appt-specialist").value,
    status: document.getElementById("appt-status").value,
    notes: document.getElementById("appt-notes").value
  };

  const url = id ? `/api/appointments/${id}` : "/api/appointments";
  const method = id ? "PUT" : "POST";

  try {
    const res = await fetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const json = await res.json();
    if (json.success) {
      closeModal("modal-appointment");
      showToast(id ? "Cita actualizada correctamente" : "Cita agendada con éxito ✨");
      loadAppointmentsForDate();
      loadStats();
    }
  } catch (err) {
    console.error(err);
  }
}

async function handlePatientSubmit(e) {
  e.preventDefault();
  const id = document.getElementById("patient-id").value;
  const payload = {
    name: document.getElementById("patient-name").value,
    phone: document.getElementById("patient-phone").value,
    email: document.getElementById("patient-email").value,
    birth_date: document.getElementById("patient-birth").value,
    skin_type: document.getElementById("patient-skin").value,
    allergies: document.getElementById("patient-allergies").value,
    notes: document.getElementById("patient-notes").value
  };

  const url = id ? `/api/patients/${id}` : "/api/patients";
  const method = id ? "PUT" : "POST";

  try {
    const res = await fetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const json = await res.json();
    if (json.success) {
      closeModal("modal-patient");
      showToast("Paciente registrado con éxito.");
      await loadPatients();
      loadStats();
    }
  } catch (err) {
    console.error(err);
  }
}

async function handleServiceSubmit(e) {
  e.preventDefault();
  const payload = {
    name: document.getElementById("service-name").value,
    category: document.getElementById("service-category").value,
    duration_minutes: parseInt(document.getElementById("service-duration").value),
    price: parseFloat(document.getElementById("service-price").value),
    color: document.getElementById("service-color").value,
    instructions: document.getElementById("service-instructions").value
  };

  try {
    const res = await fetch("/api/services", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const json = await res.json();
    if (json.success) {
      closeModal("modal-service");
      showToast("Tratamiento agregado al catálogo ✨");
      loadServices();
    }
  } catch (err) {
    console.error(err);
  }
}

// Toast
function showToast(message) {
  const container = document.getElementById("toast-container");
  const toast = document.createElement("div");
  toast.className = "toast";
  toast.innerHTML = `<span>${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.remove();
  }, 3500);
}
