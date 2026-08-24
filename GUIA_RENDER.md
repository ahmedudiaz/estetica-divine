# 🚀 Guía Paso a Paso: Desplegar Estética Divine en Render.com (Gratis 24/7)

Sigue estos sencillos pasos para tener tu aplicación funcionando en internet las 24 horas del día, accesible desde tu celular en cualquier lugar (con datos móviles 4G/5G) y con tu computadora apagada.

---

## 📋 Paso 1: Subir los Archivos a GitHub (2 minutos)

1. Ingresa a [github.com](https://github.com) e inicia sesión (o crea una cuenta gratuita si no tienes una).
2. Haz clic en el botón verde **"New"** (o ve a [github.com/new](https://github.com/new)).
3. En **Repository name**, escribe: `estetica-divine`.
4. Deja la opción **Public** seleccionada y haz clic en **"Create repository"**.
5. En la página siguiente, verás un texto que dice: *"or create a new repository on the command line... or **uploading an existing file**"*.
6. Haz clic en el enlace azul **"uploading an existing file"** (subir archivos).
7. Abre tu Finder en Mac, entra a la carpeta:
   `/Users/ahmediaz/.gemini/antigravity/scratch/estetica-agenda`
8. Selecciona todos los archivos y carpetas (`server.py`, `database.py`, `scheduler.py`, `Procfile`, `static/`, etc.) y **arrástralos a la ventana de GitHub**.
9. En la parte inferior, presiona el botón verde **"Commit changes"**.

---

## 🌐 Paso 2: Conectar y Desplegar en Render.com (1 minuto)

1. Ve a [render.com](https://render.com) e inicia sesión con tu cuenta de GitHub (clic en **"Sign in with GitHub"**).
2. En el panel principal de Render, haz clic en el botón superior **"+ New"** y elige **"Web Service"**.
3. Selecciona la opción **"Build and deploy from a Git repository"** y haz clic en **Next**.
4. Busca y selecciona tu repositorio `estetica-divine` (clic en **Connect**).
5. Configura los siguientes campos:
   - **Name**: `estetica-divine`
   - **Region**: Elige la más cercana (ej. *Oregon* o *Frankfurt*)
   - **Language**: `Python 3`
   - **Build Command**: *(Déjalo vacío o escribe `echo ok`)*
   - **Start Command**: `python3 server.py`
   - **Instance Type / Plan**: Selecciona **Free** ($0 / mes)
6. Haz clic en el botón inferior **"Create Web Service"** (o *Deploy*).

---

## 🎉 Paso 3: ¡Tu App está Online 24/7!

1. Render tardará unos 30 a 60 segundos en iniciar tu servidor.
2. En la parte superior verás tu enlace público seguro con candado HTTPS, por ejemplo:
   👉 **`https://estetica-divine.onrender.com`**
3. **Abre ese enlace en tu celular**:
   - Funciona desde cualquier lugar (4G/5G, Wi-Fi del centro o tu casa).
   - Puedes instalarla como App en tu iPhone (Safari -> Compartir -> *Añadir a pantalla de inicio*) o Android (Chrome -> *Instalar aplicación*).
   - Los recordatorios de WhatsApp automáticos usarán este enlace para que tus pacientes confirmen sus citas con 1 toque.
