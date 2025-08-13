"""
Reporte TODOENCARGO-CO
Extraído directamente del código original
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import io
import sys
import os
import calendar

# Path configuration
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, parent_dir)

from supabase import create_client
import config

def generar_reporte(fecha_inicio=None, fecha_fin=None):
    """
    Genera el reporte de TODOENCARGO-CO
    """
    
    # Si no se proporcionan fechas, usar las del mes actual
    if fecha_inicio is None or fecha_fin is None:
        hoy = datetime.now().date()
        fecha_inicio = hoy.replace(day=1)  # Primer día del mes actual
        ultimo_dia = calendar.monthrange(hoy.year, hoy.month)[1]
        fecha_fin = hoy.replace(day=ultimo_dia)  # Último día del mes actual
    
    # Initialize Supabase
    @st.cache_resource
    def init_supabase():
        return create_client(config.SUPABASE_URL, config.SUPABASE_KEY)

    supabase = init_supabase()

    # Constants
    MESES = {
        1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
        5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
        9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
    }

    # Cargar TRM - COPIADO DEL ORIGINAL
    @st.cache_data(ttl=300)
    def cargar_trm():
        try:
            result = supabase.table('trm_actual').select('*').execute()
            trm_dict = {}
            for row in result.data:
                trm_dict[row['pais']] = float(row['valor'])
            return trm_dict
        except:
            return {
                'colombia': 4250.0,
                'peru': 3.75,
                'chile': 850.0
            }

    # Mostrar las fechas que se están usando
    st.info(f"📅 **Período del reporte:** {fecha_inicio.strftime('%d/%m/%Y')} - {fecha_fin.strftime('%d/%m/%Y')}")
    
    with st.spinner("Generando reporte..."):
            
            # Cargar TRM
            trm_dict = cargar_trm()
            
            # CARGAR DATOS - CORREGIDO PARA CARGAR TODOS LOS REGISTROS
            try:
                # Usar la query directa con filtro de fecha para evitar problemas de paginación
                query = supabase.table('consolidated_orders').select('*')
                query = query.eq('account_name', '1-TODOENCARGO-CO')
                query = query.gte('logistics_date', str(fecha_inicio))
                query = query.lte('logistics_date', str(fecha_fin))
                result = query.execute()
                
                all_records = result.data
                
                if all_records:
                    df = pd.DataFrame(all_records)
                    
                    # Convertir logistics_date (ya viene filtrada por la query)
                    df['logistics_date'] = pd.to_datetime(df['logistics_date'], errors='coerce')
                    
                    if not df.empty:
                        # CALCULAR COLUMNAS - COPIADO DEL ORIGINAL
                        
                        # Limpiar valores monetarios
                        columnas_monetarias = ['declare_value', 'net_received_amount', 'logistics_total', 
                                              'aditionals_total']
                        
                        for col in columnas_monetarias:
                            if col in df.columns:
                                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                        
                        # Asegurar que quantity existe
                        if 'quantity' in df.columns:
                            df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(1)
                        else:
                            df['quantity'] = 1
                        
                        # TRM Colombia
                        df['TRM_Colombia'] = trm_dict.get('colombia', 4250.0)
                        
                        # Meli USD
                        df['Meli_USD'] = df['net_received_amount'] / df['TRM_Colombia']
                        
                        # Calcular utilidad
                        def calc_utilidad_tdc(row):
                            if row.get('order_status_meli', '') == 'refunded':
                                return -(row['declare_value'] * row['quantity'] + 
                                        row['logistics_total'] + 
                                        row['aditionals_total'])
                            elif row['logistics_total'] > 0:
                                return (row['Meli_USD'] - 
                                       (row['declare_value'] * row['quantity']) - 
                                       row['logistics_total'] - 
                                       row['aditionals_total'])
                            return 0
                        
                        df['Utilidad_Gss'] = df.apply(calc_utilidad_tdc, axis=1)
                        
                        # MOSTRAR MÉTRICAS
                        col1, col2, col3, col4 = st.columns(4)
                        col1.metric("📊 Total", len(df))
                        col2.metric("💰 Utilidad Total", f"${df['Utilidad_Gss'].sum():,.2f}")
                        col3.metric("✅ Aprobadas", (df['order_status_meli'] == 'approved').sum())
                        col4.metric("❌ Refunded", (df['order_status_meli'] == 'refunded').sum())
                        
                        # MOSTRAR TABLA - SIN FORMATO
                        st.markdown("---")
                        st.subheader("📋 Detalle del Reporte")
                        
                        # Columnas a mostrar
                        columnas_mostrar = [
                            'logistics_date', 'asignacion', 'prealert_id', 'order_id',
                            'order_status_meli', 'net_received_amount', 'declare_value', 
                            'quantity', 'logistics_total', 'aditionals_total',
                            'TRM_Colombia', 'Meli_USD', 'Utilidad_Gss'
                        ]
                        
                        columnas_disponibles = [col for col in columnas_mostrar if col in df.columns]
                        df_mostrar = df[columnas_disponibles]
                        
                        # Mostrar sin formato de estilo
                        st.dataframe(df_mostrar, use_container_width=True, height=500)
                        
                        # EXPORTAR
                        st.markdown("---")
                        col1, col2 = st.columns(2)
                        
                        nombre = f'todoencargo_co_{fecha_inicio.strftime("%Y%m%d")}_{fecha_fin.strftime("%Y%m%d")}'
                        
                        with col1:
                            csv = df_mostrar.to_csv(index=False, encoding='utf-8-sig')
                            st.download_button(
                                "📥 Descargar CSV",
                                csv,
                                f'{nombre}.csv',
                                'text/csv'
                            )
                        
                        with col2:
                            buffer = io.BytesIO()
                            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                                df_mostrar.to_excel(writer, sheet_name='TODOENCARGO-CO', index=False)
                            
                            st.download_button(
                                "📥 Descargar Excel",
                                buffer.getvalue(),
                                f'{nombre}.xlsx',
                                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                            )
                        
                        st.info(f"Período: {fecha_inicio} a {fecha_fin} | TRM: ${trm_dict.get('colombia', 4250):,.0f}")
                    
                    else:
                        st.warning(f"No se encontraron datos para el período {fecha_inicio} a {fecha_fin}")
                
                else:
                    st.warning("No se encontraron registros para TODOENCARGO-CO")
                    
            except Exception as e:
                st.error(f"Error al cargar datos: {str(e)}")