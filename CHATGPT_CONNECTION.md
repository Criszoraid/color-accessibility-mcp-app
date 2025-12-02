# 🔗 Guía de Conexión con ChatGPT

## ✅ Verificación del Servidor

Tu servidor está funcionando correctamente:

- ✅ **Health Check**: https://color-accessibility-mcp-app.onrender.com/
- ✅ **Endpoint MCP**: https://color-accessibility-mcp-app.onrender.com/mcp
- ✅ **Widget**: https://color-accessibility-mcp-app.onrender.com/widget

## 🔧 Configuración en ChatGPT

### Paso 1: URL Correcta

La URL que debes usar en ChatGPT es:
```
https://color-accessibility-mcp-app.onrender.com/mcp
```

**IMPORTANTE**: Debe terminar en `/mcp`, no solo la raíz del dominio.

### Paso 2: Configuración del Conector

1. Abre ChatGPT
2. Ve a **Settings** ⚙️ > **Connectors** o **MCP Settings**
3. Click en **"Add Connector"** ➕ o **"Nuevo conector"**
4. Configura:
   ```
   Nombre: Color Accessibility Checker
   Descripción: Revisa la accesibilidad del color en imágenes
   URL del servidor MCP: https://color-accessibility-mcp-app.onrender.com/mcp
   Autenticación: Sin autenticación
   ```
5. Acepta la advertencia de seguridad
6. Click en **"Crear"** o **"Create"**

## 🐛 Troubleshooting

### Error: "Error al crear el conector"

**Posibles causas:**

1. **URL incorrecta**: Asegúrate de que termine en `/mcp`
   - ❌ Incorrecto: `https://color-accessibility-mcp-app.onrender.com`
   - ✅ Correcto: `https://color-accessibility-mcp-app.onrender.com/mcp`

2. **Servidor inactivo**: Si estás en plan free de Render, el servidor puede estar "dormido"
   - Solución: Haz una petición primero para "despertarlo":
     ```bash
     curl https://color-accessibility-mcp-app.onrender.com/
     ```
   - Espera 30-60 segundos y luego intenta crear el conector

3. **CORS o SSL**: Verifica que el servidor responda correctamente:
   ```bash
   curl -X POST https://color-accessibility-mcp-app.onrender.com/mcp \
     -H "Content-Type: application/json" \
     -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}'
   ```

4. **Timeout**: Render free puede tener timeouts largos
   - Solución: Upgrade a plan Starter ($7/mes) para mejor rendimiento

### Error: "unhandled errors in a TaskGroup"

Este error generalmente significa que:
- El servidor no responde en el tiempo esperado
- Hay un problema de conectividad
- El endpoint no está accesible

**Solución:**
1. Verifica que el servidor esté activo
2. Prueba la URL en el navegador o con curl
3. Revisa los logs en Render para ver si hay errores

## ✅ Verificación Paso a Paso

### 1. Verificar que el servidor está activo

```bash
curl https://color-accessibility-mcp-app.onrender.com/
```

Deberías ver:
```json
{"message": "Color Accessibility Checker MCP Server", "status": "running"}
```

### 2. Verificar el endpoint MCP

```bash
curl -X POST https://color-accessibility-mcp-app.onrender.com/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}'
```

Deberías ver:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "2024-11-05",
    "capabilities": {...},
    "serverInfo": {...}
  }
}
```

### 3. Verificar tools/list

```bash
curl -X POST https://color-accessibility-mcp-app.onrender.com/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
```

Deberías ver la lista de tools disponibles.

## 📋 Checklist de Configuración

- [ ] Servidor desplegado en Render
- [ ] Health check responde correctamente
- [ ] Endpoint `/mcp` responde a `initialize`
- [ ] Endpoint `/mcp` responde a `tools/list`
- [ ] URL en ChatGPT termina en `/mcp`
- [ ] Sin autenticación configurada (o la correcta si es necesaria)
- [ ] Advertencia de seguridad aceptada
- [ ] Conector creado exitosamente

## 🔄 Si el Servidor está "Dormido" (Plan Free)

Si estás en plan free de Render, el servidor se "duerme" después de 15 minutos de inactividad.

**Solución rápida:**
1. Haz una petición para despertarlo:
   ```bash
   curl https://color-accessibility-mcp-app.onrender.com/
   ```
2. Espera 30-60 segundos
3. Intenta crear el conector nuevamente

**Solución permanente:**
- Upgrade a plan Starter ($7/mes) para mantener el servidor siempre activo

## 📞 Soporte

Si después de seguir estos pasos aún tienes problemas:
1. Revisa los logs en Render Dashboard
2. Verifica que el servidor esté activo
3. Prueba los endpoints con curl
4. Asegúrate de usar la URL correcta con `/mcp` al final


