"""
🔍 VALIDADOR - Verificación de Duplicados Pre-Consolidador
Verifica si los registros ya existen en la base de datos y genera archivo limpio
"""

import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime
import io
import numpy as np
import sys
import os

# Configuración de la página
st.set_page_config(
    page_title="Validador de Duplicados",
    page_icon="🔍",
    layout="wide"
)

# Path configuration para importar módulos
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

# Verificar autenticación
try:
    from modulos.auth import require_auth, get_current_user, is_logged_in, show_login_form
    AUTH_AVAILABLE = True
    
    if not is_logged_in():
        st.error("⛔ Debes iniciar sesión para acceder a esta página")
        show_login_form()
        st.stop()
        
except ImportError:
    AUTH_AVAILABLE = False

import config

# Función para limpiar archivos CXP con títulos
def limpiar_archivo_cxp(df):
    """
    Limpia archivos CXP que vienen con títulos y headers en las primeras filas
    """
    # Buscar la fila que contiene los nombres de las columnas reales
    # Generalmente contiene palabras clave como 'Ref', 'Date', 'Amt', etc.
    header_row = None
    
    for idx, row in df.iterrows():
        row_str = ' '.join([str(val) for val in row.values if pd.notna(val)]).lower()
        if any(keyword in row_str for keyword in ['ref', 'date', 'amt', 'consignee', 'arancel', 'iva']):
            header_row = idx
            break
    
    if header_row is not None:
        # Usar esa fila como header y filtrar datos válidos
        new_columns = []
        for val in df.iloc[header_row].values:
            if pd.notna(val) and str(val).strip():
                new_columns.append(str(val).strip())
            else:
                new_columns.append(f"Col_{len(new_columns)}")
        
        # Crear nuevo DataFrame con datos limpios
        data_rows = []
        for idx in range(header_row + 1, len(df)):
            row = df.iloc[idx]
            # Filtrar filas que tienen al menos algunos datos válidos
            if any(pd.notna(val) and str(val).strip() and str(val).strip() != 'nan' for val in row.values):
                # Verificar que no sea una fila de totales o subtítulos
                row_str = ' '.join([str(val) for val in row.values if pd.notna(val)]).lower()
                if not any(skip_word in row_str for skip_word in ['total', 'subtotal', 'drapi inc']):
                    data_rows.append(row.values[:len(new_columns)])
        
        if data_rows:
            df_limpio = pd.DataFrame(data_rows, columns=new_columns)
            st.success(f"✅ Archivo CXP limpiado: {len(df_limpio)} registros válidos encontrados")
            st.info(f"📋 Columnas detectadas: {', '.join(new_columns)}")
            return df_limpio
    
    st.warning("⚠️ No se pudo detectar estructura de títulos, usando archivo tal como está")
    return df

# Conectar a Supabase
@st.cache_resource
def init_supabase():
    return create_client(config.SUPABASE_URL, config.SUPABASE_KEY)

supabase = init_supabase()

# Título principal
st.title("🔍 Validador de Duplicados")
st.caption("Pre-verificación antes del Consolidador")
    

# Primer paso: Seleccionar tipo de archivo
st.subheader("📁 Paso 1: Selecciona el tipo de archivo")

col1, col2 = st.columns([1, 2])

with col1:
    tipo_archivo = st.selectbox(
        "Tipo de archivo:",
        ["Logistics", "Aditionals", "CXP"],
        help="Selecciona según el tipo de datos que quieres verificar"
    )

with col2:
    # Mostrar mapeo específico según tipo seleccionado
    if tipo_archivo == "Logistics":
        st.info("""
        **📡 Mapeo Logistics:**
        - Reference/Order number → order_id
        - Verifica: logistics_total, logistics_reference, logistics_guide_number
        """)
    elif tipo_archivo == "Aditionals":
        st.info("""
        **📡 Mapeo Aditionals:**
        - Order Id → prealert_id
        - Verifica: aditionals_total, aditionals_quantity, aditionals_unitprice, aditionals_item
        """)
    elif tipo_archivo == "CXP":
        st.info("""
        **📡 Mapeo CXP:**
        - Ref # → asignacion
        - Verifica: cxp_amt_due, cxp_arancel, cxp_iva
        """)

# Segundo paso: Subir archivo
st.subheader(f"📂 Paso 2: Sube tu archivo {tipo_archivo}")

uploaded_file = st.file_uploader(
    f"Selecciona el archivo {tipo_archivo} para verificar",
    type=['xlsx', 'xls', 'csv'],
    help=f"Sube tu archivo {tipo_archivo} para verificar contra la base de datos"
)

if uploaded_file:
    try:
        # Leer archivo
        if uploaded_file.name.endswith('.csv'):
            df_original = pd.read_csv(uploaded_file)
        else:
            df_original = pd.read_excel(uploaded_file)
        
        # Limpiar archivo si tiene títulos (especialmente para CXP)
        if tipo_archivo == "CXP":
            df_original = limpiar_archivo_cxp(df_original)
        
        # Verificar automáticamente al subir
        with st.spinner("Verificando en base de datos..."):
            
            # Limpiar función helper
            def clean_id(value):
                if pd.isna(value):
                    return None
                str_value = str(value).strip()
                # Remover comillas si las tiene
                if str_value.startswith("'"):
                    str_value = str_value[1:]
                # Remover .0 si es un número entero
                if str_value.endswith('.0'):
                    str_value = str_value[:-2]
                return str_value if str_value and str_value != 'nan' else None
            
            # Función para normalizar IDs para comparación
            def normalize_id_for_comparison(value):
                """Normaliza IDs tanto del archivo como de la BD para hacer match correcto"""
                if pd.isna(value) or value is None:
                    return None
                str_value = str(value).strip()
                # Remover comillas
                if str_value.startswith("'"):
                    str_value = str_value[1:]
                # Convertir a float y luego a int si es posible para quitar decimales
                try:
                    if '.' in str_value:
                        float_val = float(str_value)
                        if float_val.is_integer():
                            return str(int(float_val))
                    return str_value
                except:
                    return str_value if str_value and str_value != 'nan' else None
            
            registros_completos = []
            registros_necesarios = []
            
            if tipo_archivo == "Logistics":
                # Verificar columnas disponibles
                columnas_verificadas = []
                if 'Reference' in df_original.columns:
                    columnas_verificadas.append('Reference')
                if 'Order number' in df_original.columns:
                    columnas_verificadas.append('Order number')
                
                if not columnas_verificadas:
                    st.error("❌ No se encontraron columnas 'Reference' o 'Order number'")
                    st.stop()
                
                # Obtener IDs únicos del archivo y normalizarlos
                ids_archivo_originales = []
                for col in columnas_verificadas:
                    ids_col = df_original[col].apply(clean_id).dropna().tolist()
                    ids_archivo_originales.extend(ids_col)
                
                ids_archivo_normalizados = []
                for id_orig in ids_archivo_originales:
                    id_norm = normalize_id_for_comparison(id_orig)
                    if id_norm:
                        ids_archivo_normalizados.append(id_norm)
                
                st.info(f"📊 IDs del archivo: {ids_archivo_normalizados[:5]}")
                
                # Consultar DIRECTAMENTE por cada ID para Logistics
                registros_bd_encontrados = {}
                
                for id_norm in set(ids_archivo_normalizados):  # Eliminar duplicados
                    # Buscar variaciones del ID
                    variaciones = [id_norm, f"{id_norm}.0", int(id_norm) if id_norm.isdigit() else id_norm]
                    
                    for variacion in variaciones:
                        try:
                            # Buscar por order_id
                            result = supabase.table('consolidated_orders').select(
                                'order_id, prealert_id, logistics_total, logistics_reference, logistics_guide_number, logistics_date'
                            ).eq('order_id', variacion).execute()
                            
                            if result.data:
                                record = result.data[0]
                                registros_bd_encontrados[id_norm] = record
                                break
                            
                            # Si no se encuentra por order_id, buscar por prealert_id
                            result2 = supabase.table('consolidated_orders').select(
                                'order_id, prealert_id, logistics_total, logistics_reference, logistics_guide_number, logistics_date'
                            ).eq('prealert_id', variacion).execute()
                            
                            if result2.data:
                                record = result2.data[0]
                                registros_bd_encontrados[id_norm] = record
                                break
                                
                        except Exception as e:
                            st.warning(f"Error buscando {variacion}: {e}")
                
                # Mostrar SOLO tabla con datos de la BD
                if registros_bd_encontrados:
                    st.subheader("📊 DATOS DE LA BASE DE DATOS")
                    
                    # Crear DataFrame con los datos de BD
                    datos_bd = []
                    for id_archivo, record_bd in registros_bd_encontrados.items():
                        fila = {
                            'ID_Archivo': id_archivo,
                            'order_id_BD': record_bd.get('order_id'),
                            'prealert_id_BD': record_bd.get('prealert_id'),
                            'logistics_total': record_bd.get('logistics_total'),
                            'logistics_reference': record_bd.get('logistics_reference'),
                            'logistics_guide_number': record_bd.get('logistics_guide_number'),
                            'logistics_date': record_bd.get('logistics_date'),
                        }
                        datos_bd.append(fila)
                    
                    df_bd = pd.DataFrame(datos_bd)
                    st.dataframe(df_bd, use_container_width=True)
                    
                    # Mostrar información de procesamiento
                    st.info(f"📊 IDs del archivo: {ids_archivo_normalizados[:5]}")
                    st.info(f"🔍 Total registros encontrados en BD: {len(registros_bd_encontrados)}")
                    
                    # Evaluar completitud de registros Logistics
                    datos_bd_completos = []
                    for id_archivo, record_bd in registros_bd_encontrados.items():
                        # Verificar si los campos logistics están completos
                        total_ok = record_bd.get('logistics_total') is not None and record_bd.get('logistics_total') != 0
                        reference_ok = record_bd.get('logistics_reference') is not None and record_bd.get('logistics_reference') != ''
                        guide_ok = record_bd.get('logistics_guide_number') is not None and record_bd.get('logistics_guide_number') != ''
                        date_ok = record_bd.get('logistics_date') is not None
                        
                        estado = "✅ COMPLETO" if (total_ok and reference_ok and guide_ok and date_ok) else "❌ INCOMPLETO"
                        datos_bd_completos.append({
                            'ID_Archivo': id_archivo,
                            'ESTADO': estado
                        })
                    
                    # Contar completos vs incompletos
                    completos_bd = len([d for d in datos_bd_completos if d['ESTADO'] == "✅ COMPLETO"])
                    incompletos_bd = len([d for d in datos_bd_completos if d['ESTADO'] == "❌ INCOMPLETO"])
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("✅ Registros COMPLETOS en BD", completos_bd)
                    with col2:
                        st.metric("❌ Registros INCOMPLETOS en BD", incompletos_bd)
                    
                    # Identificar IDs que no están en BD
                    ids_no_encontrados = set(ids_archivo_normalizados) - set(registros_bd_encontrados.keys())
                    
                    # Solo ofrecer Excel si hay registros incompletos o no encontrados
                    if incompletos_bd > 0 or len(ids_no_encontrados) > 0:
                        st.warning(f"📝 Necesitan procesarse: {incompletos_bd} incompletos + {len(ids_no_encontrados)} no encontrados")
                        
                        # Identificar qué IDs necesitan procesarse
                        ids_incompletos = [d['ID_Archivo'] for d in datos_bd_completos if d['ESTADO'] == "❌ INCOMPLETO"]
                        ids_para_procesar = set(ids_incompletos) | ids_no_encontrados
                        
                        # Generar Excel con registros que necesitan procesarse
                        # Filtrar por Reference o Order number
                        mascara_filtro = pd.Series([False] * len(df_original))
                        
                        for col in columnas_verificadas:
                            mascara_col = df_original[col].apply(
                                lambda x: normalize_id_for_comparison(clean_id(x)) in ids_para_procesar
                            )
                            mascara_filtro = mascara_filtro | mascara_col
                        
                        registros_para_procesar = df_original[mascara_filtro]
                        
                        if len(registros_para_procesar) > 0:
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            nombre_archivo = f"Logistics_NECESARIOS_{timestamp}.xlsx"
                            
                            buffer = io.BytesIO()
                            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                                registros_para_procesar.to_excel(writer, index=False, sheet_name="Logistics")
                            
                            st.download_button(
                                label="📥 Descargar Excel con registros que necesitan procesarse",
                                data=buffer.getvalue(),
                                file_name=nombre_archivo,
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                type="primary"
                            )
                    else:
                        st.success("🎉 ¡Todos los registros ya están COMPLETOS en la base de datos!")
                        st.info("✅ No necesitas procesar nada - todos los campos logistics están llenos.")
                
                else:
                    st.warning("❌ No se encontraron registros en la BD")
                    # Ofrecer Excel con todos los registros para procesar
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    nombre_archivo = f"Logistics_TODOS_{timestamp}.xlsx"
                    
                    buffer = io.BytesIO()
                    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                        df_original.to_excel(writer, index=False, sheet_name="Logistics")
                    
                    st.download_button(
                        label="📥 Descargar Excel (todos los registros necesitan procesarse)",
                        data=buffer.getvalue(),
                        file_name=nombre_archivo,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        type="primary"
                    )
            
            elif tipo_archivo == "Aditionals":
                if 'Order Id' not in df_original.columns:
                    st.error("❌ No se encontró columna 'Order Id'")
                    st.stop()
                
                # Obtener IDs únicos del archivo y normalizarlos
                ids_archivo_originales = df_original['Order Id'].apply(clean_id).dropna().tolist()
                ids_archivo_normalizados = []
                
                for id_orig in ids_archivo_originales:
                    id_norm = normalize_id_for_comparison(id_orig)
                    if id_norm:
                        ids_archivo_normalizados.append(id_norm)
                
                # Consultar DIRECTAMENTE por cada ID (sin batch) para debug
                registros_bd_encontrados = {}
                
                for id_norm in ids_archivo_normalizados:
                    # Buscar variaciones del ID
                    variaciones = [id_norm, f"{id_norm}.0", int(id_norm) if id_norm.isdigit() else id_norm]
                    
                    for variacion in variaciones:
                        try:
                            result = supabase.table('consolidated_orders').select(
                                'prealert_id, order_id, aditionals_total, aditionals_quantity, aditionals_unitprice, aditionals_item, aditionals_reference, aditionals_description, aditionals_order_id'
                            ).eq('prealert_id', variacion).execute()
                            
                            if result.data:
                                record = result.data[0]
                                registros_bd_encontrados[id_norm] = record
                                break
                        except Exception as e:
                            st.warning(f"Error buscando {variacion}: {e}")
                
                # Mostrar tabla con TODOS los datos de la BD
                if registros_bd_encontrados:
                    st.subheader("📊 DATOS DE LA BASE DE DATOS")
                    
                    # Crear DataFrame con los datos de BD
                    datos_bd = []
                    for id_archivo, record_bd in registros_bd_encontrados.items():
                        fila = {
                            'Order_Id_Archivo': id_archivo,
                            'prealert_id_BD': record_bd.get('prealert_id'),
                            'order_id_BD': record_bd.get('order_id'),
                            'aditionals_total': record_bd.get('aditionals_total'),
                            'aditionals_quantity': record_bd.get('aditionals_quantity'), 
                            'aditionals_unitprice': record_bd.get('aditionals_unitprice'),
                            'aditionals_item': record_bd.get('aditionals_item'),
                            'aditionals_reference': record_bd.get('aditionals_reference'),
                            'aditionals_description': record_bd.get('aditionals_description'),
                        }
                        
                        # Verificar si está completo
                        total_ok = record_bd.get('aditionals_total') is not None and record_bd.get('aditionals_total') != 0
                        quantity_ok = record_bd.get('aditionals_quantity') is not None and record_bd.get('aditionals_quantity') != 0  
                        unitprice_ok = record_bd.get('aditionals_unitprice') is not None and record_bd.get('aditionals_unitprice') != 0
                        item_ok = record_bd.get('aditionals_item') is not None and record_bd.get('aditionals_item') != ''
                        
                        fila['ESTADO'] = "✅ COMPLETO" if (total_ok and quantity_ok and unitprice_ok and item_ok) else "❌ INCOMPLETO"
                        datos_bd.append(fila)
                    
                    df_bd = pd.DataFrame(datos_bd)
                    st.dataframe(df_bd, use_container_width=True)
                    
                    # Mostrar información de procesamiento
                    st.info(f"📊 IDs del archivo: {ids_archivo_normalizados[:5]}")
                    st.info(f"🔍 Total registros encontrados en BD: {len(registros_bd_encontrados)}")
                    
                    # Contar completos vs incompletos
                    completos_bd = len([d for d in datos_bd if d['ESTADO'] == "✅ COMPLETO"])
                    incompletos_bd = len([d for d in datos_bd if d['ESTADO'] == "❌ INCOMPLETO"])
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("✅ Registros COMPLETOS en BD", completos_bd)
                    with col2:
                        st.metric("❌ Registros INCOMPLETOS en BD", incompletos_bd)
                    
                    # Solo ofrecer Excel si hay registros incompletos o no encontrados
                    ids_no_encontrados = set(ids_archivo_normalizados) - set(registros_bd_encontrados.keys())
                    
                    if incompletos_bd > 0 or len(ids_no_encontrados) > 0:
                        st.warning(f"📝 Necesitan procesarse: {incompletos_bd} incompletos + {len(ids_no_encontrados)} no encontrados")
                        
                        # Generar Excel con registros que necesitan procesarse
                        registros_para_procesar = df_original[
                            df_original['Order Id'].apply(lambda x: normalize_id_for_comparison(clean_id(x)) in ids_no_encontrados or 
                                                        (normalize_id_for_comparison(clean_id(x)) in registros_bd_encontrados and 
                                                         any(d['ESTADO'] == "❌ INCOMPLETO" and d['Order_Id_Archivo'] == normalize_id_for_comparison(clean_id(x)) for d in datos_bd)))
                        ]
                        
                        if len(registros_para_procesar) > 0:
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            nombre_archivo = f"Aditionals_NECESARIOS_{timestamp}.xlsx"
                            
                            buffer = io.BytesIO()
                            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                                registros_para_procesar.to_excel(writer, index=False, sheet_name="Aditionals")
                            
                            st.download_button(
                                label="📥 Descargar Excel con registros que necesitan procesarse",
                                data=buffer.getvalue(),
                                file_name=nombre_archivo,
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                type="primary"
                            )
                    else:
                        st.success("🎉 ¡Todos los registros ya están COMPLETOS en la base de datos!")
                        st.info("✅ No necesitas procesar nada - todos los campos aditionals están llenos.")
                
                else:
                    st.warning("❌ No se encontraron registros en la BD")
                    # Ofrecer Excel con todos los registros para procesar
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    nombre_archivo = f"Aditionals_TODOS_{timestamp}.xlsx"
                    
                    buffer = io.BytesIO()
                    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                        df_original.to_excel(writer, index=False, sheet_name="Aditionals")
                    
                    st.download_button(
                        label="📥 Descargar Excel (todos los registros necesitan procesarse)",
                        data=buffer.getvalue(),
                        file_name=nombre_archivo,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        type="primary"
                    )
            
            elif tipo_archivo == "CXP":
                # Buscar columna Ref # (puede tener variaciones)
                ref_column = None
                for col in df_original.columns:
                    if 'Ref' in col or 'ref' in col or 'REF' in col:
                        ref_column = col
                        break
                
                if not ref_column:
                    st.error("❌ No se encontró columna de referencia (Ref #)")
                    st.stop()
                
                # Obtener IDs únicos del archivo y normalizarlos
                ids_archivo_originales = df_original[ref_column].apply(clean_id).dropna().tolist()
                ids_archivo_normalizados = []
                
                for id_orig in ids_archivo_originales:
                    id_norm = normalize_id_for_comparison(id_orig)
                    if id_norm:
                        ids_archivo_normalizados.append(id_norm)
                
                # Consultar DIRECTAMENTE por cada ID para CXP
                registros_bd_encontrados = {}
                
                for id_norm in set(ids_archivo_normalizados):  # Eliminar duplicados
                    # Buscar variaciones del ID
                    variaciones = [id_norm, f"{id_norm}.0", int(id_norm) if id_norm.isdigit() else id_norm]
                    
                    for variacion in variaciones:
                        try:
                            result = supabase.table('consolidated_orders').select(
                                'asignacion, cxp_amt_due, cxp_arancel, cxp_iva'
                            ).eq('asignacion', variacion).execute()
                            
                            if result.data:
                                record = result.data[0]
                                registros_bd_encontrados[id_norm] = record
                                break
                                
                        except Exception as e:
                            st.warning(f"Error buscando {variacion}: {e}")
                
                # Mostrar tabla con TODOS los datos de la BD
                if registros_bd_encontrados:
                    st.subheader("📊 DATOS DE LA BASE DE DATOS")
                    
                    # Crear DataFrame con los datos de BD
                    datos_bd = []
                    for id_archivo, record_bd in registros_bd_encontrados.items():
                        fila = {
                            'Ref_Archivo': id_archivo,
                            'asignacion_BD': record_bd.get('asignacion'),
                            'cxp_amt_due': record_bd.get('cxp_amt_due'),
                            'cxp_arancel': record_bd.get('cxp_arancel'),
                            'cxp_iva': record_bd.get('cxp_iva'),
                        }
                        
                        # Verificar si está completo
                        amt_due_ok = record_bd.get('cxp_amt_due') is not None and record_bd.get('cxp_amt_due') != 0
                        arancel_ok = record_bd.get('cxp_arancel') is not None and record_bd.get('cxp_arancel') != 0
                        iva_ok = record_bd.get('cxp_iva') is not None and record_bd.get('cxp_iva') != 0
                        
                        fila['ESTADO'] = "✅ COMPLETO" if (amt_due_ok and arancel_ok and iva_ok) else "❌ INCOMPLETO"
                        datos_bd.append(fila)
                    
                    df_bd = pd.DataFrame(datos_bd)
                    st.dataframe(df_bd, use_container_width=True)
                    
                    # Mostrar información de procesamiento
                    st.info(f"📊 IDs del archivo: {ids_archivo_normalizados[:5]}")
                    st.info(f"🔍 Total registros encontrados en BD: {len(registros_bd_encontrados)}")
                    
                    # Contar completos vs incompletos
                    completos_bd = len([d for d in datos_bd if d['ESTADO'] == "✅ COMPLETO"])
                    incompletos_bd = len([d for d in datos_bd if d['ESTADO'] == "❌ INCOMPLETO"])
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("✅ Registros COMPLETOS en BD", completos_bd)
                    with col2:
                        st.metric("❌ Registros INCOMPLETOS en BD", incompletos_bd)
                    
                    # Solo ofrecer Excel si hay registros incompletos o no encontrados
                    ids_no_encontrados = set(ids_archivo_normalizados) - set(registros_bd_encontrados.keys())
                    
                    if incompletos_bd > 0 or len(ids_no_encontrados) > 0:
                        st.warning(f"📝 Necesitan procesarse: {incompletos_bd} incompletos + {len(ids_no_encontrados)} no encontrados")
                        
                        # Generar Excel con registros que necesitan procesarse
                        registros_para_procesar = df_original[
                            df_original[ref_column].apply(lambda x: normalize_id_for_comparison(clean_id(x)) in ids_no_encontrados or 
                                                        (normalize_id_for_comparison(clean_id(x)) in registros_bd_encontrados and 
                                                         any(d['ESTADO'] == "❌ INCOMPLETO" and d['Ref_Archivo'] == normalize_id_for_comparison(clean_id(x)) for d in datos_bd)))
                        ]
                        
                        if len(registros_para_procesar) > 0:
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            nombre_archivo = f"CXP_NECESARIOS_{timestamp}.xlsx"
                            
                            buffer = io.BytesIO()
                            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                                registros_para_procesar.to_excel(writer, index=False, sheet_name="CXP")
                            
                            st.download_button(
                                label="📥 Descargar Excel con registros que necesitan procesarse",
                                data=buffer.getvalue(),
                                file_name=nombre_archivo,
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                type="primary"
                            )
                    else:
                        st.success("🎉 ¡Todos los registros ya están COMPLETOS en la base de datos!")
                        st.info("✅ No necesitas procesar nada - todos los campos CXP están llenos.")
                
                else:
                    st.warning("❌ No se encontraron registros en la BD")
                    # Ofrecer Excel con todos los registros para procesar
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    nombre_archivo = f"CXP_TODOS_{timestamp}.xlsx"
                    
                    buffer = io.BytesIO()
                    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                        df_original.to_excel(writer, index=False, sheet_name="CXP")
                    
                    st.download_button(
                        label="📥 Descargar Excel (todos los registros necesitan procesarse)",
                        data=buffer.getvalue(),
                        file_name=nombre_archivo,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        type="primary"
                    )
                
                
    except Exception as e:
        st.error(f"❌ Error procesando archivo: {str(e)}")
        st.exception(e)

# Página integrada - no requiere main()