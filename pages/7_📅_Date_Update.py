"""
📅 Actualizar Logistics Date - Tool
Script para actualizar logistics_date desde Excel
Hace match por prealert_id o order_id según disponibilidad
"""

import pandas as pd
import streamlit as st
from supabase import create_client
import sys
import os
from datetime import datetime

# Path configuration
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, parent_dir)

import config

def main():
    st.set_page_config(page_title="Actualizar Logistics Date", layout="wide")
    st.title("📅 Actualizar Logistics Date desde Excel")
    
    # Conectar a Supabase
    @st.cache_resource
    def init_supabase():
        return create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
    
    supabase = init_supabase()
    
    st.info("""
    📋 **Instrucciones:**
    1. El archivo Excel debe tener 3 columnas: `order_id`, `prealert_id`, `logistics_date`
    2. El script intentará hacer match primero por `prealert_id`, luego por `order_id`
    3. Solo actualizará registros que tengan match en la base de datos
    """)
    
    # Subir archivo
    uploaded_file = st.file_uploader(
        "Selecciona el archivo Excel con las fechas a actualizar",
        type=['xlsx', 'xls', 'csv']
    )
    
    if uploaded_file:
        try:
            # Leer archivo
            if uploaded_file.name.endswith('.csv'):
                df_excel = pd.read_csv(uploaded_file)
            else:
                df_excel = pd.read_excel(uploaded_file)
            
            st.success(f"✅ Archivo cargado: {len(df_excel)} filas")
            
            # Mostrar preview
            st.subheader("Vista previa del archivo:")
            st.dataframe(df_excel.head(10))
            
            # Verificar columnas requeridas
            columnas_requeridas = ['order_id', 'prealert_id', 'logistics_date']
            columnas_faltantes = [col for col in columnas_requeridas if col not in df_excel.columns]
            
            if columnas_faltantes:
                st.error(f"❌ Faltan las columnas: {', '.join(columnas_faltantes)}")
                st.stop()
            
            # Mostrar análisis inicial
            st.subheader("📊 Análisis del archivo")
            col1, col2, col3 = st.columns(3)
            
            # Limpiar y preparar datos
            df_excel['order_id'] = df_excel['order_id'].astype(str).str.strip()
            df_excel['prealert_id'] = df_excel['prealert_id'].astype(str).str.strip()
            
            # Estadísticas antes de limpiar
            total_original = len(df_excel)
            col1.metric("Total filas originales", total_original)
            
            # Convertir fecha a formato correcto
            # Primero intentar limpiar el formato a.m./p.m. con espacios
            if 'logistics_date' in df_excel.columns:
                # Reemplazar formato español de AM/PM
                df_excel['logistics_date'] = df_excel['logistics_date'].astype(str).str.replace('a. m.', 'AM', regex=False)
                df_excel['logistics_date'] = df_excel['logistics_date'].astype(str).str.replace('p. m.', 'PM', regex=False)
                df_excel['logistics_date'] = df_excel['logistics_date'].astype(str).str.replace('a.m.', 'AM', regex=False)
                df_excel['logistics_date'] = df_excel['logistics_date'].astype(str).str.replace('p.m.', 'PM', regex=False)
            
            # Ahora convertir a datetime - intentar varios formatos
            df_excel['logistics_date'] = pd.to_datetime(
                df_excel['logistics_date'], 
                format='%d/%m/%Y %I:%M:%S %p',  # Formato día/mes/año hora:min:seg AM/PM
                errors='coerce'
            )
            
            # Si todavía hay valores NaT, intentar otros formatos
            mask_nat = df_excel['logistics_date'].isna()
            if mask_nat.any():
                df_excel.loc[mask_nat, 'logistics_date'] = pd.to_datetime(
                    df_excel.loc[mask_nat, 'logistics_date'], 
                    errors='coerce',
                    dayfirst=True  # Asume día primero (formato europeo/latino)
                )
            
            # Contar registros con fecha inválida
            fechas_invalidas = df_excel['logistics_date'].isna().sum()
            col2.metric("Fechas inválidas", fechas_invalidas)
            
            # Guardar registros con fecha inválida para mostrar después
            df_fechas_invalidas = df_excel[df_excel['logistics_date'].isna()].copy()
            
            # Convertir fechas válidas a string
            df_excel.loc[df_excel['logistics_date'].notna(), 'logistics_date'] = df_excel.loc[df_excel['logistics_date'].notna(), 'logistics_date'].dt.strftime('%Y-%m-%d')
            
            # Eliminar filas sin fecha válida
            df_excel_valido = df_excel[df_excel['logistics_date'].notna()].copy()
            
            col3.metric("Registros a procesar", len(df_excel_valido))
            
            # Mostrar registros con fecha inválida si hay
            if len(df_fechas_invalidas) > 0:
                with st.expander(f"⚠️ Ver {len(df_fechas_invalidas)} registros con fecha inválida"):
                    st.dataframe(df_fechas_invalidas)
                    st.caption("Estos registros NO serán procesados porque tienen fecha inválida")
            
            # Usar df_excel_valido para el resto del proceso
            df_excel = df_excel_valido
            
            st.info(f"📊 Se procesarán {len(df_excel)} registros con fecha válida de {total_original} totales")
            
            # Opciones de procesamiento
            col1, col2 = st.columns(2)
            with col1:
                modo_test = st.checkbox("🧪 Modo TEST (no actualiza, solo muestra)", value=True)
            with col2:
                batch_size = st.number_input("Tamaño del lote", min_value=10, max_value=500, value=50)
            
            if st.button("🚀 Procesar Actualización", type="primary"):
                
                # Contadores
                actualizados_por_prealert = 0
                actualizados_por_order = 0
                no_encontrados = []
                errores = []
                log_detalle = []  # Log detallado de cada registro
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                total_filas = len(df_excel)
                
                st.info(f"🔄 Procesando {total_filas} registros...")
                
                # OPTIMIZACIÓN: Procesar por lotes grandes en lugar de uno por uno
                
                # Preparar datos limpios
                registros_a_procesar = []
                for idx, row in df_excel.iterrows():
                    order_id = str(row['order_id']) if pd.notna(row['order_id']) else None
                    prealert_id = str(row['prealert_id']) if pd.notna(row['prealert_id']) else None
                    logistics_date = str(row['logistics_date']) if pd.notna(row['logistics_date']) else None
                    
                    # Limpiar valores
                    if order_id == 'nan' or order_id == '':
                        order_id = None
                    if prealert_id == 'nan' or prealert_id == '':
                        prealert_id = None
                    
                    if order_id or prealert_id:  # Solo si tiene algún ID válido
                        registros_a_procesar.append({
                            'fila': idx + 1,
                            'order_id': order_id,
                            'prealert_id': prealert_id,
                            'logistics_date': logistics_date
                        })
                
                st.info(f"🚀 Procesamiento optimizado: {len(registros_a_procesar)} registros en lotes de {batch_size}")
                
                # Procesar en lotes de tamaño configurable
                total_registros = len(registros_a_procesar)
                lotes = [registros_a_procesar[i:i + batch_size] for i in range(0, total_registros, batch_size)]
                
                for lote_idx, lote in enumerate(lotes):
                    try:
                        # Extraer todos los IDs del lote
                        prealert_ids = [r['prealert_id'] for r in lote if r['prealert_id']]
                        order_ids = [r['order_id'] for r in lote if r['order_id']]
                        
                        # Consultar registros existentes en una sola query por lote
                        registros_existentes = {}
                        
                        # Buscar por prealert_id si hay
                        if prealert_ids:
                            if modo_test:
                                result = supabase.table('consolidated_orders').select('id, prealert_id').in_('prealert_id', prealert_ids).execute()
                            else:
                                result = supabase.table('consolidated_orders').select('id, prealert_id').in_('prealert_id', prealert_ids).execute()
                            
                            for record in result.data:
                                registros_existentes[f"prealert_{record['prealert_id']}"] = record['id']
                        
                        # Buscar por order_id si hay (solo para los que no se encontraron por prealert)
                        if order_ids:
                            if modo_test:
                                result = supabase.table('consolidated_orders').select('id, order_id').in_('order_id', order_ids).execute()
                            else:
                                result = supabase.table('consolidated_orders').select('id, order_id').in_('order_id', order_ids).execute()
                            
                            for record in result.data:
                                registros_existentes[f"order_{record['order_id']}"] = record['id']
                        
                        # Procesar cada registro del lote
                        for registro in lote:
                            actualizado = False
                            metodo = 'N/A'
                            
                            # Buscar si existe por prealert_id primero
                            if registro['prealert_id']:
                                key = f"prealert_{registro['prealert_id']}"
                                if key in registros_existentes:
                                    if not modo_test:
                                        # Actualizar individualmente (más rápido que antes porque ya tenemos los IDs)
                                        supabase.table('consolidated_orders').update({
                                            'logistics_date': registro['logistics_date']
                                        }).eq('prealert_id', registro['prealert_id']).execute()
                                    
                                    actualizados_por_prealert += 1
                                    actualizado = True
                                    metodo = 'Prealert ID'
                            
                            # Si no se encontró por prealert, buscar por order_id
                            if not actualizado and registro['order_id']:
                                key = f"order_{registro['order_id']}"
                                if key in registros_existentes:
                                    if not modo_test:
                                        supabase.table('consolidated_orders').update({
                                            'logistics_date': registro['logistics_date']
                                        }).eq('order_id', registro['order_id']).execute()
                                    
                                    actualizados_por_order += 1
                                    actualizado = True
                                    metodo = 'Order ID'
                            
                            # Agregar al log
                            if actualizado:
                                log_detalle.append({
                                    'fila': registro['fila'],
                                    'order_id': registro['order_id'],
                                    'prealert_id': registro['prealert_id'],
                                    'resultado': '✅ Actualizado' if not modo_test else '✅ Encontrado (TEST)',
                                    'metodo': metodo
                                })
                            else:
                                no_encontrados.append({
                                    'order_id': registro['order_id'],
                                    'prealert_id': registro['prealert_id'],
                                    'logistics_date': registro['logistics_date']
                                })
                                log_detalle.append({
                                    'fila': registro['fila'],
                                    'order_id': registro['order_id'],
                                    'prealert_id': registro['prealert_id'],
                                    'resultado': '❌ No encontrado',
                                    'metodo': 'N/A'
                                })
                        
                        # Actualizar progreso por lote
                        progress = (lote_idx + 1) / len(lotes)
                        progress_bar.progress(progress)
                        status_text.text(f"Lote {lote_idx + 1}/{len(lotes)} | Prealert: {actualizados_por_prealert} | Order: {actualizados_por_order} | No encontrados: {len(no_encontrados)}")
                        
                    except Exception as e:
                        # Agregar error para todo el lote
                        for registro in lote:
                            errores.append({
                                'order_id': registro['order_id'],
                                'prealert_id': registro['prealert_id'],
                                'error': str(e)
                            })
                            log_detalle.append({
                                'fila': registro['fila'],
                                'order_id': registro['order_id'],
                                'prealert_id': registro['prealert_id'],
                                'resultado': f'❌ Error: {str(e)}',
                                'metodo': 'N/A'
                            })
                
                # Mostrar resultados
                st.markdown("---")
                st.subheader("📊 Resultados del Proceso")
                
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("✅ Por Prealert ID", actualizados_por_prealert)
                col2.metric("✅ Por Order ID", actualizados_por_order)
                col3.metric("⚠️ No encontrados", len(no_encontrados))
                col4.metric("❌ Errores", len(errores))
                
                if modo_test:
                    st.warning("⚠️ MODO TEST: No se realizaron actualizaciones reales en la base de datos")
                else:
                    st.success(f"✅ Actualización completada: {actualizados_por_prealert + actualizados_por_order} registros actualizados")
                
                # Mostrar log detallado
                with st.expander("📋 Ver detalle de cada registro procesado"):
                    df_log = pd.DataFrame(log_detalle)
                    st.dataframe(df_log, use_container_width=True)
                    
                    # Resumen del log
                    st.caption(f"""
                    **Resumen del procesamiento:**
                    - Total procesados: {len(log_detalle)}
                    - Actualizados por Prealert ID: {actualizados_por_prealert}
                    - Actualizados por Order ID: {actualizados_por_order}
                    - No encontrados: {len(no_encontrados)}
                    - Errores: {len(errores)}
                    """)
                
                # Mostrar no encontrados si hay
                if no_encontrados:
                    with st.expander(f"Ver {len(no_encontrados)} registros no encontrados"):
                        df_no_encontrados = pd.DataFrame(no_encontrados)
                        st.dataframe(df_no_encontrados)
                        
                        # Opción de descargar
                        csv = df_no_encontrados.to_csv(index=False)
                        st.download_button(
                            "📥 Descargar registros no encontrados",
                            csv,
                            "registros_no_encontrados.csv",
                            "text/csv"
                        )
                
                # Mostrar errores si hay
                if errores:
                    with st.expander(f"Ver {len(errores)} errores"):
                        df_errores = pd.DataFrame(errores)
                        st.dataframe(df_errores)
                
        except Exception as e:
            st.error(f"❌ Error procesando archivo: {str(e)}")
            st.exception(e)
    
    # Instrucciones adicionales
    with st.expander("📚 Formato del archivo Excel"):
        st.markdown("""
        El archivo Excel debe tener exactamente estas 3 columnas:
        
        | order_id | prealert_id | logistics_date |
        |----------|-------------|----------------|
        | 123456   | ABC123      | 2024-01-15     |
        | 789012   | DEF456      | 2024-01-16     |
        
        **Notas importantes:**
        - Las fechas se convertirán automáticamente al formato YYYY-MM-DD
        - Si un registro tiene tanto order_id como prealert_id, se intentará primero con prealert_id
        - Los valores vacíos o 'nan' serán ignorados
        - Usa el modo TEST primero para verificar que los matches sean correctos
        """)

if __name__ == "__main__":
    main()