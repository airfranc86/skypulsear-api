# SkyPulse - Configuración de GitHub Pages
# Solo deploy el directorio public/ con el frontend
# Excluir todo el backend

# Workflows de GitHub Actions
/.github/
├── workflows/
│   └── deploy.yml
└── 
public/
├── dashboard.html
├── index.html
└── ...

# Resto del repositorio (backend, tests, etc.)
