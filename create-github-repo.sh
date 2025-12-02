#!/bin/bash

# Script para crear repositorio en GitHub y hacer push inicial
# Uso: ./create-github-repo.sh [nombre-repo] [usuario] [token]

set -e

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Parámetros
REPO_NAME="${1:-color-accessibility-mcp-app}"
GITHUB_USER="${2}"
GITHUB_TOKEN="${3}"

if [ -z "$GITHUB_USER" ] || [ -z "$GITHUB_TOKEN" ]; then
    echo -e "${RED}❌ Error: Se requieren usuario y token de GitHub${NC}"
    echo ""
    echo "Uso: ./create-github-repo.sh [nombre-repo] [usuario] [token]"
    echo ""
    echo "Ejemplo:"
    echo "  ./create-github-repo.sh mi-app mi-usuario ghp_xxxxxxxxxxxx"
    echo ""
    exit 1
fi

echo -e "${GREEN}🚀 Creando repositorio en GitHub...${NC}"
echo -e "${YELLOW}📦 Nombre del repositorio: ${REPO_NAME}${NC}"
echo -e "${YELLOW}👤 Usuario: ${GITHUB_USER}${NC}"
echo ""

# Verificar si git está inicializado
if [ ! -d ".git" ]; then
    echo -e "${YELLOW}📁 Inicializando git...${NC}"
    git init
    git branch -M main
fi

# Verificar si ya existe un remote
if git remote get-url origin >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Ya existe un remote 'origin'${NC}"
    read -p "¿Deseas reemplazarlo? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git remote remove origin
    else
        echo -e "${RED}❌ Operación cancelada${NC}"
        exit 1
    fi
fi

# Crear repositorio en GitHub usando la API
echo -e "${GREEN}📡 Creando repositorio en GitHub...${NC}"

RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
  -H "Accept: application/vnd.github.v3+json" \
  -H "Authorization: token ${GITHUB_TOKEN}" \
  https://api.github.com/user/repos \
  -d "{
    \"name\": \"${REPO_NAME}\",
    \"description\": \"OpenAI SDK App with MCP - Color Accessibility Checker\",
    \"private\": false,
    \"has_issues\": true,
    \"has_projects\": true,
    \"has_wiki\": false,
    \"auto_init\": false
  }")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$REPONSE" | sed '$d')

if [ "$HTTP_CODE" -eq 201 ]; then
    echo -e "${GREEN}✅ Repositorio creado exitosamente${NC}"
elif [ "$HTTP_CODE" -eq 422 ]; then
    echo -e "${YELLOW}⚠️  El repositorio ya existe, continuando...${NC}"
elif [ "$HTTP_CODE" -eq 401 ]; then
    echo -e "${RED}❌ Error: Token inválido o sin permisos${NC}"
    exit 1
else
    echo -e "${RED}❌ Error al crear repositorio (HTTP ${HTTP_CODE})${NC}"
    echo "$BODY"
    exit 1
fi

# Agregar remote
echo -e "${GREEN}🔗 Configurando remote...${NC}"
git remote add origin "https://${GITHUB_TOKEN}@github.com/${GITHUB_USER}/${REPO_NAME}.git"

# Verificar que no haya cambios sin commitear
if ! git diff-index --quiet HEAD --; then
    echo -e "${YELLOW}📝 Hay cambios sin commitear${NC}"
    read -p "¿Deseas hacer commit de todos los cambios? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git add .
        git commit -m "Initial commit: OpenAI SDK MCP App con GitHub Actions"
    fi
fi

# Verificar si hay commits
if ! git rev-parse --verify HEAD >/dev/null 2>&1; then
    echo -e "${YELLOW}📝 No hay commits, creando commit inicial...${NC}"
    git add .
    git commit -m "Initial commit: OpenAI SDK MCP App con GitHub Actions"
fi

# Push al repositorio
echo -e "${GREEN}📤 Subiendo código a GitHub...${NC}"
git push -u origin main || {
    echo -e "${YELLOW}⚠️  Intentando con --force...${NC}"
    git push -u origin main --force
}

echo ""
echo -e "${GREEN}✨ ¡Repositorio creado y configurado exitosamente!${NC}"
echo ""
echo -e "${YELLOW}🔗 URL del repositorio:${NC}"
echo "   https://github.com/${GITHUB_USER}/${REPO_NAME}"
echo ""
echo -e "${YELLOW}📋 Próximos pasos:${NC}"
echo "   1. Ve a https://github.com/${GITHUB_USER}/${REPO_NAME}/settings/actions"
echo "   2. Habilita GitHub Actions si no está habilitado"
echo "   3. Ve a Settings > Secrets and variables > Actions"
echo "   4. Agrega el secret BASE_URL con la URL de tu aplicación"
echo "   5. Haz un push o crea un tag para activar los workflows"
echo ""


