"""
Script para corregir valores trocados en MEGATIENDA_VEENDELO y FABORCARGO
Los valores de cxp_amt_due están intercambiados con dest_delivery y declare_value
"""

import streamlit as st
import pandas as pd
from supabase import create_client
import config
import time

# Page config
st.set_page_config(
    page_title="🔄 Corrector de Valores",
    page_icon="🔄",
    layout="wide"
)

st.title("🔄 Corrector de Valores Trocados")
st.caption("MEGATIENDA_VEENDELO y FABORCARGO - Corrección de cxp_amt_due")

# Initialize Supabase
@st.cache_resource
def init_supabase():
    return create_client(config.SUPABASE_URL, config.SUPABASE_KEY)

supabase = init_supabase()

# Función para cargar datos de las cuentas problemáticas
@st.cache_data(ttl=300)
def cargar_datos_problematicos():
    try:
        # Cargar datos de las cuentas con problemas
        accounts_problematicos = ['3-VEENDELO', '8-FABORCARGO']
        
        query = supabase.table('consolidated_orders').select('*')
        query = query.in_('account_name', accounts_problematicos)
        result = query.execute()
        
        if result.data:
            df = pd.DataFrame(result.data)
            return df
        else:
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Error al cargar datos: {str(e)}")
        return pd.DataFrame()

# Función para aplicar las correcciones
def aplicar_correcciones(df, tipo_correccion):
    """
    Aplica las correcciones según el tipo especificado
    tipo_correccion: 'intercambio_dest' o 'intercambio_declare'
    """
    df_corregido = df.copy()
    actualizaciones = []
    
    if tipo_correccion == 'intercambio_dest':
        # Caso 1: cxp_amt_due intercambiado con dest_delivery
        for index, row in df_corregido.iterrows():
            if pd.notna(row.get('cxp_amt_due')) and pd.notna(row.get('dest_delivery')):
                # Intercambiar valores
                valor_original_cxp = row['cxp_amt_due']
                valor_original_dest = row['dest_delivery']
                
                df_corregido.at[index, 'cxp_amt_due'] = valor_original_dest
                df_corregido.at[index, 'dest_delivery'] = valor_original_cxp
                
                actualizaciones.append({
                    'id': row['id'],
                    'cxp_amt_due': valor_original_dest,
                    'dest_delivery': valor_original_cxp,
                    'tipo': 'intercambio_dest_delivery'
                })
    
    elif tipo_correccion == 'intercambio_declare':
        # Caso 2: cxp_amt_due intercambiado con declare_value
        for index, row in df_corregido.iterrows():
            if pd.notna(row.get('cxp_amt_due')) and pd.notna(row.get('declare_value')):
                # Intercambiar valores
                valor_original_cxp = row['cxp_amt_due']
                valor_original_declare = row['declare_value']
                
                df_corregido.at[index, 'cxp_amt_due'] = valor_original_declare
                df_corregido.at[index, 'declare_value'] = valor_original_cxp
                
                actualizaciones.append({
                    'id': row['id'],
                    'cxp_amt_due': valor_original_declare,
                    'declare_value': valor_original_cxp,
                    'tipo': 'intercambio_declare_value'
                })
    
    return df_corregido, actualizaciones

# Función para actualizar en Supabase
def actualizar_supabase(actualizaciones):
    """
    Actualiza los registros en Supabase con los valores corregidos
    """
    exitos = 0
    errores = 0
    
    progress_bar = st.progress(0)
    total = len(actualizaciones)
    
    for i, actualizacion in enumerate(actualizaciones):
        try:
            record_id = actualizacion['id']
            
            # Preparar datos para actualizar
            update_data = {}
            if 'cxp_amt_due' in actualizacion:
                update_data['cxp_amt_due'] = actualizacion['cxp_amt_due']
            if 'dest_delivery' in actualizacion:
                update_data['dest_delivery'] = actualizacion['dest_delivery']
            if 'declare_value' in actualizacion:
                update_data['declare_value'] = actualizacion['declare_value']
            
            # Ejecutar actualización
            result = supabase.table('consolidated_orders').update(update_data).eq('id', record_id).execute()
            
            if result.data:
                exitos += 1
            else:
                errores += 1
                st.error(f"Error actualizando registro {record_id}")
                
        except Exception as e:
            errores += 1
            st.error(f"Error actualizando registro {record_id}: {str(e)}")
        
        # Actualizar barra de progreso
        progress_bar.progress((i + 1) / total)
        time.sleep(0.1)  # Pequeña pausa para no saturar la API
    
    return exitos, errores

# INTERFACE PRINCIPAL
st.markdown("---")

# Cargar datos
with st.spinner("Cargando datos problemáticos..."):
    df_problematico = cargar_datos_problematicos()

if not df_problematico.empty:
    
    st.success(f"✅ Datos cargados: {len(df_problematico)} registros de VEENDELO y FABORCARGO")
    
    # Mostrar resumen por cuenta
    col1, col2 = st.columns(2)
    
    with col1:
        veendelo_count = len(df_problematico[df_problematico['account_name'] == '3-VEENDELO'])
        st.metric("🏪 VEENDELO", f"{veendelo_count} registros")
    
    with col2:
        faborcargo_count = len(df_problematico[df_problematico['account_name'] == '8-FABORCARGO'])
        st.metric("📦 FABORCARGO", f"{faborcargo_count} registros")
    
    # Mostrar muestra de datos problemáticos
    st.markdown("### 👀 Muestra de Datos Actuales (Problemáticos)")
    columnas_importantes = ['id', 'account_name', 'order_id', 'cxp_amt_due', 'dest_delivery', 'declare_value']
    st.dataframe(df_problematico[columnas_importantes].head(10), use_container_width=True)
    
    st.markdown("---")
    
    # SECCIÓN DE CORRECCIONES
    st.markdown("### ⚙️ Aplicar Correcciones")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🔄 Tipo 1: Intercambio cxp_amt_due ↔ dest_delivery")
        if st.button("🔄 Intercambiar cxp_amt_due con dest_delivery", use_container_width=True):
            with st.spinner("Aplicando correcciones..."):
                df_corregido, actualizaciones = aplicar_correcciones(df_problematico, 'intercambio_dest')
                
                if actualizaciones:
                    st.info(f"📊 {len(actualizaciones)} registros listos para actualizar")
                    
                    # Mostrar preview de correcciones
                    with st.expander("👀 Ver preview de correcciones"):
                        st.write("Primeros 5 registros a actualizar:")
                        for act in actualizaciones[:5]:
                            st.write(f"**ID {act['id']}**: cxp_amt_due: {act['cxp_amt_due']}, dest_delivery: {act['dest_delivery']}")
                    
                    # Confirmar actualización
                    if st.button("✅ CONFIRMAR ACTUALIZACIÓN - Intercambio Dest Delivery", type="primary"):
                        with st.spinner("Actualizando base de datos..."):
                            exitos, errores = actualizar_supabase(actualizaciones)
                            
                        st.success(f"✅ Actualizaciones completadas: {exitos} éxitos, {errores} errores")
                        if errores == 0:
                            st.balloons()
                            st.cache_data.clear()  # Limpiar cache para recargar datos
                else:
                    st.warning("⚠️ No se encontraron registros para actualizar")
    
    with col2:
        st.markdown("#### 🔄 Tipo 2: Intercambio cxp_amt_due ↔ declare_value")
        if st.button("🔄 Intercambiar cxp_amt_due con declare_value", use_container_width=True):
            with st.spinner("Aplicando correcciones..."):
                df_corregido, actualizaciones = aplicar_correcciones(df_problematico, 'intercambio_declare')
                
                if actualizaciones:
                    st.info(f"📊 {len(actualizaciones)} registros listos para actualizar")
                    
                    # Mostrar preview de correcciones
                    with st.expander("👀 Ver preview de correcciones"):
                        st.write("Primeros 5 registros a actualizar:")
                        for act in actualizaciones[:5]:
                            st.write(f"**ID {act['id']}**: cxp_amt_due: {act['cxp_amt_due']}, declare_value: {act['declare_value']}")
                    
                    # Confirmar actualización
                    if st.button("✅ CONFIRMAR ACTUALIZACIÓN - Intercambio Declare Value", type="primary"):
                        with st.spinner("Actualizando base de datos..."):
                            exitos, errores = actualizar_supabase(actualizaciones)
                            
                        st.success(f"✅ Actualizaciones completadas: {exitos} éxitos, {errores} errores")
                        if errores == 0:
                            st.balloons()
                            st.cache_data.clear()  # Limpiar cache para recargar datos
                else:
                    st.warning("⚠️ No se encontraron registros para actualizar")
    
    st.markdown("---")
    
    # SECCIÓN DE CARGA DE ARCHIVO CORREGIDO
    st.markdown("### 📁 Cargar Archivo Corregido (Tu archivo con columnas específicas)")
    
    st.info("""
    📋 **Tu archivo debe tener estas columnas:**
    - `Ref #` (para identificar registros - se mapea con 'asignacion' en BD)
    - `Amt. Due` (valores corregidos de cxp_amt_due)
    - `Dest. Delivery` (valores corregidos)
    - `Goods Value` (valores corregidos de declare_value)
    """)
    
    uploaded_file = st.file_uploader(
        "Sube tu archivo CSV con los valores corregidos", 
        type=['csv'],
        help="El archivo debe tener las columnas: Ref #, Amt. Due, Dest. Delivery, Goods Value"
    )
    
    if uploaded_file is not None:
        try:
            df_corrected = pd.read_csv(uploaded_file)
            
            st.success(f"✅ Archivo cargado correctamente: {len(df_corrected)} registros")
            
            # Mostrar preview
            st.markdown("#### 👀 Preview del archivo cargado:")
            st.dataframe(df_corrected.head(), use_container_width=True)
            
            # Validar que tiene las columnas necesarias
            required_cols = ['Ref #', 'Amt. Due']
            missing_cols = [col for col in required_cols if col not in df_corrected.columns]
            
            if missing_cols:
                st.error(f"❌ Faltan columnas requeridas: {missing_cols}")
                st.info("📋 Columnas disponibles en tu archivo:")
                st.write(list(df_corrected.columns))
            else:
                # Mapear con los datos existentes
                st.markdown("#### 🔗 Mapeando con base de datos existente...")
                
                # Cargar órdenes existentes para hacer el mapeo
                try:
                    with st.spinner("Mapeando órdenes por 'Ref #' → 'asignacion'..."):
                        # Buscar por Ref # que corresponde a 'asignacion' en la BD
                        ref_numbers = df_corrected['Ref #'].unique().tolist()
                        
                        # Mapear directamente por 'asignacion'
                        query = supabase.table('consolidated_orders').select('*')
                        query = query.in_('asignacion', ref_numbers)
                        result_orders = query.execute()
                        
                        # Si no encuentra por asignacion, mostrar opciones alternativas
                        if not result_orders.data:
                            st.warning("⚠️ No se encontraron coincidencias por 'asignacion'")
                            st.markdown("##### 🔍 Opciones de mapeo alternativas:")
                            
                            # Mostrar algunos valores de Ref # para debug
                            st.markdown("##### 📋 Valores de Ref # en tu archivo (primeros 10):")
                            st.write(df_corrected['Ref #'].head(10).tolist())
                            
                            mapeo_option = st.radio(
                                "¿Cómo quieres intentar el mapeo?",
                                ["Intentar por order_id", "Intentar por reference_number", "Ver registros BD para debug"]
                            )
                            
                            if mapeo_option == "Intentar por order_id":
                                query2 = supabase.table('consolidated_orders').select('*')
                                query2 = query2.in_('order_id', ref_numbers)
                                result_orders = query2.execute()
                            
                            elif mapeo_option == "Intentar por reference_number":
                                query3 = supabase.table('consolidated_orders').select('*')
                                query3 = query3.in_('reference_number', ref_numbers)
                                result_orders = query3.execute()
                            
                            elif mapeo_option == "Ver registros BD para debug":
                                # Mostrar algunos registros de la BD para que el usuario vea el formato
                                debug_query = supabase.table('consolidated_orders').select('id, asignacion, order_id, reference_number').limit(10).execute()
                                if debug_query.data:
                                    st.markdown("##### 🔍 Muestra de registros en BD:")
                                    st.dataframe(pd.DataFrame(debug_query.data), use_container_width=True)
                        
                        if result_orders.data:
                            df_existing = pd.DataFrame(result_orders.data)
                            st.success(f"✅ Se mapearon {len(df_existing)} registros de la base de datos")
                            
                            # Crear el mapeo basado en 'asignacion'
                            mapeo_dict = {}
                            for _, row_existing in df_existing.iterrows():
                                # Mapear directamente por 'asignacion'
                                if 'asignacion' in row_existing and pd.notna(row_existing['asignacion']):
                                    ref_key = str(row_existing['asignacion'])
                                    if ref_key in df_corrected['Ref #'].astype(str).values:
                                        mapeo_dict[ref_key] = row_existing['id']
                            
                            # Preparar actualizaciones
                            actualizaciones_archivo = []
                            registros_mapeados = 0
                            
                            for _, row_corrected in df_corrected.iterrows():
                                ref_number = str(row_corrected['Ref #'])
                                
                                if ref_number in mapeo_dict:
                                    update_data = {'id': mapeo_dict[ref_number]}
                                    
                                    # Mapear columnas
                                    if 'Amt. Due' in row_corrected and pd.notna(row_corrected['Amt. Due']):
                                        # Limpiar valor (remover símbolos de moneda, comas, etc.)
                                        amt_due_clean = str(row_corrected['Amt. Due']).replace('$', '').replace(',', '').strip()
                                        if amt_due_clean and amt_due_clean != 'nan':
                                            try:
                                                update_data['cxp_amt_due'] = float(amt_due_clean)
                                            except:
                                                pass
                                    
                                    if 'Dest. Delivery' in row_corrected and pd.notna(row_corrected['Dest. Delivery']):
                                        dest_delivery_clean = str(row_corrected['Dest. Delivery']).replace('$', '').replace(',', '').strip()
                                        if dest_delivery_clean and dest_delivery_clean != 'nan':
                                            try:
                                                update_data['dest_delivery'] = float(dest_delivery_clean)
                                            except:
                                                pass
                                    
                                    if 'Goods Value' in row_corrected and pd.notna(row_corrected['Goods Value']):
                                        goods_value_clean = str(row_corrected['Goods Value']).replace('$', '').replace(',', '').strip()
                                        if goods_value_clean and goods_value_clean != 'nan':
                                            try:
                                                update_data['declare_value'] = float(goods_value_clean)
                                            except:
                                                pass
                                    
                                    if len(update_data) > 1:  # Más que solo 'id'
                                        actualizaciones_archivo.append(update_data)
                                        registros_mapeados += 1
                            
                            st.info(f"📊 {registros_mapeados} registros listos para actualizar de {len(df_corrected)} totales")
                            
                            # Mostrar preview de actualizaciones
                            if actualizaciones_archivo:
                                with st.expander("👀 Ver preview de actualizaciones"):
                                    for i, act in enumerate(actualizaciones_archivo[:5]):
                                        st.write(f"**Actualización {i+1}:**")
                                        for key, value in act.items():
                                            if key != 'id':
                                                st.write(f"  - {key}: {value}")
                                        st.write("---")
                                
                                if st.button("✅ CONFIRMAR ACTUALIZACIÓN CON ARCHIVO CARGADO", type="primary"):
                                    with st.spinner("Actualizando desde archivo..."):
                                        exitos, errores = actualizar_supabase(actualizaciones_archivo)
                                    
                                    st.success(f"✅ Actualizaciones desde archivo completadas: {exitos} éxitos, {errores} errores")
                                    if errores == 0:
                                        st.balloons()
                                        st.cache_data.clear()
                            else:
                                st.warning("⚠️ No se pudieron preparar actualizaciones. Revisa el formato de los datos.")
                        else:
                            st.error("❌ No se pudieron mapear los registros. Verifica que los OT Numbers coincidan con la base de datos.")
                            
                            # Mostrar algunos ejemplos de OT Numbers del archivo
                            st.markdown("##### 📋 OT Numbers en tu archivo (primeros 10):")
                            st.write(df_corrected['OT Number'].head(10).tolist())
                        
                except Exception as e:
                    st.error(f"❌ Error en el mapeo: {str(e)}")
                
        except Exception as e:
            st.error(f"❌ Error al procesar archivo: {str(e)}")

else:
    st.warning("⚠️ No se pudieron cargar los datos de VEENDELO y FABORCARGO")

st.markdown("---")
st.info("""
💡 **Instrucciones de uso:**
1. **Opción A - Intercambios automáticos**: Usa los botones para intercambiar automáticamente los valores trocados
2. **Opción B - Archivo corregido**: Sube un CSV con los valores ya corregidos

⚠️ **Importante**: 
- Siempre revisa el preview antes de confirmar
- Las actualizaciones son irreversibles
- Se recomienda hacer backup antes de ejecutar correcciones masivas
""")