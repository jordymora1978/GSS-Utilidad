# 👥 Usuarios del Sistema

## 🔧 Configuración Requerida

Para que el sistema de usuarios funcione correctamente:

1. **Base de datos Supabase configurada**
2. **Variables de entorno configuradas** (.env)
3. **Script SQL ejecutado** (setup_users_database.sql)

## 👤 Usuarios por Defecto

Una vez configurada la base de datos, estarán disponibles:

| Usuario | Contraseña | Rol | Estado |
|---------|------------|-----|---------|
| `admin` | `admin123` | Administrador | ✅ Configurado |
| `alejandro.perez` | `123456` | Usuario | ✅ Configurado |

## 🚨 Nota Importante

Los usuarios **NO** están incluidos en el repositorio por seguridad.
Deben crearse ejecutando el script SQL en tu instancia de Supabase.

## 📋 Pasos para configurar usuarios:

1. Configurar Supabase con tus credenciales
2. Ejecutar `setup_users_database.sql` 
3. Los usuarios se crearán automáticamente
4. Login disponible en http://localhost:8501

---
**Los usuarios están en tu base de datos, no en GitHub** 🔒