import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import sys
import os

# IMPORTANTE: Configuración de página DEBE IR PRIMERO
st.set_page_config(
    page_title="Sistema Contable Multipaís",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Función para verificar conexión a Supabase
def check_database_connection():
    """Verifica la conexión a Supabase"""
    try:
        from supabase import create_client
        import config
        
        supabase = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
        # Test de conexión
        result = supabase.table('consolidated_orders').select('id').limit(1).execute()
        return True, supabase
    except Exception as e:
        return False, str(e)

# Función para obtener estadísticas
def get_database_stats():
    """Obtiene estadísticas de la base de datos"""
    try:
        from supabase import create_client
        import config
        
        supabase = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
        
        # Contar registros totales
        total_result = supabase.table('consolidated_orders').select('*', count='exact', head=True).execute()
        total_records = total_result.count if hasattr(total_result, 'count') else 0
        
        # Obtener cuentas únicas
        accounts_result = supabase.table('consolidated_orders').select('account_name').execute()
        unique_accounts = 0
        account_distribution = {}
        
        if accounts_result.data:
            df = pd.DataFrame(accounts_result.data)
            if 'account_name' in df.columns:
                unique_accounts = df['account_name'].nunique()
                account_distribution = df['account_name'].value_counts().to_dict()
        
        # Obtener fecha del registro más reciente
        latest_result = supabase.table('consolidated_orders').select('date_created').order('date_created', desc=True).limit(1).execute()
        latest_date = None
        if latest_result.data and len(latest_result.data) > 0:
            latest_date = latest_result.data[0].get('date_created', 'N/A')
        
        return {
            'total_records': total_records,
            'unique_accounts': unique_accounts,
            'account_distribution': account_distribution,
            'latest_date': latest_date
        }
    except Exception as e:
        return None

# Crear navegación en el sidebar
with st.sidebar:
    st.title("📋 Sistema Contable")
    st.markdown("---")
    
    # Menú de navegación
    pagina = st.selectbox(
        "🔍 Selecciona un módulo:",
        ["🏠 Inicio", "📦 Consolidador", "💱 Gestión TRM", "📊 Reportes", "🔄 Corrector de Valores", "🔍 Debug CXP", "🚀 Actualizar TODOS CXP", "⚠️ Eliminar y Recargar"],
        label_visibility="visible"
    )
    
    st.markdown("---")
    
    # Estado de conexión
    st.subheader("📡 Estado del Sistema")
    
    db_connected, db_info = check_database_connection()
    
    if db_connected:
        st.success("✅ Base de Datos Conectada")
        
        # Obtener estadísticas
        stats = get_database_stats()
        if stats:
            st.metric("Total Registros", f"{stats['total_records']:,}")
            st.metric("Cuentas Activas", stats['unique_accounts'])
            if stats['latest_date']:
                st.caption(f"Última actualización: {stats['latest_date']}")
    else:
        st.error("❌ Sin conexión a BD")
        with st.expander("Ver detalles del error"):
            st.code(db_info)
    
    st.markdown("---")
    
    # Información adicional
    st.caption("**Sistema Contable Multipaís**")
    st.caption("Versión 1.0 - 2025")
    st.caption("© Todos los derechos reservados")

# NAVEGACIÓN PRINCIPAL
if pagina == "🏠 Inicio":
    # PÁGINA DE INICIO
    st.title("💼 Sistema Contable Multipaís")
    st.markdown("### Panel de Control Principal")
    st.markdown("---")
    
    # Mensaje de bienvenida
    st.markdown("""
    Bienvenido al **Sistema Contable Multipaís**, una plataforma integral para la gestión 
    de órdenes, tasas de cambio y reportes de utilidad para operaciones en múltiples países.
    """)
    
    # Cards informativos
    st.subheader("📌 Módulos Disponibles")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        with st.container():
            st.info("""
            ### 📦 Consolidador de Órdenes
            
            **Procesa archivos de:**
            - Drapify (Base principal)
            - Logistics (Costos envío)
            - Aditionals (Costos extra)
            - CXP (Cuentas por pagar)
            
            **Características:**
            - ✅ Detección de duplicados
            - ✅ Actualización incremental
            - ✅ Validación automática
            - ✅ Logs de procesamiento
            """)
    
    with col2:
        with st.container():
            st.success("""
            ### 💱 Gestión de TRM
            
            **Países soportados:**
            - 🇨🇴 Colombia (COP)
            - 🇨🇱 Chile (CLP)
            - 🇵🇪 Perú (PEN)
            
            **Funciones:**
            - ✅ Actualización diaria
            - ✅ Historial de tasas
            - ✅ Gráficos de tendencia
            - ✅ Consulta por fecha
            """)
    
    with col3:
        with st.container():
            st.warning("""
            ### 📊 Reportes de Utilidad
            
            **Tipos disponibles:**
            - TODOENCARGO
            - MEGA PERU
            - MEGA CHILE
            - FABORCARGO
            - DTPT (División)
            
            **Exportación:**
            - ✅ Excel formateado
            - ✅ Filtros avanzados
            - ✅ Gráficos incluidos
            """)
    
    st.markdown("---")
    
    # Estadísticas generales
    if db_connected:
        st.subheader("📈 Estadísticas Generales")
        
        stats = get_database_stats()
        if stats and stats['account_distribution']:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### Distribución por Cuenta")
                # Crear DataFrame para mejor visualización
                df_accounts = pd.DataFrame(
                    list(stats['account_distribution'].items()),
                    columns=['Cuenta', 'Cantidad']
                )
                df_accounts = df_accounts.sort_values('Cantidad', ascending=False)
                st.dataframe(df_accounts, use_container_width=True, hide_index=True)
            
            with col2:
                st.markdown("#### Resumen Rápido")
                total = sum(stats['account_distribution'].values())
                top_account = max(stats['account_distribution'], key=stats['account_distribution'].get)
                top_count = stats['account_distribution'][top_account]
                
                st.metric("Total de Órdenes", f"{total:,}")
                st.metric("Cuenta Principal", top_account)
                st.metric("Órdenes (Principal)", f"{top_count:,}")
                
                if stats['latest_date']:
                    st.info(f"📅 Última actualización: **{stats['latest_date']}**")
    
    # Instrucciones de uso
    st.markdown("---")
    st.subheader("🚀 Cómo empezar")
    
    st.markdown("""
    1. **📦 Consolidador**: Comienza cargando tus archivos de órdenes
    2. **💱 TRM**: Actualiza las tasas de cambio del día
    3. **📊 Reportes**: Genera reportes de utilidad por cuenta
    
    💡 **Tip**: Mantén las TRM actualizadas diariamente para cálculos precisos
    """)

elif pagina == "📦 Consolidador":
    # CARGAR PÁGINA DE CONSOLIDADOR
    try:
        # Verificar si el archivo existe
        if os.path.exists('pages/1_📦_Consolidador.py'):
            exec(open('pages/1_📦_Consolidador.py', encoding='utf-8').read())
        else:
            st.error("❌ No se encontró el archivo del Consolidador")
            st.info("Verifica que existe: pages/1_📦_Consolidador.py")
    except Exception as e:
        st.error(f"Error cargando Consolidador: {str(e)}")
        st.info("Revisa que el archivo pages/1_📦_Consolidador.py existe y no tiene errores")

elif pagina == "💱 Gestión TRM":
    # CARGAR MÓDULO DE TRM
    try:
        # Opción 1: Si está en pages/
        if os.path.exists('pages/2_💱_Gestión_TRM.py'):
            exec(open('pages/2_💱_Gestión_TRM.py', encoding='utf-8').read())
        # Opción 2: Si está como módulo
        else:
            from modulos.gestion_trm import mostrar_interfaz_trm
            mostrar_interfaz_trm()
    except Exception as e:
        st.error(f"Error cargando Gestión TRM: {str(e)}")
        st.info("Verifica que existe el archivo o módulo de gestión TRM")

elif pagina == "📊 Reportes":
    # CARGAR PÁGINA DE REPORTES
    try:
        # Verificar si el archivo existe
        if os.path.exists('pages/3_📊_Reportes.py'):
            exec(open('pages/3_📊_Reportes.py', encoding='utf-8').read())
        else:
            # Si no existe, mostrar versión básica
            st.title("📊 Módulo de Reportes de Utilidad")
            
            import config
            from modulos.gestion_trm import obtener_trm_fecha
            from supabase import create_client
            from datetime import date, timedelta
            
            supabase = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
            
            # Selector de tipo de reporte
            tipo_reporte = st.selectbox(
                "Selecciona el tipo de reporte:",
                ["TODOENCARGO", "MEGA PERU", "MEGA CHILE", "FABORCARGO", "DTPT"]
            )
            
            # Filtros de fecha
            col1, col2 = st.columns(2)
            with col1:
                fecha_inicio = st.date_input("Fecha inicio", value=date.today() - timedelta(days=30))
            with col2:
                fecha_fin = st.date_input("Fecha fin", value=date.today())
            
            # Botón para generar reporte
            if st.button("🔍 Generar Reporte", type="primary"):
                with st.spinner(f"Generando reporte {tipo_reporte}..."):
                    try:
                        # Mapeo de cuentas por tipo de reporte
                        cuentas_map = {
                            "TODOENCARGO": ["1-TODOENCARGO-CO"],
                            "MEGA PERU": ["4-MEGA TIENDAS PERUANAS"],
                            "MEGA CHILE": ["2-MEGATIENDA SPA", "3-VEENDELO"],
                            "FABORCARGO": ["7-FABORCARGO SAS", "8-FABORCARGO"],
                            "DTPT": ["5-DETODOPARATODOS", "6-COMPRAFACIL", "7-COMPRA-YA"]
                        }
                        
                        # Obtener las cuentas para este tipo de reporte
                        cuentas = cuentas_map.get(tipo_reporte, [])
                        
                        # Query base
                        query = supabase.table('consolidated_orders').select('*')
                        
                        # Filtrar por cuentas
                        if cuentas:
                            query = query.in_('account_name', cuentas)
                        
                        # Filtrar por fechas
                        query = query.gte('date_created', str(fecha_inicio))
                        query = query.lte('date_created', str(fecha_fin))
                        
                        # Ejecutar query
                        result = query.execute()
                        
                        if result.data:
                            df = pd.DataFrame(result.data)
                            st.success(f"✅ Se encontraron {len(df)} registros")
                            
                            # Mostrar vista previa
                            st.subheader("Vista previa de datos")
                            st.dataframe(df.head(10), use_container_width=True)
                            
                            # Botón para descargar
                            csv = df.to_csv(index=False)
                            st.download_button(
                                label="📥 Descargar CSV",
                                data=csv,
                                file_name=f"reporte_{tipo_reporte}_{fecha_inicio}_{fecha_fin}.csv",
                                mime="text/csv"
                            )
                            
                            st.info("💡 Para cálculos de utilidad completos, actualiza el archivo de reportes")
                            
                        else:
                            st.warning("No se encontraron registros para el período seleccionado")
                            
                    except Exception as e:
                        st.error(f"Error al generar reporte: {str(e)}")
    
    except Exception as e:
        st.error(f"Error cargando Reportes: {str(e)}")
        st.info("El módulo de reportes se está cargando...")

elif pagina == "🔄 Corrector de Valores":
    # CARGAR CORRECTOR DE VALORES TROCADOS
    try:
        if os.path.exists('corregir_valores_trocados.py'):
            exec(open('corregir_valores_trocados.py', encoding='utf-8').read())
        else:
            st.error("❌ No se encontró el archivo del Corrector de Valores")
            st.info("Verifica que existe: corregir_valores_trocados.py")
    except Exception as e:
        st.error(f"Error cargando Corrector de Valores: {str(e)}")
        st.info("Revisa que el archivo corregir_valores_trocados.py existe y no tiene errores")

elif pagina == "🔍 Debug CXP":
    # CARGAR DEBUG CXP MAPEO
    try:
        if os.path.exists('debug_cxp_mapeo.py'):
            exec(open('debug_cxp_mapeo.py', encoding='utf-8').read())
        else:
            st.error("❌ No se encontró el archivo de Debug CXP")
            st.info("Verifica que existe: debug_cxp_mapeo.py")
    except Exception as e:
        st.error(f"Error cargando Debug CXP: {str(e)}")
        st.info("Revisa que el archivo debug_cxp_mapeo.py existe y no tiene errores")

elif pagina == "🚀 Actualizar TODOS CXP":
    # CARGAR ACTUALIZAR TODOS CXP
    try:
        if os.path.exists('actualizar_todos_cxp.py'):
            exec(open('actualizar_todos_cxp.py', encoding='utf-8').read())
        else:
            st.error("❌ No se encontró el archivo actualizar_todos_cxp.py")
            st.info("Verifica que existe: actualizar_todos_cxp.py")
    except Exception as e:
        st.error(f"Error cargando Actualizar TODOS CXP: {str(e)}")
        st.info("Revisa que el archivo actualizar_todos_cxp.py existe y no tiene errores")

elif pagina == "⚠️ Eliminar y Recargar":
    # CARGAR ELIMINAR Y RECARGAR
    try:
        if os.path.exists('eliminar_y_recargar.py'):
            exec(open('eliminar_y_recargar.py', encoding='utf-8').read())
        else:
            st.error("❌ No se encontró el archivo eliminar_y_recargar.py")
            st.info("Verifica que existe: eliminar_y_recargar.py")
    except Exception as e:
        st.error(f"Error cargando Eliminar y Recargar: {str(e)}")
        st.info("Revisa que el archivo eliminar_y_recargar.py existe y no tiene errores")

# Footer global
st.markdown("---")
st.caption("Sistema Contable Multipaís | Desarrollado para gestión integral de operaciones")
