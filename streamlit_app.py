import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import sys
import os

# Importar sistema de autenticación
try:
    from modulos.auth import is_logged_in, show_login_form, get_current_user, show_user_info
    AUTH_AVAILABLE = True
except ImportError:
    AUTH_AVAILABLE = False

# IMPORTANTE: Configuración de página DEBE IR PRIMERO
st.set_page_config(
    page_title="GSS App - Sistema de Gestión",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado para ocultar TODOS los elementos de Streamlit
hide_streamlit_style = """
<style>
/* Ocultar el menú de hamburguesa */
#MainMenu {visibility: hidden !important;}

/* Ocultar el footer completo */
footer {visibility: hidden !important;}
.footer {display: none !important;}

/* Ocultar el header completo */
header {visibility: hidden !important;}
.stHeader {display: none !important;}

/* Ocultar toolbar y sus elementos */
[data-testid="stToolbar"] {display: none !important;}
.stToolbar {display: none !important;}

/* Ocultar botones específicos */
.stDeployButton {display: none !important;}
.stActionButton {display: none !important;}

/* Ocultar badges y links de Streamlit */
.viewerBadge_container__1QSob {display: none !important;}
.viewerBadge_link__1S2v2 {display: none !important;}
.viewerBadge_text__1JaDK {display: none !important;}

/* Ocultar elementos del header superior */
.stApp > header {display: none !important;}
.stApp > div[data-testid="stHeader"] {display: none !important;}

/* Ocultar el área completa del header */
section[data-testid="stHeader"] {display: none !important;}

/* Ocultar links específicos */
a[href*="github"] {display: none !important;}
a[href*="streamlit"] {display: none !important;}

/* Ocultar el elemento "Fork this app" */
.css-1dp5vir {display: none !important;}

/* Ocultar marca roja de Streamlit */
.css-1544g2n {display: none !important;}
.css-18e3th9 {display: none !important;}

/* Limpiar completamente el header */
.block-container {padding-top: 1rem !important;}

/* ELIMINACIÓN AGRESIVA DEL BADGE INFERIOR */
/* Todos los posibles selectores para el badge "Made with Streamlit" */
[data-testid="stBottom"] {display: none !important;}
.streamlit-footer {display: none !important;}
.footer {display: none !important;}
div[data-testid="stStatusWidget"] {display: none !important;}
.StatusWidget {display: none !important;}

/* Selectores adicionales para badges */
div[class*="viewerBadge"] {display: none !important;}
div[class*="made-with-streamlit"] {display: none !important;}
div[class*="streamlit-badge"] {display: none !important;}

/* Ocultar cualquier elemento que contenga "streamlit" */
*[class*="streamlit"]:not(.stApp):not([data-testid]) {display: none !important;}

/* Footer positioning fix */
.main .block-container {padding-bottom: 1rem !important;}

/* Remover completamente el área del footer */
.stApp > footer {display: none !important;}
.stApp footer {display: none !important;}
footer.stApp {display: none !important;}

/* Último recurso - ocultar por contenido */
*:contains("Made with") {display: none !important;}
*:contains("Streamlit") {display: none !important;}

/* ELIMINACIÓN NUCLEAR DEL BADGE - TODOS LOS MÉTODOS */
/* Por atributos data */
[data-testid*="status"] {display: none !important;}
[data-testid*="Status"] {display: none !important;}
[data-testid*="badge"] {display: none !important;}
[data-testid*="Badge"] {display: none !important;}

/* Por clases CSS específicas de versiones */
.css-1v0mbdj {display: none !important;}
.css-18e3th9 {display: none !important;}
.css-1544g2n {display: none !important;}
.css-k1ih3n {display: none !important;}
.css-1dp5vir {display: none !important;}

/* Fuerza bruta - cualquier div pequeño en la parte inferior */
div[style*="position: fixed"][style*="bottom"] {display: none !important;}
div[style*="position: absolute"][style*="bottom"] {display: none !important;}

/* Eliminar por z-index alto (badges suelen tener z-index alto) */
*[style*="z-index: 999"] {display: none !important;}
*[style*="z-index: 1000"] {display: none !important;}

/* Ocultar elementos muy pequeños que podrían ser badges */
div[style*="height: 20px"], div[style*="height: 30px"], div[style*="height: 40px"] {
    display: none !important;
}

/* Eliminar cualquier link externo */
a[href*="streamlit.io"] {display: none !important;}
a[href*="github.com"] {display: none !important;}
a[target="_blank"] {display: none !important;}

/* ELIMINAR ESPECÍFICAMENTE LOS LINKS QUE MENCIONASTE */
a[href*="share.streamlit.io/user/jordymora1978"] {display: none !important;}
a[href*="streamlit.io/cloud"] {display: none !important;}
a[href*="share.streamlit.io"] {display: none !important;}

/* Eliminar botones de deploy/share específicos */
button[title*="Deploy"] {display: none !important;}
button[title*="Share"] {display: none !important;}
button[aria-label*="Deploy"] {display: none !important;}
button[aria-label*="Share"] {display: none !important;}

/* Eliminar elementos con iconos de compartir/deploy */
[data-testid*="deploy"] {display: none !important;}
[data-testid*="share"] {display: none !important;}
[data-testid*="Deploy"] {display: none !important;}
[data-testid*="Share"] {display: none !important;}

/* Ocultar elementos que contengan estos textos */
*:contains("Deploy") {display: none !important;}
*:contains("Share") {display: none !important;}
*:contains("share.streamlit.io") {display: none !important;}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# JavaScript ULTRA agresivo para eliminar badges
remove_badges_js = """
<script>
function ultraRemoveBadges() {
    // MÉTODO 1: Eliminar por selectores específicos
    const selectors = [
        '[data-testid="stStatusWidget"]',
        '[data-testid="stBottom"]', 
        '.viewerBadge_container__1QSob',
        '.viewerBadge_link__1S2v2',
        '.viewerBadge_text__1JaDK',
        'div[class*="viewerBadge"]',
        'div[class*="streamlit"]',
        'div[class*="StatusWidget"]',
        '[class*="made-with"]',
        'footer',
        '.footer'
    ];
    
    selectors.forEach(selector => {
        document.querySelectorAll(selector).forEach(el => {
            if (el && !el.closest('.stApp')) {
                el.style.display = 'none !important';
                el.style.visibility = 'hidden !important';
                el.style.opacity = '0 !important';
                el.style.height = '0 !important';
                el.style.overflow = 'hidden !important';
                el.remove();
            }
        });
    });
    
    // MÉTODO 2: Por contenido de texto (más agresivo)
    document.querySelectorAll('*').forEach(el => {
        if (el.textContent) {
            const text = el.textContent.toLowerCase();
            if (text.includes('made with') || 
                text.includes('streamlit') || 
                text.includes('fork') ||
                text.includes('github') ||
                text.includes('deploy') ||
                text.includes('share')) {
                if (!el.closest('.stApp') && !el.classList.contains('stApp')) {
                    el.style.display = 'none !important';
                    el.remove();
                }
            }
        }
    });
    
    // MÉTODO ESPECÍFICO: Eliminar links exactos que mencionaste
    const specificUrls = [
        'share.streamlit.io/user/jordymora1978',
        'streamlit.io/cloud',
        'share.streamlit.io'
    ];
    
    document.querySelectorAll('a').forEach(link => {
        if (link.href) {
            specificUrls.forEach(url => {
                if (link.href.includes(url)) {
                    link.style.display = 'none !important';
                    link.remove();
                }
            });
        }
    });
    
    // MÉTODO 3: Eliminar todos los iframes (a veces el badge está ahí)
    document.querySelectorAll('iframe').forEach(iframe => {
        if (iframe.src && (iframe.src.includes('streamlit') || iframe.src.includes('github'))) {
            iframe.remove();
        }
    });
    
    // MÉTODO 4: Limpiar el DOM completamente del footer
    const footer = document.querySelector('footer');
    if (footer) footer.remove();
    
    // MÉTODO 5: Ocultar elementos por posición (último recurso)
    document.querySelectorAll('div').forEach(div => {
        const rect = div.getBoundingClientRect();
        if (rect.bottom > window.innerHeight - 100 && div.textContent && 
            (div.textContent.includes('Made') || div.textContent.includes('Streamlit'))) {
            div.remove();
        }
    });
}

// Ejecutar inmediatamente y luego cada 500ms
ultraRemoveBadges();
setInterval(ultraRemoveBadges, 500);

// FUERZA BRUTA ABSOLUTA - Inspección DOM cada 100ms
setInterval(() => {
    // Eliminar CUALQUIER elemento que contenga "streamlit" en href
    document.querySelectorAll('a[href]').forEach(link => {
        if (link.href.includes('streamlit')) {
            console.log('Destroying Streamlit link:', link.href);
            link.parentNode && link.parentNode.removeChild(link);
        }
    });
    
    // Eliminar elementos por texto visible
    document.querySelectorAll('*').forEach(el => {
        const text = el.innerText || el.textContent || '';
        if (text.includes('Made with') || text.includes('Deploy') || text.includes('Share')) {
            if (el.tagName !== 'BODY' && el.tagName !== 'HTML' && !el.classList.contains('stApp')) {
                console.log('Destroying text element:', text.substring(0, 50));
                el.style.display = 'none !important';
                el.remove();
            }
        }
    });
    
    // Eliminar por posición (elementos en esquinas)
    document.querySelectorAll('div, a, button').forEach(el => {
        const rect = el.getBoundingClientRect();
        const style = window.getComputedStyle(el);
        
        // Si está posicionado en esquinas con position fixed/absolute
        if ((style.position === 'fixed' || style.position === 'absolute') && 
            (rect.top < 100 || rect.bottom > window.innerHeight - 100) &&
            (rect.right > window.innerWidth - 200 || rect.left < 200)) {
            
            const text = el.innerText || el.textContent || '';
            if (text.length < 100 && (el.tagName === 'A' || el.href)) {
                console.log('Destroying corner element:', el);
                el.remove();
            }
        }
    });
}, 100);

// También ejecutar cuando el DOM cambie
const observer = new MutationObserver(ultraRemoveBadges);
observer.observe(document.body, { childList: true, subtree: true });

// CSS adicional inyectado dinámicamente
const style = document.createElement('style');
style.innerHTML = `
    a[href*="streamlit"] { display: none !important; visibility: hidden !important; opacity: 0 !important; }
    *[href*="share.streamlit.io"] { display: none !important; }
    button[title*="Deploy"], button[title*="Share"] { display: none !important; }
`;
document.head.appendChild(style);
</script>
"""
st.markdown(remove_badges_js, unsafe_allow_html=True)

# Función para verificar conexión a Supabase
def check_database_connection():
    """Verifica la conexión a Supabase"""
    try:
        from supabase import create_client
        import config
        
        supabase = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
        # Test de conexión con tabla que seguro existe
        result = supabase.table('users').select('id').limit(1).execute()
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
        
        # Verificar si existe tabla consolidated_orders
        try:
            total_result = supabase.table('consolidated_orders').select('*', count='exact', head=True).execute()
            total_records = total_result.count if hasattr(total_result, 'count') else 0
            
            # Obtener cuentas únicas
            accounts_result = supabase.table('consolidated_orders').select('account_name').execute()
        except:
            # Si no existe consolidated_orders, usar datos de usuarios
            total_result = supabase.table('users').select('*', count='exact', head=True).execute()
            total_records = total_result.count if hasattr(total_result, 'count') else 0
            accounts_result = supabase.table('users').select('username').execute()
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

# Verificar autenticación
if AUTH_AVAILABLE:
    if not is_logged_in():
        show_login_form()
        st.stop()
else:
    # Debug: Sistema sin autenticación
    st.warning("⚠️ Sistema ejecutándose sin autenticación (modo debug)")

# Crear navegación en el sidebar
with st.sidebar:
    st.title("🚀 GSS App")
    st.markdown("---")
    
    # Mostrar info del usuario si está logueado
    if AUTH_AVAILABLE and is_logged_in():
        show_user_info()
    
    # Menú de navegación
    menu_items = ["🏠 Inicio", "📦 Consolidador", "💱 Gestión TRM", "📊 Reportes"]
    
    # Solo admins pueden ver gestión de usuarios
    if AUTH_AVAILABLE and is_logged_in() and get_current_user().get('role') == 'admin':
        menu_items.extend(["👥 Usuarios", "🔄 Corrector de Valores", "🔍 Debug CXP", "🚀 Actualizar TODOS CXP", "⚠️ Eliminar y Recargar"])
    
    pagina = st.selectbox(
        "Navegación:",
        menu_items,
        label_visibility="hidden"
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
    st.caption("**GSS App**")
    st.caption("Versión 1.0 - 2025")
    st.caption("© Todos los derechos reservados")

# NAVEGACIÓN PRINCIPAL
if pagina == "🏠 Inicio":
    # PÁGINA DE INICIO
    st.title("🚀 GSS App - Sistema de Gestión")
    st.markdown("### Panel de Control Principal")
    st.markdown("---")
    
    # Mensaje de bienvenida
    st.markdown("""
    Bienvenido a **GSS App**, una plataforma integral para la gestión 
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
            
            **🧠 Sistema Inteligente:**
            • Detecta automáticamente duplicados
            • Actualiza información existente
            • Agrega nuevos registros
            • Preserva datos históricos
            • Sin pérdida de información
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
            st.error("❌ Archivo de reportes no encontrado")
    except Exception as e:
        st.error(f"❌ Error cargando reportes: {e}")

elif pagina == "👥 Usuarios":
    # CARGAR PÁGINA DE USUARIOS
    try:
        # Verificar si el archivo existe
        if os.path.exists('pages/4_👥_Usuarios.py'):
            exec(open('pages/4_👥_Usuarios.py', encoding='utf-8').read())
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
st.caption("GSS App | Sistema de Gestión Integral de Operaciones")
