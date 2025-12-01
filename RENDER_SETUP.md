# 🚀 Configuración Manual en Render (Solución al Error)

Render está detectando el `package.json` en la raíz y tratando de usar Node.js. Sigue estos pasos para configurarlo manualmente:

## ⚙️ Configuración Manual en Render Dashboard

### Paso 1: Crear/Editar el Web Service

1. Ve a [dashboard.render.com](https://dashboard.render.com)
2. Si ya tienes el servicio, ve a **Settings**
3. Si no, crea uno nuevo: **New +** > **Web Service**

### Paso 2: Configuración Básica

```
Name: color-accessibility-mcp-app
Region: Oregon (o la más cercana)
Branch: main
Root Directory: (dejar VACÍO)
```

### Paso 3: Runtime y Build

**IMPORTANTE**: En la sección "Build & Deploy":

1. **Runtime**: Selecciona explícitamente **"Python 3"** (NO dejes que auto-detecte)
2. **Build Command**: 
   ```bash
   pip install -r server/requirements.txt
   ```
3. **Start Command**: 
   ```bash
   cd server && python -m uvicorn main:app --host 0.0.0.0 --port $PORT
   ```

### Paso 4: Variables de Entorno

En la sección "Environment Variables", agrega:

```
BASE_URL = (dejar vacío, Render lo generará automáticamente)
PYTHON_VERSION = 3.11.0
```

### Paso 5: Guardar y Desplegar

1. Click en **"Save Changes"** o **"Create Web Service"**
2. Render comenzará a construir con Python
3. Espera 5-10 minutos

## 🔧 Si Sigue Detectando Node.js

Si Render sigue detectando Node.js después de configurar manualmente:

1. Ve a **Settings** > **Build & Deploy**
2. Asegúrate de que **"Auto-Deploy"** esté desactivado temporalmente
3. En **"Build Command"**, fuerza Python:
   ```bash
   python3 --version && pip install -r server/requirements.txt
   ```
4. Guarda y haz un **"Manual Deploy"**

## ✅ Verificación

Una vez desplegado, verifica:

```bash
curl https://color-accessibility-mcp-app.onrender.com/
```

Deberías ver:
```json
{"message": "Color Accessibility Checker MCP Server", "status": "running"}
```

