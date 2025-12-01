#!/bin/bash

# Script de despliegue para servidor externo
# Uso: ./deploy.sh [servidor] [usuario] [ruta]

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuración
SERVER="${1:-usuario@servidor.com}"
REMOTE_PATH="${2:-/var/www/mcp-app}"
LOCAL_DIST="web/dist"

echo -e "${GREEN}🚀 Iniciando despliegue...${NC}"

# Verificar que estamos en el directorio correcto
if [ ! -f "package.json" ]; then
    echo -e "${RED}❌ Error: No se encontró package.json. Ejecuta este script desde la raíz del proyecto.${NC}"
    exit 1
fi

# Build del frontend
echo -e "${YELLOW}📦 Construyendo frontend...${NC}"
if [ -d "web" ]; then
    cd web
    if [ ! -f "package.json" ]; then
        echo -e "${YELLOW}⚠️  No se encontró package.json en web/, saltando build del frontend${NC}"
    else
        npm install
        npm run build
    fi
    cd ..
else
    echo -e "${YELLOW}⚠️  No se encontró el directorio web/, saltando build del frontend${NC}"
fi

# Crear directorio temporal
TEMP_DIR=$(mktemp -d)
echo -e "${YELLOW}📁 Creando paquete de despliegue en ${TEMP_DIR}...${NC}"

# Copiar archivos necesarios
mkdir -p "$TEMP_DIR/server"
mkdir -p "$TEMP_DIR/web/dist"

# Copiar backend
if [ -d "server" ]; then
    cp -r server/* "$TEMP_DIR/server/"
    echo -e "${GREEN}✅ Backend copiado${NC}"
fi

# Copiar frontend build
if [ -d "$LOCAL_DIST" ]; then
    cp -r "$LOCAL_DIST"/* "$TEMP_DIR/web/dist/"
    echo -e "${GREEN}✅ Frontend build copiado${NC}"
fi

# Copiar archivos raíz
cp index.js "$TEMP_DIR/" 2>/dev/null || echo -e "${YELLOW}⚠️  index.js no encontrado${NC}"
cp package.json "$TEMP_DIR/" 2>/dev/null || echo -e "${YELLOW}⚠️  package.json no encontrado${NC}"
cp package-lock.json "$TEMP_DIR/" 2>/dev/null || echo -e "${YELLOW}⚠️  package-lock.json no encontrado${NC}"
cp README.md "$TEMP_DIR/" 2>/dev/null || echo -e "${YELLOW}⚠️  README.md no encontrado${NC}"

# Crear script de instalación
cat > "$TEMP_DIR/install.sh" << 'EOF'
#!/bin/bash
set -e

echo "🔧 Instalando dependencias..."

# Instalar dependencias Node.js
if [ -f "package.json" ]; then
    npm install --production
fi

# Instalar dependencias Python
if [ -d "server" ] && [ -f "server/requirements.txt" ]; then
    pip install -r server/requirements.txt
fi

echo "✅ Dependencias instaladas"
EOF

chmod +x "$TEMP_DIR/install.sh"

# Crear script de inicio
cat > "$TEMP_DIR/start.sh" << 'EOF'
#!/bin/bash
set -e

export PORT=${PORT:-8000}
export BASE_URL=${BASE_URL:-http://localhost:$PORT}

echo "🚀 Iniciando servidor en puerto $PORT..."

if [ -d "server" ]; then
    cd server
    uvicorn main:app --host 0.0.0.0 --port $PORT
else
    echo "❌ No se encontró el directorio server/"
    exit 1
fi
EOF

chmod +x "$TEMP_DIR/start.sh"

# Crear archivo .env.example
cat > "$TEMP_DIR/.env.example" << 'EOF'
# Configuración del servidor
PORT=8000
BASE_URL=https://tu-dominio.com

# Configuración de OpenAI (si es necesario)
# OPENAI_API_KEY=tu_api_key_aqui
EOF

# Crear tar.gz
echo -e "${YELLOW}📦 Comprimiendo paquete...${NC}"
cd "$TEMP_DIR"
tar -czf deploy.tar.gz *
cd - > /dev/null

# Mostrar información
echo -e "${GREEN}✅ Paquete creado: ${TEMP_DIR}/deploy.tar.gz${NC}"
echo ""
echo -e "${YELLOW}📋 Para desplegar en el servidor:${NC}"
echo ""
echo "1. Copiar el archivo al servidor:"
echo "   scp ${TEMP_DIR}/deploy.tar.gz ${SERVER}:~/"
echo ""
echo "2. Conectarse al servidor:"
echo "   ssh ${SERVER}"
echo ""
echo "3. Extraer y configurar:"
echo "   mkdir -p ${REMOTE_PATH}"
echo "   cd ${REMOTE_PATH}"
echo "   tar -xzf ~/deploy.tar.gz"
echo "   chmod +x install.sh start.sh"
echo "   ./install.sh"
echo ""
echo "4. Configurar variables de entorno:"
echo "   cp .env.example .env"
echo "   nano .env  # Editar según necesidad"
echo ""
echo "5. Iniciar servidor:"
echo "   ./start.sh"
echo ""
echo -e "${GREEN}✨ ¡Despliegue listo!${NC}"

