"""
Script temporal para actualizar logistics_date desde Excel
Hace match por prealert_id o order_id según disponibilidad
"""

import pandas as pd
import streamlit as st
from supabase import create_client
import config
from datetime import datetime

def main():
    st.set_page_config(page_title="Actualizar Logistics Date", layout="wide")
    st.title("🔧 Actualizar Logistics Date desde Excel")
    
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
                
                for idx, row in df_excel.iterrows():
                    try:
                        order_id = str(row['order_id']) if pd.notna(row['order_id']) else None
                        prealert_id = str(row['prealert_id']) if pd.notna(row['prealert_id']) else None
                        # Asegurar que logistics_date es string, no Timestamp
                        logistics_date = str(row['logistics_date']) if pd.notna(row['logistics_date']) else None
                        
                        # Remover valores 'nan' o vacíos
                        if order_id == 'nan' or order_id == '':
                            order_id = None
                        if prealert_id == 'nan' or prealert_id == '':
                            prealert_id = None
                        
                        actualizado = False
                        
                        # Intentar actualizar por prealert_id primero
                        if prealert_id and prealert_id != 'nan':
                            if modo_test:
                                # En modo test, solo verificar si existe
                                result = supabase.table('consolidated_orders').select('id').eq('prealert_id', prealert_id).limit(1).execute()
                                if result.data:
                                    actualizados_por_prealert += 1
                                    actualizado = True
                            else:
                                # Actualizar en base de datos
                                result = supabase.table('consolidated_orders').update({
                                    'logistics_date': logistics_date
                                }).eq('prealert_id', prealert_id).execute()
                                
                                if result.data:
                                    actualizados_por_prealert += 1
                                    actualizado = True
                        
                        # Si no se actualizó por prealert_id, intentar por order_id
                        if not actualizado and order_id and order_id != 'nan':
                            if modo_test:
                                # En modo test, solo verificar si existe
                                result = supabase.table('consolidated_orders').select('id').eq('order_id', order_id).limit(1).execute()
                                if result.data:
                                    actualizados_por_order += 1
                                    actualizado = True
                            else:
                                # Actualizar en base de datos
                                result = supabase.table('consolidated_orders').update({
                                    'logistics_date': logistics_date
                                }).eq('order_id', order_id).execute()
                                
                                if result.data:
                                    actualizados_por_order += 1
                                    actualizado = True
                        
                        # Si no se encontró registro
                        if not actualizado:
                            no_encontrados.append({
                                'order_id': order_id,
                                'prealert_id': prealert_id,
                                'logistics_date': logistics_date
                            })
                            log_detalle.append({
                                'fila': idx + 1,
                                'order_id': order_id,
                                'prealert_id': prealert_id,
                                'resultado': '❌ No encontrado',
                                'metodo': 'N/A'
                            })
                        else:
                            metodo = 'Prealert ID' if actualizados_por_prealert > actualizados_por_order else 'Order ID'
                            log_detalle.append({
                                'fila': idx + 1,
                                'order_id': order_id,
                                'prealert_id': prealert_id,
                                'resultado': '✅ Actualizado' if not modo_test else '✅ Encontrado (TEST)',
                                'metodo': metodo
                            })
                        
                        # Actualizar progreso
                        progress = (idx + 1) / total_filas
                        progress_bar.progress(progress)
                        status_text.text(f"Procesando: {idx + 1}/{total_filas} | Prealert: {actualizados_por_prealert} | Order: {actualizados_por_order}")
                        
                    except Exception as e:
                        errores.append({
                            'order_id': order_id,
                            'prealert_id': prealert_id,
                            'error': str(e)
                        })
                        log_detalle.append({
                            'fila': idx + 1,
                            'order_id': order_id,
                            'prealert_id': prealert_id,
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