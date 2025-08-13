-- Eliminar tablas si existen y recrear sin RLS
DROP TABLE IF EXISTS user_sessions CASCADE;
DROP TABLE IF EXISTS activity_logs CASCADE;  
DROP TABLE IF EXISTS users CASCADE;

-- Crear tabla de usuarios SIN RLS
CREATE TABLE users (
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

-- Crear tabla de logs SIN RLS
CREATE TABLE activity_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    username VARCHAR(50) NOT NULL,
    action VARCHAR(50) NOT NULL,
    description TEXT,
    file_type VARCHAR(50),
    file_name VARCHAR(255),
    records_count INTEGER,
    status VARCHAR(20) DEFAULT 'success' CHECK (status IN ('success', 'error', 'warning')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Crear tabla de sesiones SIN RLS
CREATE TABLE user_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true
);

-- Insertar usuarios
INSERT INTO users (username, email, password_hash, full_name, role) VALUES 
('admin', 'admin@empresa.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewLdoQQGgA8r8F/q', 'Administrador del Sistema', 'admin'),
('alejandro.perez', 'alejandro.perez@empresa.com', '$2b$12$5Ew1xfHPYJnG8c2iJN8F5OSaVfT5QZnczNvI8xmKxw1VT6Q8cTntu', 'Alejandro Pérez', 'user');

-- Verificar
SELECT username, full_name, role FROM users;