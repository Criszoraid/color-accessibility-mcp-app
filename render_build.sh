#!/usr/bin/env bash
# exit on error
set -o errexit

echo "🚀 Starting Build Process..."

# Check Node version
echo "📦 Checking Node.js..."
if ! command -v node &> /dev/null; then
    echo "❌ Node.js not found! Installing..."
    # Install Node.js manually if missing (fallback)
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt-get install -y nodejs
else
    echo "✅ Node.js found: $(node -v)"
    echo "✅ npm found: $(npm -v)"
fi

# Build Frontend
echo "🏗️ Building Frontend..."
cd web
npm install
npm run build

# Verify Output
echo "🔍 Verifying build output..."
if [ -d "dist/assets" ]; then
    echo "✅ Assets directory created at $(pwd)/dist/assets"
    ls -la dist/assets
else
    echo "❌ Assets directory NOT found at $(pwd)/dist/assets"
    exit 1
fi

cd ..

# Install Backend Dependencies
echo "🐍 Installing Python Dependencies..."
pip install -r server/requirements.txt

echo "✅ Build Complete!"
