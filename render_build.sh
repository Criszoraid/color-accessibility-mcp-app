#!/usr/bin/env bash
# exit on error
set -o errexit

echo "🚀 Starting Build Process..."

# Install Backend Dependencies (main requirement)
echo "🐍 Installing Python Dependencies..."
pip install -r server/requirements.txt

# Build Frontend only if web directory exists (optional)
if [ -d "web" ] && [ -f "web/package.json" ]; then
    echo "🏗️ Building Frontend..."
    # Check Node version
    if command -v node &> /dev/null; then
        echo "✅ Node.js found: $(node -v)"
        cd web
        npm install
        npm run build
        cd ..
        echo "✅ Frontend build complete"
    else
        echo "⚠️ Node.js not found, skipping frontend build (not required for widget endpoint)"
    fi
else
    echo "⚠️ No web directory found, skipping frontend build (not required for widget endpoint)"
fi

echo "✅ Build Complete!"
