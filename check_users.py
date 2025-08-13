"""
Script para verificar usuarios existentes
"""
from supabase import create_client
import config

def check_users():
    """Verificar qué usuarios existen"""
    try:
        supabase = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
        
        # Intentar obtener usuarios
        result = supabase.table('users').select('*').execute()
        
        print(f"Usuarios encontrados: {len(result.data)}")
        for user in result.data:
            print(f"- {user['username']} ({user['full_name']}) - Rol: {user['role']}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_users()