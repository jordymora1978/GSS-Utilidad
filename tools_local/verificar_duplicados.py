"""
Script para verificar duplicados antes de subir archivos al Consolidador
Verifica si los registros ya existen en la base de datos y genera archivo limpio
"""

import streamlit as st
import pandas as pd
from supabase import create_client
import config
from datetime import datetime
import io
import numpy as np

def main():
    st.set_page_config(page_title="Verificador de Duplicados", layout="wide", page_icon="🔍")
    st.title("🔍 Verificador de Duplicados - Pre-Consolidador")
    
    # Conectar a Supabase
    @st.cache_resource
    def init_supabase():
        return create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
    
    supabase = init_supabase()
    
    # Información
    st.info("""
    **🎯 Objetivo:** Verificar si los registros ya existen en la base de datos antes de subirlos al Consolidador.
    
    **📋 Proceso:**
    1. Sube tu archivo (Logistics, Aditionals o CXP)
    2. El sistema verificará qué registros ya existen
    3. Descarga un archivo limpio solo con registros nuevos
    4. Usa ese archivo limpio en el Consolidador
    """)
    
    # Seleccionar tipo de archivo
    col1, col2 = st.columns([1, 2])
    
    with col1:
        tipo_archivo = st.selectbox(
            "📁 Tipo de archivo",
            ["Logistics", "Aditionals", "CXP"],
            help="Selecciona el tipo de archivo que vas a verificar"
        )
    
    with col2:
        st.info(f"""
        **Verificación para {tipo_archivo}:**
        - **Logistics:** Si columnas logistics_* están llenas
        - **Aditionals:** Si columnas aditionals_* están llenas  
        - **CXP:** Si columnas cxp_* están llenas
        
        **Solo incluye registros que necesitan completar datos**
        """)
    
    # Subir archivo
    uploaded_file = st.file_uploader(
        f"Selecciona el archivo {tipo_archivo} para verificar",
        type=['xlsx', 'xls', 'csv'],
        help="El archivo debe tener el mismo formato que usas en el Consolidador"
    )
    
    if uploaded_file:
        try:
            # Leer archivo
            if uploaded_file.name.endswith('.csv'):
                df_original = pd.read_csv(uploaded_file)
            else:
                df_original = pd.read_excel(uploaded_file)
            
            st.success(f"✅ Archivo cargado: {len(df_original)} registros")
            
            # Mostrar preview
            with st.expander("👁️ Ver primeros registros del archivo"):
                st.dataframe(df_original.head(20))
            
            # Botón de verificación
            if st.button("🔍 Verificar Duplicados", type="primary"):
                
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
                        st.info("🚚 Verificando archivo Logistics...")
                        
                        # Verificar columnas disponibles
                        columnas_verificadas = []
                        if 'Reference' in df_original.columns:
                            columnas_verificadas.append('Reference')
                        if 'Order number' in df_original.columns:
                            columnas_verificadas.append('Order number')
                        
                        if not columnas_verificadas:
                            st.error("❌ No se encontraron columnas 'Reference' o 'Order number'")
                            st.stop()
                        
                        # Obtener IDs únicos del archivo
                        ids_archivo = set()
                        for col in columnas_verificadas:
                            ids_limpios = df_original[col].apply(clean_id).dropna()
                            ids_archivo.update(ids_limpios)
                        
                        # Consultar base de datos con campos logistics
                        registros_bd = {}
                        
                        # Buscar por order_id con campos logistics
                        for batch_ids in [list(ids_archivo)[i:i+50] for i in range(0, len(ids_archivo), 50)]:
                            try:
                                result = supabase.table('consolidated_orders').select(
                                    'order_id, prealert_id, logistics_total, logistics_reference, logistics_guide_number'
                                ).in_('order_id', batch_ids).execute()
                                for record in result.data:
                                    registros_bd[record['order_id']] = record
                            except Exception as e:
                                st.warning(f"Error consultando por order_id: {str(e)}")
                        
                        # Buscar por prealert_id con campos logistics
                        for batch_ids in [list(ids_archivo)[i:i+50] for i in range(0, len(ids_archivo), 50)]:
                            try:
                                result = supabase.table('consolidated_orders').select(
                                    'order_id, prealert_id, logistics_total, logistics_reference, logistics_guide_number'
                                ).in_('prealert_id', batch_ids).execute()
                                for record in result.data:
                                    if record['prealert_id']:
                                        registros_bd[record['prealert_id']] = record
                            except Exception as e:
                                st.warning(f"Error consultando por prealert_id: {str(e)}")
                        
                        # Clasificar registros
                        for idx, row in df_original.iterrows():
                            id_encontrado = None
                            record_bd = None
                            
                            # Buscar el ID en los registros de BD
                            for col in columnas_verificadas:
                                id_limpio = clean_id(row.get(col))
                                if id_limpio and id_limpio in registros_bd:
                                    id_encontrado = id_limpio
                                    record_bd = registros_bd[id_limpio]
                                    break
                            
                            if record_bd:
                                # Verificar si los campos logistics están llenos
                                campos_llenos = bool(
                                    record_bd.get('logistics_total') and 
                                    record_bd.get('logistics_reference') and
                                    record_bd.get('logistics_guide_number')
                                )
                                
                                if campos_llenos:
                                    registros_completos.append(idx)
                                else:
                                    registros_necesarios.append(idx)
                            else:
                                # No existe en BD, se necesita procesar
                                registros_necesarios.append(idx)
                    
                    elif tipo_archivo == "Aditionals":
                        st.info("➕ Verificando archivo Aditionals...")
                        
                        if 'Order Id' not in df_original.columns:
                            st.error("❌ No se encontró columna 'Order Id'")
                            st.stop()
                        
                        # Obtener IDs únicos
                        ids_archivo = set(df_original['Order Id'].apply(clean_id).dropna())
                        
                        # Consultar base de datos con campos aditionals
                        registros_bd = {}
                        for batch_ids in [list(ids_archivo)[i:i+50] for i in range(0, len(ids_archivo), 50)]:
                            try:
                                result = supabase.table('consolidated_orders').select(
                                    'prealert_id, aditionals_total, aditionals_quantity, aditionals_item'
                                ).in_('prealert_id', batch_ids).execute()
                                for record in result.data:
                                    if record['prealert_id']:
                                        # Normalizar el ID de la BD también
                                        id_normalizado = normalize_id_for_comparison(record['prealert_id'])
                                        if id_normalizado:
                                            registros_bd[id_normalizado] = record
                            except Exception as e:
                                st.warning(f"Error consultando aditionals: {str(e)}")
                        
                        st.caption(f"🔍 Debug: Se encontraron {len(registros_bd)} registros en BD")
                        
                        # Clasificar registros
                        for idx, row in df_original.iterrows():
                            id_limpio = normalize_id_for_comparison(row.get('Order Id'))
                            
                            if id_limpio and id_limpio in registros_bd:
                                record_bd = registros_bd[id_limpio]
                                
                                # Verificar si los campos aditionals están llenos
                                total_ok = record_bd.get('aditionals_total') is not None and record_bd.get('aditionals_total') != 0
                                quantity_ok = record_bd.get('aditionals_quantity') is not None and record_bd.get('aditionals_quantity') != 0  
                                item_ok = record_bd.get('aditionals_item') is not None and record_bd.get('aditionals_item') != ''
                                
                                campos_llenos = total_ok and quantity_ok and item_ok
                                
                                if campos_llenos:
                                    registros_completos.append(idx)
                                else:
                                    registros_necesarios.append(idx)
                            else:
                                # No existe en BD, se necesita procesar
                                registros_necesarios.append(idx)
                    
                    elif tipo_archivo == "CXP":
                        st.info("💰 Verificando archivo CXP...")
                        
                        # Buscar columna Ref # (puede tener variaciones)
                        ref_column = None
                        for col in df_original.columns:
                            if 'Ref' in col or 'ref' in col or 'REF' in col:
                                ref_column = col
                                break
                        
                        if not ref_column:
                            st.error("❌ No se encontró columna de referencia (Ref #)")
                            st.stop()
                        
                        st.caption(f"Usando columna: {ref_column}")
                        
                        # Obtener IDs únicos
                        ids_archivo = set(df_original[ref_column].apply(clean_id).dropna())
                        
                        # Consultar base de datos con campos CXP
                        registros_bd = {}
                        for batch_ids in [list(ids_archivo)[i:i+50] for i in range(0, len(ids_archivo), 50)]:
                            try:
                                result = supabase.table('consolidated_orders').select(
                                    'asignacion, cxp_amt_due, cxp_arancel, cxp_iva'
                                ).in_('asignacion', batch_ids).execute()
                                for record in result.data:
                                    if record['asignacion']:
                                        registros_bd[record['asignacion']] = record
                            except Exception as e:
                                st.warning(f"Error consultando CXP: {str(e)}")
                        
                        # Clasificar registros
                        for idx, row in df_original.iterrows():
                            id_limpio = clean_id(row.get(ref_column))
                            
                            if id_limpio and id_limpio in registros_bd:
                                record_bd = registros_bd[id_limpio]
                                
                                # Verificar si los campos CXP están llenos
                                campos_llenos = bool(
                                    record_bd.get('cxp_amt_due') and 
                                    record_bd.get('cxp_arancel') and
                                    record_bd.get('cxp_iva')
                                )
                                
                                if campos_llenos:
                                    registros_completos.append(idx)
                                else:
                                    registros_necesarios.append(idx)
                            else:
                                # No existe en BD, se necesita procesar
                                registros_necesarios.append(idx)
                    
                    # Mostrar resultados
                    st.markdown("---")
                    st.subheader("📊 Resultados de la Verificación")
                    
                    col1, col2, col3 = st.columns(3)
                    
                    total = len(df_original)
                    completos = len(registros_completos)
                    necesarios = len(registros_necesarios)
                    
                    col1.metric("📁 Total en archivo", total)
                    col2.metric("✅ Datos completos", completos, delta=f"-{completos}")
                    col3.metric("📝 Necesitan datos", necesarios, delta=f"+{necesarios}")
                    
                    # Mostrar porcentajes
                    if total > 0:
                        porcentaje_completos = (completos / total) * 100
                        porcentaje_necesarios = (necesarios / total) * 100
                        
                        st.info(f"""
                        📈 **Estadísticas:**
                        - {porcentaje_completos:.1f}% ya tienen datos completos en BD
                        - {porcentaje_necesarios:.1f}% necesitan completar datos
                        """)
                    
                    # Generar archivo con registros que necesitan datos
                    if necesarios > 0:
                        st.success(f"✅ Se encontraron {necesarios} registros que necesitan completar datos")
                        
                        # Crear DataFrame con solo registros necesarios
                        df_necesarios = df_original.iloc[registros_necesarios].copy()
                        
                        # Mostrar preview
                        with st.expander(f"👁️ Ver los {min(necesarios, 20)} primeros registros que necesitan datos"):
                            st.dataframe(df_necesarios.head(20))
                        
                        # Generar archivo para descargar
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        nombre_archivo = f"{tipo_archivo}_NECESARIOS_{timestamp}.xlsx"
                        
                        # Crear Excel
                        buffer = io.BytesIO()
                        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                            df_necesarios.to_excel(writer, index=False, sheet_name=tipo_archivo)
                        
                        st.download_button(
                            label=f"📥 Descargar archivo con {necesarios} registros necesarios",
                            data=buffer.getvalue(),
                            file_name=nombre_archivo,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            type="primary"
                        )
                        
                        st.success(f"""
                        ✅ **Próximos pasos:**
                        1. Descarga el archivo con los {necesarios} registros que necesitan datos
                        2. Ve al Consolidador
                        3. Sube este archivo para completar los datos faltantes
                        4. ¡Los registros se actualizarán con la información completa!
                        """)
                    else:
                        st.warning("🎉 ¡Excelente! Todos los registros del archivo ya tienen datos completos en la base de datos.")
                    
                    # Mostrar registros completos si el usuario quiere verlos
                    if completos > 0:
                        with st.expander(f"📋 Ver los {min(completos, 20)} primeros registros con datos COMPLETOS"):
                            df_completos = df_original.iloc[registros_completos].copy()
                            st.dataframe(df_completos.head(20))
                            st.caption("Estos registros ya tienen todos los datos necesarios y no requieren actualización.")
                            
                            # Opción de descargar completos también
                            buffer2 = io.BytesIO()
                            with pd.ExcelWriter(buffer2, engine='openpyxl') as writer:
                                df_completos.to_excel(writer, index=False, sheet_name=f"{tipo_archivo}_Completos")
                            
                            st.download_button(
                                label=f"📥 Descargar {completos} registros completos (referencia)",
                                data=buffer2.getvalue(),
                                file_name=f"{tipo_archivo}_COMPLETOS_{timestamp}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                    
        except Exception as e:
            st.error(f"❌ Error procesando archivo: {str(e)}")
            st.exception(e)
    
    # Instrucciones adicionales
    with st.expander("📚 Ayuda y formato de archivos"):
        st.markdown("""
        ### 📁 Formatos esperados:
        
        **Logistics:**
        - Debe tener columna `Reference` o `Order number`
        - Verifica si `logistics_total`, `logistics_reference` y `logistics_guide_number` están llenos
        
        **Aditionals:**
        - Debe tener columna `Order Id`
        - Verifica si `aditionals_total`, `aditionals_quantity` y `aditionals_item` están llenos
        
        **CXP (Chilexpress):**
        - Debe tener columna `Ref #` o similar
        - Verifica si `cxp_amt_due`, `cxp_arancel` y `cxp_iva` están llenos
        
        ### 🎯 Beneficios:
        - ✅ Solo procesa registros que necesitan completar datos
        - ✅ Evita sobrescribir información ya completa
        - ✅ Ahorra tiempo mostrando qué necesita actualización
        - ✅ Mantiene la integridad de los datos existentes
        - ✅ Workflow más eficiente
        
        ### 💡 Tips:
        - **"Datos completos"** = los campos específicos ya tienen valores
        - **"Necesitan datos"** = campos vacíos o nulos, requieren procesamiento
        - Registros nuevos (no existen en BD) siempre se incluyen
        - Si todos están completos, no necesitas hacer nada
        """)

if __name__ == "__main__":
    main()