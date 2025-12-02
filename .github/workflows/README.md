# GitHub Actions Workflows

Este directorio contiene los workflows de GitHub Actions para automatizar CI/CD.

## 📋 Workflows Disponibles

### 1. `ci.yml` - Continuous Integration

**Cuándo se ejecuta:**
- Push a `main`, `master`, o `develop`
- Pull requests a `main` o `master`

**Qué hace:**
- ✅ Ejecuta tests del servidor MCP en Node.js (versiones 18.x y 20.x)
- ✅ Ejecuta tests del servidor Python (versiones 3.10, 3.11, 3.12)
- ✅ Construye el frontend React
- ✅ Crea un paquete de despliegue cuando se hace push a `main`/`master`

**Artefactos generados:**
- `frontend-dist`: Build del frontend
- `deployment-package`: Paquete completo listo para despliegue

### 2. `deploy.yml` - Despliegue a GitHub Pages

**Cuándo se ejecuta:**
- Push a `main` o `master`
- Manualmente desde la pestaña Actions

**Qué hace:**
- ✅ Construye el frontend
- ✅ Despliega a GitHub Pages
- ✅ Configura automáticamente la URL base

**Requisitos:**
- Habilitar GitHub Pages en Settings > Pages
- Source: GitHub Actions

### 3. `release.yml` - Crear Releases

**Cuándo se ejecuta:**
- Cuando se crea un tag que empieza con `v` (ej: `v1.0.0`)

**Qué hace:**
- ✅ Construye la aplicación completa
- ✅ Crea un release en GitHub
- ✅ Genera paquetes `.tar.gz` y `.zip`
- ✅ Incluye notas de release automáticas

**Uso:**
```bash
git tag v1.0.0
git push origin v1.0.0
```

## 🔧 Configuración

### Secrets Requeridos

Ve a **Settings > Secrets and variables > Actions** y agrega:

- `BASE_URL`: URL base de tu aplicación (para GitHub Pages)
- `SERVER_HOST`: IP o dominio del servidor (opcional, para despliegue automático)
- `SERVER_USER`: Usuario SSH (opcional)
- `SSH_PRIVATE_KEY`: Clave privada SSH (opcional)

### Variables de Entorno

Puedes configurar variables de entorno en **Settings > Secrets and variables > Actions > Variables**:

- `NODE_VERSION`: Versión de Node.js (default: 20.x)
- `PYTHON_VERSION`: Versión de Python (default: 3.11)

## 📊 Ver Resultados

1. Ve a la pestaña **Actions** en tu repositorio
2. Selecciona el workflow que quieres ver
3. Haz click en la ejecución específica
4. Descarga artefactos si están disponibles

## 🐛 Troubleshooting

### Workflow falla en tests
- Verifica que todas las dependencias estén en `package.json` y `requirements.txt`
- Revisa los logs para ver el error específico

### Build del frontend falla
- Asegúrate de que `web/package.json` exista
- Verifica que `npm run build` funcione localmente

### Despliegue a GitHub Pages falla
- Verifica que GitHub Pages esté habilitado
- Asegúrate de que el secret `BASE_URL` esté configurado

## 📚 Más Información

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [DEPLOY.md](../DEPLOY.md) - Guía completa de despliegue

