#!/bin/bash
# Script para iniciar Estética Divine con Túnel Público Online (4G/5G y Wi-Fi Remoto)
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "✨ ========================================================="
echo "🌸 Estética Divine - Modo Online (Datos Móviles 4G/5G)"
echo "✨ ========================================================="
echo "📱 Iniciando servidor y generando túnel seguro HTTPS..."
echo "🌍 Podrás abrir la agenda desde cualquier celular o lugar"
echo "✨ ========================================================="

python3 server.py --online
