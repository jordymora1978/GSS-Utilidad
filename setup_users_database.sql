-- Script SQL para crear tablas de usuarios y logs de actividad
-- Ejecutar en Supabase SQL Editor

-- 1. Tabla de usuarios
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

-- 2. Tabla de logs de actividad
CREATE TABLE activity_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    username VARCHAR(50) NOT NULL, -- Guardamos también el username por si se borra el usuario
    action VARCHAR(50) NOT NULL, -- 'upload_file', 'process_data', 'export_report', etc.
    description TEXT,
    file_type VARCHAR(50), -- 'drapify', 'logistics', 'aditionals', 'cxp'
    file_name VARCHAR(255),
    records_count INTEGER,
    status VARCHAR(20) DEFAULT 'success' CHECK (status IN ('success', 'error', 'warning')),
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Tabla de sesiones (para login/logout)
CREATE TABLE user_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true
);

-- 4. Índices para mejor rendimiento
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_activity_logs_user_id ON activity_logs(user_id);
CREATE INDEX idx_activity_logs_action ON activity_logs(action);
CREATE INDEX idx_activity_logs_created_at ON activity_logs(created_at);
CREATE INDEX idx_user_sessions_token ON user_sessions(session_token);

-- 5. Función para actualizar updated_at automáticamente
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 6. Trigger para users
CREATE TRIGGER update_users_updated_at 
    BEFORE UPDATE ON users 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- 7. Usuarios iniciales (cambiar las contraseñas después del primer login)
-- admin / admin123
-- alejandro.perez / 123456
INSERT INTO users (username, email, password_hash, full_name, role) VALUES 
('admin', 'admin@empresa.com', '$2b$12$XF4X.lApKUx5RPCbI0cVG.mr4E79JN953FDx5q3rqynnm1CVpaW3m', 'Administrador del Sistema', 'admin'),
('alejandro.perez', 'alejandro.perez@empresa.com', '$2b$12$IglvZZ3DolYA600xghRTsezbrA.MSUxwyHHcSReIZdjsJGAQoxQ.e', 'Alejandro Pérez', 'user');

-- 8. Comentarios en las tablas
COMMENT ON TABLE users IS 'Tabla de usuarios del sistema';
COMMENT ON TABLE activity_logs IS 'Registro de todas las actividades de los usuarios';
COMMENT ON TABLE user_sessions IS 'Sesiones activas de usuarios';

-- 9. Políticas RLS (Row Level Security) - opcional para mayor seguridad
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE activity_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_sessions ENABLE ROW LEVEL SECURITY;

-- Los usuarios solo pueden ver sus propios logs
CREATE POLICY "Users can view their own logs" ON activity_logs
    FOR SELECT USING (user_id = current_setting('app.current_user_id')::integer);

-- Los admins pueden ver todo
CREATE POLICY "Admins can view all logs" ON activity_logs
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM users 
            WHERE id = current_setting('app.current_user_id')::integer 
            AND role = 'admin'
        )
    );