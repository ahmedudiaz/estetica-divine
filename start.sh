#!/bin/bash
# Script para iniciar el servidor de GlowAura Estética
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "✨ ==================================================="
echo "🌸 Iniciando Estética Divine - Sistema de Agenda"
echo "✨ ==================================================="
echo "🔗 Abrir en navegador: http://localhost:8000"
echo "📱 Portal de confirmación para pacientes activo"
echo "📲 Módulo de recordatorios de WhatsApp 24h listo"
echo "✨ ==================================================="

python3 server.py
