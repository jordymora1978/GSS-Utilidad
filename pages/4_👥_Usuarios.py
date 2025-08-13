"""
Página de gestión de usuarios
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import sys
import os

# Agregar la carpeta raíz al path para importar módulos
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modulos.auth import (
    require_auth, get_supabase_client, hash_password, 
    get_current_user, log_activity, show_user_info
)

st.set_page_config(
    page_title="👥 Gestión de Usuarios",
    page_icon="👥",
    layout="wide"
)

# Verificar autenticación (solo admins)
require_auth(allowed_roles=['admin'])

# Mostrar info del usuario en sidebar
show_user_info()

# Título principal
st.title("👥 Gestión de Usuarios")

# Obtener cliente Supabase
supabase = get_supabase_client()
if not supabase:
    st.error("❌ Error de conexión con la base de datos")
    st.stop()

# Tabs principales
tab1, tab2, tab3, tab4 = st.tabs(["👥 Lista de Usuarios", "➕ Nuevo Usuario", "📊 Actividad", "📈 Estadísticas"])

with tab1:
    st.header("📋 Lista de Usuarios")
    
    # Obtener usuarios
    try:
        result = supabase.table('users').select('*').order('created_at', desc=True).execute()
        users_df = pd.DataFrame(result.data)
        
        if not users_df.empty:
            # Formatear fechas
            for col in ['created_at', 'updated_at', 'last_login']:
                if col in users_df.columns:
                    users_df[col] = pd.to_datetime(users_df[col]).dt.strftime('%Y-%m-%d %H:%M')
            
            # Ocultar password_hash
            display_columns = ['id', 'username', 'email', 'full_name', 'role', 'is_active', 
                             'created_at', 'last_login']
            
            st.dataframe(
                users_df[display_columns],
                use_container_width=True,
                column_config={
                    "id": st.column_config.NumberColumn("ID", width="small"),
                    "username": st.column_config.TextColumn("Usuario", width="medium"),
                    "email": st.column_config.TextColumn("Email", width="large"),
                    "full_name": st.column_config.TextColumn("Nombre Completo", width="medium"),
                    "role": st.column_config.SelectboxColumn(
                        "Rol",
                        options=["admin", "user", "viewer"],
                        width="small"
                    ),
                    "is_active": st.column_config.CheckboxColumn("Activo", width="small"),
                    "created_at": st.column_config.TextColumn("Creado", width="medium"),
                    "last_login": st.column_config.TextColumn("Último Login", width="medium")
                }
            )
            
            # Estadísticas rápidas
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Usuarios", len(users_df))
            with col2:
                active_count = len(users_df[users_df['is_active'] == True])
                st.metric("Usuarios Activos", active_count)
            with col3:
                admin_count = len(users_df[users_df['role'] == 'admin'])
                st.metric("Administradores", admin_count)
            with col4:
                recent_logins = len(users_df[
                    pd.to_datetime(users_df['last_login'], errors='coerce') > 
                    datetime.now() - timedelta(days=7)
                ])
                st.metric("Logins (7 días)", recent_logins)
                
            # Acciones sobre usuarios
            st.subheader("🔧 Acciones")
            selected_user_id = st.selectbox(
                "Seleccionar usuario:",
                options=users_df['id'].tolist(),
                format_func=lambda x: f"{users_df[users_df['id']==x]['username'].iloc[0]} - {users_df[users_df['id']==x]['full_name'].iloc[0]}"
            )
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("🔄 Cambiar Estado"):
                    selected_user = users_df[users_df['id'] == selected_user_id].iloc[0]
                    new_status = not selected_user['is_active']
                    
                    supabase.table('users').update({
                        'is_active': new_status
                    }).eq('id', selected_user_id).execute()
                    
                    action = "activar" if new_status else "desactivar"
                    st.success(f"✅ Usuario {action}do exitosamente")
                    log_activity(f"user_{action}", f"Usuario {selected_user['username']} {action}do")
                    st.rerun()
            
            with col2:
                new_role = st.selectbox("Cambiar rol:", ["admin", "user", "viewer"])
                if st.button("👤 Actualizar Rol"):
                    supabase.table('users').update({
                        'role': new_role
                    }).eq('id', selected_user_id).execute()
                    
                    selected_user = users_df[users_df['id'] == selected_user_id].iloc[0]
                    st.success(f"✅ Rol actualizado a {new_role}")
                    log_activity("change_role", f"Rol de {selected_user['username']} cambiado a {new_role}")
                    st.rerun()
            
            with col3:
                if st.button("🗑️ Eliminar Usuario", type="secondary"):
                    if selected_user_id == get_current_user()['id']:
                        st.error("❌ No puedes eliminar tu propio usuario")
                    else:
                        # Confirmar eliminación
                        if st.checkbox("⚠️ Confirmar eliminación"):
                            selected_user = users_df[users_df['id'] == selected_user_id].iloc[0]
                            supabase.table('users').delete().eq('id', selected_user_id).execute()
                            st.success("✅ Usuario eliminado exitosamente")
                            log_activity("delete_user", f"Usuario {selected_user['username']} eliminado")
                            st.rerun()
        
        else:
            st.info("📭 No hay usuarios registrados")
            
    except Exception as e:
        st.error(f"❌ Error al cargar usuarios: {e}")

with tab2:
    st.header("➕ Crear Nuevo Usuario")
    
    with st.form("new_user_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            new_username = st.text_input("👤 Nombre de usuario*")
            new_email = st.text_input("📧 Email*")
            new_full_name = st.text_input("👨‍💼 Nombre completo*")
        
        with col2:
            new_password = st.text_input("🔒 Contraseña*", type="password")
            confirm_password = st.text_input("🔒 Confirmar contraseña*", type="password")
            new_role = st.selectbox("👤 Rol", ["user", "admin", "viewer"])
        
        submit_new_user = st.form_submit_button("✅ Crear Usuario", type="primary")
        
        if submit_new_user:
            # Validaciones
            errors = []
            
            if not all([new_username, new_email, new_full_name, new_password]):
                errors.append("Todos los campos marcados con * son obligatorios")
            
            if new_password != confirm_password:
                errors.append("Las contraseñas no coinciden")
            
            if len(new_password) < 6:
                errors.append("La contraseña debe tener al menos 6 caracteres")
            
            if "@" not in new_email:
                errors.append("Email no válido")
            
            if errors:
                for error in errors:
                    st.error(f"❌ {error}")
            else:
                try:
                    # Verificar si el usuario ya existe
                    existing = supabase.table('users').select('id').eq('username', new_username).execute()
                    if existing.data:
                        st.error("❌ El nombre de usuario ya existe")
                    else:
                        # Crear usuario
                        password_hash = hash_password(new_password)
                        
                        result = supabase.table('users').insert({
                            'username': new_username,
                            'email': new_email,
                            'password_hash': password_hash,
                            'full_name': new_full_name,
                            'role': new_role
                        }).execute()
                        
                        st.success("✅ Usuario creado exitosamente!")
                        log_activity("create_user", f"Usuario {new_username} creado con rol {new_role}")
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"❌ Error al crear usuario: {e}")

with tab3:
    st.header("📊 Registro de Actividad")
    
    # Filtros
    col1, col2, col3 = st.columns(3)
    
    with col1:
        days_filter = st.selectbox("📅 Período", [1, 7, 30, 90], index=1)
    
    with col2:
        # Obtener usuarios para filtro
        users_result = supabase.table('users').select('username').execute()
        usernames = ['Todos'] + [u['username'] for u in users_result.data]
        user_filter = st.selectbox("👤 Usuario", usernames)
    
    with col3:
        actions = ['Todos', 'upload_file', 'process_data', 'create_user', 'login', 'logout']
        action_filter = st.selectbox("🔄 Acción", actions)
    
    # Obtener logs
    try:
        query = supabase.table('activity_logs').select('*')
        
        # Aplicar filtros
        start_date = datetime.now() - timedelta(days=days_filter)
        query = query.gte('created_at', start_date.isoformat())
        
        if user_filter != 'Todos':
            query = query.eq('username', user_filter)
        
        if action_filter != 'Todos':
            query = query.eq('action', action_filter)
        
        result = query.order('created_at', desc=True).limit(100).execute()
        
        if result.data:
            logs_df = pd.DataFrame(result.data)
            
            # Formatear fecha
            logs_df['created_at'] = pd.to_datetime(logs_df['created_at']).dt.strftime('%Y-%m-%d %H:%M:%S')
            
            # Mostrar logs
            display_cols = ['created_at', 'username', 'action', 'description', 'file_type', 'records_count', 'status']
            
            st.dataframe(
                logs_df[display_cols],
                use_container_width=True,
                column_config={
                    "created_at": st.column_config.TextColumn("Fecha", width="medium"),
                    "username": st.column_config.TextColumn("Usuario", width="small"),
                    "action": st.column_config.TextColumn("Acción", width="medium"),
                    "description": st.column_config.TextColumn("Descripción", width="large"),
                    "file_type": st.column_config.TextColumn("Tipo", width="small"),
                    "records_count": st.column_config.NumberColumn("Registros", width="small"),
                    "status": st.column_config.SelectboxColumn(
                        "Estado",
                        options=["success", "error", "warning"],
                        width="small"
                    )
                }
            )
        else:
            st.info("📭 No hay actividad registrada para los filtros seleccionados")
            
    except Exception as e:
        st.error(f"❌ Error al cargar logs: {e}")

with tab4:
    st.header("📈 Estadísticas de Uso")
    
    try:
        # Estadísticas de actividad por día
        result = supabase.table('activity_logs').select('*').gte(
            'created_at', (datetime.now() - timedelta(days=30)).isoformat()
        ).execute()
        
        if result.data:
            logs_df = pd.DataFrame(result.data)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📊 Actividad por Usuario (30 días)")
                user_activity = logs_df.groupby('username').size().reset_index(columns=['Actividades'])
                st.bar_chart(user_activity.set_index('username'))
            
            with col2:
                st.subheader("🎯 Acciones Más Frecuentes")
                action_counts = logs_df['action'].value_counts()
                st.bar_chart(action_counts)
            
            # Actividad por día
            st.subheader("📅 Actividad Diaria")
            logs_df['date'] = pd.to_datetime(logs_df['created_at']).dt.date
            daily_activity = logs_df.groupby('date').size().reset_index(columns=['Actividades'])
            st.line_chart(daily_activity.set_index('date'))
            
        else:
            st.info("📭 No hay suficiente data para generar estadísticas")
            
    except Exception as e:
        st.error(f"❌ Error al cargar estadísticas: {e}")

# Footer
st.markdown("---")
st.caption(f"👤 Gestionado por: {get_current_user()['full_name']} | Sistema Contable v1.0")