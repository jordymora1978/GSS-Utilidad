"""
Reporte MEGA TIENDAS PERUANAS
Proveedor: Anicam | País: Perú
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
    Genera el reporte de MEGA TIENDAS PERUANAS
    """
    
    # Si no se proporcionan fechas, usar las del mes actual
    if fecha_inicio is None or fecha_fin is None:
        hoy = datetime.now().date()
        fecha_inicio = hoy.replace(day=1)
        ultimo_dia = calendar.monthrange(hoy.year, hoy.month)[1]
        fecha_fin = hoy.replace(day=ultimo_dia)
    
    # Mostrar título del reporte específico
    st.title("🇵🇪 Reporte: Mega Tiendas Peruanas")
    
    st.caption("Proveedor: Anicam | País: Perú | Campo: logistics_date")
    
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

    # Cargar TRM
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
        
        # CARGAR DATOS - CORREGIDO PARA EVITAR PROBLEMAS DE PAGINACIÓN
        try:
            # Query directa con filtro de fecha para mayor eficiencia
            query = supabase.table('consolidated_orders').select('*')
            query = query.eq('account_name', '4-MEGA TIENDAS PERUANAS')
            query = query.gte('logistics_date', str(fecha_inicio))
            query = query.lte('logistics_date', str(fecha_fin))
            result = query.execute()
            
            all_records = result.data
            
            if all_records:
                df = pd.DataFrame(all_records)
                
                # Convertir logistics_date (ya viene filtrada por la query)
                df['logistics_date'] = pd.to_datetime(df['logistics_date'], errors='coerce')
                
                if not df.empty:
                    # CALCULAR COLUMNAS PARA MEGA TIENDAS PERUANAS
                    
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
                    
                    # TRM Peru
                    df['TRM_Peru'] = trm_dict.get('peru', 3.75)
                    
                    # Socio cuenta (1 USD si es approved)
                    df['Socio_cuenta'] = df['order_status_meli'].apply(lambda x: 1 if x == 'approved' else 0)
                    
                    # Meli USD
                    df['Meli_USD'] = df['net_received_amount'] / df['TRM_Peru']
                        
                    # Calcular utilidad MEGA TIENDAS
                    def calc_utilidad_mega(row):
                        # Si es refunded, la utilidad es negativa
                        if row.get('order_status_meli', '') == 'refunded':
                            return -(row['declare_value'] * row['quantity'] + 
                                    row['logistics_total'] + 
                                    row['aditionals_total'])
                        # Si hay logistics_total, calcular normal
                        elif row['logistics_total'] > 0:
                            return (row['Meli_USD'] - 
                                   (row['declare_value'] * row['quantity']) - 
                                   row['logistics_total'] - 
                                   row['aditionals_total'] - 
                                   row['Socio_cuenta'])  # Se resta Socio_cuenta
                        return 0
                    
                    df['Utilidad_Gss'] = df.apply(calc_utilidad_mega, axis=1)
                    
                    # MOSTRAR MÉTRICAS COMPACTAS
                    total_registros = len(df)
                    utilidad_total = df['Utilidad_Gss'].sum()
                    aprobadas = (df['order_status_meli'] == 'approved').sum()
                    refunded = (df['order_status_meli'] == 'refunded').sum()
                    trm_peru = trm_dict.get('peru', 3.75)
                    total_socio = df['Socio_cuenta'].sum()

                    # MOSTRAR MÉTRICAS
                    st.markdown("---")
                    col1, col2, col3, col4, col5, col6 = st.columns(6)
                    col1.metric("📊 Total", total_registros)
                    col2.metric("💰 Utilidad", f"${utilidad_total:,.2f}")
                    col3.metric("✅ Aprobadas", aprobadas)
                    col4.metric("❌ Refunded", refunded)
                    col5.metric("🇵🇪 TRM Perú", f"${trm_peru:,.2f}")
                    col6.metric("💵 Socio Total", f"${total_socio:,.2f}")
                    
                    # MOSTRAR TABLA
                    st.markdown("---")
                    st.subheader("📋 Detalle del Reporte")
                    
                    # Columnas a mostrar
                    columnas_mostrar = [
                        'logistics_date', 'asignacion', 'prealert_id', 'order_id',
                        'order_status_meli', 'net_received_amount', 'declare_value', 
                        'quantity', 'logistics_total', 'aditionals_total',
                        'TRM_Peru', 'Socio_cuenta', 'Meli_USD', 'Utilidad_Gss'
                    ]
                    
                    columnas_disponibles = [col for col in columnas_mostrar if col in df.columns]
                    df_mostrar = df[columnas_disponibles].copy()
                    
                    # FORMATEAR PARA DISPLAY CON INDICADORES VISUALES
                    # Formatear net_received_amount según país (Perú - Soles)
                    if 'net_received_amount' in df_mostrar.columns:
                        df_mostrar['💵 Net Received'] = df_mostrar['net_received_amount'].apply(
                            lambda x: f"S/{x * trm_dict.get('peru', 3.75):.2f}" if pd.notna(x) and x != 0 else "S/0.00"
                        )
                        df_mostrar = df_mostrar.drop('net_received_amount', axis=1)
                    
                    # Formatear otras columnas con indicadores
                    if 'declare_value' in df_mostrar.columns:
                        df_mostrar['🟢 Declare Value'] = df_mostrar['declare_value'].apply(
                            lambda x: f"${x:,.2f}" if pd.notna(x) else "$0.00"
                        )
                        df_mostrar = df_mostrar.drop('declare_value', axis=1)
                    
                    if 'Meli_USD' in df_mostrar.columns:
                        df_mostrar['🟡 Meli USD'] = df_mostrar['Meli_USD'].apply(
                            lambda x: f"${x:,.2f}" if pd.notna(x) else "$0.00"
                        )
                        df_mostrar = df_mostrar.drop('Meli_USD', axis=1)
                    
                    # Para Perú, Bodegal no se aplica típicamente, pero agregamos las columnas disponibles
                    if 'logistics_total' in df_mostrar.columns:
                        df_mostrar['🔵 Bodegal'] = df_mostrar['logistics_total'].apply(
                            lambda x: f"${x:,.2f}" if pd.notna(x) else "$0.00"
                        )
                        df_mostrar = df_mostrar.drop('logistics_total', axis=1)
                    
                    if 'Socio_cuenta' in df_mostrar.columns:
                        df_mostrar['🟣 Socio Cuenta'] = df_mostrar['Socio_cuenta'].apply(
                            lambda x: f"${x:,.2f}" if pd.notna(x) else "$0.00"
                        )
                        df_mostrar = df_mostrar.drop('Socio_cuenta', axis=1)
                    
                    # Impuesto Fact (aditionals_total para Perú)
                    if 'aditionals_total' in df_mostrar.columns:
                        df_mostrar['🔴 Impuesto Fact.'] = df_mostrar['aditionals_total'].apply(
                            lambda x: f"${x:,.2f}" if pd.notna(x) else "$0.00"
                        )
                        df_mostrar = df_mostrar.drop('aditionals_total', axis=1)
                    
                    if 'Utilidad_Gss' in df_mostrar.columns:
                        df_mostrar['⚪ Utilidad GSS'] = df_mostrar['Utilidad_Gss'].apply(
                            lambda x: f"${x:,.2f}" if pd.notna(x) else "$0.00"
                        )
                        df_mostrar = df_mostrar.drop('Utilidad_Gss', axis=1)
                    
                    # Agregar columna Amazon (que sería el declare_value * quantity para este reporte)
                    if 'quantity' in df.columns:
                        df_mostrar['🟠 Amazon'] = (df['declare_value'] * df['quantity']).apply(
                            lambda x: f"${x:,.2f}" if pd.notna(x) else "$0.00"
                        )
                    
                    # Mostrar dataframe formateado
                    st.dataframe(df_mostrar, use_container_width=True, height=500)
                    
                    # EXPORTAR
                    st.markdown("---")
                    col1, col2 = st.columns(2)
                    
                    nombre = f'mega_tiendas_peruanas_{fecha_inicio.strftime("%Y%m%d")}_{fecha_fin.strftime("%Y%m%d")}'
                    
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
                            df_mostrar.to_excel(writer, sheet_name='MEGA-TIENDAS-PE', index=False)
                        
                        st.download_button(
                            "📥 Descargar Excel",
                            buffer.getvalue(),
                            f'{nombre}.xlsx',
                            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                        )
                    
                    # Información adicional
                    st.info(f"""
                    📌 **Resumen:**
                    - Período: {fecha_inicio} a {fecha_fin}
                    - TRM Perú: ${trm_dict.get('peru', 3.75):,.2f}
                    - Total Socio cuenta: ${df['Socio_cuenta'].sum():,.2f}
                    - Fórmula: Meli_USD - Amazon - Logística - Adicionales - Socio_cuenta
                    """)
                
                else:
                    st.warning(f"No se encontraron datos para el período {fecha_inicio} a {fecha_fin}")
            
            else:
                st.warning("No se encontraron registros para MEGA TIENDAS PERUANAS")
                
        except Exception as e:
            st.error(f"Error al cargar datos: {str(e)}")