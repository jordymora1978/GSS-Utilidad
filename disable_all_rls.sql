-- Desactivar completamente RLS y políticas
ALTER TABLE users DISABLE ROW LEVEL SECURITY;
ALTER TABLE activity_logs DISABLE ROW LEVEL SECURITY;
ALTER TABLE user_sessions DISABLE ROW LEVEL SECURITY;

-- Eliminar todas las políticas
DROP POLICY IF EXISTS "Users can view their own logs" ON activity_logs;
DROP POLICY IF EXISTS "Admins can view all logs" ON activity_logs;

-- Verificar que podemos leer usuarios
SELECT username, full_name, role, is_active FROM users;