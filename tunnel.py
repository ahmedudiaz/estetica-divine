"""
tunnel.py - Gestor de Enlace Público Seguro (Túnel HTTPS) para Estética Divine
Permite acceder a la aplicación desde cualquier celular con datos móviles (4G/5G) o fuera del Wi-Fi.
"""
import subprocess
import threading
import time
import re
import os
import urllib.request
from database import update_setting, get_settings

TUNNEL_PROCESS = None
CURRENT_PUBLIC_URL = None

def get_saved_public_url():
    settings = get_settings()
    return settings.get("public_url", "")

def set_public_url(url):
    global CURRENT_PUBLIC_URL
    CURRENT_PUBLIC_URL = url
    update_setting("public_url", url)

def start_ssh_tunnel(port=8000, callback=None):
    """
    Inicia un túnel SSH seguro y gratuito con localhost.run o pinggy
    No requiere instalar nada ni crear cuentas.
    """
    global TUNNEL_PROCESS

    def run_tunnel():
        global TUNNEL_PROCESS, CURRENT_PUBLIC_URL
        # Intentar con localhost.run
        cmd = [
            "ssh",
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", "ServerAliveInterval=30",
            "-R", f"80:localhost:{port}",
            "nokey@localhost.run"
        ]

        try:
            print("🌐 Iniciando túnel seguro para acceso desde datos móviles (4G/5G)...")
            TUNNEL_PROCESS = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            for line in TUNNEL_PROCESS.stdout:
                # Buscar URLs HTTPS generadas en el log
                match = re.search(r'(https://[a-zA-Z0-9\-\.]+\.lhr\.life|https://[a-zA-Z0-9\-\.]+\.localhost\.run)', line)
                if match:
                    public_url = match.group(1)
                    set_public_url(public_url)
                    print("\n" + "=" * 60)
                    print(f"🌍 ¡ENLACE PÚBLICO GLOBAL ACTIVO!")
                    print(f"📱 Abre en tu celular desde cualquier lugar: {public_url}")
                    print(f"✨ Funciona con datos móviles 4G/5G y cualquier Wi-Fi")
                    print("=" * 60 + "\n")
                    if callback:
                        callback(public_url)
                    break
        except Exception as e:
            print(f"Error iniciando túnel SSH: {e}")

    thread = threading.Thread(target=run_tunnel, daemon=True)
    thread.start()
    return thread
