-- Desactivar RLS temporalmente para crear usuarios
ALTER TABLE users DISABLE ROW LEVEL SECURITY;
ALTER TABLE activity_logs DISABLE ROW LEVEL SECURITY;
ALTER TABLE user_sessions DISABLE ROW LEVEL SECURITY;

-- También eliminar las políticas problemáticas
DROP POLICY IF EXISTS "Users can view their own logs" ON activity_logs;
DROP POLICY IF EXISTS "Admins can view all logs" ON activity_logs;