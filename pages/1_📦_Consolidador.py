# Actualizado: 2025-01-13 - Corrección de error en archivo Logistics
import streamlit as st
import pandas as pd
import numpy as np
from supabase import create_client, Client
import os
from datetime import datetime, timedelta, date
import io
import time
import re
import hashlib
import math
import sys

# Agregar la carpeta raíz al path para importar módulos
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importar sistema de autenticación
try:
    from modulos.auth import require_auth, log_activity, show_user_info, get_current_user
    AUTH_AVAILABLE = True
except ImportError:
    AUTH_AVAILABLE = False

# Configuración de la página
st.set_page_config(
    page_title="Consolidador de Órdenes",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Verificar autenticación PRIMERO
if AUTH_AVAILABLE:
    try:
        from modulos.auth import is_logged_in, show_login_form
        if not is_logged_in():
            st.error("⛔ Debes iniciar sesión para acceder a esta página")
            show_login_form()
            st.stop()
    except:
        pass

# Configuración de Supabase usando config.py
@st.cache_resource
def init_supabase():
    try:
        import config
        return create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
    except Exception as e:
        st.error(f"Error conectando a Supabase: {e}")
        return None

supabase = init_supabase()

# Test de conexión al inicio
if supabase:
    try:
        test_result = supabase.table('consolidated_orders').select('id').limit(1).execute()
        st.sidebar.success("✅ Conectado a Supabase")
    except Exception as e:
        # Si no existe consolidated_orders, intentar con users
        try:
            test_result = supabase.table('users').select('id').limit(1).execute()
            st.sidebar.success("✅ Conectado a Supabase")
        except:
            st.sidebar.error(f"❌ Error de conexión: {str(e)}")
else:
    st.error("❌ No se pudo conectar a la base de datos")
    st.stop()

# =====================================================
# FUNCIONES DE FORMATO Y LIMPIEZA
# =====================================================

def fix_encoding(text):
    """Corrige caracteres mal codificados automáticamente"""
    if pd.isna(text) or not isinstance(text, str):
        return text
    
    try:
        if 'Ã' in text:
            fixed = text.encode('latin-1').decode('utf-8')
            return fixed
    except:
        pass
    
    return text

def format_currency_no_decimals(value):
    """Formato currency sin decimales: $#,##0"""
    if pd.isna(value):
        return None
    try:
        num_value = float(value)
        rounded_value = round(num_value)
        return f"${rounded_value:,}"
    except:
        return value

def format_currency_with_decimals(value):
    """Formato currency con decimales: $#,##0.00"""
    if pd.isna(value):
        return None
    try:
        num_value = float(value)
        return f"${num_value:,.2f}"
    except:
        return value

def format_date_standard(date_value, input_format="auto"):
    """Convierte fechas a formato YYYY-MM-DD"""
    if pd.isna(date_value) or date_value == "":
        return None
    
    date_str = str(date_value).strip()
    
    try:
        if re.match(r'\d{4}-\d{2}-\d{2}\s', date_str):
            return date_str.split(' ')[0]
        
        if re.match(r'\d{1,2}/\d{1,2}/\d{4}', date_str):
            parts = date_str.split('/')
            if len(parts) == 3:
                month = parts[0].zfill(2)
                day = parts[1].zfill(2)
                year = parts[2]
                return f"{year}-{month}-{day}"
        
        if re.match(r'\d{4}-\d{2}-\d{2}$', date_str):
            return date_str
            
    except:
        pass
    
    return date_str

def check_existing_data():
    """Verifica si hay datos existentes en la tabla"""
    try:
        result = supabase.table('consolidated_orders').select('id').limit(1).execute()
        return len(result.data) > 0
    except:
        return False

def clean_id(value):
    """Limpia y normaliza IDs removiendo comillas y espacios"""
    if pd.isna(value):
        return None
    str_value = str(value).strip()
    if str_value.startswith("'"):
        str_value = str_value[1:]
    if str_value.endswith('.0'):
        str_value = str_value[:-2]
    return str_value if str_value and str_value != 'nan' else None

def clean_id_aggressive(value):
    """Limpieza más agresiva para IDs corruptos"""
    if pd.isna(value):
        return None
    
    str_value = str(value).strip()
    str_value = str_value.replace("'", "")
    str_value = str_value.replace('"', "")
    str_value = str_value.replace(" ", "")
    str_value = str_value.replace("\t", "")
    str_value = str_value.replace("\n", "")
    str_value = str_value.replace(".", "")
    
    if str_value.endswith('0') and len(str_value) > 1:
        original = str(value)
        if '.0' in original:
            str_value = str_value[:-1]
    
    return str_value if str_value and str_value != 'nan' else None

def create_error_log(filename, errors_list):
    """Crea un archivo de log con los errores"""
    if not errors_list:
        return None
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"error_log_{filename}_{timestamp}.txt"
    log_content = f"ERROR LOG - {filename}\n"
    log_content += f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    log_content += "="*60 + "\n\n"
    
    for error in errors_list:
        log_content += f"{error}\n"
    
    return log_content, log_filename

def show_concise_report(total_in_file, found_in_db, processed, failed_list=None):
    """Muestra un reporte conciso del proceso"""
    success_rate = (processed / total_in_file * 100) if total_in_file > 0 else 0
    
    # Reporte principal
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📄 En archivo", total_in_file)
    with col2:
        st.metric("🔍 Encontrados en BD", found_in_db)
    with col3:
        st.metric("✅ Procesados", processed)
    with col4:
        st.metric("📊 Tasa éxito", f"{success_rate:.1f}%")
    
    # Si hay fallos, mostrar alerta
    if failed_list and len(failed_list) > 0:
        st.warning(f"⚠️ {len(failed_list)} registros no procesados")
        
        # Crear log de errores
        log_content, log_filename = create_error_log("consolidador", failed_list)
        if log_content:
            st.download_button(
                label="📥 Descargar log de errores",
                data=log_content,
                file_name=log_filename,
                mime="text/plain"
            )
    
    return success_rate

def normalize_id_for_db_match(value):
    """Normaliza IDs para hacer match con la base de datos que tiene formato 'ID"""
    if pd.isna(value):
        return None
    
    # Convertir a string y limpiar espacios
    str_value = str(value).strip()
    
    # Si está vacío o es 'nan', retornar None
    if not str_value or str_value.lower() == 'nan':
        return None
    
    # Remover .0 si es un número entero (1049072.0 -> 1049072)
    if str_value.endswith('.0'):
        str_value = str_value[:-2]
    
    # NO agregar comilla aquí - la dejaremos para el matching
    return str_value

def clean_numeric_value(value):
    """Limpia valores numéricos, eliminando basura como 'XXXXXXXXXX'"""
    if pd.isna(value) or value is None:
        return None
    
    str_value = str(value).strip()
    
    garbage_values = [
        'XXXXXXXXXX', 'XXXXXXX', 'XXXXX', 'XXX',
        'N/A', 'n/a', 'NA', 'na',
        '-', '--', '---',
        '#N/A', '#VALUE!', '#REF!',
        'null', 'NULL', 'Null',
        '', ' '
    ]
    
    if str_value in garbage_values:
        return None
    
    try:
        clean_value = str_value.replace('$', '').replace(',', '').replace(' ', '')
        return float(clean_value)
    except:
        return None

def clean_update_data(update_data):
    """Limpia los datos de actualización eliminando NaN e infinitos"""
    cleaned = {}
    for key, value in update_data.items():
        if value is None:
            cleaned[key] = None
        elif pd.isna(value):
            cleaned[key] = None
        elif isinstance(value, float):
            if math.isnan(value) or math.isinf(value):
                cleaned[key] = None
            else:
                cleaned[key] = value
        elif isinstance(value, np.float64) or isinstance(value, np.float32):
            if np.isnan(value) or np.isinf(value):
                cleaned[key] = None
            else:
                cleaned[key] = float(value)
        elif isinstance(value, np.int64) or isinstance(value, np.int32):
            cleaned[key] = int(value)
        elif isinstance(value, str):
            if value.lower() in ['nan', 'none', 'null', '']:
                cleaned[key] = None
            else:
                cleaned[key] = value
        else:
            cleaned[key] = value
    
    return cleaned

def calculate_asignacion(account_name, serial_number):
    """Calcula la asignación basada en el account_name y serial_number"""
    if pd.isna(account_name) or pd.isna(serial_number):
        return None
    
    clean_serial = clean_id(serial_number)
    if not clean_serial:
        return None
    
    account_mapping = {
        '1-TODOENCARGO-CO': 'TDC',
        '2-MEGATIENDA SPA': 'MEGA',
        '4-MEGA TIENDAS PERUANAS': 'MGA-PE',
        '5-DETODOPARATODOS': 'DTPT',
        '6-COMPRAFACIL': 'CFA',
        '7-COMPRA-YA': 'CPYA',
        '8-FABORCARGO': 'FBC',
        '3-VEENDELO': 'VEEN'
    }
    
    prefix = account_mapping.get(account_name, '')
    return f"{prefix}{clean_serial}" if prefix else clean_serial

def map_column_names(df):
    """Mapea nombres de columnas del CSV a los nombres de la base de datos"""
    column_mapping = {
        'System#': 'system_number',
        'Serial#': 'serial_number',
        'order_id': 'order_id',
        'pack_id': 'pack_id',
        'ASIN': 'asin',
        'client_first_name': 'client_first_name',
        'client_last_name': 'client_last_name',
        'client_doc_id': 'client_doc_id',
        'account_name': 'account_name',
        'date_created': 'date_created',
        'quantity': 'quantity',
        'title': 'title',
        'unit_price': 'unit_price',
        'logistic_type': 'logistic_type',
        'address_line': 'address_line',
        'street_name': 'street_name',
        'street_number': 'street_number',
        'city': 'city',
        'state': 'state',
        'country': 'country',
        'receiver_phone': 'receiver_phone',
        'amz_order_id': 'amz_order_id',
        'prealert_id': 'prealert_id',
        'ETIQUETA_ENVIO': 'etiqueta_envio',
        'order_status_meli': 'order_status_meli',
        'Declare Value': 'declare_value',
        'Meli Fee': 'meli_fee',
        'IVA': 'iva',
        'ICA': 'ica',
        'FUENTE': 'fuente',
        'senders_cost': 'senders_cost',
        'gross_amount': 'gross_amount',
        'net_received_amount': 'net_received_amount',
        'nombre_del_tercero': 'nombre_del_tercero',
        'direccion': 'direccion',
        'apelido_del_tercero': 'apelido_del_tercero',
        'Estado': 'estado',
        'razon_social': 'razon_social',
        'Ciudad': 'ciudad',
        'Numero de documento': 'numero_de_documento',
        'digital_verification': 'digital_verification',
        'tipo': 'tipo',
        'telefono': 'telefono',
        'giro': 'giro',
        'correo': 'correo',
        'net_real_amount': 'net_real_amount',
        'logistic_weight_lbs': 'logistic_weight_lbs',
        'refunded_date': 'refunded_date',
        'Asignacion': 'asignacion',
    }
    
    renamed_df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
    return renamed_df

def apply_basic_formatting(df):
    """Aplica formatos básicos sin afectar campos numéricos para BD"""
    
    st.info("🔧 Aplicando formatos básicos para base de datos...")
    
    text_columns = [
        'client_first_name', 'client_last_name', 'title', 'address_line', 
        'street_name', 'city', 'state', 'country', 'nombre_del_tercero',
        'direccion', 'apelido_del_tercero', 'estado', 'razon_social', 'ciudad',
        'logistics_description', 'logistics_shipper', 'logistics_consignee',
        'logistics_country', 'logistics_state', 'logistics_city', 'logistics_address'
    ]
    
    for col in text_columns:
        if col in df.columns:
            df[col] = df[col].apply(fix_encoding)
    
    date_columns = {
        'date_created': 'datetime',
        'cxp_date': 'cxp_format'
    }
    
    for col, format_type in date_columns.items():
        if col in df.columns:
            df[col] = df[col].apply(format_date_standard)
    
    st.success("✅ Formatos básicos aplicados")
    return df

def detect_cxp_column(df, target_field):
    """
    Detecta inteligentemente la columna correcta para un campo CXP
    NO depende de posiciones, solo de nombres y patrones
    """
    column_patterns = {
        'ot_number': ['OT Number', 'OT_Number', 'ot number', 'OT#', 'OT #', 'Order Transfer'],
        'date': ['Date', 'DATE', 'Fecha', 'date', 'Creation Date'],
        'ref_number': ['Ref #', 'Ref#', 'REF #', 'Reference', 'ref_number', 'Referencia', 'REF#'],
        'consignee': ['Consignee', 'CONSIGNEE', 'Destinatario', 'Recipient'],
        'co_aereo': ['CO Aereo', 'CO_Aereo', 'co aereo', 'CO AEREO', 'Aereo', 'Air Cost', 'Costo Aereo'],
        'arancel': ['Arancel', 'ARANCEL', 'Tariff', 'Duty', 'Customs Duty', 'Impuesto'],
        'iva': ['IVA', 'iva', 'I.V.A.', 'Tax', 'VAT', 'Value Added Tax'],
        'handling': ['Handling', 'HANDLING', 'Manejo', 'Handle', 'Processing'],
        'dest_delivery': ['Dest. Delivery', 'Dest Delivery', 'Destination Delivery', 'Delivery', 'Entrega Destino'],
        'amt_due': ['Amt. Due', 'Amt Due', 'Amount Due', 'Total Due', 'Monto Adeudado', 'Total'],
        'goods_value': ['Goods Value', 'GOODS VALUE', 'Valor Mercancia', 'Value', 'Merchandise Value']
    }
    
    patterns = column_patterns.get(target_field, [])
    
    # Primero buscar coincidencia exacta
    for pattern in patterns:
        if pattern in df.columns:
            return pattern
    
    # Luego buscar coincidencia parcial (case-insensitive)
    for col in df.columns:
        col_lower = col.lower().strip()
        for pattern in patterns:
            pattern_lower = pattern.lower().strip()
            if pattern_lower in col_lower or col_lower in pattern_lower:
                return col
    
    return None

def get_column_value_safe(row, column_mappings, field_name):
    """
    Obtiene el valor de una columna de forma segura usando el mapeo detectado
    """
    column_name = column_mappings.get(field_name)
    if column_name and column_name in row.index:
        return row[column_name]
    return None

def process_files_according_to_rules(drapify_df, logistics_df=None, aditionals_df=None, cxp_df=None, logistics_date=None):
    """
    Procesa y consolida todos los archivos según las reglas especificadas
    """
    
    st.info("🔄 Iniciando consolidación según reglas especificadas...")
    
    # PASO 1: Usar Drapify como base
    consolidated_df = drapify_df.copy()
    st.success(f"✅ Archivo base Drapify procesado: {len(consolidated_df)} registros")
    
    # PASO 2: Procesar archivo Logistics (SE CONECTA VIA Reference = order_id O Order number = order_id)
    if logistics_df is not None and len(logistics_df) > 0:
        st.info("🚚 Procesando archivo Logistics...")
        st.caption("🔗 Conexión: Reference = order_id O Order number = order_id")
        
        if logistics_date:
            st.info(f"📅 Aplicando fecha {logistics_date} a registros de Logistics")
        
        logistics_dict_by_reference = {}
        logistics_dict_by_order_number = {}
        
        for idx, row in logistics_df.iterrows():
            # Limpiar IDs pero no agregar comilla todavía
            reference = normalize_id_for_db_match(row.get('Reference', ''))
            order_number = normalize_id_for_db_match(row.get('Order number', ''))
            
            # Ignorar valores inválidos como "PACKAGE RECALLED FROM UNKNOWN"
            if reference and not 'PACKAGE' in str(reference).upper():
                logistics_dict_by_reference[reference] = row
            if order_number:
                logistics_dict_by_order_number[order_number] = row
        
        st.info(f"📋 Logistics indexado: {len(logistics_dict_by_reference)} por Reference, {len(logistics_dict_by_order_number)} por Order number")
        
        logistics_columns = [
            'Guide Number', 'Order number', 'Reference', 'SAP Code', 'Invoice', 
            'Status', 'FOB', 'Unit', 'Weight', 'Length', 'Width', 'Height',
            'Insurance', 'Logistics', 'Duties Prealert', 'Duties Pay', 
            'Duty Fee', 'Saving', 'Total', 'Description', 'Shipper', 'Phone',
            'Consignee', 'Identification', 'Country', 'State', 'City', 
            'Address', 'Master Guide', 'Tariff Position', 'External Id'
        ]
        
        if logistics_date:
            consolidated_df['logistics_date'] = np.nan
        
        for col in logistics_columns:
            if col in logistics_df.columns:
                consolidated_df[f'logistics_{col.lower().replace(" ", "_")}'] = np.nan
        
        matched_by_order_id = 0
        matched_by_prealert_id = 0
        no_match_count = 0
        
        for idx, row in consolidated_df.iterrows():
            order_id = clean_id_aggressive(row.get('order_id', ''))
            prealert_id = clean_id_aggressive(row.get('prealert_id', ''))
            
            logistics_row = None
            match_type = None
            
            if order_id and order_id in logistics_dict_by_reference:
                logistics_row = logistics_dict_by_reference[order_id]
                matched_by_order_id += 1
                match_type = "order_id->Reference"
            elif order_id and order_id in logistics_dict_by_order_number:
                logistics_row = logistics_dict_by_order_number[order_id]
                matched_by_order_id += 1
                match_type = "order_id->Order number"
            elif prealert_id and prealert_id in logistics_dict_by_order_number:
                logistics_row = logistics_dict_by_order_number[prealert_id]
                matched_by_prealert_id += 1
                match_type = "prealert_id->Order number"
            
            if logistics_row is not None and not (isinstance(logistics_row, pd.Series) and logistics_row.empty):
                for col in logistics_columns:
                    if col in logistics_df.columns:
                        if isinstance(logistics_row, pd.Series):
                            value = logistics_row.get(col)
                        else:
                            value = logistics_row.get(col)
                        consolidated_df.loc[idx, f'logistics_{col.lower().replace(" ", "_")}'] = value
                
                if logistics_date:
                    consolidated_df.loc[idx, 'logistics_date'] = str(logistics_date)
            else:
                no_match_count += 1
        
        st.success(f"✅ Logistics procesado: {matched_by_order_id} por order_id, {matched_by_prealert_id} por prealert_id, {no_match_count} sin match")
    
    # PASO 3: Procesar archivo Aditionals (SE CONECTA VIA Order Id = prealert_id)
    if aditionals_df is not None and len(aditionals_df) > 0:
        st.info("➕ Procesando archivo Aditionals...")
        st.caption("🔗 Conexión: Order Id = prealert_id (NO order_id)")
        
        # Crear diccionario para sumar múltiples filas del mismo Order Id
        aditionals_dict = {}
        for idx, row in aditionals_df.iterrows():
            order_id = clean_id_aggressive(row.get('Order Id', ''))
            if order_id:
                if order_id not in aditionals_dict:
                    # Primera vez que vemos este order_id - crear entrada nueva
                    aditionals_dict[order_id] = {
                        'Order Id': order_id,
                        'Item': row.get('Item', ''),
                        'Reference': row.get('Reference', ''),
                        'Description': row.get('Description', ''),
                        'Quantity': float(row.get('Quantity', 0)) if pd.notnull(row.get('Quantity')) else 0,
                        'UnitPrice': float(row.get('UnitPrice', 0)) if pd.notnull(row.get('UnitPrice')) else 0,
                        'Total': float(row.get('Total', 0)) if pd.notnull(row.get('Total')) else 0
                    }
                else:
                    # Ya existe este order_id - sumar los valores numéricos
                    existing = aditionals_dict[order_id]
                    existing['Quantity'] += float(row.get('Quantity', 0)) if pd.notnull(row.get('Quantity')) else 0
                    existing['UnitPrice'] += float(row.get('UnitPrice', 0)) if pd.notnull(row.get('UnitPrice')) else 0
                    existing['Total'] += float(row.get('Total', 0)) if pd.notnull(row.get('Total')) else 0
                    # Para campos de texto, mantener el primero (o concatenar si prefieres)
                    if not existing['Item'] and row.get('Item'):
                        existing['Item'] = row.get('Item', '')
                    if not existing['Reference'] and row.get('Reference'):
                        existing['Reference'] = row.get('Reference', '')
                    if not existing['Description'] and row.get('Description'):
                        existing['Description'] = row.get('Description', '')
        
        
        aditionals_columns = ['Order Id', 'Item', 'Reference', 'Description', 'Quantity', 'UnitPrice', 'Total']
        
        for col in aditionals_columns:
            if col in aditionals_df.columns:
                consolidated_df[f'aditionals_{col.lower().replace(" ", "_")}'] = np.nan
        
        matched_aditionals = 0
        
        for idx, row in consolidated_df.iterrows():
            prealert_id = clean_id_aggressive(row.get('prealert_id', ''))
            
            if prealert_id and prealert_id in aditionals_dict:
                aditionals_row = aditionals_dict[prealert_id]
                matched_aditionals += 1
                
                for col in aditionals_columns:
                    if col in aditionals_df.columns:
                        consolidated_df.loc[idx, f'aditionals_{col.lower().replace(" ", "_")}'] = aditionals_row.get(col)
        
        # Contar cuántos Order Id tenían múltiples filas
        total_rows = len(aditionals_df)
        unique_orders = len(aditionals_dict)
        multiple_rows = total_rows - unique_orders
        
        if multiple_rows > 0:
            st.info(f"ℹ️ Se encontraron {multiple_rows} filas duplicadas que fueron sumadas automáticamente")
        
        st.success(f"✅ Aditionals procesado: {matched_aditionals} matches por prealert_id (de {unique_orders} Order Id únicos procesados)")
    
    # PASO 4: Calcular columna Asignacion
    st.info("🏷️ Calculando columna Asignacion...")
    
    if 'account_name' in consolidated_df.columns and 'Serial#' in consolidated_df.columns:
        consolidated_df['Asignacion'] = consolidated_df.apply(
            lambda row: calculate_asignacion(row['account_name'], row['Serial#']), 
            axis=1
        )
        asignaciones_calculadas = consolidated_df['Asignacion'].notna().sum()
        st.success(f"✅ Asignaciones calculadas: {asignaciones_calculadas}")
    else:
        st.warning("⚠️ No se pudo calcular Asignacion: faltan columnas account_name o Serial#")
    
    # PASO 5: Procesar archivo CXP (SE CONECTA VIA Ref # = asignacion)
    if cxp_df is not None and len(cxp_df) > 0:
        st.info("💰 Procesando archivo CXP (Chilexpress)...")
        st.caption("🔗 Conexión: Ref # = asignacion (campo calculado)")
        
        # Detectar automáticamente el mapeo de columnas
        column_mappings = {}
        for field in ['ot_number', 'date', 'ref_number', 'consignee', 'co_aereo', 
                     'arancel', 'iva', 'handling', 'dest_delivery', 'amt_due', 'goods_value']:
            detected_col = detect_cxp_column(cxp_df, field)
            if detected_col:
                column_mappings[field] = detected_col
        
        st.write(f"🔍 Columnas detectadas automáticamente en CXP:")
        for field, col in column_mappings.items():
            if col:
                st.write(f"   • {field} → {col}")
        
        # Crear diccionario usando la columna de referencia detectada
        ref_column = column_mappings.get('ref_number')
        if not ref_column:
            st.warning("⚠️ No se encontró columna de referencia en CXP")
            return consolidated_df
        
        cxp_dict = {}
        for idx, row in cxp_df.iterrows():
            ref_number = clean_id_aggressive(row.get(ref_column, ''))
            if ref_number:
                cxp_dict[ref_number] = row
        
        st.info(f"📋 CXP indexado: {len(cxp_dict)} registros")
        
        # Agregar columnas CXP al dataframe consolidado
        consolidated_df['cxp_ot_number'] = np.nan
        consolidated_df['cxp_date'] = np.nan
        consolidated_df['cxp_ref_number'] = np.nan
        consolidated_df['cxp_consignee'] = np.nan
        consolidated_df['cxp_co_aereo'] = np.nan
        consolidated_df['cxp_arancel'] = np.nan
        consolidated_df['cxp_iva'] = np.nan
        consolidated_df['cxp_handling'] = np.nan
        consolidated_df['cxp_dest_delivery'] = np.nan
        consolidated_df['cxp_amt_due'] = np.nan
        consolidated_df['cxp_goods_value'] = np.nan
        
        matched_cxp = 0
        
        if 'Asignacion' in consolidated_df.columns:
            for idx, row in consolidated_df.iterrows():
                asignacion = clean_id_aggressive(row.get('Asignacion', ''))
                
                if asignacion and asignacion in cxp_dict:
                    cxp_row = cxp_dict[asignacion]
                    matched_cxp += 1
                    
                    # MAPEO INTELIGENTE DE VALORES
                    consolidated_df.loc[idx, 'cxp_ot_number'] = get_column_value_safe(cxp_row, column_mappings, 'ot_number')
                    consolidated_df.loc[idx, 'cxp_date'] = format_date_standard(
                        get_column_value_safe(cxp_row, column_mappings, 'date')
                    )
                    consolidated_df.loc[idx, 'cxp_ref_number'] = get_column_value_safe(cxp_row, column_mappings, 'ref_number')
                    consolidated_df.loc[idx, 'cxp_consignee'] = get_column_value_safe(cxp_row, column_mappings, 'consignee')
                    
                    # VALORES NUMÉRICOS CON LIMPIEZA
                    consolidated_df.loc[idx, 'cxp_co_aereo'] = clean_numeric_value(
                        get_column_value_safe(cxp_row, column_mappings, 'co_aereo')
                    )
                    consolidated_df.loc[idx, 'cxp_arancel'] = clean_numeric_value(
                        get_column_value_safe(cxp_row, column_mappings, 'arancel')
                    )
                    consolidated_df.loc[idx, 'cxp_iva'] = clean_numeric_value(
                        get_column_value_safe(cxp_row, column_mappings, 'iva')
                    )
                    consolidated_df.loc[idx, 'cxp_handling'] = clean_numeric_value(
                        get_column_value_safe(cxp_row, column_mappings, 'handling')
                    )
                    consolidated_df.loc[idx, 'cxp_dest_delivery'] = clean_numeric_value(
                        get_column_value_safe(cxp_row, column_mappings, 'dest_delivery')
                    )
                    consolidated_df.loc[idx, 'cxp_amt_due'] = clean_numeric_value(
                        get_column_value_safe(cxp_row, column_mappings, 'amt_due')
                    )
                    consolidated_df.loc[idx, 'cxp_goods_value'] = clean_numeric_value(
                        get_column_value_safe(cxp_row, column_mappings, 'goods_value')
                    )
        
        st.success(f"✅ CXP procesado: {matched_cxp} matches por Asignacion")
    
    # PASO 6: Aplicar formatos básicos
    consolidated_df = apply_basic_formatting(consolidated_df)
    
    # PASO 7: Validación de duplicados
    st.info("🔍 Validando duplicados por order_id...")
    
    if 'order_id' in consolidated_df.columns:
        initial_count = len(consolidated_df)
        consolidated_df = consolidated_df.drop_duplicates(subset=['order_id'], keep='first')
        final_count = len(consolidated_df)
        
        if initial_count != final_count:
            removed_count = initial_count - final_count
            st.warning(f"⚠️ Se removieron {removed_count} registros duplicados por order_id")
        else:
            st.success("✅ No se encontraron duplicados por order_id")
    
    st.success(f"🎉 Consolidación completada: {len(consolidated_df)} registros finales")
    return consolidated_df

def prepare_record_for_db(record):
    """Prepara un registro para inserción en la base de datos"""
    
    integer_columns = ['system_number', 'quantity', 'iva', 'ica']
    
    numeric_columns = [
        'unit_price', 'declare_value', 'meli_fee', 'fuente', 
        'senders_cost', 'gross_amount', 'net_received_amount',
        'digital_verification', 'net_real_amount', 'logistic_weight_lbs',
        'logistics_fob', 'logistics_weight', 'logistics_length', 
        'logistics_width', 'logistics_height', 'logistics_insurance',
        'logistics_logistics', 'logistics_duties_prealert', 
        'logistics_duties_pay', 'logistics_duty_fee', 'logistics_saving',
        'logistics_total',
        'aditionals_quantity', 'aditionals_unitprice', 'aditionals_total',
        'cxp_co_aereo', 'cxp_arancel', 'cxp_iva', 'cxp_handling',
        'cxp_dest_delivery', 'cxp_amt_due', 'cxp_goods_value'
    ]
    
    date_columns = ['logistics_date', 'date_created', 'refunded_date', 'cxp_date']
    
    cleaned_record = {}
    
    for key, value in record.items():
        if pd.isna(value) or value is None:
            cleaned_record[key] = None
        elif isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            cleaned_record[key] = None
        elif key in date_columns:
            if isinstance(value, (pd.Timestamp, datetime)):
                cleaned_record[key] = value.strftime('%Y-%m-%d')
            elif isinstance(value, date):
                cleaned_record[key] = value.strftime('%Y-%m-%d')
            elif isinstance(value, str) and value and value != 'nan':
                cleaned_record[key] = value
            else:
                cleaned_record[key] = None
        elif isinstance(value, (pd.Timestamp, datetime)):
            cleaned_record[key] = value.strftime('%Y-%m-%d') if hasattr(value, 'strftime') else str(value)
        elif key in integer_columns:
            try:
                clean_val = clean_numeric_value(value)
                if clean_val is not None and not math.isnan(clean_val) and not math.isinf(clean_val):
                    cleaned_record[key] = int(float(clean_val))
                else:
                    cleaned_record[key] = None
            except:
                cleaned_record[key] = None
        elif key in numeric_columns:
            clean_val = clean_numeric_value(value)
            if clean_val is not None and not math.isnan(clean_val) and not math.isinf(clean_val):
                cleaned_record[key] = clean_val
            else:
                cleaned_record[key] = None
        else:
            str_value = str(value)
            if str_value == 'nan' or str_value == 'None':
                cleaned_record[key] = None
            else:
                cleaned_record[key] = str_value
    
    return cleaned_record

def insert_or_update_to_supabase(df, filename=None, logistics_matched=0, aditionals_matched=0, cxp_matched=0):
    """Inserta nuevos registros o actualiza existentes en Supabase"""
    start_time = time.time()
    
    try:
        st.info("🔍 Verificando registros existentes en la base de datos...")
        
        df_mapped = map_column_names(df)
        
        order_ids_to_process = df_mapped['order_id'].dropna().unique().tolist()
        
        if not order_ids_to_process:
            st.error("❌ No se encontraron order_ids válidos para procesar")
            return 0, 0
        
        st.info(f"📊 Procesando {len(order_ids_to_process)} order_ids únicos")
        
        existing_order_ids = []
        batch_size = 100
        
        for i in range(0, len(order_ids_to_process), batch_size):
            batch = order_ids_to_process[i:i + batch_size]
            try:
                result = supabase.table('consolidated_orders').select('order_id').in_('order_id', batch).execute()
                existing_order_ids.extend([record['order_id'] for record in result.data])
            except Exception as e:
                st.error(f"Error consultando registros existentes: {str(e)}")
        
        existing_order_ids_set = set(existing_order_ids)
        
        new_records = []
        update_records = []
        
        db_columns = [
            'system_number', 'serial_number', 'order_id', 'pack_id', 'asin',
            'client_first_name', 'client_last_name', 'client_doc_id', 'account_name',
            'date_created', 'quantity', 'title', 'unit_price', 'logistic_type',
            'address_line', 'street_name', 'street_number', 'city', 'state', 'country',
            'receiver_phone', 'amz_order_id', 'prealert_id', 'etiqueta_envio',
            'order_status_meli', 'declare_value', 'meli_fee', 'iva', 'ica', 'fuente',
            'senders_cost', 'gross_amount', 'net_received_amount', 'nombre_del_tercero',
            'direccion', 'apelido_del_tercero', 'estado', 'razon_social', 'ciudad',
            'numero_de_documento', 'digital_verification', 'tipo', 'telefono', 'giro',
            'correo', 'net_real_amount', 'logistic_weight_lbs', 'refunded_date',
            'asignacion'
        ]
        
        for col in df_mapped.columns:
            if (col.startswith('logistics_') or col.startswith('aditionals_') or col.startswith('cxp_')) and col not in db_columns:
                db_columns.append(col)
        
        df_filtered = df_mapped[[col for col in db_columns if col in df_mapped.columns]]
        records = df_filtered.to_dict('records')
        
        for record in records:
            cleaned_record = prepare_record_for_db(record)
            order_id = cleaned_record.get('order_id')
            
            if order_id and order_id in existing_order_ids_set:
                update_records.append(cleaned_record)
            else:
                new_records.append(cleaned_record)
        
        st.info(f"📊 Resumen de procesamiento:")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total a procesar", len(records))
        with col2:
            st.metric("Registros existentes", len(update_records))
        with col3:
            st.metric("Registros nuevos", len(new_records))
        
        total_inserted = 0
        total_updated = 0
        
        if new_records:
            st.info(f"➕ Insertando {len(new_records)} nuevos registros...")
            
            batch_size = 50
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for i in range(0, len(new_records), batch_size):
                batch = new_records[i:i + batch_size]
                
                try:
                    result = supabase.table('consolidated_orders').insert(batch).execute()
                    total_inserted += len(batch)
                    
                    progress = min(1.0, (i + batch_size) / len(new_records))
                    progress_bar.progress(progress)
                    status_text.text(f"Insertando nuevos: {total_inserted}/{len(new_records)} registros")
                    
                except Exception as batch_error:
                    st.error(f"Error insertando lote: {str(batch_error)}")
                    continue
            
            progress_bar.progress(1.0)
            st.success(f"✅ {total_inserted} registros nuevos insertados")
            
            # Log de actividad
            if AUTH_AVAILABLE:
                log_activity("process_data", f"Consolidación completa procesada: {total_inserted} registros insertados", 
                           "consolidation", None, total_inserted)
        
        if update_records:
            st.info(f"🔄 Actualizando {len(update_records)} registros existentes...")
            
            batch_size = 50
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for i in range(0, len(update_records), batch_size):
                batch = update_records[i:i + batch_size]
                
                try:
                    result = supabase.table('consolidated_orders').upsert(
                        batch, 
                        on_conflict='order_id',
                        ignore_duplicates=False
                    ).execute()
                    
                    total_updated += len(batch)
                    
                    progress = (i + batch_size) / len(update_records)
                    progress_bar.progress(min(1.0, progress))
                    status_text.text(f"Actualizando: {total_updated}/{len(update_records)} registros")
                    
                    if i % 500 == 0 and i > 0:
                        time.sleep(0.1)
                    
                except Exception as update_error:
                    st.warning(f"Error actualizando lote {i//batch_size + 1}: {str(update_error)}")
                    continue
            
            progress_bar.progress(1.0)
            st.success(f"✅ {total_updated} registros actualizados")
        
        return total_inserted, total_updated
        
    except Exception as e:
        st.error(f"Error general: {str(e)}")
        return 0, 0

def update_logistics_only(logistics_df, logistics_date=None):
    """Actualiza solo las columnas de logistics en registros existentes"""
    try:
        # Variables para reporte
        total_in_file = len(logistics_df)
        not_found_records = []
        
        logistics_dict_by_reference = {}
        logistics_dict_by_order_number = {}
        
        for idx, row in logistics_df.iterrows():
            # Limpiar IDs pero no agregar comilla todavía
            reference = normalize_id_for_db_match(row.get('Reference', ''))
            order_number = normalize_id_for_db_match(row.get('Order number', ''))
            
            # Ignorar valores inválidos como "PACKAGE RECALLED FROM UNKNOWN"
            if reference and not 'PACKAGE' in str(reference).upper():
                logistics_dict_by_reference[reference] = row
            if order_number:
                logistics_dict_by_order_number[order_number] = row
        
        
        # Obtener todos los IDs únicos del logistics para buscar específicamente
        all_logistics_ids = set()
        all_logistics_ids.update(logistics_dict_by_reference.keys())
        all_logistics_ids.update(logistics_dict_by_order_number.keys())
        
        if not all_logistics_ids:
            st.warning("No hay IDs válidos en el archivo Logistics")
            return 0
        
        # Buscar registros específicos por order_id y prealert_id
        matching_records = []
        
        # Buscar registros específicos por order_id y prealert_id (silencioso)
        # Buscar por order_id (References del archivo)
        order_ids_to_search = list(logistics_dict_by_reference.keys())
        if order_ids_to_search:
            for ref_id in order_ids_to_search:
                # Probar múltiples formatos
                search_variants = [
                    ref_id,                    # Como está: 2000011458658334
                    f"'{ref_id}",             # Con comilla: '2000011458658334
                    f"{ref_id}.0",            # Con .0: 2000011458658334.0
                    f"'{ref_id}.0"            # Con comilla y .0
                ]
                
                found = False
                for variant in search_variants:
                    try:
                        result = supabase.table('consolidated_orders').select('id, order_id, prealert_id').eq('order_id', variant).limit(1).execute()
                        if result.data:
                            matching_records.extend(result.data)
                            found = True
                            break
                    except:
                        pass
                
                if not found:
                    not_found_records.append(f"Reference: {ref_id}")
        
        # Buscar por prealert_id (Order numbers del archivo)
        prealert_ids_to_search = list(logistics_dict_by_order_number.keys())
        if prealert_ids_to_search:
            for order_num in prealert_ids_to_search:
                # Probar múltiples formatos
                search_variants = [
                    order_num,                    # Como está: 1020539
                    f"{order_num}.0",            # Con .0: 1020539.0
                    f"'{order_num}",             # Con comilla: '1020539
                    f"'{order_num}.0"            # Con comilla y .0
                ]
                
                found = False
                for variant in search_variants:
                    try:
                        result = supabase.table('consolidated_orders').select('id, order_id, prealert_id').eq('prealert_id', variant).limit(1).execute()
                        if result.data:
                            # Evitar duplicados
                            existing_ids = {r['id'] for r in matching_records}
                            if result.data[0]['id'] not in existing_ids:
                                matching_records.extend(result.data)
                            found = True
                            break
                    except:
                        pass
                
                if not found:
                    not_found_records.append(f"Order number: {order_num}")
        
        if not matching_records:
            return 0
        
        existing_records = pd.DataFrame(matching_records)
        
        updates_to_perform = []
        matched_count = 0
        
        for _, record in existing_records.iterrows():
            order_id_raw = record.get('order_id', '')
            prealert_id_raw = record.get('prealert_id', '')
            db_id = record.get('id')
            
            logistics_row = None
            match_info = None
            
            # Intentar hacer match con múltiples formatos para order_id -> Reference
            for ref_key in logistics_dict_by_reference.keys():
                if str(order_id_raw) == ref_key or \
                   str(order_id_raw).replace("'", '') == ref_key or \
                   str(order_id_raw).replace('.0', '') == ref_key or \
                   str(order_id_raw).replace("'", '').replace('.0', '') == ref_key:
                    logistics_row = logistics_dict_by_reference[ref_key]
                    match_info = f"order_id->Reference: {order_id_raw}"
                    break
            
            # Si no se encontró, intentar con prealert_id -> Order number
            if logistics_row is None or (isinstance(logistics_row, pd.Series) and logistics_row.empty):
                for order_key in logistics_dict_by_order_number.keys():
                    if str(prealert_id_raw) == order_key or \
                       str(prealert_id_raw).replace('.0', '') == order_key or \
                       str(prealert_id_raw).replace("'", '') == order_key or \
                       str(prealert_id_raw).replace("'", '').replace('.0', '') == order_key:
                        logistics_row = logistics_dict_by_order_number[order_key]
                        match_info = f"prealert_id->Order number: {prealert_id_raw}"
                        break
            
            if logistics_row is not None and not (isinstance(logistics_row, pd.Series) and logistics_row.empty):
                matched_count += 1
                
                update_data = {'id': db_id}
                
                logistics_mapping = {
                    'Guide Number': 'logistics_guide_number',
                    'Order number': 'logistics_order_number',
                    'Reference': 'logistics_reference',
                    'SAP Code': 'logistics_sap_code',
                    'Invoice': 'logistics_invoice',
                    'Status': 'logistics_status',
                    'FOB': 'logistics_fob',
                    'Unit': 'logistics_unit',
                    'Weight': 'logistics_weight',
                    'Length': 'logistics_length',
                    'Width': 'logistics_width',
                    'Height': 'logistics_height',
                    'Insurance': 'logistics_insurance',
                    'Logistics': 'logistics_logistics',
                    'Duties Prealert': 'logistics_duties_prealert',
                    'Duties Pay': 'logistics_duties_pay',
                    'Duty Fee': 'logistics_duty_fee',
                    'Saving': 'logistics_saving',
                    'Total': 'logistics_total',
                    'Description': 'logistics_description',
                    'Shipper': 'logistics_shipper',
                    'Phone': 'logistics_phone',
                    'Consignee': 'logistics_consignee',
                    'Identification': 'logistics_identification',
                    'Country': 'logistics_country',
                    'State': 'logistics_state',
                    'City': 'logistics_city',
                    'Address': 'logistics_address',
                    'Master Guide': 'logistics_master_guide',
                    'Tariff Position': 'logistics_tariff_position',
                    'External Id': 'logistics_external_id'
                }
                
                for orig_col, db_col in logistics_mapping.items():
                    if orig_col in logistics_df.columns:
                        value = logistics_row.get(orig_col)
                        
                        if pd.isna(value):
                            update_data[db_col] = None
                        elif orig_col in ['FOB', 'Weight', 'Length', 'Width', 'Height', 'Insurance', 
                                         'Logistics', 'Duties Prealert', 'Duties Pay', 'Duty Fee', 
                                         'Saving', 'Total']:
                            clean_val = clean_numeric_value(value)
                            if clean_val is not None and not math.isnan(clean_val if isinstance(clean_val, float) else 0):
                                update_data[db_col] = clean_val
                            else:
                                update_data[db_col] = None
                        else:
                            update_data[db_col] = value if value and str(value).lower() != 'nan' else None
                
                if logistics_date:
                    if isinstance(logistics_date, (datetime, date)):
                        update_data['logistics_date'] = logistics_date.strftime('%Y-%m-%d')
                    else:
                        update_data['logistics_date'] = str(logistics_date)
                
                cleaned_update = clean_update_data(update_data)
                updates_to_perform.append(cleaned_update)
        
        if updates_to_perform:
            
            batch_size = 50
            total_updated = 0
            progress_bar = st.progress(0)
            
            for i in range(0, len(updates_to_perform), batch_size):
                batch = updates_to_perform[i:i + batch_size]
                
                try:
                    for update in batch:
                        try:
                            record_id = update.pop('id')
                            final_clean_update = clean_update_data(update)
                            supabase.table('consolidated_orders').update(final_clean_update).eq('id', record_id).execute()
                            total_updated += 1
                        except Exception as individual_error:
                            continue
                    
                    progress = min(1.0, (i + batch_size) / len(updates_to_perform))
                    progress_bar.progress(progress)
                    
                except Exception as e:
                    st.warning(f"Error actualizando lote: {str(e)}")
                    continue
            
            progress_bar.progress(1.0)
            
            # Mostrar reporte conciso
            st.markdown("### 📊 Reporte de Logistics")
            found_in_db = len(existing_records)
            show_concise_report(total_in_file, found_in_db, total_updated, not_found_records)
            
            if total_updated > 0:
                st.success(f"✅ {total_updated} registros actualizados exitosamente")
            
            return total_updated
        else:
            # Mostrar reporte aunque no haya actualizaciones
            st.markdown("### 📊 Reporte de Logistics")
            found_in_db = 0
            show_concise_report(total_in_file, found_in_db, 0, not_found_records)
            st.error("❌ No se actualizaron registros")
            return 0
            
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return 0

def update_aditionals_only(aditionals_df):
    """Actualiza solo las columnas de aditionals en registros existentes"""
    try:
        # Variables para reporte
        total_in_file = len(aditionals_df)
        not_found_records = []
        
        # Crear diccionario para sumar múltiples filas del mismo Order Id  
        aditionals_dict = {}
        
        for idx, row in aditionals_df.iterrows():
            # Normalizar Order Id para que coincida con formato de BD (con comilla si es necesario)
            order_id = normalize_id_for_db_match(row.get('Order Id', ''))
            if order_id:
                if order_id not in aditionals_dict:
                    # Primera vez que vemos este order_id - crear entrada nueva
                    aditionals_dict[order_id] = {
                        'Order Id': order_id,
                        'Item': row.get('Item', ''),
                        'Reference': row.get('Reference', ''),
                        'Description': row.get('Description', ''),
                        'Quantity': float(row.get('Quantity', 0)) if pd.notnull(row.get('Quantity')) else 0,
                        'UnitPrice': float(row.get('UnitPrice', 0)) if pd.notnull(row.get('UnitPrice')) else 0,
                        'Total': float(row.get('Total', 0)) if pd.notnull(row.get('Total')) else 0
                    }
                else:
                    # Ya existe este order_id - sumar los valores numéricos
                    existing = aditionals_dict[order_id]
                    existing['Quantity'] += float(row.get('Quantity', 0)) if pd.notnull(row.get('Quantity')) else 0
                    existing['UnitPrice'] += float(row.get('UnitPrice', 0)) if pd.notnull(row.get('UnitPrice')) else 0
                    existing['Total'] += float(row.get('Total', 0)) if pd.notnull(row.get('Total')) else 0
                    # Para campos de texto, mantener el primero
                    if not existing['Item'] and row.get('Item'):
                        existing['Item'] = row.get('Item', '')
                    if not existing['Reference'] and row.get('Reference'):
                        existing['Reference'] = row.get('Reference', '')
                    if not existing['Description'] and row.get('Description'):
                        existing['Description'] = row.get('Description', '')
        
        
        # Obtener IDs específicos para buscar en BD
        if not aditionals_dict:
            return 0
        
        aditionals_ids_to_search = list(aditionals_dict.keys())
        
        # Buscar registros específicos por prealert_id
        matching_records = []
        
        # Buscar registros específicos por prealert_id (silencioso)
        # Para cada ID, buscar en múltiples formatos
        for order_id in aditionals_ids_to_search:
            # Generar todas las variantes posibles del ID
            search_variants = [
                order_id,                    # Como está: 1049072
                f"{order_id}.0",            # Con .0: 1049072.0
                f"'{order_id}",             # Con comilla: '1049072
                f"'{order_id}.0"            # Con comilla y .0: '1049072.0
            ]
            
            found = False
            for variant in search_variants:
                try:
                    result = supabase.table('consolidated_orders').select('id, order_id, prealert_id').eq('prealert_id', variant).limit(1).execute()
                    if result.data:
                        matching_records.extend(result.data)
                        found = True
                        break
                except:
                    pass
            
            if not found:
                not_found_records.append(f"Order ID: {order_id}")
        
        if not matching_records:
            return 0
        
        existing_records = pd.DataFrame(matching_records)
        
        updates_to_perform = []
        matched_count = 0
        
        for _, record in existing_records.iterrows():
            prealert_id_raw = record.get('prealert_id', '')
            db_id = record.get('id')
            
            # Intentar hacer match con múltiples formatos
            matched_key = None
            for key in aditionals_dict.keys():
                # Comparar diferentes formatos
                if str(prealert_id_raw) == key or \
                   str(prealert_id_raw).replace('.0', '') == key or \
                   str(prealert_id_raw).replace("'", '') == key or \
                   str(prealert_id_raw).replace("'", '').replace('.0', '') == key:
                    matched_key = key
                    break
            
            if matched_key:
                matched_count += 1
                aditionals_row = aditionals_dict[matched_key]
                
                update_data = {'id': db_id}
                
                aditionals_mapping = {
                    'Order Id': 'aditionals_order_id',
                    'Item': 'aditionals_item',
                    'Reference': 'aditionals_reference',
                    'Description': 'aditionals_description',
                    'Quantity': 'aditionals_quantity',
                    'UnitPrice': 'aditionals_unitprice',
                    'Total': 'aditionals_total'
                }
                
                for orig_col, db_col in aditionals_mapping.items():
                    if orig_col in aditionals_df.columns:
                        value = aditionals_row.get(orig_col)
                        if orig_col in ['Quantity', 'UnitPrice', 'Total']:
                            value = clean_numeric_value(value)
                        update_data[db_col] = value
                
                updates_to_perform.append(update_data)
        
        if updates_to_perform:
            
            batch_size = 50
            total_updated = 0
            progress_bar = st.progress(0)
            
            for i in range(0, len(updates_to_perform), batch_size):
                batch = updates_to_perform[i:i + batch_size]
                
                try:
                    for update in batch:
                        record_id = update.pop('id')
                        clean_update = clean_update_data(update)
                        supabase.table('consolidated_orders').update(clean_update).eq('id', record_id).execute()
                        total_updated += 1
                    
                    progress = min(1.0, (i + batch_size) / len(updates_to_perform))
                    progress_bar.progress(progress)
                    
                except Exception as e:
                    st.warning(f"Error actualizando lote: {str(e)}")
                    continue
            
            progress_bar.progress(1.0)
            
            # Mostrar reporte conciso
            st.markdown("### 📊 Reporte de Aditionals")
            found_in_db = len(existing_records) if 'existing_records' in locals() else matched_count
            show_concise_report(total_in_file, found_in_db, total_updated, not_found_records)
            
            if total_updated > 0:
                st.success(f"✅ {total_updated} registros actualizados exitosamente")
            
            return total_updated
        else:
            # Mostrar reporte aunque no haya actualizaciones
            st.markdown("### 📊 Reporte de Aditionals")
            show_concise_report(total_in_file, 0, 0, not_found_records)
            st.error("❌ No se actualizaron registros")
            return 0
            
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return 0

def update_cxp_only(cxp_df):
    """
    🔄 ACTUALIZA AUTOMÁTICAMENTE las columnas de CXP en registros existentes 
    SIEMPRE FUERZA LA ACTUALIZACIÓN - Corrige valores trocados automáticamente
    """
    try:
        st.info("💰 🔄 Actualizando columnas CXP (Chilexpress) - MODO CORRECCIÓN AUTOMÁTICA")
        st.success("✨ **NUEVO**: Esta función corrige automáticamente valores trocados")
        
        # Detectar automáticamente el mapeo de columnas
        st.info("🔍 Detectando estructura del archivo CXP...")
        
        column_mappings = {}
        for field in ['ot_number', 'date', 'ref_number', 'consignee', 'co_aereo', 
                     'arancel', 'iva', 'handling', 'dest_delivery', 'amt_due', 'goods_value']:
            detected_col = detect_cxp_column(cxp_df, field)
            if detected_col:
                column_mappings[field] = detected_col
        
        # Mostrar mapeo detectado
        st.success("✅ Mapeo de columnas detectado:")
        for field, col in column_mappings.items():
            if col:
                st.write(f"   • {field} → {col}")
        
        # Verificar columna de referencia
        ref_column_name = column_mappings.get('ref_number')
        if not ref_column_name:
            st.error("❌ No se encontró columna de referencia en el archivo CXP")
            st.info(f"Columnas disponibles: {list(cxp_df.columns)}")
            return 0
        
        st.info(f"📌 Usando columna '{ref_column_name}' para referencias")
        
        # Crear diccionario de CXP por referencia
        cxp_dict = {}
        ref_values_sample = []
        
        for idx, row in cxp_df.iterrows():
            ref_number = clean_id_aggressive(row.get(ref_column_name, ''))
            if ref_number:
                cxp_dict[ref_number] = row
                if len(ref_values_sample) < 10:
                    ref_values_sample.append(ref_number)
        
        st.info(f"📋 CXP indexado: {len(cxp_dict)} registros por ref_number")
        if ref_values_sample:
            st.write(f"🔍 Ejemplos de ref_number en CXP: {ref_values_sample[:5]}")
        
        # Obtener TODOS los registros de VEENDELO, FABORCARGO y MEGATIENDA SPA
        cxp_accounts = ['3-VEENDELO', '8-FABORCARGO', '2-MEGATIENDA SPA']
        
        # OBTENER TODOS LOS REGISTROS - Cuenta por cuenta para evitar límites
        st.info("🔍 Obteniendo TODOS los registros de cuentas CXP...")
        all_records = []
        
        for account_name in cxp_accounts:
            st.write(f"   📂 Obteniendo registros de {account_name}...")
            page_size = 1000
            current_page = 0
            account_records = []
            
            while True:
                offset = current_page * page_size
                
                # Query específica por cuenta con paginación
                result = supabase.table('consolidated_orders').select(
                    'id, account_name, serial_number, asignacion, cxp_amt_due'
                ).eq('account_name', account_name).range(offset, offset + page_size - 1).execute()
                
                if not result.data or len(result.data) == 0:
                    break
                    
                account_records.extend(result.data)
                current_page += 1
                
                # Si obtenemos menos de 1000, es la última página
                if len(result.data) < page_size:
                    break
                
                # Límite de seguridad
                if current_page > 20:  # Máximo 20,000 registros por cuenta
                    st.warning(f"   ⚠️ Límite de seguridad alcanzado para {account_name}")
                    break
            
            st.write(f"   ✅ {account_name}: {len(account_records)} registros obtenidos")
            all_records.extend(account_records)
        
        st.success(f"📊 TOTAL REGISTROS OBTENIDOS: {len(all_records)}")
        
        if not all_records:
            st.warning("No hay registros de VEENDELO o FABORCARGO en la base de datos para actualizar")
            return 0
        
        existing_records = pd.DataFrame(all_records)
        
        # Contar registros con valores problemáticos
        registros_con_error = 0
        for _, row in existing_records.iterrows():
            cxp_amt = row.get('cxp_amt_due')
            if pd.notna(cxp_amt) and cxp_amt < 11.2:
                registros_con_error += 1
        
        st.info(f"📊 Total registros en BD: {len(existing_records)}")
        if registros_con_error > 0:
            st.warning(f"⚠️ {registros_con_error} registros tienen cxp_amt_due < 11.2 (valores incorrectos)")
        
        # Calcular asignaciones si no existen
        asignaciones_sample = []
        for idx, record in existing_records.iterrows():
            if pd.isna(record.get('asignacion')) or not record.get('asignacion'):
                asignacion = calculate_asignacion(
                    record.get('account_name'),
                    record.get('serial_number')
                )
                existing_records.loc[idx, 'asignacion'] = asignacion
            
            asig = existing_records.loc[idx, 'asignacion']
            if asig and len(asignaciones_sample) < 10:
                asignaciones_sample.append(clean_id_aggressive(asig))
        
        if asignaciones_sample:
            st.write(f"🔍 Ejemplos de Asignaciones en BD: {asignaciones_sample[:5]}")
        
        # Preparar actualizaciones - SIEMPRE ACTUALIZAR (MODO CORRECCIÓN)
        updates_to_perform = []
        matched_count = 0
        total_records = len(existing_records)
        
        st.info(f"🔍 Buscando matches entre {len(cxp_dict)} refs del archivo y {total_records} asignaciones de BD...")
        
        for idx, record in existing_records.iterrows():
            asignacion = clean_id_aggressive(record.get('asignacion', ''))
            db_id = record.get('id')
            account = record.get('account_name', '')
            
            # Forzar match - No importa si ya tiene CXP data
            if asignacion and asignacion in cxp_dict:
                matched_count += 1
                cxp_row = cxp_dict[asignacion]
                
                update_data = {
                    'id': db_id,
                    'asignacion': asignacion
                }
                
                # MAPEO INTELIGENTE - No depende de nombres exactos
                update_data['cxp_ot_number'] = get_column_value_safe(cxp_row, column_mappings, 'ot_number')
                update_data['cxp_date'] = format_date_standard(get_column_value_safe(cxp_row, column_mappings, 'date'))
                update_data['cxp_ref_number'] = get_column_value_safe(cxp_row, column_mappings, 'ref_number')
                update_data['cxp_consignee'] = get_column_value_safe(cxp_row, column_mappings, 'consignee')
                
                # 🔄 VALORES NUMÉRICOS CON CORRECCIÓN AUTOMÁTICA
                cxp_amt_due_value = clean_numeric_value(get_column_value_safe(cxp_row, column_mappings, 'amt_due'))
                dest_delivery_value = clean_numeric_value(get_column_value_safe(cxp_row, column_mappings, 'dest_delivery'))
                goods_value = clean_numeric_value(get_column_value_safe(cxp_row, column_mappings, 'goods_value'))
                
                # FORZAR LA ACTUALIZACIÓN CON LOS VALORES CORRECTOS DEL ARCHIVO
                update_data['cxp_co_aereo'] = clean_numeric_value(
                    get_column_value_safe(cxp_row, column_mappings, 'co_aereo')
                )
                update_data['cxp_arancel'] = clean_numeric_value(
                    get_column_value_safe(cxp_row, column_mappings, 'arancel')
                )
                update_data['cxp_iva'] = clean_numeric_value(
                    get_column_value_safe(cxp_row, column_mappings, 'iva')
                )
                update_data['cxp_handling'] = clean_numeric_value(
                    get_column_value_safe(cxp_row, column_mappings, 'handling')
                )
                
                # 🔄 VALORES CORREGIDOS - Los del archivo son los correctos
                update_data['cxp_dest_delivery'] = dest_delivery_value
                update_data['cxp_amt_due'] = cxp_amt_due_value
                update_data['cxp_goods_value'] = goods_value
                
                # También actualizar declare_value (sin prefijo cxp_) y NO dest_delivery
                update_data['declare_value'] = goods_value
                # NO actualizar dest_delivery - no existe en la tabla
                
                updates_to_perform.append(update_data)
                
                if matched_count <= 5:
                    st.write(f"🔄 Corrigiendo {matched_count}: {account} - {asignacion}")
                    st.write(f"   • cxp_amt_due: {cxp_amt_due_value}")
                    st.write(f"   • dest_delivery: {dest_delivery_value}")
                    st.write(f"   • declare_value: {goods_value}")
        
        # MOSTRAR ESTADÍSTICAS DE MATCHING
        st.info(f"📊 **Estadísticas de Matching:**")
        st.write(f"• Total registros en CXP: {len(cxp_dict)}")
        st.write(f"• Total registros en BD: {total_records}")
        st.write(f"• **Matches encontrados: {matched_count}**")
        
        if matched_count > 0:
            match_percentage = (matched_count / len(cxp_dict)) * 100
            st.write(f"• **Porcentaje de match: {match_percentage:.1f}%**")
        
        # EJECUTAR ACTUALIZACIONES FORZADAS
        if updates_to_perform:
            st.success(f"🔄 **FORZANDO ACTUALIZACIÓN** de {len(updates_to_perform)} registros con valores corregidos")
            
            batch_size = 25  # Lotes más pequeños para mayor confiabilidad
            total_updated = 0
            progress_bar = st.progress(0)
            errors_count = 0
            success_details = []
            
            for i in range(0, len(updates_to_perform), batch_size):
                batch = updates_to_perform[i:i + batch_size]
                
                try:
                    for update in batch:
                        try:
                            # Hacer copia para no modificar el original
                            update_copy = update.copy()
                            record_id = update_copy.pop('id')
                            
                            # Limpiar datos antes de enviar
                            clean_update = clean_update_data(update_copy)
                            
                            # Verificar que tenemos datos válidos para actualizar
                            if not clean_update or len(clean_update) == 0:
                                continue
                            
                            # FORZAR LA ACTUALIZACIÓN - Incluir todos los campos
                            result = supabase.table('consolidated_orders').update(clean_update).eq('id', record_id).execute()
                            
                            if result.data and len(result.data) > 0:
                                total_updated += 1
                                success_details.append({
                                    'id': record_id,
                                    'asignacion': update.get('asignacion'),
                                    'cxp_amt_due': clean_update.get('cxp_amt_due'),
                                    'dest_delivery': clean_update.get('dest_delivery'),
                                    'declare_value': clean_update.get('declare_value')
                                })
                            else:
                                errors_count += 1
                                if errors_count <= 5:
                                    st.warning(f"⚠️ No se actualizó registro ID {record_id}: respuesta vacía")
                                
                        except Exception as individual_error:
                            errors_count += 1
                            if errors_count <= 5:
                                st.error(f"❌ Error actualizando ID {record_id}: {str(individual_error)}")
                            continue
                    
                    progress = min(1.0, (i + batch_size) / len(updates_to_perform))
                    progress_bar.progress(progress)
                    
                    # Mostrar progreso en tiempo real
                    if i % 50 == 0:
                        st.write(f"⏳ Procesando lote {i//batch_size + 1}... ({total_updated} actualizados)")
                    
                except Exception as e:
                    st.warning(f"Error actualizando lote: {str(e)}")
                    continue
            
            progress_bar.progress(1.0)
            
            # MOSTRAR RESULTADOS DETALLADOS
            if total_updated > 0:
                st.success(f"✅ **¡CORRECCIÓN COMPLETADA!** {total_updated} registros actualizados")
                
                # Mostrar algunos ejemplos de correcciones
                if success_details:
                    st.info("📋 **Ejemplos de correcciones aplicadas:**")
                    for detail in success_details[:5]:
                        st.write(f"• {detail['asignacion']}: amt_due={detail['cxp_amt_due']}, dest_delivery={detail['dest_delivery']}")
                
                st.balloons()
                
            if errors_count > 0:
                st.warning(f"⚠️ Se encontraron {errors_count} errores durante la actualización")
            
            return total_updated
        else:
            st.warning("⚠️ No se encontraron coincidencias entre las asignaciones de la BD y los ref_number del archivo CXP")
            
            # DIAGNÓSTICO DETALLADO cuando no hay matches
            st.error("🔍 **DIAGNÓSTICO**: Análisis de por qué no hay matches")
            
            # Mostrar ejemplos de ambos lados
            cxp_sample = list(cxp_dict.keys())[:10]
            bd_asignaciones_sample = [clean_id_aggressive(str(asig)) for asig in existing_records['asignacion'].dropna().head(10)]
            
            st.write("**📄 Ejemplos de Ref# en archivo CXP:**")
            st.code("\n".join(cxp_sample))
            
            st.write("**🗄️ Ejemplos de asignaciones en BD:**")
            st.code("\n".join(bd_asignaciones_sample))
            
            # Analizar prefijos
            cxp_prefixes = set()
            bd_prefixes = set()
            
            for ref in cxp_sample:
                if len(ref) >= 3:
                    cxp_prefixes.add(ref[:4])
            
            for asig in bd_asignaciones_sample:
                if asig and len(asig) >= 3:
                    bd_prefixes.add(asig[:4])
            
            st.write(f"**🏷️ Prefijos en archivo CXP:** {list(cxp_prefixes)}")
            st.write(f"**🏷️ Prefijos en BD:** {list(bd_prefixes)}")
            
            st.info("💡 **Solución**: Usa el Debug CXP para análisis más detallado")
            return 0
            
    except Exception as e:
        st.error(f"Error en update_cxp_only: {str(e)}")
        st.exception(e)
        return 0

# =====================================================
# INTERFAZ PRINCIPAL
# =====================================================

def main():
    # Verificar autenticación si está disponible
    if AUTH_AVAILABLE:
        require_auth()
        show_user_info()
    
    st.title("📦 Consolidador de Órdenes")
    st.markdown("### Sistema Modular de Consolidación de Datos")
    
    # Explicación del sistema modular
    with st.expander("📋 ¿Cómo funciona el sistema modular?", expanded=False):
        st.markdown("""
        **🎯 CONCEPTO**: Sistema de archivos independientes que se complementan
        
        **1. 📊 Archivo Drapify (PRINCIPAL)**
        - ✅ **CREA** la base de datos usando `order_id`
        - 🏗️ Archivo MADRE que establece todos los registros base
        - 🔑 Cada `order_id` genera un registro único
        
        **2. 🚚 Archivo Logistics (OPCIONAL)**  
        - 🔗 Se conecta via: `Reference` = `order_id` O `Order number` = `order_id`
        - ➕ **AGREGA** información logística a registros existentes
        - 📦 Pesos, dimensiones, costos de envío
        
        **3. ➕ Archivo Aditionals (OPCIONAL)**
        - 🔗 Se conecta via: `Order Id` = `prealert_id` (NO order_id)
        - ➕ **AGREGA** costos adicionales y detalles extra
        - 💰 Seguros, servicios especiales, etc.
        
        **4. 💰 Archivo CXP (OPCIONAL)**
        - 🔗 Se conecta via: `Ref #` = `asignacion` (campo calculado)
        - ➕ **AGREGA** información de cuentas por pagar  
        - 🧾 Impuestos, aranceles, costos finales
        
        **🔄 VENTAJAS**:
        - ✅ Puedes subir archivos independientemente  
        - ✅ Si un `order_id` ya existe, solo se ACTUALIZA/RELLENA
        - ✅ No se duplican registros
        - ✅ Información se va completando por partes
        - ✅ Flexibilidad total en el orden de carga
        """)
    
    st.markdown("---")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuración")
        
        has_existing_data = check_existing_data()
        
        if has_existing_data:
            st.success("✅ Base de datos con registros")
            st.info("• Registros nuevos se **agregan**")
            st.info("• Registros existentes se **actualizan**")
        else:
            st.info("📊 Base de datos vacía")
            st.info("Todos los registros se insertarán")
        
        st.markdown("---")
        st.markdown("**📋 Sistema Inteligente:**")
        st.markdown("• Detecta automáticamente duplicados")
        st.markdown("• Actualiza información existente")
        st.markdown("• Agrega nuevos registros")
        st.markdown("• Preserva datos históricos")
        st.markdown("• Sin pérdida de información")
    
    # Área principal
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("📁 Subir Archivos")
        
        has_existing_data = check_existing_data()
        if has_existing_data:
            st.info("🔄 **MODO ACTUALIZACIÓN**: Los archivos se agregarán a la base existente sin duplicar")
        else:
            st.info("🆕 **MODO INICIAL**: Se creará la base de datos")
        
        drapify_file = st.file_uploader(
            "1. 📊 Archivo Drapify (Base de datos) - PRINCIPAL",
            type=['xlsx', 'xls', 'csv'],
            key="drapify",
            help="🎯 ARCHIVO MADRE: Crea registros usando order_id. Este archivo establece la base de datos."
        )
        
        logistics_file = st.file_uploader(
            "2. 🚚 Archivo Logistics (opcional)",
            type=['xlsx', 'xls', 'csv'],
            key="logistics",
            help="📡 SE CONECTA VIA: Reference = order_id O Order number = order_id. Agrega información logística a registros existentes."
        )
        
        # Selector de fecha para Logistics
        if logistics_file:
            st.subheader("📅 Fecha para archivo Logistics")
            col_date1, col_date2, col_date3 = st.columns(3)
            
            with col_date1:
                if st.button("📅 Hoy"):
                    st.session_state.logistics_date = datetime.now().date()
            
            with col_date2:
                if st.button("📅 Ayer"):
                    st.session_state.logistics_date = (datetime.now() - timedelta(days=1)).date()
            
            with col_date3:
                selected_date = st.date_input(
                    "Fecha personalizada",
                    value=st.session_state.get('logistics_date', datetime.now().date())
                )
                st.session_state.logistics_date = selected_date
            
            st.info(f"📅 Fecha seleccionada: **{st.session_state.get('logistics_date', datetime.now().date())}**")
        
        aditionals_file = st.file_uploader(
            "3. ➕ Archivo Aditionals (opcional)",
            type=['xlsx', 'xls', 'csv'],
            key="aditionals",
            help="📡 SE CONECTA VIA: Order Id = prealert_id (NO order_id). Agrega información adicional."
        )
        
        cxp_file = st.file_uploader(
            "4. 💰 Archivo CXP (opcional)",
            type=['xlsx', 'xls', 'csv'],
            key="cxp",
            help="📡 SE CONECTA VIA: Ref # = asignacion (calculado). Agrega información de cuentas por pagar."
        )
    
    with col2:
        st.header("📊 Estado")
        
        files_status = {
            "Drapify": "✅" if drapify_file else "⚪",
            "Logistics": "✅" if logistics_file else "⚪",
            "Aditionals": "✅" if aditionals_file else "⚪",
            "CXP": "✅" if cxp_file else "⚪"
        }
        
        for file_type, status in files_status.items():
            st.write(f"{status} {file_type}")
        
        st.markdown("---")
        
        if any([drapify_file, logistics_file, aditionals_file, cxp_file]):
            st.success("✅ Archivos listos para procesar")
        else:
            st.info("📤 Sube al menos un archivo")
    
    # Botón de procesamiento
    if st.button("🚀 Procesar Archivos", disabled=not any([drapify_file, logistics_file, aditionals_file, cxp_file]), type="primary"):
        
        with st.spinner("Procesando archivos..."):
            try:
                # Determinar el modo de procesamiento
                if drapify_file:
                    # MODO 1: Consolidación completa con Drapify como base
                    st.info("📊 Modo: Consolidación completa con archivo base Drapify")
                    
                    # Leer archivo Drapify
                    if drapify_file.name.endswith('.csv'):
                        drapify_df = pd.read_csv(drapify_file)
                    else:
                        drapify_df = pd.read_excel(drapify_file)
                    st.success(f"✅ Drapify cargado: {len(drapify_df)} registros")
                    
                    # Log de actividad
                    if AUTH_AVAILABLE:
                        log_activity("upload_file", f"Archivo Drapify procesado", 
                                   "drapify", drapify_file.name, len(drapify_df))
                    
                    # Leer otros archivos si están disponibles
                    logistics_df = None
                    if logistics_file:
                        if logistics_file.name.endswith('.csv'):
                            logistics_df = pd.read_csv(logistics_file)
                        else:
                            logistics_df = pd.read_excel(logistics_file)
                        st.success(f"✅ Logistics cargado: {len(logistics_df)} registros")
                        
                        # Log de actividad
                        if AUTH_AVAILABLE:
                            log_activity("upload_file", f"Archivo Logistics procesado", 
                                       "logistics", logistics_file.name, len(logistics_df))
                    
                    aditionals_df = None
                    if aditionals_file:
                        if aditionals_file.name.endswith('.csv'):
                            aditionals_df = pd.read_csv(aditionals_file)
                        else:
                            aditionals_df = pd.read_excel(aditionals_file)
                        st.success(f"✅ Aditionals cargado: {len(aditionals_df)} registros")
                        
                        # Log de actividad
                        if AUTH_AVAILABLE:
                            log_activity("upload_file", f"Archivo Aditionals procesado", 
                                       "aditionals", aditionals_file.name, len(aditionals_df))
                    
                    cxp_df = None
                    if cxp_file:
                        if cxp_file.name.endswith('.csv'):
                            cxp_df = pd.read_csv(cxp_file)
                        else:
                            cxp_df = pd.read_excel(cxp_file)
                        st.success(f"✅ CXP cargado: {len(cxp_df)} registros")
                        
                        # Log de actividad
                        if AUTH_AVAILABLE:
                            log_activity("upload_file", f"Archivo CXP procesado", 
                                       "cxp", cxp_file.name, len(cxp_df))
                    
                    # Procesar consolidación completa
                    logistics_date = st.session_state.get('logistics_date') if logistics_file else None
                    consolidated_df = process_files_according_to_rules(
                        drapify_df, logistics_df, aditionals_df, cxp_df, logistics_date
                    )
                    
                    # Mostrar estadísticas detalladas
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("Total Registros", len(consolidated_df))
                    
                    with col2:
                        logistics_matched = 0
                        if any(col.startswith('logistics_') for col in consolidated_df.columns):
                            logistics_cols = [col for col in consolidated_df.columns if col.startswith('logistics_')]
                            if logistics_cols:
                                logistics_matched = consolidated_df[logistics_cols[0]].notna().sum()
                        st.metric("Logistics Matched", logistics_matched)
                    
                    with col3:
                        aditionals_matched = 0
                        if any(col.startswith('aditionals_') for col in consolidated_df.columns):
                            aditionals_cols = [col for col in consolidated_df.columns if col.startswith('aditionals_')]
                            if aditionals_cols:
                                aditionals_matched = consolidated_df[aditionals_cols[0]].notna().sum()
                        st.metric("Aditionals Matched", aditionals_matched)
                    
                    with col4:
                        cxp_matched = 0
                        if any(col.startswith('cxp_') for col in consolidated_df.columns):
                            cxp_cols = [col for col in consolidated_df.columns if col.startswith('cxp_')]
                            if cxp_cols:
                                cxp_matched = consolidated_df[cxp_cols[0]].notna().sum()
                        st.metric("CXP Matched", cxp_matched)
                    
                    # Guardar en base de datos
                    st.header("💾 Guardando en Base de Datos")
                    
                    with st.spinner("Procesando registros en Supabase..."):
                        filename = drapify_file.name
                        inserted_count, updated_count = insert_or_update_to_supabase(
                            consolidated_df, filename, logistics_matched, aditionals_matched, cxp_matched
                        )
                        
                        if inserted_count > 0 or updated_count > 0:
                            st.success(f"🎉 ¡Procesamiento completado!")
                            
                            # Resumen general
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.success(f"📊 {len(consolidated_df)} procesados")
                            with col2:
                                st.success(f"➕ {inserted_count} nuevos")
                            with col3:
                                st.success(f"🔄 {updated_count} actualizados")
                            
                            # Detalle por archivo
                            st.info("📋 **Detalle del procesamiento:**")
                            
                            if inserted_count > 0:
                                st.write(f"• **Drapify**: {inserted_count} registros nuevos agregados")
                            
                            if updated_count > 0:
                                update_details = []
                                
                                if logistics_file and logistics_matched > 0:
                                    update_details.append(f"• **Logistics**: {logistics_matched} registros actualizados")
                                
                                if aditionals_file and aditionals_matched > 0:
                                    update_details.append(f"• **Aditionals**: {aditionals_matched} registros actualizados")
                                
                                if cxp_file and cxp_matched > 0:
                                    update_details.append(f"• **CXP**: {cxp_matched} registros actualizados")
                                
                                if not update_details and updated_count > 0:
                                    update_details.append(f"• **Base de datos**: {updated_count} registros actualizados")
                                
                                for detail in update_details:
                                    st.write(detail)
                            
                            st.balloons()
                        else:
                            st.warning("⚠️ No se realizaron cambios en la base de datos")
                            st.info("Posibles razones: todos los registros ya existen con la misma información")
                
                else:
                    # MODO 2: Actualización parcial sin Drapify
                    st.info("🔄 Modo: Actualización parcial de columnas específicas")
                    
                    files_to_update = []
                    if logistics_file:
                        files_to_update.append(("Logistics", logistics_file))
                    if aditionals_file:
                        files_to_update.append(("Aditionals", aditionals_file))
                    if cxp_file:
                        files_to_update.append(("CXP", cxp_file))
                    
                    total_updated_all = 0
                    
                    for file_type, file_obj in files_to_update:
                        st.info(f"📝 Procesando archivo {file_type}...")
                        
                        # Leer archivo
                        if file_obj.name.endswith('.csv'):
                            df = pd.read_csv(file_obj)
                        else:
                            df = pd.read_excel(file_obj)
                        
                        st.success(f"✅ {file_type} cargado: {len(df)} registros")
                        
                        # Procesar según el tipo de archivo
                        updated = 0
                        if file_type == "Logistics":
                            updated = update_logistics_only(df, st.session_state.get('logistics_date'))
                            if updated > 0:
                                st.success(f"✅ **Logistics**: {updated:,} registros actualizados en la base de datos")
                            else:
                                st.warning(f"⚠️ **Logistics**: No se encontraron registros para actualizar")
                        elif file_type == "Aditionals":
                            updated = update_aditionals_only(df)
                            if updated > 0:
                                st.success(f"✅ **Aditionals**: {updated:,} registros actualizados en la base de datos")
                            else:
                                st.warning(f"⚠️ **Aditionals**: No se encontraron registros para actualizar")
                        elif file_type == "CXP":
                            updated = update_cxp_only(df)
                            if updated > 0:
                                st.success(f"✅ **CXP**: {updated:,} registros actualizados en la base de datos")
                            else:
                                st.warning(f"⚠️ **CXP**: No se encontraron registros para actualizar")
                        
                        total_updated_all += updated
                    
                    # Resumen final
                    st.markdown("---")
                    if total_updated_all > 0:
                        st.success(f"🎉 **¡Actualización completada!**")
                        st.info(f"📊 **Resumen total**: {total_updated_all:,} registros actualizados en total")
                        st.balloons()
                    else:
                        st.warning("⚠️ No se actualizaron registros")
                        st.info("Verifica que los IDs coincidan con registros existentes en la base de datos")
                
            except Exception as e:
                st.error(f"❌ Error procesando archivos: {str(e)}")
                st.exception(e)
    
    # Sección de consultas
    st.markdown("---")
    st.header("🔍 Consultar Datos Existentes")
    
    query_col1, query_col2 = st.columns(2)
    
    with query_col1:
        if st.button("📊 Ver Estadísticas Generales", type="primary"):
            try:
                result = supabase.table('consolidated_orders').select('account_name').execute()
                
                if result.data:
                    df = pd.DataFrame(result.data)
                    if 'account_name' in df.columns:
                        st.subheader("Registros por Account Name")
                        account_counts = df['account_name'].value_counts()
                        st.bar_chart(account_counts)
                        st.dataframe(account_counts.reset_index())
                else:
                    st.info("No hay datos en la base de datos")
                    
            except Exception as e:
                st.error(f"Error consultando estadísticas: {str(e)}")
    
    with query_col2:
        if st.button("📋 Ver Últimos Registros", type="primary"):
            try:
                result = supabase.table('consolidated_orders').select('*').order('id', desc=True).limit(10).execute()
                
                if result.data:
                    recent_df = pd.DataFrame(result.data)
                    st.subheader("Últimos 10 Registros")
                    st.dataframe(recent_df, use_container_width=True)
                else:
                    st.info("No hay datos en la base de datos")
                    
            except Exception as e:
                st.error(f"Error consultando registros: {str(e)}")
    
    # Búsqueda específica
    st.subheader("🔎 Búsqueda Específica")
    
    # Botones de búsqueda rápida
    quick_col1, quick_col2, quick_col3, quick_col4 = st.columns(4)
    
    with quick_col1:
        if st.button("📊 Últimos 20", type="primary"):
            try:
                result = supabase.table('consolidated_orders').select('*').order('id', desc=True).limit(20).execute()
                if result.data:
                    quick_df = pd.DataFrame(result.data)
                    st.success(f"✅ Últimos {len(quick_df)} registros")
                    st.dataframe(quick_df[['id', 'order_id', 'account_name', 'client_first_name', 'title', 'date_created']], use_container_width=True)
                else:
                    st.warning("No hay registros en la base de datos")
            except Exception as e:
                st.error(f"Error: {str(e)}")
    
    with quick_col2:
        if st.button("🔍 Con Logistics", type="primary"):
            try:
                result = supabase.table('consolidated_orders').select('*').not_.is_('logistics_reference', 'null').limit(20).execute()
                if result.data:
                    quick_df = pd.DataFrame(result.data)
                    st.success(f"✅ {len(quick_df)} registros con Logistics")
                    st.dataframe(quick_df[['id', 'order_id', 'logistics_reference', 'logistics_total']], use_container_width=True)
                else:
                    st.warning("No hay registros con datos de Logistics")
            except Exception as e:
                st.error(f"Error: {str(e)}")
    
    with quick_col3:
        if st.button("💰 Con CXP", type="primary"):
            try:
                result = supabase.table('consolidated_orders').select('*').not_.is_('cxp_amt_due', 'null').limit(20).execute()
                if result.data:
                    quick_df = pd.DataFrame(result.data)
                    st.success(f"✅ {len(quick_df)} registros con CXP")
                    st.dataframe(quick_df[['id', 'order_id', 'asignacion', 'cxp_amt_due', 'cxp_ref_number']], use_container_width=True)
                else:
                    st.warning("No hay registros con datos de CXP")
            except Exception as e:
                st.error(f"Error: {str(e)}")
    
    with quick_col4:
        if st.button("🔢 Contar Todo", type="primary"):
            try:
                # Conteo total
                total_result = supabase.table('consolidated_orders').select('id', count='exact').execute()
                total_count = total_result.count if total_result.count else 0
                
                # Conteos específicos
                logistics_result = supabase.table('consolidated_orders').select('id', count='exact').not_.is_('logistics_reference', 'null').execute()
                logistics_count = logistics_result.count if logistics_result.count else 0
                
                cxp_result = supabase.table('consolidated_orders').select('id', count='exact').not_.is_('cxp_amt_due', 'null').execute()
                cxp_count = cxp_result.count if cxp_result.count else 0
                
                st.success("📊 Estadísticas de la Base de Datos")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Registros", f"{total_count:,}")
                with col2:
                    st.metric("Con Logistics", f"{logistics_count:,}")
                with col3:
                    st.metric("Con CXP", f"{cxp_count:,}")
                    
            except Exception as e:
                st.error(f"Error: {str(e)}")
    
    st.markdown("---")
    
    # Mostrar ejemplos de uso
    with st.expander("💡 Ejemplos de búsqueda múltiple", expanded=False):
        st.markdown("""
        **Búsqueda simple:**
        - Order ID: `123456`
        - Prealert ID: `abc123`
        
        **Búsqueda múltiple (separados por comas):**
        - Order IDs: `123456, 789012, 345678`
        - Prealert IDs: `abc123, def456, ghi789`
        
        **Consejos:**
        - ✅ Usa comas para separar múltiples IDs
        - ✅ Los espacios se limpian automáticamente
        - ✅ Puedes combinar con filtro de Account
        - ⚠️ Máximo 200 resultados por búsqueda
        """)
    
    search_col1, search_col2, search_col3 = st.columns(3)
    
    with search_col1:
        search_order_id = st.text_input("Buscar por Order ID", 
                                       placeholder="123456 o 123,456,789",
                                       help="Un solo ID o múltiples separados por comas")
    
    with search_col2:
        search_prealert_id = st.text_input("Buscar por Prealert ID", 
                                          placeholder="abc123 o abc,def,ghi",
                                          help="Un solo ID o múltiples separados por comas")
    
    with search_col3:
        search_account = st.selectbox(
            "Filtrar por Account",
            ["Todos", "1-TODOENCARGO-CO", "2-MEGATIENDA SPA", "3-VEENDELO", 
             "4-MEGA TIENDAS PERUANAS", "5-DETODOPARATODOS", "6-COMPRAFACIL", 
             "7-COMPRA-YA", "8-FABORCARGO"]
        )
    
    if st.button("🔍 Buscar", type="primary"):
        try:
            # Preparar listas de IDs
            order_ids = []
            prealert_ids = []
            
            # Procesar Order IDs (múltiples separados por coma)
            if search_order_id.strip():
                order_ids = [id.strip() for id in search_order_id.split(',') if id.strip()]
            
            # Procesar Prealert IDs (múltiples separados por coma)
            if search_prealert_id.strip():
                prealert_ids = [id.strip() for id in search_prealert_id.split(',') if id.strip()]
            
            # Si no hay filtros, mostrar últimos 50 registros
            if not order_ids and not prealert_ids and search_account == "Todos":
                st.info("Mostrando últimos 50 registros (sin filtros específicos)")
                result = supabase.table('consolidated_orders').select('*').order('id', desc=True).limit(50).execute()
            else:
                # Usar búsqueda con filtros
                base_query = supabase.table('consolidated_orders').select('*')
                
                # Aplicar filtros de order_ids si existen
                if order_ids:
                    if len(order_ids) == 1:
                        base_query = base_query.eq('order_id', order_ids[0])
                        st.info(f"🔍 Buscando Order ID: {order_ids[0]}")
                    else:
                        base_query = base_query.in_('order_id', order_ids)
                        st.info(f"🔍 Buscando {len(order_ids)} Order IDs: {', '.join(order_ids[:5])}{'...' if len(order_ids) > 5 else ''}")
                
                # Aplicar filtros de prealert_ids si existen
                if prealert_ids:
                    if len(prealert_ids) == 1:
                        prealert_search = prealert_ids[0]
                        try:
                            # Si es un número, probar ambos formatos (.0 y sin .0)
                            float(prealert_search)
                            format1 = prealert_search
                            format2 = f"{prealert_search}.0" if '.' not in prealert_search else prealert_search.replace('.0', '')
                            # Buscar en ambos formatos usando in_
                            base_query = base_query.in_('prealert_id', [format1, format2])
                            st.info(f"🔍 Buscando Prealert ID: {prealert_search} (probando: '{format1}' y '{format2}')")
                        except ValueError:
                            # Si no es número, buscar tal como está
                            base_query = base_query.eq('prealert_id', prealert_search)
                            st.info(f"🔍 Buscando Prealert ID: {prealert_search} (formato texto)")
                    else:
                        # Para múltiples IDs, expandir cada uno a sus posibles formatos
                        expanded_prealert_ids = []
                        for pid in prealert_ids:
                            expanded_prealert_ids.append(pid)
                            try:
                                float(pid)
                                if '.' not in pid:
                                    expanded_prealert_ids.append(f"{pid}.0")
                                else:
                                    expanded_prealert_ids.append(pid.replace('.0', ''))
                            except ValueError:
                                pass
                        base_query = base_query.in_('prealert_id', expanded_prealert_ids)
                        st.info(f"🔍 Buscando {len(prealert_ids)} Prealert IDs: {', '.join(prealert_ids[:5])}{'...' if len(prealert_ids) > 5 else ''}")
                
                # Aplicar filtro de account si está seleccionado
                if search_account != "Todos":
                    base_query = base_query.eq('account_name', search_account)
                    st.info(f"🏢 Filtrando por cuenta: {search_account}")
                
                result = base_query.limit(200).execute()  # Aumentar límite para búsquedas múltiples
            
            if result.data:
                search_df = pd.DataFrame(result.data)
                st.success(f"✅ Encontrados {len(search_df)} registros")
                
                # Mostrar columnas más importantes primero
                important_cols = ['id', 'order_id', 'prealert_id', 'account_name', 'client_first_name', 
                                'client_last_name', 'title', 'quantity', 'unit_price', 'date_created']
                
                # Reordenar columnas para mostrar las importantes primero
                available_important_cols = [col for col in important_cols if col in search_df.columns]
                other_cols = [col for col in search_df.columns if col not in important_cols]
                ordered_cols = available_important_cols + other_cols
                
                search_df_ordered = search_df[ordered_cols]
                
                st.dataframe(search_df_ordered, use_container_width=True)
                
                # Mostrar estadísticas rápidas
                if len(search_df) > 0:
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("Total Registros", len(search_df))
                    
                    with col2:
                        if 'account_name' in search_df.columns:
                            unique_accounts = search_df['account_name'].nunique()
                            st.metric("Cuentas Únicas", unique_accounts)
                    
                    with col3:
                        if 'unit_price' in search_df.columns:
                            total_value = search_df['unit_price'].sum()
                            st.metric("Valor Total", f"${total_value:,.2f}" if pd.notna(total_value) else "N/A")
                
            else:
                st.warning("No se encontraron registros con los criterios especificados")
                st.info("💡 Intenta:")
                st.write("• Verificar que los IDs existen en la base de datos")
                st.write("• Para múltiples IDs usa comas: 123,456,789")
                st.write("• Revisar que no hay espacios extra")
                st.write("• Usar el botón '📊 Últimos 20' para ver registros recientes")
                
        except Exception as e:
            st.error(f"Error en la búsqueda: {str(e)}")
            st.exception(e)

if __name__ == "__main__":
    main()
