"""
Generar hash para alejandro.perez
"""
import bcrypt

def generate_alejandro_hash():
    """Generar hash para 123456"""
    password = "123456"
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    hash_str = hashed.decode('utf-8')
    
    print(f"Contraseña: {password}")
    print(f"Hash: {hash_str}")
    
    # SQL para insertar alejandro
    print(f"\nSQL para crear alejandro.perez:")
    print(f"INSERT INTO users (username, email, password_hash, full_name, role) VALUES ('alejandro.perez', 'alejandro.perez@empresa.com', '{hash_str}', 'Alejandro Pérez', 'user');")

if __name__ == "__main__":
    generate_alejandro_hash()