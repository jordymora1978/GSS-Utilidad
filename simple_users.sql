-- Insertar usuarios directamente sin RLS
INSERT INTO users (username, email, password_hash, full_name, role) VALUES 
('admin', 'admin@empresa.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewLdoQQGgA8r8F/q', 'Administrador del Sistema', 'admin'),
('alejandro.perez', 'alejandro.perez@empresa.com', '$2b$12$5Ew1xfHPYJnG8c2iJN8F5OSaVfT5QZnczNvI8xmKxw1VT6Q8cTntu', 'Alejandro Pérez', 'user');

-- Verificar inserción
SELECT username, full_name, role FROM users;