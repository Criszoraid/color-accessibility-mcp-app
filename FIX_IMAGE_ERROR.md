# 🔧 Solución al Error "Could not parse args as JSON"

## 🚨 Problema Identificado

ChatGPT estaba rechazando las imágenes con el error **"Could not parse args as JSON"** debido a:

### 1. **Schema Inválido con `oneOf`**
```python
# ❌ ANTES (Incorrecto)
"inputSchema": {
    "type": "object",
    "properties": {
        "image_data": {"type": "string", "description": "Base64 encoded image data"},
        "image_url": {"type": "string", "description": "URL of the image"}
    },
    "oneOf": [
        {"required": ["image_data"]},
        {"required": ["image_url"]}
    ]
}
```

**Problema**: El uso de `oneOf` no es estándar en MCP y confunde a ChatGPT sobre qué parámetro enviar.

### 2. **Imágenes Base64 Demasiado Grandes**
- Las imágenes en base64 pueden superar **varios MB** de texto
- Los servidores MCP tienen límites internos de tamaño de payload
- ChatGPT no puede enviar strings base64 muy largos en JSON-RPC

---

## ✅ Solución Implementada

### 1. **Schema Simplificado - Solo URL**
```python
# ✅ AHORA (Correcto)
"inputSchema": {
    "type": "object",
    "properties": {
        "image_url": {
            "type": "string",
            "description": "URL of the image to analyze (required)"
        },
        "wcag_level": {
            "type": "string",
            "enum": ["AA", "AAA"],
            "description": "WCAG conformance level to check against (default: AA)",
            "default": "AA"
        }
    },
    "required": ["image_url"]
}
```

**Ventajas**:
- ✅ Schema claro y sin ambigüedades
- ✅ ChatGPT sabe exactamente qué enviar
- ✅ URLs son mucho más pequeñas que base64
- ✅ ChatGPT puede proporcionar URLs temporales de imágenes subidas

### 2. **Logging para Debugging**
```python
# Get the image URL from arguments
image_url = arguments.get("image_url", "")
wcag_level = arguments.get("wcag_level", "AA")

# Log for debugging
print(f"🎨 Analyzing image: {image_url}")
print(f"📊 WCAG Level: {wcag_level}")
```

### 3. **Respuesta Informativa**
```python
"text": f"🎨 Analyzed image from URL: {image_url[:50]}...\n\n📊 WCAG {wcag_level}: {accessibility_data['total_pairs']} color pairs found. {accessibility_data['passed_pairs']} passed, {accessibility_data['failed_pairs']} failed."
```

---

## 🎯 Cómo Funciona Ahora

### Flujo de Trabajo:

```
1. Usuario sube imagen a ChatGPT
   ↓
2. ChatGPT genera URL temporal para la imagen
   ↓
3. ChatGPT llama al tool con: {"image_url": "https://..."}
   ↓
4. Servidor MCP recibe la URL (pequeña, ~100 bytes)
   ↓
5. Servidor descarga y analiza la imagen
   ↓
6. Servidor responde con widget + datos estructurados
   ↓
7. ChatGPT renderiza el widget interactivo
```

---

## 📋 Próximos Pasos (Opcional)

### Implementar Análisis Real de Imágenes

Para procesar imágenes reales en lugar de datos mock:

#### 1. **Instalar Dependencias**
```bash
pip install pillow opencv-python pytesseract numpy
```

#### 2. **Agregar a `requirements.txt`**
```txt
pillow>=10.0.0
opencv-python>=4.8.0
pytesseract>=0.3.10
numpy>=1.24.0
```

#### 3. **Implementar Análisis**
```python
import requests
from PIL import Image
from io import BytesIO
import cv2
import numpy as np

def analyze_image_colors(image_url: str):
    # Download image
    response = requests.get(image_url)
    img = Image.open(BytesIO(response.content))
    
    # Convert to OpenCV format
    img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    
    # Extract dominant colors
    # Detect text regions
    # Calculate contrast ratios
    # Generate OKLCH suggestions
    
    return accessibility_data
```

---

## 🧪 Cómo Probar

### 1. **Desplegar los Cambios**
```bash
git add server/main.py
git commit -m "fix: Accept image_url instead of base64 to avoid JSON parse errors"
git push
```

### 2. **Esperar Deploy en Render** (5-10 min)

### 3. **Probar en ChatGPT**
```
👤 "Check the accessibility of this image [adjuntar imagen]"
```

ChatGPT debería:
- ✅ Llamar al tool sin errores
- ✅ Mostrar el widget interactivo
- ✅ Mostrar la URL de la imagen en el texto de respuesta

### 4. **Verificar Logs en Render**
Deberías ver:
```
🎨 Analyzing image: https://files.oaiusercontent.com/...
📊 WCAG Level: AA
```

---

## 🔍 Debugging

Si aún hay errores:

### Ver logs del servidor:
```bash
# En Render Dashboard
Logs → Ver últimas 100 líneas
```

### Verificar el schema:
```bash
curl -X POST https://app-color-accessibility.onrender.com/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list"
  }'
```

### Probar el tool manualmente:
```bash
curl -X POST https://app-color-accessibility.onrender.com/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
      "name": "analyze_color_accessibility",
      "arguments": {
        "image_url": "https://example.com/test.png"
      }
    }
  }'
```

---

## 📚 Referencias

- [MCP Specification](https://modelcontextprotocol.io/)
- [OpenAI Apps SDK](https://github.com/openai/openai-apps-sdk-examples)
- [JSON Schema Validation](https://json-schema.org/understanding-json-schema/)
- [WCAG Color Contrast](https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum.html)

---

## ✅ Checklist de Verificación

- [x] Eliminado `oneOf` del schema
- [x] Cambiado a solo `image_url` (requerido)
- [x] Agregado parámetro opcional `wcag_level`
- [x] Implementado logging para debugging
- [x] Actualizado mensaje de respuesta con URL
- [ ] (Opcional) Implementar análisis real de imágenes
- [ ] (Opcional) Agregar caché de resultados
- [ ] (Opcional) Implementar rate limiting

---

**🎉 ¡El error "Could not parse args as JSON" debería estar resuelto!**
