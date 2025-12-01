#!/bin/bash

echo "🚀 Starting Color Accessibility Checker Development Server..."

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Build the widget
echo -e "${BLUE}📦 Building widget...${NC}"
cd web
npm install
npm run build
cd ..

# Start Python server
echo -e "${GREEN}🐍 Starting Python MCP server on port 8000...${NC}"
source .venv/bin/activate 2>/dev/null || python3 -m venv .venv && source .venv/bin/activate
pip install -r server/requirements.txt
cd server
python main.py
