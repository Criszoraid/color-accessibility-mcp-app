# 🚀 Guía de Despliegue en GitHub

Esta guía te ayudará a desplegar tu aplicación SDK de OpenAI con MCP en un servidor externo usando GitHub.

## 📋 Requisitos Previos

- Cuenta de GitHub
- Repositorio creado en GitHub
- Acceso a un servidor externo (VPS, Cloud, etc.)
- SSH configurado para acceso al servidor

## 🔧 Configuración Inicial

### 1. Configurar el Repositorio

```bash
# Inicializar git si no está inicializado
git init

# Agregar el remoto de GitHub
git remote add origin https://github.com/TU_USUARIO/TU_REPOSITORIO.git

# Agregar todos los archivos
git add .

# Hacer commit inicial
git commit -m "Initial commit: OpenAI SDK MCP App"

# Subir a GitHub
git push -u origin main
```

### 2. Configurar Secrets en GitHub

Ve a **Settings > Secrets and variables > Actions** en tu repositorio y agrega:

- `BASE_URL`: URL base de tu aplicación (ej: `https://tu-dominio.com`)
- `SERVER_HOST`: IP o dominio del servidor
- `SERVER_USER`: Usuario SSH del servidor
- `SSH_PRIVATE_KEY`: Clave privada SSH para acceso al servidor

## 🎯 Opciones de Despliegue

### Opción 1: Despliegue Automático con GitHub Actions

El workflow `.github/workflows/ci.yml` crea automáticamente un paquete de despliegue.

#### Pasos:

1. **Habilitar GitHub Actions**: Ve a **Settings > Actions > General** y habilita los workflows.

2. **Push a main/master**: Cada push a la rama principal creará un artefacto de despliegue.

3. **Descargar el artefacto**:
   - Ve a **Actions** en tu repositorio
   - Selecciona el workflow ejecutado
   - Descarga el artefacto `deployment-package`

4. **Desplegar en el servidor**:
   ```bash
   # En tu servidor
   scp deploy.tar.gz usuario@servidor:/ruta/destino/
   
   # Conectarse al servidor
   ssh usuario@servidor
   
   # Extraer y configurar
   cd /ruta/destino
   tar -xzf deploy.tar.gz
   cd deploy
   
   # Instalar dependencias
   npm install
   cd server && pip install -r requirements.txt
   
   # Configurar variables de entorno
   export BASE_URL=https://tu-dominio.com
   export PORT=8000
   
   # Iniciar servidor
   cd server
   uvicorn main:app --host 0.0.0.0 --port $PORT
   ```

### Opción 2: Despliegue Manual con Script

Crea un script de despliegue personalizado:

```bash
#!/bin/bash
# deploy.sh

SERVER="usuario@servidor"
REMOTE_PATH="/var/www/app"
LOCAL_DIST="web/dist"

# Build local
cd web && npm run build && cd ..

# Copiar archivos
rsync -avz --exclude 'node_modules' \
  server/ $SERVER:$REMOTE_PATH/server/
rsync -avz $LOCAL_DIST/ $SERVER:$REMOTE_PATH/web/dist/
scp index.js package.json $SERVER:$REMOTE_PATH/

# Ejecutar en servidor
ssh $SERVER << 'EOF'
cd /var/www/app
npm install
cd server && pip install -r requirements.txt
pm2 restart app || pm2 start server/main.py --name app --interpreter python3
EOF
```

### Opción 3: GitHub Pages (Frontend Estático)

Para desplegar solo el frontend en GitHub Pages:

1. **Habilitar GitHub Pages**:
   - Ve a **Settings > Pages**
   - Source: **GitHub Actions**

2. **El workflow `.github/workflows/deploy.yml`** se ejecutará automáticamente.

3. **Tu app estará disponible en**:
   ```
   https://TU_USUARIO.github.io/TU_REPOSITORIO
   ```

**Nota**: GitHub Pages solo sirve contenido estático. El backend MCP debe estar en otro servidor.

### Opción 4: Despliegue con Docker

Crea un `Dockerfile`:

```dockerfile
FROM node:20-alpine AS frontend-builder
WORKDIR /app/web
COPY web/package*.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

FROM python:3.11-slim
WORKDIR /app

# Instalar Node.js para MCP server
RUN apt-get update && apt-get install -y nodejs npm && rm -rf /var/lib/apt/lists/*

# Copiar backend
COPY server/ ./server/
RUN pip install --no-cache-dir -r server/requirements.txt

# Copiar frontend build
COPY --from=frontend-builder /app/web/dist ./web/dist

# Copiar MCP server
COPY index.js package*.json ./
RUN npm install

EXPOSE 8000
ENV PORT=8000
ENV BASE_URL=http://localhost:8000

CMD ["python", "server/main.py"]
```

Y un `docker-compose.yml`:

```yaml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - BASE_URL=${BASE_URL}
      - PORT=8000
    restart: unless-stopped
```

## 🔐 Configuración del Servidor

### Instalar Dependencias del Sistema

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3.11 python3-pip nodejs npm nginx

# Configurar Node.js
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
```

### Configurar Nginx como Reverse Proxy

```nginx
# /etc/nginx/sites-available/app
server {
    listen 80;
    server_name tu-dominio.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/app /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Usar PM2 para Gestión de Procesos

```bash
# Instalar PM2
npm install -g pm2

# Iniciar aplicación
cd /ruta/a/tu/app
pm2 start server/main.py --name mcp-app --interpreter python3

# Guardar configuración
pm2 save
pm2 startup
```

## 🔄 Actualizaciones Automáticas

### Con GitHub Actions + Webhook

1. **Crear webhook en GitHub**:
   - Settings > Webhooks > Add webhook
   - Payload URL: `https://tu-servidor.com/webhook`
   - Content type: `application/json`

2. **Endpoint de webhook en tu servidor**:
   ```python
   # server/webhook.py
   from fastapi import FastAPI, Request
   import subprocess
   
   @app.post("/webhook")
   async def github_webhook(request: Request):
       # Verificar firma de GitHub
       # Ejecutar git pull y reiniciar
       subprocess.run(["git", "pull"])
       subprocess.run(["pm2", "restart", "mcp-app"])
       return {"status": "updated"}
   ```

## 📊 Monitoreo

### Health Check Endpoint

Tu servidor ya tiene un endpoint de salud:

```bash
curl https://tu-dominio.com/
```

### Logs

```bash
# Ver logs con PM2
pm2 logs mcp-app

# Ver logs de Nginx
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

## 🐛 Troubleshooting

### Problema: El frontend no carga
- Verifica que `BASE_URL` esté configurado correctamente
- Revisa la consola del navegador para errores CORS
- Asegúrate de que los archivos estáticos estén en `web/dist/`

### Problema: MCP server no responde
- Verifica que el puerto 8000 esté abierto
- Revisa los logs: `pm2 logs mcp-app`
- Verifica que las dependencias estén instaladas

### Problema: GitHub Actions falla
- Revisa los logs en la pestaña **Actions**
- Verifica que los secrets estén configurados
- Asegúrate de que los paths sean correctos

## 📚 Recursos Adicionales

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [GitHub Pages Documentation](https://docs.github.com/en/pages)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
- [PM2 Documentation](https://pm2.keymetrics.io/docs/usage/quick-start/)

## ✅ Checklist de Despliegue

- [ ] Repositorio creado en GitHub
- [ ] Código subido a GitHub
- [ ] Secrets configurados
- [ ] GitHub Actions habilitado
- [ ] Servidor configurado con dependencias
- [ ] Dominio/DNS configurado (opcional)
- [ ] SSL/HTTPS configurado (opcional pero recomendado)
- [ ] Monitoreo configurado
- [ ] Backups configurados

---

¿Necesitas ayuda? Abre un issue en el repositorio.

