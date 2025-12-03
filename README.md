# 🎨 Color Accessibility Checker

**Aplicación integrada con ChatGPT para analizar la accesibilidad de colores según estándares WCAG.**

Utiliza el [OpenAI Apps SDK](https://github.com/openai/openai-apps-sdk-examples) y el [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) para crear una experiencia interactiva donde ChatGPT analiza imágenes y muestra los resultados en un widget embebido.

![Status](https://img.shields.io/badge/Status-Production-success)
![Python](https://img.shields.io/badge/Python-3.10+-blue)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## 📋 Índice

- [Descripción del Proyecto](#-descripción-del-proyecto)
- [Características](#-características)
- [Arquitectura](#-arquitectura)
- [Flujo de Funcionamiento](#-flujo-de-funcionamiento)
- [Tecnologías Utilizadas](#️-tecnologías-utilizadas)
- [Instalación](#-instalación)
- [Uso](#-uso)
- [Estructura del Proyecto](#-estructura-del-proyecto)
- [API MCP](#-api-mcp)
- [Demo](#-demo)
- [Autor](#-autor)

---

## 📖 Descripción del Proyecto

**Color Accessibility Checker** es una herramienta que permite verificar si las combinaciones de colores de una interfaz cumplen con los estándares de accesibilidad WCAG (Web Content Accessibility Guidelines).

### Problema que resuelve

Muchos diseños web y aplicaciones utilizan combinaciones de colores que dificultan la lectura para personas con discapacidad visual o daltonismo. Verificar manualmente cada combinación de colores es tedioso y propenso a errores.

### Solución

Esta aplicación permite al usuario subir una captura de pantalla o imagen de diseño a ChatGPT, que automáticamente:

1. **Analiza visualmente** la imagen usando sus capacidades de visión
2. **Extrae los colores** de texto y fondo que detecta
3. **Calcula los ratios de contraste** según WCAG
4. **Muestra un widget interactivo** con los resultados
5. **Sugiere correcciones** usando el espacio de color OKLCH

---

## ✨ Características

| Característica | Descripción |
|----------------|-------------|
| 🔍 **Análisis Visual** | ChatGPT usa su visión para extraer colores de cualquier imagen |
| 📊 **Evaluación WCAG** | Verifica cumplimiento de AA y AAA para texto normal y grande |
| 💡 **Sugerencias OKLCH** | Genera alternativas de color que cumplen los estándares |
| 🎯 **Widget Interactivo** | Resultados visuales embebidos directamente en ChatGPT |
| ⚡ **Tiempo Real** | Respuesta inmediata sin necesidad de herramientas externas |

---

## 🏗 Arquitectura

```
┌─────────────────┐      ┌──────────────────┐      ┌─────────────────┐
│                 │      │                  │      │                 │
│    Usuario      │─────▶│     ChatGPT      │─────▶│   MCP Server    │
│  (sube imagen)  │      │    (Vision)      │      │   (FastAPI)     │
│                 │      │                  │      │                 │
└─────────────────┘      └──────────────────┘      └─────────────────┘
                                │                          │
                                │ Extrae colores           │ Calcula WCAG
                                │ hex (#RRGGBB)            │ + sugerencias
                                │                          │
                                ▼                          ▼
                         ┌──────────────────────────────────────┐
                         │                                      │
                         │          Widget HTML/JS              │
                         │     (embebido en ChatGPT)            │
                         │                                      │
                         └──────────────────────────────────────┘
```

### Componentes

- **Frontend**: Widget HTML/CSS/JS embebido usando `text/html+skybridge`
- **Backend**: Servidor FastAPI que implementa el protocolo MCP
- **Protocolo**: JSON-RPC 2.0 sobre HTTP (Model Context Protocol)
- **Hosting**: Render.com con auto-deploy desde GitHub

---

## 🔄 Flujo de Funcionamiento

```
1. USUARIO                    2. CHATGPT                   3. SERVIDOR
   │                             │                            │
   │  Sube imagen               │                            │
   │  "Analiza accesibilidad"   │                            │
   │ ─────────────────────────▶ │                            │
   │                             │                            │
   │                             │  Ve la imagen              │
   │                             │  Extrae colores:           │
   │                             │  - Título: #333 / #FFF     │
   │                             │  - Botón: #0066CC / #EEE   │
   │                             │                            │
   │                             │  tools/call                │
   │                             │  check_color_accessibility │
   │                             │ ─────────────────────────▶ │
   │                             │                            │
   │                             │                            │  Calcula ratios
   │                             │                            │  WCAG AA/AAA
   │                             │                            │  Genera sugerencias
   │                             │                            │
   │                             │         Widget HTML        │
   │                             │ ◀───────────────────────── │
   │                             │                            │
   │       Muestra widget        │                            │
   │ ◀───────────────────────── │                            │
   │                             │                            │
```

---

## ⚙️ Tecnologías Utilizadas

### Backend
| Tecnología | Versión | Uso |
|------------|---------|-----|
| Python | 3.10+ | Lenguaje principal |
| FastAPI | 0.115+ | Framework web / API |
| Uvicorn | 0.32+ | Servidor ASGI |
| coloraide | 1.0+ | Conversiones de color OKLCH |

### Frontend
| Tecnología | Uso |
|------------|-----|
| HTML5 | Estructura del widget |
| CSS3 | Estilos y diseño responsivo |
| JavaScript | Renderizado dinámico de datos |

### Infraestructura
| Servicio | Uso |
|----------|-----|
| Render | Hosting del servidor |
| GitHub | Control de versiones y CI/CD |

### Protocolos
| Protocolo | Uso |
|-----------|-----|
| MCP (Model Context Protocol) | Comunicación con ChatGPT |
| JSON-RPC 2.0 | Formato de mensajes |

---

## 💻 Instalación

### Requisitos Previos

- Python 3.10 o superior
- pip (gestor de paquetes Python)
- Git

### Pasos

```bash
# 1. Clonar el repositorio
git clone https://github.com/Criszoraid/color-accessibility-mcp-app.git
cd color-accessibility-mcp-app

# 2. Crear entorno virtual
python -m venv .venv

# 3. Activar entorno virtual
# En macOS/Linux:
source .venv/bin/activate
# En Windows:
.venv\Scripts\activate

# 4. Instalar dependencias
pip install -r server/requirements.txt

# 5. Ejecutar servidor
cd server
uvicorn main:app --host 0.0.0.0 --port 8000
```

El servidor estará disponible en `http://localhost:8000`

---

## 🚀 Uso

### Configurar en ChatGPT

1. Abre **ChatGPT** → **Settings** ⚙️
2. Ve a **Connectors** o **Apps**
3. Añade un nuevo conector MCP:
   ```
   Nombre: Color Accessibility
   URL: https://app-color-accessibility.onrender.com/mcp
   ```
4. Guarda y refresca

### Analizar una Imagen

1. Sube una captura de pantalla o imagen de diseño a ChatGPT
2. Escribe: **"Analiza la accesibilidad de los colores de esta imagen"**
3. ChatGPT extraerá los colores visualmente y mostrará el widget con:
   - Ratio de contraste para cada par de colores
   - Estado de cumplimiento WCAG (AA/AAA)
   - Sugerencias de mejora cuando no cumple

### Ejemplo de Conversación

```
👤 Usuario: [Sube captura de una web] 
            "Revisa si los colores de texto son accesibles"

🤖 ChatGPT: Analizando la imagen... He detectado los siguientes 
            pares de colores:
            
            [Widget interactivo mostrando:]
            ┌────────────────────────────────────┐
            │ 🎨 Color Accessibility Check       │
            │                                    │
            │ Total: 4  ✅ Passed: 2  ❌ Failed: 2│
            │                                    │
            │ ┌──────────────────────────────┐  │
            │ │ Título principal             │  │
            │ │ Aa  #333333 / #FFFFFF        │  │
            │ │ Ratio: 12.63:1 ✅             │  │
            │ │ AA ✓  AAA ✓                  │  │
            │ └──────────────────────────────┘  │
            │                                    │
            │ ┌──────────────────────────────┐  │
            │ │ Texto secundario             │  │
            │ │ Aa  #999999 / #FFFFFF        │  │
            │ │ Ratio: 2.85:1 ❌              │  │
            │ │ 💡 Sugerencias OKLCH:        │  │
            │ │    darken bg → 4.5:1         │  │
            │ └──────────────────────────────┘  │
            └────────────────────────────────────┘
```

---

## 📁 Estructura del Proyecto

```
color-accessibility-mcp-app/
│
├── server/
│   ├── main.py              # Servidor FastAPI + lógica MCP
│   └── requirements.txt     # Dependencias Python
│
├── render.yaml              # Configuración de despliegue en Render
├── README.md                # Este archivo
└── LICENSE                  # Licencia MIT
```

### Archivo Principal: `server/main.py`

| Función | Descripción |
|---------|-------------|
| `calculate_luminance()` | Calcula luminancia relativa según WCAG |
| `calculate_contrast_ratio()` | Calcula ratio de contraste entre dos colores |
| `evaluate_wcag()` | Evalúa cumplimiento de AA y AAA |
| `generate_oklch_suggestions()` | Genera sugerencias de color alternativas |
| `mcp_endpoint()` | Endpoint principal que maneja el protocolo MCP |

---

## 🔌 API MCP

### Tool: `check_color_accessibility`

Analiza pares de colores y devuelve evaluación WCAG.

**Input:**
```json
{
  "color_pairs": [
    {
      "foreground": "#333333",
      "background": "#FFFFFF",
      "element": "Título principal"
    },
    {
      "foreground": "#0066CC",
      "background": "#F5F5F5",
      "element": "Enlace de navegación"
    }
  ]
}
```

**Output:**
```json
{
  "total_pairs": 2,
  "passed_pairs": 1,
  "failed_pairs": 1,
  "color_pairs": [
    {
      "text_sample": "Título principal",
      "foreground": "#333333",
      "background": "#FFFFFF",
      "ratio": 12.63,
      "passes_aa_normal": true,
      "passes_aa_large": true,
      "passes_aaa_normal": true,
      "passes_aaa_large": true,
      "suggestions": []
    },
    {
      "text_sample": "Enlace de navegación",
      "foreground": "#0066CC",
      "background": "#F5F5F5",
      "ratio": 4.12,
      "passes_aa_normal": false,
      "passes_aa_large": true,
      "passes_aaa_normal": false,
      "passes_aaa_large": false,
      "suggestions": [
        {
          "type": "darken_bg",
          "new_contrast_ratio": 5.2,
          "preview_hex_bg": "#E0E0E0",
          "preview_hex_fg": "#0066CC"
        }
      ]
    }
  ]
}
```

---

## 🌐 Demo

**Servidor en Producción:**  
🔗 https://app-color-accessibility.onrender.com

**Endpoint MCP:**  
🔗 https://app-color-accessibility.onrender.com/mcp

**Widget de Prueba:**  
🔗 https://app-color-accessibility.onrender.com/widget

---

## 📊 Estándares WCAG

| Nivel | Texto Normal | Texto Grande |
|-------|--------------|--------------|
| **AA** | ≥ 4.5:1 | ≥ 3.0:1 |
| **AAA** | ≥ 7.0:1 | ≥ 4.5:1 |

> **Texto grande**: 18pt (24px) o 14pt (18.5px) en negrita

---

## 👤 Autor

**Cristina Sánchez**  
GitHub: [@Criszoraid](https://github.com/Criszoraid)

---

## 📄 Licencia

Este proyecto está bajo la licencia MIT. Ver [LICENSE](./LICENSE) para más detalles.

---

## 🙏 Agradecimientos

- [OpenAI](https://openai.com) - Apps SDK y documentación
- [FastAPI](https://fastapi.tiangolo.com/) - Framework web
- [Render](https://render.com) - Hosting
- [WCAG](https://www.w3.org/WAI/WCAG21/quickref/) - Estándares de accesibilidad
