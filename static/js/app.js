// Estética Divine - App Logic SPA & Sincronización Móvil
let state = {
  authToken: localStorage.getItem("estetica_auth_token") || null,
  currentUser: null,
  currentDate: new Date(),
  calendarDate: new Date(),
  activeTab: "agenda",
  appointments: [],
  patients: [],
  services: [],
  settings: {},
  stats: {},
  network: {}
};

// Wrapper para inyectar token de autenticación en todas las peticiones
async function apiFetch(url, options = {}) {
  options.headers = options.headers || {};
  if (state.authToken) {
    if (options.headers instanceof Headers) {
      options.headers.set("Authorization", "Bearer " + state.authToken);
    } else {
      options.headers["Authorization"] = "Bearer " + state.authToken;
    }
  }
  try {
    const response = await fetch(url, options);
    if (response.status === 401 && !url.includes("/api/auth/login") && !url.includes("/api/auth/register")) {
      console.warn("Sesión no autorizada o expirada. Redirigiendo a Login...");
      state.authToken = null;
      state.currentUser = null;
      localStorage.removeItem("estetica_auth_token");
      showAuthGateway();
    }
    return response;
  } catch (err) {
    console.error("Error en apiFetch:", err);
    throw err;
  }
}

// Inicialización
document.addEventListener("DOMContentLoaded", () => {
  initServiceWorker();
  initDateTime();
  initNavigation();
  initEventListeners();
  checkAuthSession();
});

// Control de Sesión y Gateway de Entrada
async function checkAuthSession() {
  if (!state.authToken) {
    showAuthGateway();
    return;
  }
  try {
    const res = await apiFetch("/api/auth/me");
    const json = await res.json();
    if (json.success && json.data) {
      state.currentUser = json.data;
      updateUserProfileUI();
      hideAuthGateway();
      loadAllData();
    } else {
      showAuthGateway();
    }
  } catch (e) {
    showAuthGateway();
  }
}

function showAuthGateway() {
  const viewAuth = document.getElementById("view-auth");
  const mainLayout = document.getElementById("app-main-layout");
  if (viewAuth) viewAuth.style.display = "flex";
  if (mainLayout) mainLayout.style.display = "none";
}

function hideAuthGateway() {
  const viewAuth = document.getElementById("view-auth");
  const mainLayout = document.getElementById("app-main-layout");
  if (viewAuth) viewAuth.style.display = "none";
  if (mainLayout) mainLayout.style.display = "block";
}

function updateUserProfileUI() {
  if (!state.currentUser) return;
  const u = state.currentUser;
  
  const nameEl = document.getElementById("sidebar-user-name");
  const roleEl = document.getElementById("sidebar-user-role");
  const specEl = document.getElementById("sidebar-user-specialty");
  const avatarEl = document.getElementById("sidebar-user-avatar");

  if (nameEl) nameEl.textContent = u.name;
  if (roleEl) roleEl.textContent = u.specialty || "Especialista";
  if (specEl) specEl.textContent = u.specialty || "Centro de Estética";

  if (avatarEl && u.name) {
    const initials = u.name.split(" ").filter(w => w.length > 0).map(w => w[0]).slice(0, 2).join("").toUpperCase();
    avatarEl.textContent = initials || "ED";
  }

  const specialistInput = document.getElementById("appt-specialist");
  if (specialistInput && (!specialistInput.value || specialistInput.value.includes("Constanza"))) {
    specialistInput.value = u.name;
  }
}

function switchAuthTab(tab) {
  const tabLogin = document.getElementById("tab-btn-login");
  const tabReg = document.getElementById("tab-btn-register");
  const formLogin = document.getElementById("form-login");
  const formReg = document.getElementById("form-register");
  const errLogin = document.getElementById("auth-login-error");
  const errReg = document.getElementById("auth-register-error");

  if (errLogin) errLogin.style.display = "none";
  if (errReg) errReg.style.display = "none";

  if (tab === "login") {
    if (tabLogin) tabLogin.classList.add("active");
    if (tabReg) tabReg.classList.remove("active");
    if (formLogin) formLogin.style.display = "flex";
    if (formReg) formReg.style.display = "none";
  } else {
    if (tabReg) tabReg.classList.add("active");
    if (tabLogin) tabLogin.classList.remove("active");
    if (formReg) formReg.style.display = "flex";
    if (formLogin) formLogin.style.display = "none";
  }
}

async function handleLoginSubmit(event) {
  event.preventDefault();
  const email = document.getElementById("login-email").value.trim();
  const password = document.getElementById("login-password").value;
  const errorBox = document.getElementById("auth-login-error");
  const submitBtn = document.getElementById("btn-login-submit");

  if (errorBox) errorBox.style.display = "none";
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.textContent = "Verificando...";
  }

  try {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password })
    });
    const json = await res.json();

    if (json.success && json.data) {
      state.authToken = json.data.token;
      state.currentUser = json.data.user;
      localStorage.setItem("estetica_auth_token", state.authToken);
      updateUserProfileUI();
      hideAuthGateway();
      showToast("¡Bienvenida, " + (state.currentUser.name || "Especialista") + "! 🌸");
      loadAllData();
    } else {
      if (errorBox) {
        errorBox.textContent = json.error || "Credenciales incorrectas";
        errorBox.style.display = "flex";
      }
    }
  } catch (err) {
    if (errorBox) {
      errorBox.textContent = "Error al conectar con el servidor.";
      errorBox.style.display = "flex";
    }
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = "Ingresar a mi Agenda 🌸";
    }
  }
}

async function handleRegisterSubmit(event) {
  event.preventDefault();
  const name = document.getElementById("reg-name").value.trim();
  const specialty = document.getElementById("reg-specialty").value.trim();
  const phone = document.getElementById("reg-phone").value.trim();
  const email = document.getElementById("reg-email").value.trim();
  const password = document.getElementById("reg-password").value;
  const errorBox = document.getElementById("auth-register-error");
  const submitBtn = document.getElementById("btn-register-submit");

  if (errorBox) errorBox.style.display = "none";
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.textContent = "Creando cuenta...";
  }

  try {
    const res = await fetch("/api/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, specialty, phone, email, password })
    });
    const json = await res.json();

    if (json.success && json.data) {
      state.authToken = json.data.token;
      state.currentUser = json.data.user;
      localStorage.setItem("estetica_auth_token", state.authToken);
      updateUserProfileUI();
      hideAuthGateway();
      showToast("¡Cuenta creada con éxito! Bienvenida, " + (state.currentUser.name || "Especialista") + " ✨");
      loadAllData();
    } else {
      if (errorBox) {
        errorBox.textContent = json.error || "No se pudo crear la cuenta.";
        errorBox.style.display = "flex";
      }
    }
  } catch (err) {
    if (errorBox) {
      errorBox.textContent = "Error al conectar con el servidor.";
      errorBox.style.display = "flex";
    }
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = "Crear mi Cuenta & Entrar ✨";
    }
  }
}

async function handleLogout() {
  if (confirm("¿Deseas cerrar tu sesión actual?")) {
    try {
      await apiFetch("/api/auth/logout", { method: "POST" });
    } catch (e) {}
    state.authToken = null;
    state.currentUser = null;
    localStorage.removeItem("estetica_auth_token");
    showAuthGateway();
    showToast("Sesión cerrada correctamente 🚪");
  }
}


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
    calendar: "Calendario Horario (Saltos de 1h)",
    reminders: "Confirmaciones 24h (WhatsApp)",
    sync: "Sincronizar con el Celular",
    patients: "Directorio de Pacientes & Fichas",
    services: "Catálogo de Tratamientos",
    settings: "Configuración & Plantilla WhatsApp"
  };
  document.getElementById("view-title").textContent = titles[tabName] || "Estética Divine";

  if (tabName === "agenda") loadAppointmentsForDate();
  if (tabName === "calendar") loadWeeklyCalendar();
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

  // Navegación de Semana en Calendario Horario
  const btnPrevWeek = document.getElementById("btn-prev-week");
  if (btnPrevWeek) {
    btnPrevWeek.addEventListener("click", () => {
      state.calendarDate.setDate(state.calendarDate.getDate() - 7);
      loadWeeklyCalendar();
    });
  }

  const btnNextWeek = document.getElementById("btn-next-week");
  if (btnNextWeek) {
    btnNextWeek.addEventListener("click", () => {
      state.calendarDate.setDate(state.calendarDate.getDate() + 7);
      loadWeeklyCalendar();
    });
  }

  const btnCurrentWeek = document.getElementById("btn-current-week");
  if (btnCurrentWeek) {
    btnCurrentWeek.addEventListener("click", () => {
      state.calendarDate = new Date();
      loadWeeklyCalendar();
    });
  }

  const calWeekPicker = document.getElementById("calendar-week-picker");
  if (calWeekPicker) {
    calWeekPicker.addEventListener("change", (e) => {
      if (e.target.value) {
        const parts = e.target.value.split("-");
        state.calendarDate = new Date(parts[0], parts[1] - 1, parts[2]);
        loadWeeklyCalendar();
      }
    });
  }

  // Botón Agendar Cita Rápida
  document.getElementById("btn-quick-new-appointment").addEventListener("click", () => {
    openAppointmentModal();
  });

  // Botón Nuevo Paciente
  document.getElementById("btn-new-patient").addEventListener("click", () => {
    openPatientModal();
  });

  // Botón Nuevo Tratamiento
  document.getElementById("btn-new-service").addEventListener("click", () => {
    openServiceModal();
  });

  // Búsqueda de Pacientes
  let searchTimer;
  document.getElementById("patient-search").addEventListener("input", (e) => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      loadPatients(e.target.value);
    }, 300);
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
        await apiFetch("/api/tunnel/start", { method: "POST" });
        let attempts = 0;
        const interval = setInterval(async () => {
          attempts++;
          const res = await apiFetch("/api/network-info");
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
        const res = await apiFetch("/api/tunnel/set-url", {
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
  await checkAndRestorePersistedState();
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
    const res = await apiFetch("/api/stats");
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
    const res = await apiFetch("/api/network-info");
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
// TAB 1: AGENDA & TURNOS (DIARIA)
// ----------------------------------------------------
async function loadAppointmentsForDate() {
  const dateStr = formatDateISO(state.currentDate);
  document.getElementById("agenda-date-picker").value = dateStr;
  document.getElementById("agenda-date-display").textContent = formatDisplayDate(state.currentDate);

  try {
    const res = await apiFetch(`/api/appointments?date_from=${dateStr}&date_to=${dateStr}`);
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
// TAB: CALENDARIO VISUAL POR HORAS (SALTOS DE 1 HORA)
// ----------------------------------------------------
state.calendarMobileView = (window.innerWidth <= 768) ? "day" : "week";

function setCalendarMobileView(mode) {
  state.calendarMobileView = mode;
  const btnDay = document.getElementById("btn-view-day");
  const btnWeek = document.getElementById("btn-view-week");
  if (btnDay && btnWeek) {
    if (mode === "day") {
      btnDay.classList.add("active");
      btnWeek.classList.remove("active");
    } else {
      btnWeek.classList.add("active");
      btnDay.classList.remove("active");
    }
  }
  loadWeeklyCalendar();
}

async function loadWeeklyCalendar() {
  const container = document.getElementById("weekly-calendar-container");
  if (!container) return;

  // Calcular Lunes de la semana seleccionada
  const curr = new Date(state.calendarDate);
  const dayOfWeek = curr.getDay(); // 0 = Domingo, 1 = Lunes, ...
  const distanceToMonday = dayOfWeek === 0 ? -6 : 1 - dayOfWeek;
  const monday = new Date(curr);
  monday.setDate(curr.getDate() + distanceToMonday);

  // Generar 7 días (Lunes a Domingo)
  const weekDays = [];
  for (let i = 0; i < 7; i++) {
    const d = new Date(monday);
    d.setDate(monday.getDate() + i);
    weekDays.push(d);
  }

  const startDateStr = formatDateISO(weekDays[0]);
  const endDateStr = formatDateISO(weekDays[6]);

  // Actualizar display de semana
  const monthNames = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"];
  const startDay = weekDays[0].getDate();
  const startMonth = monthNames[weekDays[0].getMonth()];
  const endDay = weekDays[6].getDate();
  const endMonth = monthNames[weekDays[6].getMonth()];
  const year = weekDays[6].getFullYear();

  document.getElementById("calendar-week-display").textContent = `${startDay} ${startMonth} - ${endDay} ${endMonth} ${year}`;
  if (document.getElementById("calendar-week-picker")) {
    document.getElementById("calendar-week-picker").value = formatDateISO(state.calendarDate);
  }

  // Cargar citas de la semana
  try {
    const res = await apiFetch(`/api/appointments?date_from=${startDateStr}&date_to=${endDateStr}`);
    const json = await res.json();
    const appointments = json.success ? json.data : [];

    // Renderizar Day Pills para selector móvil
    renderMobileDayPills(weekDays, appointments);

    if (state.calendarMobileView === "day") {
      renderMobileDayTimeline(state.calendarDate, appointments);
    } else {
      renderCalendarGrid(weekDays, appointments);
    }
  } catch (err) {
    console.error("Error al cargar citas de la semana:", err);
  }
}

function renderMobileDayPills(weekDays, appointments) {
  const pillsContainer = document.getElementById("calendar-mobile-day-pills");
  if (!pillsContainer) return;

  const dayNames = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"];
  const selectedDateISO = formatDateISO(state.calendarDate);

  pillsContainer.innerHTML = weekDays.map((d, idx) => {
    const dateISO = formatDateISO(d);
    const isSelected = dateISO === selectedDateISO;
    const hasAppts = appointments.some(a => a.appointment_date === dateISO);

    return `
      <div class="day-pill ${isSelected ? 'active' : ''} ${hasAppts ? 'has-appts' : ''}" onclick="selectCalendarDay('${dateISO}')">
        <span class="pill-day-name">${dayNames[idx]}</span>
        <span class="pill-day-number">${d.getDate()}</span>
        <span class="pill-dot"></span>
      </div>
    `;
  }).join("");
}

function selectCalendarDay(dateISO) {
  const parts = dateISO.split("-");
  state.calendarDate = new Date(parts[0], parts[1] - 1, parts[2]);
  loadWeeklyCalendar();
}

function renderMobileDayTimeline(selectedDate, appointments) {
  const container = document.getElementById("weekly-calendar-container");
  const dateISO = formatDateISO(selectedDate);
  const dayOptions = { weekday: 'long', day: 'numeric', month: 'long' };
  const dayNameStr = selectedDate.toLocaleDateString('es-ES', dayOptions);

  const hours = [];
  for (let h = 8; h <= 20; h++) {
    hours.push(String(h).padStart(2, '0') + ":00");
  }

  let html = `
    <div style="margin-bottom: 14px; padding: 4px 8px; display: flex; align-items: center; justify-content: space-between;">
      <h4 style="font-size: 0.95rem; font-weight: 700; color: var(--text-main); text-transform: capitalize;">
        📅 ${dayNameStr}
      </h4>
      <span style="font-size: 0.75rem; color: var(--text-muted);">Horarios de 1h</span>
    </div>
    <div class="mobile-day-timeline">
  `;

  hours.forEach((hourStr, idx) => {
    const hourNum = parseInt(hourStr.split(":")[0]);
    const nextHourStr = String(hourNum + 1).padStart(2, '0') + ":00";

    const slotAppts = appointments.filter(a => {
      if (a.appointment_date !== dateISO) return false;
      const apptHour = parseInt(a.appointment_time.split(":")[0]);
      return apptHour === hourNum;
    });

    html += `
      <div class="timeline-hour-block">
        <div class="timeline-hour-label">
          <span class="time-start">${hourStr}</span>
          <span class="time-end">${nextHourStr}</span>
        </div>
        <div class="timeline-slot-content">
    `;

    if (slotAppts.length > 0) {
      slotAppts.forEach(appt => {
        html += `
          <div class="timeline-slot-card" style="border-left-color: ${appt.service_color || 'var(--primary)'};" onclick="editAppointment(${appt.id})">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
              <span style="font-size: 0.85rem; font-weight: 700; color: var(--text-main);">${appt.patient_name}</span>
              <span class="status-badge status-${appt.status.replace(/\s+/g, '.')}" style="font-size: 0.68rem; padding: 2px 8px;">
                ${appt.status}
              </span>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.775rem; color: var(--text-muted);">
              <span>💆‍♀️ ${appt.service_name}</span>
              <span style="font-weight: 600; color: var(--text-main);">$${appt.service_price}</span>
            </div>
            <div style="font-size: 0.7rem; color: var(--text-muted); margin-top: 3px;">
              ⏰ ${appt.appointment_time} hrs (${appt.duration_minutes} min) • 👩‍⚕️ ${appt.specialist}
            </div>
          </div>
        `;
      });
    } else {
      html += `
        <div class="timeline-slot-empty" onclick="openAppointmentModal({ appointment_date: '${dateISO}', appointment_time: '${hourStr}' })">
          <span>+ ${hourStr} Libre (Toca para agendar)</span>
        </div>
      `;
    }

    html += `
        </div>
      </div>
    `;
  });

  html += `</div>`;
  container.innerHTML = html;
}

function renderCalendarGrid(weekDays, appointments) {
  const container = document.getElementById("weekly-calendar-container");
  const dayNames = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"];
  const todayISO = formatDateISO(new Date());

  // Horas del día: 08:00 a 20:00 (Saltos de 1 hora)
  const hours = [];
  for (let h = 8; h <= 20; h++) {
    hours.push(String(h).padStart(2, '0') + ":00");
  }

  let html = `<table class="calendar-grid-table">`;
  
  // Encabezado con días
  html += `<thead><tr>`;
  html += `<th class="time-col-header">Horario</th>`;
  weekDays.forEach((d, idx) => {
    const dateISO = formatDateISO(d);
    const isToday = dateISO === todayISO;
    html += `
      <th class="${isToday ? 'is-today' : ''}">
        <span class="day-name">${dayNames[idx]}</span>
        <span class="day-number">${d.getDate()}</span>
      </th>
    `;
  });
  html += `</tr></thead><tbody>`;

  // Filas por cada salto de 1 hora
  hours.forEach(hourStr => {
    const hourNum = parseInt(hourStr.split(":")[0]);
    html += `<tr>`;
    html += `<td class="time-cell-label">${hourStr}</td>`;

    weekDays.forEach(d => {
      const dateISO = formatDateISO(d);
      
      // Buscar citas que caigan en esta fecha y comiencen en esta hora
      const slotAppts = appointments.filter(a => {
        if (a.appointment_date !== dateISO) return false;
        const apptHour = parseInt(a.appointment_time.split(":")[0]);
        return apptHour === hourNum;
      });

      if (slotAppts.length > 0) {
        // Celda Ocupada con Cita(s)
        html += `<td class="time-slot-cell has-appointment">`;
        slotAppts.forEach(appt => {
          html += `
            <div class="calendar-event-card" style="border-left-color: ${appt.service_color || 'var(--primary)'};" onclick="editAppointment(${appt.id})" title="Clic para ver/editar cita">
              <div class="calendar-event-header">
                <span class="calendar-event-time">${appt.appointment_time}</span>
                <span class="status-dot" style="background: ${getStatusColor(appt.status)};"></span>
              </div>
              <div class="calendar-event-patient">${appt.patient_name}</div>
              <div class="calendar-event-service">${appt.service_name}</div>
              <div class="calendar-event-footer">
                <span style="font-size: 0.65rem; color: var(--text-muted);">${appt.duration_minutes}m</span>
                <span style="font-size: 0.65rem; font-weight: 700; color: var(--text-main);">$${appt.service_price}</span>
              </div>
            </div>
          `;
        });
        html += `</td>`;
      } else {
        // Celda Libre (Clic para agendar en esa fecha y hora exacta)
        html += `
          <td class="time-slot-cell slot-empty" onclick="openAppointmentModal({ appointment_date: '${dateISO}', appointment_time: '${hourStr}' })" title="Hora disponible: Clic para agendar a las ${hourStr}">
          </td>
        `;
      }
    });

    html += `</tr>`;
  });

  html += `</tbody></table>`;
  container.innerHTML = html;
}

function getStatusColor(status) {
  switch (status) {
    case 'Confirmada': return '#10b981';
    case 'Recordatorio Enviado': return '#3b82f6';
    case 'Completada': return '#8b5cf6';
    case 'Cancelada': return '#ef4444';
    default: return '#f59e0b';
  }
}

// ----------------------------------------------------
// TAB 2: RECORDATORIOS 24H (WHATSAPP)
// ----------------------------------------------------
async function loadTomorrowReminders() {
  const container = document.getElementById("tomorrow-reminders-list");
  container.innerHTML = `<p style="padding: 20px; color: var(--text-muted);">Cargando citas de mañana...</p>`;

  try {
    const res = await apiFetch("/api/reminders/tomorrow");
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

          <div class="reminder-meta">
            <span>📅 Mañana a las <strong>${item.appointment_time} hrs</strong></span>
            <span>💆‍♀️ ${item.service_name} (${item.duration_minutes} min)</span>
            <span>👩‍⚕️ ${item.specialist}</span>
          </div>

          <div class="msg-preview-box">
            ${item.formatted_message.replace(/\n/g, '<br>')}
          </div>
        </div>

        <div class="reminder-actions-col">
          <div class="reminder-badge-whatsapp">
            📱 WhatsApp Directo: ${item.patient_phone}
          </div>

          <div style="display: flex; flex-direction: column; gap: 8px;">
            <a href="${item.whatsapp_link}" target="_blank" class="btn btn-whatsapp" onclick="markSentAndReload(${item.id})">
              💬 Abrir WhatsApp & Enviar
            </a>

            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
              <button class="btn btn-secondary btn-sm" onclick="copyToClipboard('${encodeURIComponent(item.formatted_message)}')">
                📋 Copiar Texto
              </button>
              <a href="/confirmar/${item.confirmation_token}" target="_blank" class="btn btn-secondary btn-sm" style="text-align: center;">
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
    await apiFetch(`/api/reminders/send/${apptId}`, { method: "POST" });
    showToast("Recordatorio registrado como enviado.");
    triggerPersistentBackup();
    setTimeout(() => {
      loadStats();
      if (state.activeTab === "reminders") loadTomorrowReminders();
    }, 500);
  } catch (e) {
    console.error(e);
  }
}

async function sendIndividualReminder(apptId) {
  try {
    const res = await apiFetch(`/api/reminders/send/${apptId}`, { method: "POST" });
    const json = await res.json();
    if (json.success && json.data.whatsapp_link) {
      window.open(json.data.whatsapp_link, "_blank");
      showToast("Mensaje de WhatsApp abierto y registrado");
      triggerPersistentBackup();
      loadStats();
      loadAppointmentsForDate();
      if (state.activeTab === "reminders") loadTomorrowReminders();
      if (state.activeTab === "calendar") loadWeeklyCalendar();
    }
  } catch (e) {
    console.error(e);
  }
}

async function sendAllPendingReminders() {
  try {
    const res = await apiFetch("/api/reminders/tomorrow");
    const json = await res.json();
    if (json.success && json.data.length > 0) {
      const pending = json.data.filter(a => a.status !== "Confirmada" && a.status !== "Cancelada");
      if (pending.length === 0) {
        showToast("No hay recordatorios pendientes de confirmación.");
        return;
      }
      for (const item of pending) {
        await apiFetch(`/api/reminders/send/${item.id}`, { method: "POST" });
      }
      showToast(`Se prepararon y registraron ${pending.length} recordatorios.`);
      triggerPersistentBackup();
      loadTomorrowReminders();
      loadStats();
    }
  } catch (e) {
    console.error(e);
  }
}

function copyToClipboard(text) {
  navigator.clipboard.writeText(decodeURIComponent(text)).then(() => {
    showToast("Mensaje copiado al portapapeles ✅");
  });
}

// ----------------------------------------------------
// TAB 3: PACIENTES & FICHAS (CON EDITAR Y ELIMINAR)
// ----------------------------------------------------
async function loadPatients(search = "") {
  try {
    const res = await apiFetch(`/api/patients?search=${encodeURIComponent(search)}`);
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
        <button class="btn btn-secondary btn-sm" onclick="viewPatientHistory(${p.id})" title="Ver ficha clínica">
          📄 Ficha
        </button>
        <button class="btn btn-secondary btn-sm" onclick="editPatient(${p.id})" title="Editar datos">
          ✏️ Editar
        </button>
        <button class="btn btn-primary btn-sm" onclick="quickScheduleForPatient(${p.id})" title="Nueva Cita">
          + Cita
        </button>
        <button class="btn btn-danger btn-sm" onclick="deletePatientConfirm(${p.id}, '${p.name.replace(/'/g, "\\'")}')" title="Eliminar paciente">
          🗑️
        </button>
      </td>
    </tr>
  `).join("");
}

function openPatientModal(initialData = null) {
  const form = document.getElementById("form-patient");
  form.reset();

  if (initialData) {
    document.getElementById("modal-patient-title").textContent = "Editar Datos del Paciente";
    document.getElementById("patient-id").value = initialData.id;
    document.getElementById("patient-name").value = initialData.name || "";
    document.getElementById("patient-phone").value = initialData.phone || "";
    document.getElementById("patient-email").value = initialData.email || "";
    document.getElementById("patient-birth").value = initialData.birth_date || "";
    document.getElementById("patient-skin").value = initialData.skin_type || "";
    document.getElementById("patient-allergies").value = initialData.allergies || "Ninguna";
    document.getElementById("patient-notes").value = initialData.notes || "";
  } else {
    document.getElementById("modal-patient-title").textContent = "Registrar Paciente";
    document.getElementById("patient-id").value = "";
  }

  openModal("modal-patient");
}

async function editPatient(patientId) {
  try {
    const res = await apiFetch(`/api/patients/${patientId}`);
    const json = await res.json();
    if (json.success && json.data) {
      openPatientModal(json.data);
    }
  } catch (e) {
    console.error(e);
  }
}

async function deletePatientConfirm(patientId, patientName) {
  if (confirm(`¿Estás segura de que deseas eliminar a la paciente "${patientName}"?\nSe borrarán permanentemente sus datos y citas asociadas.`)) {
    try {
      const res = await apiFetch(`/api/patients/${patientId}`, { method: "DELETE" });
      const json = await res.json();
      if (json.success) {
        showToast("Paciente eliminado con éxito.");
        await loadPatients();
        loadStats();
        loadAppointmentsForDate();
        if (state.activeTab === "calendar") loadWeeklyCalendar();
      }
    } catch (e) {
      console.error(e);
    }
  }
}

async function viewPatientHistory(patientId) {
  try {
    const res = await apiFetch(`/api/patients/${patientId}`);
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
// TAB 4: TRATAMIENTOS & SERVICIOS (CON EDITAR Y ELIMINAR)
// ----------------------------------------------------
async function loadServices() {
  try {
    const res = await apiFetch("/api/services");
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
    <div class="card" style="border-top: 4px solid ${s.color}; display: flex; flex-direction: column; justify-content: space-between;">
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
          <div style="background: #fdf2f4; border-radius: var(--radius-sm); padding: 8px 10px; font-size: 0.775rem; color: #831843; margin-bottom: 12px;">
            💡 <strong>Indicaciones:</strong> ${s.instructions}
          </div>
        ` : ''}

        <div class="card-actions-bar">
          <button class="btn btn-secondary btn-sm" onclick="editService(${s.id})" title="Editar tratamiento">
            ✏️ Editar
          </button>
          <button class="btn btn-danger btn-sm" onclick="deleteServiceConfirm(${s.id}, '${s.name.replace(/'/g, "\\'")}')" title="Eliminar tratamiento">
            🗑️ Eliminar
          </button>
        </div>
      </div>
    </div>
  `).join("");
}

function openServiceModal(initialData = null) {
  const form = document.getElementById("form-service");
  form.reset();

  if (initialData) {
    document.getElementById("modal-service-title").textContent = "Editar Tratamiento";
    document.getElementById("service-id").value = initialData.id;
    document.getElementById("service-name").value = initialData.name || "";
    document.getElementById("service-category").value = initialData.category || "Facial";
    document.getElementById("service-duration").value = initialData.duration_minutes || 60;
    document.getElementById("service-price").value = initialData.price || 0;
    document.getElementById("service-color").value = initialData.color || "#F472B6";
    document.getElementById("service-instructions").value = initialData.instructions || "";
  } else {
    document.getElementById("modal-service-title").textContent = "Nuevo Tratamiento / Servicio";
    document.getElementById("service-id").value = "";
    document.getElementById("service-color").value = "#F472B6";
  }

  openModal("modal-service");
}

async function editService(serviceId) {
  try {
    const res = await apiFetch(`/api/services/${serviceId}`);
    const json = await res.json();
    if (json.success && json.data) {
      openServiceModal(json.data);
    }
  } catch (e) {
    console.error(e);
  }
}

async function deleteServiceConfirm(serviceId, serviceName) {
  if (confirm(`¿Estás segura de que deseas eliminar el tratamiento "${serviceName}" del catálogo?`)) {
    try {
      const res = await apiFetch(`/api/services/${serviceId}`, { method: "DELETE" });
      const json = await res.json();
      if (json.success) {
        showToast("Tratamiento eliminado del catálogo.");
        loadServices();
      }
    } catch (e) {
      console.error(e);
    }
  }
}

// ----------------------------------------------------
// TAB 5: CONFIGURACIÓN
// ----------------------------------------------------
async function loadSettings() {
  try {
    const res = await apiFetch("/api/settings");
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
    const res = await apiFetch("/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      showToast("Configuración guardada correctamente ✨");
      triggerPersistentBackup();
    }
  } catch (err) {
    console.error(err);
  }
}

// ----------------------------------------------------
// PERSISTENCIA & SINCRONIZACIÓN AUTOMÁTICA EN CLIENTE
// ----------------------------------------------------
let syncSaveTimeout = null;

function triggerPersistentBackup() {
  clearTimeout(syncSaveTimeout);
  syncSaveTimeout = setTimeout(async () => {
    try {
      const res = await apiFetch("/api/sync/state");
      const json = await res.json();
      if (json.success && json.data) {
        localStorage.setItem("estetica_divine_backup_v1", JSON.stringify(json.data));
        localStorage.setItem("estetica_divine_has_custom_data", "true");
        console.log("💾 Respaldo automático guardado en el dispositivo.");
      }
    } catch (e) {
      console.warn("No se pudo guardar respaldo:", e);
    }
  }, 400);
}

async function checkAndRestorePersistedState() {
  const hasCustom = localStorage.getItem("estetica_divine_has_custom_data");
  const savedData = localStorage.getItem("estetica_divine_backup_v1");

  try {
    const res = await apiFetch("/api/sync/state");
    const json = await res.json();

    if (json.success && json.data) {
      const serverPatients = json.data.patients || [];
      const serverAppts = json.data.appointments || [];

      // Si el servidor está vacío (reinicio de Render) y el cliente tiene datos guardados:
      if (serverPatients.length === 0 && serverAppts.length === 0 && hasCustom === "true" && savedData) {
        const parsed = JSON.parse(savedData);
        await apiFetch("/api/sync/state", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(parsed)
        });
        console.log("✨ Base de datos restaurada automáticamente desde la memoria del dispositivo.");
      } else if (serverPatients.length > 0 || serverAppts.length > 0) {
        // El servidor tiene datos reales (o confirmaciones de pacientes recibidas por WhatsApp):
        localStorage.setItem("estetica_divine_backup_v1", JSON.stringify(json.data));
        localStorage.setItem("estetica_divine_has_custom_data", "true");
        console.log("🔄 Memoria local actualizada con las confirmaciones y citas más recientes del servidor.");
      }
    }
  } catch (e) {
    console.warn("Sincronización inicial:", e);
  }
}

async function downloadBackupJSON() {
  try {
    const res = await apiFetch("/api/sync/state");
    const json = await res.json();
    if (json.success) {
      const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(json.data, null, 2));
      const downloadAnchor = document.createElement('a');
      const todayISO = formatDateISO(new Date());
      downloadAnchor.setAttribute("href", dataStr);
      downloadAnchor.setAttribute("download", `estetica_divine_respaldo_${todayISO}.json`);
      document.body.appendChild(downloadAnchor);
      downloadAnchor.click();
      downloadAnchor.remove();
      showToast("Copia de seguridad descargada 📥");
    }
  } catch (e) {
    console.error(e);
    showToast("Error al descargar respaldo");
  }
}

async function restoreBackupJSON(event) {
  const file = event.target.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = async (e) => {
    try {
      const data = JSON.parse(e.target.result);
      const res = await apiFetch("/api/sync/state", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data)
      });
      const json = await res.json();
      if (json.success) {
        localStorage.setItem("estetica_divine_backup_v1", JSON.stringify(data));
        localStorage.setItem("estetica_divine_has_custom_data", "true");
        showToast("Copia de seguridad restaurada con éxito ✨");
        loadAllData();
      } else {
        showToast("El archivo de respaldo no es válido.");
      }
    } catch (err) {
      console.error(err);
      showToast("Error al leer el archivo de respaldo.");
    }
  };
  reader.readAsText(file);
}

async function clearSampleDemoData() {
  if (confirm("¿Estás segura de que deseas borrar los pacientes y citas de ejemplo para comenzar con la agenda limpia?")) {
    const emptyState = {
      patients: [],
      appointments: [],
      services: state.services,
      settings: state.settings
    };
    try {
      const res = await apiFetch("/api/sync/state", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(emptyState)
      });
      if (res.ok) {
        localStorage.setItem("estetica_divine_backup_v1", JSON.stringify(emptyState));
        localStorage.setItem("estetica_divine_has_custom_data", "true");
        showToast("Datos de prueba eliminados. Agenda lista para uso real ✨");
        await loadAllData();
      }
    } catch (e) {
      console.error(e);
    }
  }
}

// ----------------------------------------------------
// HELPERS & MODALS
// ----------------------------------------------------
function populatePatientSelect() {
  const select = document.getElementById("appt-patient-select");
  select.innerHTML = '<option value="">-- Selecciona un Paciente --</option>' +
    state.patients.map(p => `<option value="${p.id}">${p.name} (${p.phone})</option>`).join("");
}

function populateServiceSelect() {
  const select = document.getElementById("appt-service-select");
  select.innerHTML = '<option value="">-- Selecciona un Tratamiento --</option>' +
    state.services.map(s => `<option value="${s.id}">${s.name} - $${s.price} (${s.duration_minutes} min)</option>`).join("");
}

function openModal(modalId) {
  document.getElementById(modalId).classList.add("active");
}

function closeModal(modalId) {
  document.getElementById(modalId).classList.remove("active");
}

function openAppointmentModal(initialData = {}) {
  const form = document.getElementById("form-appointment");
  form.reset();

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
    const res = await apiFetch(`/api/appointments/${apptId}`);
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
      await apiFetch(`/api/appointments/${apptId}`, { method: "DELETE" });
      showToast("Cita eliminada.");
      loadAppointmentsForDate();
      if (state.activeTab === "calendar") loadWeeklyCalendar();
      loadStats();
      triggerPersistentBackup();
    } catch (e) {
      console.error(e);
    }
  }
}

async function deletePatientConfirm(patientId, patientName) {
  if (confirm(`¿Estás segura de que deseas eliminar a "${patientName}" y todas sus citas asociadas?`)) {
    try {
      const res = await apiFetch(`/api/patients/${patientId}`, { method: "DELETE" });
      const json = await res.json();
      if (json.success) {
        showToast("Paciente eliminado con éxito.");
        await loadPatients();
        loadStats();
        if (state.activeTab === "agenda") loadAppointmentsForDate();
        if (state.activeTab === "calendar") loadWeeklyCalendar();
        triggerPersistentBackup();
      }
    } catch (e) {
      console.error(e);
    }
  }
}

async function deleteServiceConfirm(serviceId, serviceName) {
  if (confirm(`¿Estás segura de que deseas eliminar el tratamiento "${serviceName}" del catálogo?`)) {
    try {
      const res = await apiFetch(`/api/services/${serviceId}`, { method: "DELETE" });
      const json = await res.json();
      if (json.success) {
        showToast("Tratamiento eliminado del catálogo.");
        loadServices();
        triggerPersistentBackup();
      }
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
    const res = await apiFetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const json = await res.json();
    if (json.success) {
      closeModal("modal-appointment");
      showToast(id ? "Cita actualizada correctamente ✨" : "Cita agendada con éxito ✨");
      loadAppointmentsForDate();
      if (state.activeTab === "calendar") loadWeeklyCalendar();
      loadStats();
      triggerPersistentBackup();
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
    const res = await apiFetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const json = await res.json();
    if (json.success) {
      closeModal("modal-patient");
      showToast(id ? "Paciente actualizado correctamente ✨" : "Paciente registrado con éxito ✨");
      await loadPatients();
      loadStats();
      triggerPersistentBackup();
    }
  } catch (err) {
    console.error(err);
  }
}

async function handleServiceSubmit(e) {
  e.preventDefault();
  const id = document.getElementById("service-id").value;
  const payload = {
    name: document.getElementById("service-name").value,
    category: document.getElementById("service-category").value,
    duration_minutes: parseInt(document.getElementById("service-duration").value),
    price: parseFloat(document.getElementById("service-price").value),
    color: document.getElementById("service-color").value,
    instructions: document.getElementById("service-instructions").value
  };

  const url = id ? `/api/services/${id}` : "/api/services";
  const method = id ? "PUT" : "POST";

  try {
    const res = await apiFetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const json = await res.json();
    if (json.success) {
      closeModal("modal-service");
      showToast(id ? "Tratamiento actualizado correctamente ✨" : "Tratamiento agregado al catálogo ✨");
      loadServices();
      triggerPersistentBackup();
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

