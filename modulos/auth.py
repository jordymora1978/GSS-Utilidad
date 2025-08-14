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
    Autenticar usuario con persistencia de 12 horas
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
        
        # Generar token de sesión con 12 horas de duración
        session_token = generate_session_token()
        expires_at = datetime.now() + timedelta(hours=12)  # 12 horas de duración
        
        # Guardar sesión en BD
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
        st.session_state.token_expires_at = expires_at.timestamp()
        
        # CRÍTICO: Guardar en localStorage mediante JavaScript
        token_data = {
            "session_token": session_token,
            "user_id": user['id'],
            "username": user['username'],
            "user_role": user['role'],
            "user_full_name": user['full_name'],
            "expires_at": expires_at.timestamp(),
            "login_time": datetime.now().timestamp()
        }
        
        # JavaScript para guardar en localStorage
        st.markdown(f"""
        <script>
        // Guardar token de 12 horas en localStorage
        localStorage.setItem('gss_auth_token', JSON.stringify({token_data}));
        console.log('Token guardado en localStorage por 12 horas');
        </script>
        """, unsafe_allow_html=True)
        
        return {
            "success": True, 
            "message": "Login exitoso - Sesión persistente por 12 horas",
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
    """Cerrar sesión del usuario y limpiar localStorage"""
    supabase = get_supabase_client()
    
    if hasattr(st.session_state, 'session_token'):
        try:
            # Desactivar sesión en la base de datos
            supabase.table('user_sessions').update({
                'is_active': False
            }).eq('session_token', st.session_state.session_token).execute()
        except:
            pass
    
    # CRÍTICO: Limpiar localStorage mediante JavaScript
    st.markdown("""
    <script>
    // Limpiar token de localStorage
    localStorage.removeItem('gss_auth_token');
    console.log('Token removido de localStorage - Logout exitoso');
    </script>
    """, unsafe_allow_html=True)
    
    # Limpiar session_state completamente
    keys_to_clear = ['user_id', 'username', 'user_role', 'user_full_name', 
                     'session_token', 'logged_in', 'token_expires_at', 
                     'last_auth_check', 'localStorage_checked']
    
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]

def is_logged_in() -> bool:
    """Verificar si el usuario está logueado con persistencia localStorage"""
    # PRIORIDAD 1: Verificar localStorage al cargar la página
    if not hasattr(st.session_state, 'localStorage_checked'):
        # JavaScript para recuperar token de localStorage
        st.markdown("""
        <script>
        // Recuperar token de localStorage
        const storedToken = localStorage.getItem('gss_auth_token');
        if (storedToken) {
            const tokenData = JSON.parse(storedToken);
            const now = Date.now() / 1000;
            
            // Verificar si el token no ha expirado (12 horas)
            if (now < tokenData.expires_at) {
                // Token válido - enviar a Streamlit
                const sessionData = {
                    'token_found': true,
                    'session_token': tokenData.session_token,
                    'user_id': tokenData.user_id,
                    'username': tokenData.username,
                    'user_role': tokenData.user_role,
                    'user_full_name': tokenData.user_full_name,
                    'expires_at': tokenData.expires_at
                };
                
                // Marcar que encontramos token válido
                console.log('Token válido encontrado en localStorage');
                window.localStorage_session_data = sessionData;
            } else {
                // Token expirado - limpiar localStorage
                localStorage.removeItem('gss_auth_token');
                console.log('Token expirado - removido de localStorage');
                window.localStorage_session_data = {'token_found': false};
            }
        } else {
            window.localStorage_session_data = {'token_found': false};
        }
        </script>
        """, unsafe_allow_html=True)
        
        # Simular datos recuperados de localStorage (en producción vendría del JS)
        # Por ahora verificamos si ya tenemos session_state válido
        st.session_state.localStorage_checked = True
        
        # Si no tenemos sesión actual, intentar recuperar de localStorage
        # En una implementación completa, esto vendría del JavaScript
        if not hasattr(st.session_state, 'logged_in') or not st.session_state.logged_in:
            # Por ahora mantenemos la lógica existente
            pass
    
    # PRIORIDAD 2: Verificar session_state actual
    if not hasattr(st.session_state, 'logged_in') or not st.session_state.logged_in:
        return False
    
    if not hasattr(st.session_state, 'session_token'):
        return False
    
    # PRIORIDAD 3: Si tenemos verificación reciente (menos de 10 minutos), confiar en ella
    if hasattr(st.session_state, 'last_auth_check'):
        time_since_check = datetime.now() - st.session_state.last_auth_check
        if time_since_check < timedelta(minutes=10):  # Aumentado a 10 minutos
            return True
    
    # PRIORIDAD 4: Verificar token en base de datos solo cada 10 minutos
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
        
        # Verificar expiración (12 horas desde login)
        expires_at = datetime.fromisoformat(result.data[0]['expires_at'].replace('Z', '+00:00'))
        if datetime.now() > expires_at.replace(tzinfo=None):
            logout_user()
            return False
        
        # Marcar que verificamos recientemente
        st.session_state.last_auth_check = datetime.now()
        return True
        
    except Exception as e:
        # En caso de error, mantener sesión si el token no está expirado
        if hasattr(st.session_state, 'token_expires_at'):
            if datetime.now().timestamp() < st.session_state.token_expires_at:
                return True
        logout_user()
        return False

def refresh_token_if_needed():
    """Renovar token automáticamente si está cerca de expirar"""
    if not hasattr(st.session_state, 'token_expires_at'):
        return
    
    # Si faltan menos de 2 horas para expirar, renovar token
    current_time = datetime.now().timestamp()
    time_until_expiry = st.session_state.token_expires_at - current_time
    
    if time_until_expiry < 7200:  # Menos de 2 horas (7200 segundos)
        supabase = get_supabase_client()
        if not supabase:
            return
        
        try:
            # Generar nuevo token de 12 horas
            new_session_token = generate_session_token()
            new_expires_at = datetime.now() + timedelta(hours=12)
            
            # Actualizar token en BD
            supabase.table('user_sessions').update({
                'session_token': new_session_token,
                'expires_at': new_expires_at.isoformat()
            }).eq('user_id', st.session_state.user_id).execute()
            
            # Actualizar session_state
            st.session_state.session_token = new_session_token
            st.session_state.token_expires_at = new_expires_at.timestamp()
            
            # Actualizar localStorage
            token_data = {
                "session_token": new_session_token,
                "user_id": st.session_state.user_id,
                "username": st.session_state.username,
                "user_role": st.session_state.user_role,
                "user_full_name": st.session_state.user_full_name,
                "expires_at": new_expires_at.timestamp(),
                "login_time": datetime.now().timestamp()
            }
            
            st.markdown(f"""
            <script>
            // Actualizar token renovado en localStorage
            localStorage.setItem('gss_auth_token', JSON.stringify({token_data}));
            console.log('Token renovado automáticamente - 12 horas más');
            </script>
            """, unsafe_allow_html=True)
            
        except Exception as e:
            # Si falla la renovación, mantener sesión actual
            pass

def require_auth(allowed_roles: list = None):
    """
    Decorator para páginas que requieren autenticación
    allowed_roles: lista de roles permitidos ['admin', 'user']
    """
    if not is_logged_in():
        st.warning("🔐 Debes iniciar sesión para acceder a esta página")
        show_login_form()
        st.stop()
    
    # Renovar token automáticamente si es necesario
    refresh_token_if_needed()
    
    if allowed_roles and st.session_state.user_role not in allowed_roles:
        st.error("❌ No tienes permisos para acceder a esta página")
        st.stop()

def show_login_form():
    """Mostrar formulario de login en el sidebar"""
    
    with st.sidebar:
        st.markdown("### 🔐 Iniciar Sesión")
        
        # CSS para hacer el formulario más compacto en sidebar
        st.markdown("""
        <style>
        .stTextInput > div > div > input {
            height: 32px;
            font-size: 14px;
        }
        .stButton > button {
            width: 100%;
            height: 38px;
            background-color: #FF6B6B;
            color: white;
            border: none;
            border-radius: 4px;
            font-weight: bold;
            font-size: 14px;
        }
        .stButton > button:hover {
            background-color: #FF5252;
        }
        </style>
        """, unsafe_allow_html=True)
        
        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("👤 Usuario", placeholder="Usuario")
            password = st.text_input("🔒 Contraseña", type="password", placeholder="Contraseña")
            
            submit = st.form_submit_button("🚀 Entrar")
            
            if submit:
                if not username or not password:
                    st.error("❌ Completa todos los campos")
                else:
                    with st.spinner('Verificando...'):
                        result = login_user(username, password)
                        if result['success']:
                            st.success(f"✅ {result['message']}")
                            st.rerun()
                        else:
                            st.error(f"❌ {result['message']}")
        
        # Separador visual
        st.markdown("---")
        
    # Mensaje principal en el contenido
    st.info("👈 **Inicia sesión** en el panel lateral para acceder al sistema")
    st.markdown("---")
    st.markdown("""
    ## 🚀 GSS App - Sistema de Gestión
    
    **Características principales:**
    - 📦 **Consolidador**: Procesamiento inteligente de datos
    - 💱 **Gestión TRM**: Administración de tasas de cambio
    - 📊 **Reportes**: Análisis y visualización avanzada
    - 👥 **Usuarios**: Sistema completo de autenticación
    
    **Inicia sesión para comenzar** 👈
    """)

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