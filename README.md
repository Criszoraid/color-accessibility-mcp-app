# 🚀 GPT Apps SDK - Task Manager

**Aplicación de accesibilidad color integrada con ChatGPT** usando el [OpenAI Apps SDK](https://github.com/openai/openai-apps-sdk-examples) y el [Model Context Protocol (MCP)](https://modelcontextprotocol.io/).

Este proyecto demuestra cómo crear una aplicación completa que se integra directamente en ChatGPT, mostrando widgets interactivos de React que se actualizan dinámicamente cuando ChatGPT realiza acciones.

![Demo](https://img.shields.io/badge/Status-Production-success)
![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Node](https://img.shields.io/badge/Node-18+-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## 📋 Tabla de Contenidos

- [Características](#-características)
- [¿Cómo Funciona?](#-cómo-funciona)
- [Demo en Vivo](#-demo-en-vivo)
- [Requisitos](#-requisitos)
- [Instalación Local](#-instalación-local)
- [Desarrollo Local](#️-desarrollo-local)
- [Despliegue en GitHub](#-despliegue-en-github)
- [Despliegue en Render](#-despliegue-en-render)
- [Integración con ChatGPT](#-integración-con-chatgpt)
- [Estructura del Proyecto](#-estructura-del-proyecto)
- [Comandos Disponibles](#-comandos-disponibles)
- [Cómo Funciona el Widget](#-cómo-funciona-el-widget)
- [Tecnologías Utilizadas](#️-tecnologías-utilizadas)
- [Documentación Adicional](#-documentación-adicional)
- [Licencia](#-licencia)

---

## ✨ Características

- ✅ **Widget Interactivo de React** con [OpenAI Apps SDK UI](https://github.com/openai/apps-sdk-ui)
- ✅ **Servidor MCP** en Python/FastAPI que expone herramientas a ChatGPT
- ✅ **Actualización Dinámica** - El widget se actualiza cuando ChatGPT crea/completa tareas
- ✅ **Diseño Moderno** con Tailwind CSS 4 y componentes accesibles
- ✅ **Desplegado en Render** - Listo para usar en producción
- ✅ **JSON-RPC 2.0** - Protocolo MCP estándar
- ✅ **Recursos HTML** - Widgets embebidos con `text/html+skybridge`

---

## 🎯 ¿Cómo Funciona?

```
┌─────────────┐         ┌──────────────┐         ┌─────────────────┐
│   ChatGPT   │────────>│  MCP Server  │────────>│  React Widget   │
│             │<────────│  (FastAPI)   │<────────│  (Tailwind UI)  │
└─────────────┘         └──────────────┘         └─────────────────┘
    Usuario                 Python                    HTML/JS/CSS
                         JSON-RPC 2.0              Apps SDK UI
```

1. **Usuario pregunta** a ChatGPT: *"Check the accessibility of this image [adjuntar imagen]"*
2. **ChatGPT llama** al servidor MCP usando JSON-RPC 2.0
3. **Servidor responde** con datos estructurados + HTML del widget
4. **ChatGPT renderiza** el widget React directamente en la conversación
5. **Usuario interactúa** con el widget (revisa accesibilidad, etc.)
6. **Widget se actualiza** dinámicamente cuando ChatGPT crea nuevas tareas

---

## 🌐 Demo en Vivo

**Servidor en Producción:**  
🔗 [https://app-color-accessibility.onrender.com](https://app-color-accessibility.onrender.com)

**Endpoint MCP:**  
🔗 [https://app-color-accessibility.onrender.com/mcp](https://app-color-accessibility.onrender.com/mcp)

**Widget de Prueba:**  
🔗 [https://app-color-accessibility.onrender.com/widget](https://app-color-accessibility.onrender.com/widget)

---

## 📋 Requisitos

- **Node.js** 18+ ([Descargar](https://nodejs.org/))
- **Python** 3.10+ ([Descargar](https://www.python.org/))
- **npm** (incluido con Node.js)
- **Git** (opcional, para clonar el repositorio)

---

## 💻 Instalación Local

### 1️⃣ Clonar el Repositorio

```bash
git clone https://github.com/Criszoraid/app-color-accessibility.git
cd app-color-accessibility
```

### 2️⃣ Instalar Dependencias de Node.js

```bash
npm install
```

### 3️⃣ Crear Entorno Virtual de Python

**macOS/Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows:**
```bash
python -m venv .venv
.venv\Scripts\activate
```

### 4️⃣ Instalar Dependencias de Python

```bash
pip install -r server_python/requirements.txt
```

---

## 🛠️ Desarrollo Local

### Opción A: Script Automático (Recomendado)

**macOS/Linux:**
```bash
chmod +x start-dev.sh
./start-dev.sh
```

**Windows:**
```powershell
.\start-dev.ps1
```

Esto inicia automáticamente:
- ✅ Servidor de assets estáticos (puerto 4444)
- ✅ Servidor MCP Python/FastAPI (puerto 8000)

### Opción B: Paso a Paso

#### 1. Compilar el Widget

```bash
npm run build
```

#### 2. Servir Assets Estáticos

En una terminal:
```bash
npm run serve
```

#### 3. Iniciar Servidor MCP

En otra terminal:
```bash
source .venv/bin/activate  # Windows: .venv\Scripts\activate
npm run server:python
```

### Acceso Local

- **Servidor MCP:** http://localhost:8000
- **MCP Endpoint:** http://localhost:8000/mcp
- **Widget de Prueba:** http://localhost:8000/widget
- **Assets:** http://localhost:4444

---

## 🚀 Despliegue en GitHub

Esta aplicación está configurada para ser desplegada en servidores externos usando GitHub Actions y workflows automatizados.

### 📋 Características de Despliegue

- ✅ **CI/CD Automático** con GitHub Actions
- ✅ **Build y Test** en cada push
- ✅ **Paquetes de Despliegue** generados automáticamente
- ✅ **GitHub Pages** para frontend estático (opcional)
- ✅ **Releases Automáticos** con tags

### 🎯 Opción 1: Despliegue Automático con GitHub Actions

1. **Configurar el Repositorio**:
   ```bash
   git init
   git remote add origin https://github.com/TU_USUARIO/TU_REPOSITORIO.git
   git add .
   git commit -m "Initial commit: OpenAI SDK MCP App"
   git push -u origin main
   ```

2. **Configurar Secrets** (Settings > Secrets and variables > Actions):
   - `BASE_URL`: URL de tu aplicación
   - `SERVER_HOST`: IP o dominio del servidor
   - `SERVER_USER`: Usuario SSH
   - `SSH_PRIVATE_KEY`: Clave privada SSH

3. **Workflows Incluidos**:
   - **`.github/workflows/ci.yml`**: Tests y build automático
   - **`.github/workflows/deploy.yml`**: Despliegue a GitHub Pages
   - **`.github/workflows/release.yml`**: Crear releases con tags

4. **Descargar Artefacto de Despliegue**:
   - Ve a **Actions** en tu repositorio
   - Selecciona el workflow ejecutado
   - Descarga el artefacto `deployment-package`

### 🎯 Opción 2: Script de Despliegue Manual

Usa el script incluido `deploy.sh`:

```bash
# Hacer ejecutable
chmod +x deploy.sh

# Ejecutar (crea un paquete de despliegue)
./deploy.sh

# O con parámetros personalizados
./deploy.sh usuario@servidor.com /var/www/app
```

El script creará un `deploy.tar.gz` listo para subir a tu servidor.

### 🎯 Opción 3: GitHub Pages (Frontend)

Para desplegar solo el frontend:

1. Ve a **Settings > Pages** en tu repositorio
2. Source: **GitHub Actions**
3. El workflow `.github/workflows/deploy.yml` se ejecutará automáticamente
4. Tu app estará en: `https://TU_USUARIO.github.io/TU_REPOSITORIO`

**Nota**: El backend MCP debe estar en otro servidor.

### 📚 Documentación Completa

Para instrucciones detalladas, consulta **[DEPLOY.md](./DEPLOY.md)** que incluye:
- Configuración paso a paso
- Múltiples opciones de despliegue
- Configuración de servidor
- Troubleshooting
- Monitoreo y logs

---

## 🚀 Despliegue en Render

### Opción 1: Desde GitHub (Recomendado)

1. **Fork este repositorio** en tu cuenta de GitHub
2. Ve a [Render.com](https://render.com) y crea una cuenta
3. Crea un nuevo **Web Service**
4. Conecta tu repositorio de GitHub
5. Configura:
   - **Build Command:** `npm install && npm run build && pip install -r server_python/requirements.txt`
   - **Start Command:** `cd server_python && uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Environment:** Python 3
6. Añade variable de entorno:
   - `BASE_URL` = `https://tu-app.onrender.com`
7. Click en **Deploy**

### Opción 2: Usando `render.yaml`

El proyecto incluye un archivo `render.yaml` preconfigurado:

```bash
git push origin main
# Render detectará automáticamente render.yaml
```

---

## 🔗 Integración con ChatGPT

### Configurar el Connector

1. Abre **ChatGPT** → **Settings** ⚙️
2. Ve a **Connectors** o **MCP Settings**
3. Click en **Add Connector** ➕
4. Configura:
   ```
   Name: Tareas
   Type: MCP
   URL: https://app-color-accessibility.onrender.com/mcp
   ```
5. Click en **Save** y luego **Refresh** ↻

### Usar la Aplicación

Inicia una nueva conversación y prueba:

```
👤 "Check the accessibility of this image [adjuntar imagen]"
```

ChatGPT mostrará el widget interactivo con la accesibilidad.

```
👤 "Analyze all color combinations in this app screenshot"
```

El widget se actualizará automáticamente con la sugerencia en color OKLCH.



---

## 📁 Estructura del Proyecto

```
app-GPT/
├── src/
│   └── app-color-accessibility /              # Widget de React
│       ├── index.html             # HTML base del widget
│       ├── main.tsx               # Entry point React
│       ├── App.tsx                # Componente principal con estado
│       └── main.css               # Estilos Tailwind
│
├── server_python/                 # Servidor MCP
│   ├── main.py                    # FastAPI app + MCP protocol
│   └── requirements.txt           # Dependencias Python
│
├── dist/                          # Assets compilados (generado)
│   ├── src/app-color-accessibility/
│   │   └── index.html
│   └── assets/
│       ├── app-color-accessibility-*.js
│       └── app-color-accessibility-*.css
│
├── package.json                   # Dependencias Node.js
├── vite.config.ts                 # Configuración Vite
├── postcss.config.mjs             # Configuración PostCSS/Tailwind
├── render.yaml                    # Configuración Render
├── start-dev.sh                   # Script dev macOS/Linux
├── start-dev.ps1                  # Script dev Windows
│
├── QUICKSTART.md                  # Guía rápida
├── TUTORIAL.md                    # Tutorial completo
├── PROJECT_STRUCTURE.md           # Estructura detallada
├── DEPLOY_RENDER.md               # Guía de despliegue
├── RENDER.md                      # Configuración Render
└── README.md                      # Este archivo
```

---

## 📦 Comandos Disponibles

### Node.js / Frontend

```bash
npm run build          # Compilar widget React
npm run serve          # Servir assets en localhost:4444
npm run dev            # Watch mode (Vite)
```

### Python / Backend

```bash
npm run server:python  # Iniciar servidor MCP (puerto 8000)
```

### Desarrollo

```bash
./start-dev.sh         # Iniciar todo (macOS/Linux)
.\start-dev.ps1        # Iniciar todo (Windows)
```

### Git

```bash
git add -A
git commit -m "mensaje"
git push                # Despliega automáticamente en Render
```

---

## 🎨 Cómo Funciona el Widget

### 1. Estructura HTML

El widget se embebe en ChatGPT usando el MIME type `text/html+skybridge`:

```python
# server_python/main.py
{
    "uri": "ui://widget/app-color-accessibility.html",
    "mimeType": "text/html+skybridge",
    "text": "<html>...</html>"
}
```

### 2. Estado Dinámico en React

```typescript
// src/app-color-accessibility/App.tsx
const [tasks, setTasks] = useState(() => {
  return window.openai?.toolOutput?.tasks || defaultTasks;
});

// Escuchar eventos de ChatGPT
useEffect(() => {
  const handleSetGlobals = (event: any) => {
    if (event.detail?.globals?.toolOutput?.tasks) {
      setTasks(event.detail.globals.toolOutput.tasks);
    }
  };
  
  window.addEventListener("openai:set_globals", handleSetGlobals);
  return () => window.removeEventListener("openai:set_globals", handleSetGlobals);
}, []);
```

### 3. Interacción con MCP Tools

```typescript
// Usuario hace click en adjuntar imagen
const handleToggleTask = async (taskId: string) => {
  // Actualización optimista
  setTasks(prev => prev.map(task => 
    task.id === taskId ? { ...task, completed: !task.completed } : task
  ));
  
  // Llamar al MCP tool
  if (window.openai?.callTool) {
    const response = await window.openai.callTool("update_task_status", {
      task_id: taskId,
      completed: true
    });
  }
};
```

### 4. Protocolo MCP (JSON-RPC 2.0)

```json
// ChatGPT → Servidor
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "get_tasks",
    "arguments": {}
  }
}

// Servidor → ChatGPT
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "📋 Tienes 3 tareas"
      },
      {
        "type": "resource",
        "resource": {
          "uri": "ui://widget/task-manager.html",
          "mimeType": "text/html+skybridge",
          "text": "<html>...</html>"
        }
      }
    ],
    "structuredContent": {
      "tasks": [...],
      "_meta": {
        "openai/outputTemplate": {
          "type": "resource",
          "resource": "ui://widget/task-manager.html"
        }
      }
    }
  }
}
```

---

## ⚙️ Tecnologías Utilizadas

### Frontend
- **React 18+** - Librería UI
- **TypeScript** - Type safety
- **Vite** - Build tool ultra-rápido
- **Tailwind CSS 4** - Utility-first CSS
- **@openai/apps-sdk-ui** - Design system de OpenAI

### Backend
- **Python 3.10+** - Lenguaje
- **FastAPI** - Framework web moderno
- **Uvicorn** - Servidor ASGI
- **Pydantic** - Validación de datos

### Infraestructura
- **Render** - Cloud hosting
- **GitHub** - Version control
- **ngrok** - Tunneling (desarrollo local)

### Protocolos
- **MCP** - Model Context Protocol
- **JSON-RPC 2.0** - Comunicación ChatGPT ↔ Servidor

---


### Enlaces Externos

- 📖 [OpenAI Apps SDK Examples](https://github.com/openai/openai-apps-sdk-examples)
- 🎨 [Apps SDK UI Documentation](https://github.com/openai/apps-sdk-ui)
- 🔗 [Model Context Protocol](https://modelcontextprotocol.io/)
- ⚡ [FastAPI Documentation](https://fastapi.tiangolo.com/)
- 🎯 [Vite Documentation](https://vitejs.dev/)

---

## 🤝 Contribuir

¡Las contribuciones son bienvenidas! Por favor:

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/amazing-feature`)
3. Commit tus cambios (`git commit -m 'Add amazing feature'`)
4. Push a la rama (`git push origin feature/amazing-feature`)
5. Abre un Pull Request

---

## 🐛 Reportar Issues

Si encuentras algún problema, por favor [abre un issue](https://github.com/Criszoraid/app-color-accessibility/issues) con:
- Descripción del problema
- Pasos para reproducir
- Comportamiento esperado vs actual
- Screenshots (si aplica)

---

## 📄 Licencia

Este proyecto está bajo la licencia MIT. Ver el archivo [LICENSE](./LICENSE) para más detalles.

---

## 👤 Autor

**Cristina Sánchez**  
- GitHub: [@Criszoraid](https://github.com/Criszoraid)

---

## 🙏 Agradecimientos

- [OpenAI](https://openai.com) por el Apps SDK y la documentación
- [FastAPI](https://fastapi.tiangolo.com/) por el framework web
- [Render](https://render.com) por el hosting gratuito
- La comunidad de desarrolladores MCP

---

**⭐ Si te gusta este proyecto, dale una estrella en GitHub!**

