import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime
import io

# ====================================
# CREDENCIALES DE SUPABASE (YA CONFIGURADAS)
# ====================================
SUPABASE_URL = "https://pvbzzpeyhhxexyabizbv.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InB2Ynp6cGV5aGh4ZXh5YWJpemJ2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTM5OTc5ODcsImV4cCI6MjA2OTU3Mzk4N30.06S8jDjNReAd6Oj8AZvOS2PUcO2ASJHVA3VUNYVeAR4"

# NOMBRE CORRECTO DE LA TABLA
TABLE_NAME = "consolidated_orders"  # ← CAMBIADO: Era consolidated_orders_rows

# Configuración de la página
st.set_page_config(
    page_title="Actualizador de Fechas - Supabase",
    page_icon="📅",
    layout="wide"
)

# Título principal
st.title("📅 Actualizador Masivo de Fechas Logísticas")
st.markdown("---")

# Sidebar para configuración
st.sidebar.header("⚙️ Configuración de Supabase")

# Verificar conexión
connection_status = st.sidebar.empty()

if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        connection_status.success("✅ Conectado a Supabase")
        st.sidebar.info(f"📊 Tabla: {TABLE_NAME}")
    except Exception as e:
        connection_status.error(f"❌ Error de conexión: {str(e)}")
        supabase = None
else:
    connection_status.info("⏳ Configurando credenciales...")
    supabase = None

st.sidebar.markdown("---")
st.sidebar.info(
    """
    **Instrucciones:**
    1. Carga el archivo Excel con las fechas
    2. Revisa la vista previa
    3. Ejecuta la actualización
    
    **Nota:** Los order_id deben tener comilla simple (') al inicio
    """
)

# Función para procesar fechas
def parse_date(date_str):
    """Convierte fecha del formato DD/MM/YYYY a YYYY-MM-DD"""
    try:
        if pd.isna(date_str):
            return None
        date_str = str(date_str)
        date_part = date_str.split(' ')[0]
        day, month, year = date_part.split('/')
        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    except:
        return None

# Contenido principal
col1, col2 = st.columns([1, 1])

with col1:
    st.header("📁 1. Cargar Archivo Excel")
    
    # Checkbox para agregar comilla automáticamente
    auto_add_quote = st.checkbox(
        "Agregar comilla (') automáticamente", 
        value=True,
        help="Marca esto si tu Excel NO tiene comillas al inicio de los order_id"
    )
    
    uploaded_file = st.file_uploader(
        "Selecciona el archivo Excel",
        type=['xlsx', 'xls'],
        help="El archivo debe tener columnas: order_id (o Order Reference) y logistics_date (o Enlistment Date)"
    )
    
    if uploaded_file is not None:
        try:
            # Intentar leer diferentes formatos de Excel
            df = pd.read_excel(uploaded_file, sheet_name=0)
            
            # Detectar columnas automáticamente
            col_names = df.columns.tolist()
            
            # Buscar columna de order_id
            order_col = None
            date_col = None
            
            for col in col_names:
                col_lower = str(col).lower()
                if 'order' in col_lower or 'id' in col_lower:
                    order_col = col
                if 'date' in col_lower or 'logistics' in col_lower or 'enlist' in col_lower:
                    date_col = col
            
            if order_col and date_col:
                st.success(f"✅ Columnas detectadas: {order_col}, {date_col}")
                
                # Renombrar para trabajar más fácil
                df = df.rename(columns={order_col: 'order_reference', date_col: 'enlistment_date'})
            elif len(df.columns) >= 2:
                # Si no se detectan, asumir que son las primeras 2
                df.columns = ['order_reference', 'enlistment_date'] + list(df.columns[2:])
                st.info("ℹ️ Usando las primeras 2 columnas")
            else:
                st.error("El archivo debe tener al menos 2 columnas")
                st.stop()
            
            # Mostrar info del archivo
            st.success(f"✅ Archivo cargado: {uploaded_file.name}")
            st.info(f"📊 Total de filas: {len(df)}")
            
            # Filtrar registros válidos
            df_valid = df[
                (df['order_reference'].notna()) & 
                (df['enlistment_date'].notna())
            ].copy()
            
            # Convertir order_reference a string
            df_valid['order_reference'] = df_valid['order_reference'].astype(str).str.strip()
            
            # IMPORTANTE: Agregar comilla si es necesario
            if auto_add_quote:
                # Solo agregar si no tiene comilla ya
                df_valid['order_reference'] = df_valid['order_reference'].apply(
                    lambda x: x if x.startswith("'") else "'" + x
                )
                st.info("✅ Comillas agregadas automáticamente a los order_id")
            
            # Convertir fechas
            df_valid['formatted_date'] = df_valid['enlistment_date'].apply(parse_date)
            df_valid = df_valid[df_valid['formatted_date'].notna()]
            
            # Mostrar estadísticas
            col1_1, col1_2, col1_3 = st.columns(3)
            with col1_1:
                st.metric("Registros válidos", len(df_valid))
            with col1_2:
                st.metric("Registros excluidos", len(df) - len(df_valid))
            with col1_3:
                st.metric("Fechas únicas", df_valid['formatted_date'].nunique())
            
        except Exception as e:
            st.error(f"Error al procesar el archivo: {str(e)}")
            df_valid = None
    else:
        df_valid = None

with col2:
    st.header("👁️ 2. Vista Previa")
    
    if df_valid is not None:
        # Mostrar muestra de datos
        st.subheader("Primeros 10 registros a actualizar:")
        preview_df = pd.DataFrame({
            'Order ID (con comilla)': df_valid['order_reference'].head(10),
            'Nueva Fecha': df_valid['formatted_date'].head(10)
        })
        st.dataframe(preview_df, use_container_width=True)
        
        # Rango de fechas
        st.info(f"📅 Rango de fechas: {df_valid['formatted_date'].min()} a {df_valid['formatted_date'].max()}")
        
        # Mostrar ejemplo del formato
        st.success(f"Ejemplo de order_id que se enviará: {df_valid['order_reference'].iloc[0]}")
    else:
        st.info("⏳ Carga un archivo para ver la vista previa")

# Sección de actualización
st.markdown("---")
st.header("🚀 3. Ejecutar Actualización")

if df_valid is not None and supabase is not None:
    col3_1, col3_2, col3_3 = st.columns([1, 2, 1])
    
    with col3_2:
        st.warning(f"⚠️ Se actualizarán {len(df_valid)} registros en la tabla '{TABLE_NAME}'")
        
        # Opciones de actualización
        batch_size = st.slider("Tamaño del lote", 10, 500, 50, step=10)
        
        # Checkbox de confirmación
        confirm = st.checkbox("✅ Confirmo que quiero actualizar la base de datos")
        
        if confirm:
            if st.button("🔄 ACTUALIZAR BASE DE DATOS", type="primary", use_container_width=True):
                
                # Barra de progreso
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Contadores
                success_count = 0
                error_count = 0
                errors = []
                
                # Procesar en lotes
                total_batches = (len(df_valid) + batch_size - 1) // batch_size
                
                for i in range(0, len(df_valid), batch_size):
                    batch = df_valid.iloc[i:i+batch_size]
                    batch_num = (i // batch_size) + 1
                    
                    status_text.text(f"Procesando lote {batch_num}/{total_batches}...")
                    
                    for _, row in batch.iterrows():
                        try:
                            # IMPORTANTE: Usar el nombre correcto de la tabla
                            response = supabase.table(TABLE_NAME).update({
                                'logistics_date': row['formatted_date']
                            }).eq('order_id', row['order_reference']).execute()
                            
                            if response.data:
                                success_count += 1
                            else:
                                error_count += 1
                                if len(errors) <= 10:
                                    errors.append(f"Order {row['order_reference']}: No se encontró")
                        except Exception as e:
                            error_count += 1
                            if len(errors) <= 10:
                                errors.append(f"Order {row['order_reference']}: {str(e)}")
                    
                    # Actualizar progreso
                    progress = min((i + batch_size) / len(df_valid), 1.0)
                    progress_bar.progress(progress)
                
                # Mostrar resultados
                status_text.empty()
                progress_bar.empty()
                
                st.markdown("---")
                st.subheader("📊 Resultados de la Actualización")
                
                col4_1, col4_2 = st.columns(2)
                with col4_1:
                    if success_count > 0:
                        st.success(f"✅ Registros actualizados: {success_count}")
                    else:
                        st.warning(f"Registros actualizados: {success_count}")
                with col4_2:
                    if error_count > 0:
                        st.error(f"❌ Registros con error: {error_count}")
                    else:
                        st.info("✨ Sin errores")
                
                # Mostrar errores si hay
                if errors:
                    with st.expander("Ver errores"):
                        for error in errors:
                            st.text(error)
                        if error_count > 10:
                            st.text(f"... y {error_count - 10} errores más")
                
                # Mensaje según resultado
                if success_count == len(df_valid):
                    st.balloons()
                    st.success("🎉 ¡ÉXITO TOTAL! Todos los registros fueron actualizados.")
                elif success_count > 0:
                    st.warning(f"Actualización parcial completada.")
                else:
                    st.error("No se pudo actualizar ningún registro. Verifica que los order_id existan en la base de datos.")
                
                # Reporte
                report = f"""REPORTE DE ACTUALIZACIÓN
========================
Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Tabla: {TABLE_NAME}
Total procesados: {len(df_valid)}
Exitosos: {success_count}
Errores: {error_count}

Detalles de errores:
{chr(10).join(errors) if errors else 'Sin errores'}
"""
                
                st.download_button(
                    label="📥 Descargar Reporte",
                    data=report,
                    file_name=f"reporte_actualizacion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                    mime="text/plain"
                )
        else:
            st.info("☑️ Marca la confirmación para habilitar el botón")

elif df_valid is None:
    st.info("📁 Por favor, carga un archivo Excel para continuar")
elif supabase is None:
    st.warning("🔐 Error de conexión con Supabase")

# Sección de verificación
with st.expander("🔍 Verificar conexión y datos"):
    if st.button("Probar conexión"):
        try:
            # Intentar leer un registro
            test = supabase.table(TABLE_NAME).select("*").limit(1).execute()
            if test.data:
                st.success(f"✅ Conexión exitosa a tabla '{TABLE_NAME}'")
                st.write("Muestra de datos:", test.data[0])
            else:
                st.warning("La tabla está vacía")
        except Exception as e:
            st.error(f"Error: {str(e)}")
    
    # Test con un order_id específico
    test_order = st.text_input("Probar con un order_id específico (con comilla):", value="'2000009361266262")
    if test_order and st.button("Buscar"):
        try:
            result = supabase.table(TABLE_NAME).select("*").eq('order_id', test_order).execute()
            if result.data:
                st.success("✅ Order encontrado:")
                st.write(result.data[0])
            else:
                st.warning(f"No se encontró el order_id: {test_order}")
        except Exception as e:
            st.error(f"Error: {str(e)}")

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray;'>
    Actualizador de Fechas Logísticas | Tabla: consolidated_orders
    </div>
    """,
    unsafe_allow_html=True
)
