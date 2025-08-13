# 🚀 GSS App - Sistema de Gestión

Sistema integral de gestión contable para operaciones en múltiples países con capacidades de consolidación automática, gestión de usuarios y reportes avanzados.

## ✨ Características Principales

- 🤖 **Sistema Inteligente**: Detecta automáticamente duplicados, actualiza información existente y preserva datos históricos
- 👥 **Gestión de Usuarios**: Sistema completo con roles, autenticación y logs de actividad
- 📦 **Consolidación Automática**: Procesa múltiples fuentes de datos simultáneamente
- 💱 **Gestión TRM**: Administración de tasas de cambio para múltiples países
- 📊 **Reportes Avanzados**: Generación de reportes de utilidad por país/canal
- 🛡️ **Seguridad**: Autenticación con bcrypt y variables de entorno
- 🔄 **Tracking**: Logs automáticos de todas las operaciones de usuarios

## 🚀 Instalación Rápida

1. **Clona el repositorio:**
   ```bash
   git clone https://github.com/jordymora1978/sistema-contable-multipais.git
   cd sistema-contable-multipais
   ```

2. **Instala dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configura variables de entorno:**
   ```bash
   cp .env.example .env
   # Edita .env con tus credenciales de Supabase
   ```

4. **Configura la base de datos:**
   - Ejecuta `setup_users_database.sql` en Supabase SQL Editor

5. **Ejecuta la aplicación:**
   ```bash
   streamlit run streamlit_app.py
   ```

## 👤 Usuarios por Defecto

| Usuario | Contraseña | Rol | Permisos |
|---------|------------|-----|----------|
| `admin` | `admin123` | Administrador | ✅ Acceso completo + gestión usuarios |
| `alejandro.perez` | `123456` | Usuario | ✅ Consolidador, Reportes, TRM |

⚠️ **Importante:** 
- Los usuarios se crean ejecutando `setup_users_database.sql` en **tu Supabase**
- **NO están en el repositorio** por seguridad
- Cambia las contraseñas después del primer login

## 🏗️ Estructura del Proyecto

```
📁 sistema-contable-multipais/
├── 🚀 streamlit_app.py          # Aplicación principal
├── 📁 pages/                    # Módulos de la aplicación
│   ├── 1_📦_Consolidador.py     # Sistema de consolidación
│   ├── 2_💱_Gestión_TRM.py      # Gestión de tasas
│   ├── 3_📊_Reportes.py         # Generación de reportes
│   └── 4_👥_Usuarios.py         # Gestión de usuarios
├── 📁 modulos/                  # Lógica de negocio
│   ├── auth.py                  # Sistema de autenticación
│   ├── gestion_trm.py           # Lógica TRM
│   └── reportes/                # Módulos de reportes
├── 🔧 config.py                 # Configuración (con variables de entorno)
├── 🛡️ SECURITY.md              # Guía de seguridad
├── 📚 README_USUARIOS.md        # Documentación de usuarios
└── 🗃️ setup_users_database.sql # Script de configuración DB
```

## 📦 Módulos Principales

### 🤖 Consolidador Inteligente
- **Detección automática** de duplicados
- **Procesamiento simultáneo** de múltiples archivos
- **Actualización incremental** de datos existentes
- **Preservación** de información histórica
- **Soporte para**: Drapify, Logistics, Aditionals, CXP

### 💱 Gestión TRM
- Administración de **tasas de cambio** por país y fecha
- **Histórico** de fluctuaciones
- **Cálculos automáticos** de conversión

### 📊 Reportes Avanzados
- Reportes de **utilidad por canal**
- **Análisis por país** y período
- **Exportación** en múltiples formatos
- **Dashboards interactivos**

### 👥 Sistema de Usuarios
- **Roles**: Admin, User, Viewer
- **Autenticación segura** con bcrypt
- **Logs de actividad** automáticos
- **Gestión completa** de usuarios

## 🔒 Seguridad

- ✅ **Credenciales en variables de entorno**
- ✅ **Autenticación con bcrypt**
- ✅ **Sesiones seguras con tokens**
- ✅ **Logs de actividad completos**
- ✅ **Repositorio privado compatible**

Ver [SECURITY.md](SECURITY.md) para más detalles.

## 🛠️ Tecnologías

- **Frontend**: Streamlit
- **Backend**: Python 3.13+
- **Base de Datos**: Supabase (PostgreSQL)
- **Autenticación**: bcrypt + JWT
- **Procesamiento**: Pandas, NumPy
- **Visualización**: Plotly, Matplotlib

## 📖 Documentación Adicional

- [📚 Guía de Usuarios](README_USUARIOS.md) - Gestión completa del sistema de usuarios
- [🛡️ Guía de Seguridad](SECURITY.md) - Configuración segura y mejores prácticas

## 🚀 Próximas Funcionalidades

- [ ] Dashboard de métricas en tiempo real
- [ ] Integración con APIs externas
- [ ] Notificaciones automáticas
- [ ] Backup automático de datos
- [ ] App móvil complementaria

## 📞 Soporte

Para reportes de bugs o solicitudes de características, contacta al administrador del sistema.

---

**GSS App v1.0** - Sistema de Gestión Integral de Operaciones
© 2025 - Todos los derechos reservados
