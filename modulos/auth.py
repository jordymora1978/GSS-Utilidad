"""
Sistema de autenticación para el sistema contable
"""
import streamlit as st
import bcrypt
import secrets
import hashlib
from datetime import datetime, timedelta
from supabase import create_client, Client
import os
from typing import Optional, Dict, Any

# Configuración de Supabase
def get_supabase_client():
    """Obtener cliente de Supabase"""
    try:
        # Intentar importar desde config.py primero
        import config
        url = config.SUPABASE_URL
        key = config.SUPABASE_KEY
    except:
        # Si no funciona, usar variables de entorno
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
    
    if not url or not key:
        st.error("❌ Configuración de Supabase no encontrada")
        return None
    return create_client(url, key)

def hash_password(password: str) -> str:
    """Hashear contraseña con bcrypt"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verificar contraseña"""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except:
        return False

def generate_session_token() -> str:
    """Generar token de sesión único"""
    return secrets.token_urlsafe(32)

def login_user(username: str, password: str) -> Dict[str, Any]:
    """
    Autenticar usuario
    Returns: dict con 'success', 'message', 'user_data'
    """
    supabase = get_supabase_client()
    if not supabase:
        return {"success": False, "message": "Error de conexión"}
    
    try:
        # Buscar usuario
        result = supabase.table('users').select('*').eq('username', username).eq('is_active', True).execute()
        
        if not result.data:
            return {"success": False, "message": "Usuario o contraseña incorrectos"}
        
        user = result.data[0]
        
        # Verificar contraseña
        if not verify_password(password, user['password_hash']):
            return {"success": False, "message": "Usuario o contraseña incorrectos"}
        
        # Generar token de sesión
        session_token = generate_session_token()
        expires_at = datetime.now() + timedelta(hours=24)  # 24 horas
        
        # Guardar sesión
        supabase.table('user_sessions').insert({
            'user_id': user['id'],
            'session_token': session_token,
            'expires_at': expires_at.isoformat()
        }).execute()
        
        # Actualizar último login
        supabase.table('users').update({
            'last_login': datetime.now().isoformat()
        }).eq('id', user['id']).execute()
        
        # Guardar en session_state
        st.session_state.user_id = user['id']
        st.session_state.username = user['username']
        st.session_state.user_role = user['role']
        st.session_state.user_full_name = user['full_name']
        st.session_state.session_token = session_token
        st.session_state.logged_in = True
        
        return {
            "success": True, 
            "message": "Login exitoso",
            "user_data": {
                "id": user['id'],
                "username": user['username'],
                "role": user['role'],
                "full_name": user['full_name']
            }
        }
        
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}

def logout_user():
    """Cerrar sesión del usuario"""
    supabase = get_supabase_client()
    
    if hasattr(st.session_state, 'session_token'):
        try:
            # Desactivar sesión en la base de datos
            supabase.table('user_sessions').update({
                'is_active': False
            }).eq('session_token', st.session_state.session_token).execute()
        except:
            pass
    
    # Limpiar session_state
    for key in ['user_id', 'username', 'user_role', 'user_full_name', 'session_token', 'logged_in']:
        if key in st.session_state:
            del st.session_state[key]

def is_logged_in() -> bool:
    """Verificar si el usuario está logueado"""
    if not hasattr(st.session_state, 'logged_in') or not st.session_state.logged_in:
        return False
    
    if not hasattr(st.session_state, 'session_token'):
        return False
    
    # Verificar token en base de datos
    supabase = get_supabase_client()
    if not supabase:
        return False
    
    try:
        result = supabase.table('user_sessions').select('expires_at').eq(
            'session_token', st.session_state.session_token
        ).eq('is_active', True).execute()
        
        if not result.data:
            logout_user()
            return False
        
        # Verificar expiración
        expires_at = datetime.fromisoformat(result.data[0]['expires_at'].replace('Z', '+00:00'))
        if datetime.now() > expires_at.replace(tzinfo=None):
            logout_user()
            return False
        
        return True
        
    except Exception as e:
        logout_user()
        return False

def require_auth(allowed_roles: list = None):
    """
    Decorator para páginas que requieren autenticación
    allowed_roles: lista de roles permitidos ['admin', 'user']
    """
    if not is_logged_in():
        st.warning("🔐 Debes iniciar sesión para acceder a esta página")
        show_login_form()
        st.stop()
    
    if allowed_roles and st.session_state.user_role not in allowed_roles:
        st.error("❌ No tienes permisos para acceder a esta página")
        st.stop()

def show_login_form():
    """Mostrar formulario de login"""
    st.title("🔐 Iniciar Sesión")
    
    with st.form("login_form"):
        username = st.text_input("👤 Usuario")
        password = st.text_input("🔒 Contraseña", type="password")
        submit = st.form_submit_button("🚀 Iniciar Sesión")
        
        if submit:
            if not username or not password:
                st.error("❌ Por favor completa todos los campos")
            else:
                result = login_user(username, password)
                if result['success']:
                    st.success(f"✅ {result['message']}")
                    st.rerun()
                else:
                    st.error(f"❌ {result['message']}")

def get_current_user() -> Dict[str, Any]:
    """Obtener información del usuario actual"""
    if not is_logged_in():
        return {}
    
    return {
        "id": st.session_state.get('user_id'),
        "username": st.session_state.get('username'),
        "role": st.session_state.get('user_role'),
        "full_name": st.session_state.get('user_full_name')
    }

def log_activity(action: str, description: str = None, file_type: str = None, 
                file_name: str = None, records_count: int = None, 
                status: str = 'success'):
    """
    Registrar actividad del usuario
    """
    if not is_logged_in():
        return
    
    supabase = get_supabase_client()
    if not supabase:
        return
    
    try:
        supabase.table('activity_logs').insert({
            'user_id': st.session_state.user_id,
            'username': st.session_state.username,
            'action': action,
            'description': description,
            'file_type': file_type,
            'file_name': file_name,
            'records_count': records_count,
            'status': status
        }).execute()
    except Exception as e:
        st.error(f"Error logging activity: {e}")

def show_user_info():
    """Mostrar información del usuario en la barra lateral"""
    if is_logged_in():
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 👤 Usuario Actual")
        st.sidebar.info(f"**{st.session_state.user_full_name}**")
        st.sidebar.caption(f"@{st.session_state.username} | {st.session_state.user_role}")
        
        if st.sidebar.button("🚪 Cerrar Sesión"):
            logout_user()
            st.rerun()