# 🚀 Guía de Despliegue en Render

Esta guía te ayudará a desplegar tu aplicación SDK de OpenAI con MCP en Render.com.

## 📋 Requisitos Previos

- Cuenta en [Render.com](https://render.com) (gratis o de pago)
- Repositorio en GitHub (ya configurado: https://github.com/Criszoraid/color-accessibility-mcp-app)
- Acceso a tu cuenta de GitHub

## 🎯 Opción 1: Despliegue Automático con render.yaml (Recomendado)

Render detectará automáticamente el archivo `render.yaml` en la raíz del repositorio.

### Pasos:

1. **Inicia sesión en Render**:
   - Ve a [dashboard.render.com](https://dashboard.render.com)
   - Inicia sesión con tu cuenta de GitHub

2. **Crear un nuevo Web Service**:
   - Click en **"New +"** > **"Web Service"**
   - Conecta tu repositorio de GitHub
   - Selecciona: `Criszoraid/color-accessibility-mcp-app`
   - Render detectará automáticamente el `render.yaml`

3. **Configuración Automática**:
   - **Name**: `color-accessibility-mcp-app` (o el que prefieras)
   - **Region**: Oregon (o la más cercana a ti)
   - **Branch**: `main`
   - **Root Directory**: (dejar vacío, usa la raíz)
   - Render usará automáticamente:
     - Build Command del `render.yaml`
     - Start Command del `render.yaml`
     - Variables de entorno del `render.yaml`

4. **Variables de Entorno**:
   - `BASE_URL`: Se generará automáticamente (ej: `https://color-accessibility-mcp-app.onrender.com`)
   - Puedes agregar más si es necesario:
     - `OPENAI_API_KEY` (si tu app lo requiere)
     - `ENVIRONMENT=production`

5. **Click en "Create Web Service"**:
   - Render comenzará a construir y desplegar tu aplicación
   - El proceso tomará 5-10 minutos la primera vez

6. **Verificar el Despliegue**:
   - Ve a la pestaña **"Logs"** para ver el progreso
   - Cuando termine, verás: `✅ Build successful`
   - Tu app estará disponible en: `https://color-accessibility-mcp-app.onrender.com`

## 🎯 Opción 2: Configuración Manual

Si prefieres configurar manualmente sin usar `render.yaml`:

### Pasos:

1. **Crear Web Service**:
   - **New +** > **Web Service**
   - Conecta tu repositorio de GitHub
   - Selecciona: `Criszoraid/color-accessibility-mcp-app`

2. **Configuración Manual**:
   ```
   Name: color-accessibility-mcp-app
   Region: Oregon (o la más cercana)
   Branch: main
   Root Directory: (vacío)
   Runtime: Python 3
   Build Command: 
     if [ -f "web/package.json" ]; then cd web && npm ci && npm run build && cd ..; fi && pip install -r server/requirements.txt
   Start Command: 
     cd server && uvicorn main:app --host 0.0.0.0 --port $PORT
   ```

3. **Variables de Entorno**:
   - Click en **"Environment"**
   - Agrega:
     ```
     BASE_URL=https://color-accessibility-mcp-app.onrender.com
     PYTHON_VERSION=3.11.0
     PORT=10000
     ```

4. **Plan**:
   - **Free**: Gratis, pero se "duerme" después de 15 minutos de inactividad
   - **Starter ($7/mes)**: Siempre activo, mejor para producción

5. **Click en "Create Web Service"**

## ⚙️ Configuración Avanzada

### Health Check

Render verificará automáticamente que tu app esté funcionando en:
- `GET /` - Debe retornar un status 200

Tu servidor ya tiene este endpoint configurado en `server/main.py`.

### Auto-Deploy

Con `autoDeploy: true` en `render.yaml`, cada push a `main` desplegará automáticamente.

Para desactivar:
- Ve a **Settings** > **Auto-Deploy**
- Desactiva "Auto-Deploy"

### Logs y Monitoreo

- **Logs en tiempo real**: Pestaña "Logs" en el dashboard
- **Métricas**: Pestaña "Metrics" (solo en planes de pago)
- **Notificaciones**: Configura alertas en Settings > Notifications

## 🔧 Troubleshooting

### Problema: Build falla

**Error común**: `npm: command not found`

**Solución**: Render necesita Node.js instalado. Agrega al inicio del buildCommand:
```yaml
buildCommand: |
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
  apt-get install -y nodejs && \
  cd web && npm ci && npm run build && cd .. && \
  pip install -r server/requirements.txt
```

O mejor aún, usa un buildpack de Node.js primero.

### Problema: Frontend no se construye

**Causa**: No existe `web/package.json`

**Solución**: El buildCommand ya maneja esto con una verificación condicional. Si necesitas el frontend:
1. Asegúrate de que `web/package.json` exista
2. O construye el frontend localmente y sube `web/dist/` al repositorio

### Problema: App se "duerme" (plan free)

**Solución**:
1. Upgrade a plan Starter ($7/mes) para mantenerla siempre activa
2. O usa un servicio de "ping" como [UptimeRobot](https://uptimerobot.com) para mantenerla despierta

### Problema: Puerto incorrecto

**Error**: `Address already in use`

**Solución**: Render usa la variable `$PORT` automáticamente. Asegúrate de que tu `startCommand` use `$PORT`:
```yaml
startCommand: cd server && uvicorn main:app --host 0.0.0.0 --port $PORT
```

### Problema: CORS errors

**Solución**: Tu `server/main.py` ya tiene CORS configurado con `allow_origins=["*"]`. Si necesitas restringir:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://tu-dominio.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 📊 Verificar el Despliegue

### 1. Health Check

```bash
curl https://color-accessibility-mcp-app.onrender.com/
```

Deberías ver:
```json
{"message": "Color Accessibility Checker MCP Server", "status": "running"}
```

### 2. Endpoint MCP

```bash
curl -X POST https://color-accessibility-mcp-app.onrender.com/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}'
```

### 3. Widget HTML

Abre en el navegador:
```
https://color-accessibility-mcp-app.onrender.com/widget
```

## 🔗 Integración con ChatGPT

Una vez desplegado, configura el connector en ChatGPT:

1. Abre **ChatGPT** → **Settings** ⚙️
2. Ve a **Connectors** o **MCP Settings**
3. Click en **Add Connector** ➕
4. Configura:
   ```
   Name: Color Accessibility Checker
   Type: MCP
   URL: https://color-accessibility-mcp-app.onrender.com/mcp
   ```
5. Click en **Save** y luego **Refresh** ↻

## 💰 Planes y Precios

### Free Plan
- ✅ Gratis
- ✅ 750 horas/mes
- ⚠️ Se "duerme" después de 15 min de inactividad
- ⚠️ Builds más lentos

### Starter Plan ($7/mes)
- ✅ Siempre activo
- ✅ Builds más rápidos
- ✅ Mejor para producción
- ✅ Soporte prioritario

### Pro Plan ($25/mes)
- ✅ Todo lo anterior
- ✅ Más recursos
- ✅ Métricas avanzadas

## 📚 Recursos Adicionales

- [Render Documentation](https://render.com/docs)
- [Python on Render](https://render.com/docs/python)
- [Environment Variables](https://render.com/docs/environment-variables)
- [Custom Domains](https://render.com/docs/custom-domains)

## ✅ Checklist de Despliegue

- [ ] Cuenta de Render creada
- [ ] Repositorio conectado a Render
- [ ] Web Service creado
- [ ] Variables de entorno configuradas
- [ ] Build exitoso
- [ ] Health check pasando
- [ ] Endpoint MCP funcionando
- [ ] Connector configurado en ChatGPT
- [ ] Dominio personalizado (opcional)

---

¿Necesitas ayuda? Revisa los logs en Render o abre un issue en el repositorio.

