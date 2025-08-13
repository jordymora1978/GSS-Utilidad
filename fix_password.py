"""
Generar hash correcto para la contraseña
"""
import bcrypt

def generate_hash():
    """Generar hash para admin123"""
    password = "admin123"
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    hash_str = hashed.decode('utf-8')
    
    print(f"Contraseña: {password}")
    print(f"Hash: {hash_str}")
    
    # Verificar que funciona
    test_result = bcrypt.checkpw(password.encode('utf-8'), hashed)
    print(f"Verificacion: {test_result}")
    
    # SQL para actualizar
    print(f"\nSQL para actualizar:")
    print(f"UPDATE users SET password_hash = '{hash_str}' WHERE username = 'admin';")

if __name__ == "__main__":
    generate_hash()