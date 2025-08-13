"""
Script para configurar la base de datos de usuarios
Ejecutar una sola vez para crear las tablas y usuarios iniciales
"""
import bcrypt
from supabase import create_client
import config

def hash_password(password: str) -> str:
    """Hashear contraseña con bcrypt"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def setup_database():
    """Configurar base de datos completa"""
    
    # Conectar a Supabase
    supabase = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
    
    print("Configurando base de datos de usuarios...")
    
    # SQL para crear las tablas
    create_tables_sql = """
    -- 1. Tabla de usuarios
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username VARCHAR(50) UNIQUE NOT NULL,
        email VARCHAR(100) UNIQUE NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        full_name VARCHAR(100) NOT NULL,
        role VARCHAR(20) DEFAULT 'user' CHECK (role IN ('admin', 'user', 'viewer')),
        is_active BOOLEAN DEFAULT true,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        last_login TIMESTAMP WITH TIME ZONE
    );

    -- 2. Tabla de logs de actividad
    CREATE TABLE IF NOT EXISTS activity_logs (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
        username VARCHAR(50) NOT NULL,
        action VARCHAR(50) NOT NULL,
        description TEXT,
        file_type VARCHAR(50),
        file_name VARCHAR(255),
        records_count INTEGER,
        status VARCHAR(20) DEFAULT 'success' CHECK (status IN ('success', 'error', 'warning')),
        ip_address INET,
        user_agent TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );

    -- 3. Tabla de sesiones
    CREATE TABLE IF NOT EXISTS user_sessions (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        session_token VARCHAR(255) UNIQUE NOT NULL,
        expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        is_active BOOLEAN DEFAULT true
    );

    -- 4. Índices
    CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
    CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
    CREATE INDEX IF NOT EXISTS idx_activity_logs_user_id ON activity_logs(user_id);
    CREATE INDEX IF NOT EXISTS idx_activity_logs_created_at ON activity_logs(created_at);
    CREATE INDEX IF NOT EXISTS idx_user_sessions_token ON user_sessions(session_token);
    """
    
    try:
        # Ejecutar SQL para crear tablas (nota: esto podría no funcionar desde Python)
        print("Creando tablas...")
        # supabase.postgrest.rpc('execute_sql', {'sql': create_tables_sql})
        print("ADVERTENCIA: Las tablas deben crearse manualmente en Supabase SQL Editor")
        print("Usa el archivo setup_users_database.sql")
        
    except Exception as e:
        print(f"Error creando tablas: {e}")
        print("Por favor ejecuta manualmente el archivo setup_users_database.sql en Supabase")
    
    # Crear usuarios iniciales
    try:
        print("Creando usuarios iniciales...")
        
        # Usuario administrador
        admin_password = hash_password("admin123")
        admin_result = supabase.table('users').insert({
            'username': 'admin',
            'email': 'admin@empresa.com',
            'password_hash': admin_password,
            'full_name': 'Administrador del Sistema',
            'role': 'admin'
        }).execute()
        
        if admin_result.data:
            print("Usuario admin creado exitosamente")
        
        # Usuario Alejandro Pérez
        alejandro_password = hash_password("123456")
        alejandro_result = supabase.table('users').insert({
            'username': 'alejandro.perez',
            'email': 'alejandro.perez@empresa.com',
            'password_hash': alejandro_password,
            'full_name': 'Alejandro Pérez',
            'role': 'user'
        }).execute()
        
        if alejandro_result.data:
            print("Usuario alejandro.perez creado exitosamente")
        
        print("\nBase de datos configurada correctamente!")
        print("\nUsuarios creados:")
        print("   - admin / admin123 (Administrador)")
        print("   - alejandro.perez / 123456 (Usuario)")
        print("\nReinicia Streamlit para aplicar los cambios")
        
    except Exception as e:
        print(f"Error creando usuarios: {e}")
        if "already exists" in str(e):
            print("Los usuarios ya existen en la base de datos")

if __name__ == "__main__":
    setup_database()