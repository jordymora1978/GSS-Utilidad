# 📋 CLAUDE - Documentación del Proyecto

## 🎯 Metodología de Desarrollo: Tools vs Pages

### 🔧 TOOLS (Herramientas Locales)
**Características:**
- Scripts temporales y utilidades de mantenimiento
- Se ejecutan independientemente desde el directorio raíz
- **NO se sincronizan automáticamente** con el sistema online
- Solo se convierten a páginas con orden específica

**Ubicación:** Archivos `.py` en la raíz del proyecto
**Ejecución:** `streamlit run [script].py --server.port [puerto]`

**Ejemplos actuales:**
- `actualizar_logistics_date.py` - Puerto 8502
- `verificar_duplicados.py` - Port 8503

### 📱 PAGES (Sistema Principal)
**Características:**
- Interfaces permanentes del sistema
- Integradas en el menú lateral de Streamlit
- **SÍ se sincronizan** cuando se decide actualizar online
- Parte del flujo principal del usuario

**Ubicación:** `/pages/` directory
**Acceso:** A través del menú lateral del sistema principal

### 🔄 Proceso de Conversión
Para convertir una TOOL en PAGE:
1. **Orden específica:** "convertir [herramienta] a página"
2. **Mover código** a `/pages/` con numeración apropiada
3. **Integrar autenticación** y permisos del sistema
4. **Actualizar menús** y navegación
5. **Sincronizar** con versión online cuando se decida

## 📁 Estructura del Proyecto

```
sistema-contable-multipais/
├── 🔧 TOOLS (Local only)
│   ├── actualizar_logistics_date.py
│   ├── verificar_duplicados.py
│   └── tools_local/ (respaldos)
│
├── 📱 PAGES (Sistema principal)
│   ├── 1_📦_Consolidador.py
│   ├── 2_💱_Gestión_TRM.py  
│   ├── 3_📊_Reportes.py
│   ├── 4_👥_Usuarios.py
│   └── tools/
│       └── 5_🔧_Tools.py (índice de herramientas)
│
├── 📂 MÓDULOS
│   ├── auth.py
│   ├── utilidades.py
│   └── reportes/
│
└── 📋 CONFIGURACIÓN
    ├── config.py
    ├── streamlit_app.py (principal)
    └── CLAUDE.md (esta documentación)
```

## 🚀 Comandos de Desarrollo

### Sistema Principal
```bash
streamlit run streamlit_app.py --server.port 8501
```
URL: http://localhost:8501

### Herramientas (Tools)
```bash
# Actualizar fechas logistics_date
streamlit run actualizar_logistics_date.py --server.port 8502

# Verificar duplicados pre-consolidador  
streamlit run verificar_duplicados.py --server.port 8503
```

## 📝 Reglas de Desarrollo

### ❌ Lo que NO hacer automáticamente:
- Sincronizar herramientas con GitHub
- Convertir scripts temporales en páginas
- Subir utilidades de una sola vez al sistema principal

### ✅ Lo que SÍ hacer:
- Desarrollar herramientas como scripts independientes
- Documentar en esta sección cuando se crea una nueva tool
- Esperar orden específica para convertir tool → page
- Mantener separación clara entre tools y pages

## 🔐 Sistema de Autenticación

Las **páginas** usan el sistema de autenticación completo:
```python
from modulos.auth import require_auth, is_logged_in, show_login_form
```

Las **herramientas** pueden usar autenticación simplificada o ninguna.

## 🎨 Formatos y Convenciones

### Páginas (sistema principal):
- Numeración: `1_📦_Nombre.py`
- Icono en el nombre del archivo
- Integración completa con auth
- Layout wide por defecto

### Herramientas:
- Nombre descriptivo: `accion_objeto.py`
- Puerto específico (8502+)
- Documentación en Tools page
- Independientes del sistema principal

## 🔄 Workflow de Trabajo

1. **Desarrollo inicial:** Todo es TOOL (local)
2. **Testing:** Probar herramienta localmente
3. **Evaluación:** Determinar si debe ser permanente
4. **Conversión:** Solo con orden específica convertir a PAGE
5. **Sincronización:** Solo cuando se decide actualizar GitHub

## 📊 Herramientas Actuales

| Herramienta | Puerto | Descripción | Estado |
|-------------|--------|-------------|--------|
| `actualizar_logistics_date.py` | 8502 | Actualizar fechas desde Excel | 🔧 TOOL |
| `verificar_duplicados.py` | 8503 | Pre-verificar archivos consolidador | 🔧 TOOL |

## 🎯 Próximas Herramientas

- Scripts de limpieza de datos
- Utilidades de análisis de BD
- Herramientas de backup/restore
- Scripts de migración

---

**Última actualización:** 2025-08-18
**Versión:** 1.0
**Autor:** Claude + Jordy