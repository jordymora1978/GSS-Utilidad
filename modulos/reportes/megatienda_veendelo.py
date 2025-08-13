"""
Reporte MEGATIENDA SPA/VEENDELO
Proveedor: Chilexpress | País: Chile
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
    Genera el reporte de MEGATIENDA SPA/VEENDELO
    """
    
    # Si no se proporcionan fechas, usar las del mes actual
    if fecha_inicio is None or fecha_fin is None:
        hoy = datetime.now().date()
        fecha_inicio = hoy.replace(day=1)
        ultimo_dia = calendar.monthrange(hoy.year, hoy.month)[1]
        fecha_fin = hoy.replace(day=ultimo_dia)
    
    # Mostrar título del reporte específico
    st.title("🛒 Reporte: MegaTienda Veendelo")
    
    st.caption("Proveedor: Chilexpress | País: Chile | Campo: cxp_date")

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
                'colombia': 4300.0,
                'peru': 3.70,
                'chile': 990.0
            }

    # Mostrar las fechas que se están usando
    st.info(f"📅 **Período del reporte:** {fecha_inicio.strftime('%d/%m/%Y')} - {fecha_fin.strftime('%d/%m/%Y')}")
    
    with st.spinner("Generando reporte..."):
        
        # Cargar TRM
        trm_dict = cargar_trm()
        
        # CARGAR DATOS - CORREGIDO PARA EVITAR PROBLEMAS DE PAGINACIÓN
        try:
            # Buscar ambas cuentas: MEGATIENDA SPA y VEENDELO
            account_names = ['2-MEGATIENDA SPA', '3-VEENDELO']
            
            # Query directa con filtro de cxp_date (campo principal para Chile)
            query = supabase.table('consolidated_orders').select('*')
            query = query.in_('account_name', account_names)
            query = query.gte('cxp_date', str(fecha_inicio))
            query = query.lte('cxp_date', str(fecha_fin))
            result = query.execute()
            
            all_records = result.data
            
            if all_records:
                df = pd.DataFrame(all_records)
                
                # Convertir cxp_date (ya viene filtrada por la query)
                df['cxp_date'] = pd.to_datetime(df['cxp_date'], errors='coerce')
                
                if not df.empty:
                    # CALCULAR COLUMNAS PARA MEGATIENDA/VEENDELO
                    
                    # Limpiar valores monetarios (incluye columnas CXP)
                    columnas_monetarias = ['declare_value', 'net_received_amount', 
                                          'cxp_amt_due', 'cxp_arancel', 'cxp_iva']
                    
                    for col in columnas_monetarias:
                        if col in df.columns:
                            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                    
                    # Asegurar que quantity existe
                    if 'quantity' in df.columns:
                        df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(1)
                    else:
                        df['quantity'] = 1
                    
                    # TRM Chile
                    df['TRM_Chile'] = trm_dict.get('chile', 990.0)
                    
                    # Bodegal (3.5 USD si logistic_type es xd_drop_off)
                    if 'logistic_type' in df.columns:
                        df['Bodegal'] = df['logistic_type'].apply(lambda x: 3.5 if x == 'xd_drop_off' else 0)
                    else:
                        df['Bodegal'] = 0
                    
                    # Socio cuenta (1 USD si es approved)
                    df['Socio_cuenta'] = df['order_status_meli'].apply(lambda x: 1 if x == 'approved' else 0)
                    
                    # Meli USD
                    df['Meli_USD'] = df['net_received_amount'] / df['TRM_Chile']
                    
                    # Calcular utilidad MEGATIENDA/VEENDELO
                    def calc_utilidad_veen(row):
                        # Si es refunded, la utilidad es negativa (solo costos, sin ingresos)
                        if row.get('order_status_meli', '') == 'refunded':
                            # Para refunded: solo pérdidas (declare_value + cxp_amt_due + Bodegal + Socio)
                            return -(row['declare_value'] * row['quantity'] + 
                                   row['cxp_amt_due'] + 
                                   row['Bodegal'] + 
                                   row['Socio_cuenta'])
                        # Si hay cxp_amt_due y NO es refunded, calcular normal
                        elif row['cxp_amt_due'] > 0:
                            return (row['Meli_USD'] - 
                                   (row['declare_value'] * row['quantity']) - 
                                   row['cxp_amt_due'] - 
                                   row['Bodegal'] - 
                                   row['Socio_cuenta'])
                        return 0
                    
                    df['Utilidad_Gss'] = df.apply(calc_utilidad_veen, axis=1)
                    
                    # MOSTRAR MÉTRICAS COMPACTAS
                    total_registros = len(df)
                    utilidad_total = df['Utilidad_Gss'].sum()
                    aprobadas = (df['order_status_meli'] == 'approved').sum()
                    refunded = (df['order_status_meli'] == 'refunded').sum()
                    trm_chile = trm_dict.get('chile', 990)
                    total_socio = df['Socio_cuenta'].sum()
                    total_bodegal = df['Bodegal'].sum()

                    # MOSTRAR MÉTRICAS
                    st.markdown("---")
                    col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
                    col1.metric("📊 Total", total_registros)
                    col2.metric("💰 Utilidad", f"${utilidad_total:,.2f}")
                    col3.metric("✅ Aprobadas", aprobadas)
                    col4.metric("❌ Refunded", refunded)
                    col5.metric("🇨🇱 TRM Chile", f"${trm_chile:,.0f}")
                    col6.metric("💵 Socio", f"${total_socio:,.2f}")
                    col7.metric("📦 Bodegal", f"${total_bodegal:,.2f}")
                    
                    # MOSTRAR TABLA
                    st.markdown("---")
                    st.subheader("📋 Detalle del Reporte")
                    
                    # Columnas a mostrar (usando columnas CXP)
                    columnas_mostrar = [
                        'cxp_date', 'account_name', 'asignacion', 'order_status_meli', 
                        'net_received_amount', 'cxp_ref_number', 'cxp_consignee',
                        'cxp_arancel', 'cxp_iva', 'cxp_amt_due', 
                        'declare_value', 'quantity', 'TRM_Chile', 'Bodegal', 
                        'Socio_cuenta', 'Meli_USD', 'Utilidad_Gss'
                    ]
                    
                    columnas_disponibles = [col for col in columnas_mostrar if col in df.columns]
                    df_mostrar = df[columnas_disponibles]
                    
                    # Mostrar sin formato de estilo
                    st.dataframe(df_mostrar, use_container_width=True, height=500)
                    
                    # EXPORTAR
                    st.markdown("---")
                    col1, col2 = st.columns(2)
                    
                    nombre = f'megatienda_veendelo_{fecha_inicio.strftime("%Y%m%d")}_{fecha_fin.strftime("%Y%m%d")}'
                    
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
                            df_mostrar.to_excel(writer, sheet_name='MEGATIENDA-VEENDELO', index=False)
                        
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
                    - TRM Chile: ${trm_dict.get('chile', 990):,.0f}
                    - Total Socio: ${df['Socio_cuenta'].sum():,.2f}
                    - Total Bodegal: ${df['Bodegal'].sum():,.2f}
                    - Fórmula: Meli_USD - Amazon - CXP_amt_due - Bodegal - Socio
                    """)
                
                else:
                    st.warning(f"No se encontraron datos para el período {fecha_inicio} a {fecha_fin}")
                
            else:
                st.warning("No se encontraron registros para MEGATIENDA SPA/VEENDELO")
                
        except Exception as e:
            st.error(f"Error al cargar datos: {str(e)}")