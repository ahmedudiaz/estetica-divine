// confirm.js - Manejo del Portal de Confirmación de la Paciente
document.addEventListener("DOMContentLoaded", () => {
  const token = window.location.pathname.split("/").pop();
  if (!token) {
    document.getElementById("portal-loading").innerHTML = `<p style="color: #ef4444;">Enlace inválido o token no proporcionado.</p>`;
    return;
  }

  loadAppointmentInfo(token);

  document.getElementById("btn-confirm-appointment").addEventListener("click", () => {
    confirmAppointment(token, "confirm");
  });

  document.getElementById("btn-cancel-appointment").addEventListener("click", () => {
    const reason = prompt("¿Deseas indicarnos el motivo por el cual no podrás asistir o qué día prefieres reprogramar?") || "Solicitud de reprogramación";
    confirmAppointment(token, "reschedule", reason);
  });
});

async function loadAppointmentInfo(token) {
  try {
    const res = await fetch(`/api/confirm-info/${token}`);
    const result = await res.json();

    if (!result.success || !result.data) {
      document.getElementById("portal-loading").innerHTML = `<p style="color: #ef4444;">No encontramos información para este enlace de confirmación.</p>`;
      return;
    }

    const { appointment, clinic } = result.data;

    // Poblar textos
    if (clinic.name) {
      document.getElementById("portal-clinic-name").textContent = clinic.name;
    }
    document.getElementById("portal-greeting").textContent = `¡Hola, ${appointment.patient_name.split(" ")[0]}!`;
    document.getElementById("portal-service-name").textContent = appointment.service_name;
    
    // Formatear fecha amigable
    const dtParts = appointment.appointment_date.split("-");
    const formattedDate = `${dtParts[2]}/${dtParts[1]}/${dtParts[0]}`;
    document.getElementById("portal-datetime").textContent = `${formattedDate} a las ${appointment.appointment_time} hrs (${appointment.duration_minutes} min)`;
    
    document.getElementById("portal-specialist").textContent = appointment.specialist || "Especialista";
    document.getElementById("portal-address").textContent = clinic.address || "Consultorio del centro";

    if (appointment.service_instructions) {
      document.getElementById("portal-instructions").textContent = appointment.service_instructions;
      document.getElementById("portal-instructions-box").style.display = "flex";
    } else {
      document.getElementById("portal-instructions-box").style.display = "none";
    }

    // Actualizar estado visual
    updateStatusUI(appointment.status, clinic.phone);

    document.getElementById("portal-loading").style.display = "none";
    document.getElementById("portal-content").style.display = "block";

  } catch (error) {
    console.error("Error cargando cita:", error);
    document.getElementById("portal-loading").innerHTML = `<p style="color: #ef4444;">Error al conectar con el servidor.</p>`;
  }
}

function updateStatusUI(status, clinicPhone) {
  const badge = document.getElementById("portal-status-badge");
  const statusText = document.getElementById("portal-status-text");
  const actions = document.getElementById("portal-actions");
  const confirmedView = document.getElementById("portal-confirmed-view");
  const rescheduleView = document.getElementById("portal-reschedule-view");

  badge.className = `status-badge status-${status.replace(/\s+/g, '.')}`;
  statusText.textContent = status;

  const phoneClean = (clinicPhone || "").replace(/[^0-9]/g, "");
  const waUrl = `https://wa.me/${phoneClean}`;

  if (status === "Confirmada") {
    actions.style.display = "none";
    confirmedView.style.display = "block";
    rescheduleView.style.display = "none";
    document.getElementById("btn-contact-whatsapp").href = waUrl;
  } else if (status === "Cancelada") {
    actions.style.display = "none";
    confirmedView.style.display = "none";
    rescheduleView.style.display = "block";
    document.getElementById("btn-reschedule-whatsapp").href = waUrl;
  } else {
    actions.style.display = "flex";
    confirmedView.style.display = "none";
    rescheduleView.style.display = "none";
  }
}

async function confirmAppointment(token, action, reason = "") {
  try {
    const res = await fetch(`/api/confirm-action/${token}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action, reason })
    });
    const result = await res.json();
    if (result.success && result.data) {
      updateStatusUI(result.data.status);
    } else {
      alert("Error al registrar la respuesta.");
    }
  } catch (error) {
    console.error("Error enviando confirmación:", error);
    alert("Error de red.");
  }
}
