# 🛡️ Guía de Seguridad

## 🔒 **Configuración Segura**

Este proyecto utiliza variables de entorno para mantener las credenciales seguras.

### 📋 **Configuración Inicial**

1. **Copia el archivo de ejemplo:**
   ```bash
   cp .env.example .env
   ```

2. **Edita el archivo .env con tus credenciales reales:**
   - `SUPABASE_URL`: URL de tu proyecto Supabase
   - `SUPABASE_KEY`: Service Role Key (NO la anon key)

3. **NUNCA subas el archivo .env a GitHub**

### 🔑 **Obtener Credenciales de Supabase**

1. Ve a tu dashboard de Supabase
2. Settings → API
3. Copia el **Service Role Key** (más larga, comienza diferente)

### 🚨 **Importante**

- ✅ El archivo `.env` está en `.gitignore`
- ✅ Solo se sube `.env.example` sin credenciales
- ✅ Usa Service Role Key, no Anon Key
- ❌ NUNCA hardcodees credenciales en el código

### 🔄 **Para rotar keys**

Si necesitas cambiar las credenciales:
1. Genera nuevas keys en Supabase
2. Actualiza el archivo `.env`
3. Reinicia la aplicación

### 👥 **Para nuevos desarrolladores**

1. Clona el repositorio
2. Copia `.env.example` → `.env`  
3. Pide las credenciales al administrador
4. Configura el archivo `.env`
5. ¡Listo para desarrollar!