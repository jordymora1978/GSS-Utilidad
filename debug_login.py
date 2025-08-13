"""
Debug del sistema de login
"""
import bcrypt
from supabase import create_client
import config

def debug_login():
    """Debug del proceso de login"""
    try:
        supabase = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
        print("Conexion a Supabase exitosa")
        
        # Intentar leer usuarios
        print("\nIntentando leer usuarios...")
        result = supabase.table('users').select('*').execute()
        print(f"Resultado: {result}")
        print(f"Data: {result.data}")
        print(f"Count: {result.count if hasattr(result, 'count') else 'No count'}")
        
        if result.data:
            print(f"\nUsuarios encontrados: {len(result.data)}")
            for user in result.data:
                print(f"- {user['username']} | {user['full_name']} | {user['role']}")
        else:
            print("\nNo se encontraron usuarios")
            
        # Intentar buscar admin específicamente
        print("\nBuscando usuario admin...")
        admin_result = supabase.table('users').select('*').eq('username', 'admin').execute()
        print(f"Admin result: {admin_result}")
        
        if admin_result.data:
            admin_user = admin_result.data[0]
            print(f"Usuario admin encontrado: {admin_user['full_name']}")
            
            # Probar verificación de contraseña
            print("\nProbando verificacion de contraseña...")
            test_password = "admin123"
            stored_hash = admin_user['password_hash']
            
            try:
                is_valid = bcrypt.checkpw(test_password.encode('utf-8'), stored_hash.encode('utf-8'))
                print(f"Contraseña valida: {is_valid}")
            except Exception as e:
                print(f"Error verificando contraseña: {e}")
        else:
            print("Usuario admin no encontrado")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_login()