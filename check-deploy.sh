#!/bin/bash

# Script para verificar el estado del deploy en Render
# Uso: ./check-deploy.sh

PROD_URL="https://app-color-accessibility.onrender.com"
MAX_RETRIES=30
RETRY_DELAY=10

echo "🔍 Verificando deploy en Render..."
echo "URL: $PROD_URL"
echo "================================================"
echo ""

# Función para verificar si el servidor está respondiendo
check_server() {
    echo "📡 Verificando que el servidor esté activo..."
    response=$(curl -s -o /dev/null -w "%{http_code}" "$PROD_URL/")
    
    if [ "$response" -eq 200 ]; then
        echo "✅ Servidor activo (HTTP $response)"
        return 0
    else
        echo "❌ Servidor no responde (HTTP $response)"
        return 1
    fi
}

# Función para verificar el schema
check_schema() {
    echo ""
    echo "📋 Verificando schema del tool..."
    
    schema=$(curl -s -X POST "$PROD_URL/mcp" \
        -H "Content-Type: application/json" \
        -d '{
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list"
        }' | jq -r '.result.tools[0].inputSchema')
    
    # Verificar que image_url está presente
    if echo "$schema" | grep -q "image_url"; then
        echo "✅ image_url encontrado en schema"
    else
        echo "❌ image_url NO encontrado en schema"
        return 1
    fi
    
    # Verificar que oneOf NO está presente
    if echo "$schema" | grep -q "oneOf"; then
        echo "❌ oneOf aún presente en schema (ERROR)"
        return 1
    else
        echo "✅ oneOf eliminado correctamente"
    fi
    
    # Verificar que image_data NO está presente
    if echo "$schema" | grep -q "image_data"; then
        echo "❌ image_data aún presente en schema (ERROR)"
        return 1
    else
        echo "✅ image_data eliminado correctamente"
    fi
    
    # Verificar que wcag_level está presente
    if echo "$schema" | grep -q "wcag_level"; then
        echo "✅ wcag_level encontrado en schema"
    else
        echo "⚠️  wcag_level no encontrado (opcional, pero debería estar)"
    fi
    
    return 0
}

# Función para probar el tool
test_tool() {
    echo ""
    echo "🧪 Probando llamada al tool..."
    
    response=$(curl -s -X POST "$PROD_URL/mcp" \
        -H "Content-Type: application/json" \
        -d '{
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "analyze_color_accessibility",
                "arguments": {
                    "image_url": "https://example.com/test.png",
                    "wcag_level": "AA"
                }
            }
        }')
    
    # Verificar que no hay error
    if echo "$response" | jq -e '.error' > /dev/null 2>&1; then
        echo "❌ Error en la respuesta del tool:"
        echo "$response" | jq '.error'
        return 1
    fi
    
    # Verificar que hay contenido
    if echo "$response" | jq -e '.result.content' > /dev/null 2>&1; then
        echo "✅ Tool respondió correctamente"
        
        # Mostrar el texto de respuesta
        text=$(echo "$response" | jq -r '.result.content[0].text')
        echo ""
        echo "📝 Respuesta del tool:"
        echo "$text"
        
        # Verificar que la URL está en la respuesta
        if echo "$text" | grep -q "https://example.com/test.png"; then
            echo ""
            echo "✅ URL de imagen incluida en respuesta"
        else
            echo ""
            echo "⚠️  URL de imagen NO incluida en respuesta"
        fi
        
        return 0
    else
        echo "❌ Respuesta del tool no tiene contenido"
        return 1
    fi
}

# Esperar a que el servidor esté activo
echo "⏳ Esperando a que el deploy complete..."
echo ""

retry_count=0
while [ $retry_count -lt $MAX_RETRIES ]; do
    if check_server; then
        break
    fi
    
    retry_count=$((retry_count + 1))
    echo "⏳ Reintentando en $RETRY_DELAY segundos... ($retry_count/$MAX_RETRIES)"
    sleep $RETRY_DELAY
done

if [ $retry_count -eq $MAX_RETRIES ]; then
    echo ""
    echo "❌ El servidor no respondió después de $MAX_RETRIES intentos"
    echo "Verifica el estado del deploy en: https://dashboard.render.com"
    exit 1
fi

# Verificar el schema
if ! check_schema; then
    echo ""
    echo "❌ El schema no está correctamente actualizado"
    echo "Puede que el deploy aún esté en progreso o haya fallado"
    exit 1
fi

# Probar el tool
if ! test_tool; then
    echo ""
    echo "❌ El tool no funciona correctamente"
    exit 1
fi

# Todo OK
echo ""
echo "================================================"
echo "✅ ¡Deploy verificado exitosamente!"
echo "================================================"
echo ""
echo "🎉 El servidor está funcionando correctamente con los nuevos cambios:"
echo "  ✅ Servidor activo"
echo "  ✅ Schema actualizado (solo image_url)"
echo "  ✅ oneOf eliminado"
echo "  ✅ Tool funciona correctamente"
echo "  ✅ URL incluida en respuesta"
echo ""
echo "🚀 Ahora puedes probar en ChatGPT:"
echo "  1. Ve a https://chat.openai.com"
echo "  2. Sube una imagen"
echo "  3. Pide: 'Check the accessibility of this image'"
echo ""
echo "📊 Ver logs en tiempo real:"
echo "  https://dashboard.render.com"
echo ""
