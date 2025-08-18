"""
Reporte DTPT GROUP
Proveedor: Anicam | País: Colombia
Incluye: DETODOPARATODOS, COMPRAFACIL, COMPRA-YA
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
    Genera el reporte de DTPT GROUP
    """
    
    # Si no se proporcionan fechas, usar las del mes actual
    if fecha_inicio is None or fecha_fin is None:
        hoy = datetime.now().date()
        fecha_inicio = hoy.replace(day=1)
        ultimo_dia = calendar.monthrange(hoy.year, hoy.month)[1]
        fecha_fin = hoy.replace(day=ultimo_dia)
    
    # Mostrar título del reporte específico
    st.title("🏢 Reporte: DTPT Group")
    
    st.caption("Proveedor: Anicam | País: Colombia | Campo: logistics_date")
    st.caption("Incluye: DETODOPARATODOS, COMPRAFACIL, COMPRA-YA")

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
            # Las 3 cuentas del DTPT GROUP
            account_names = ['5-DETODOPARATODOS', '6-COMPRAFACIL', '7-COMPRA-YA']
            
            # Query directa con filtro de fecha (DTPT usa logistics_date)
            query = supabase.table('consolidated_orders').select('*')
            query = query.in_('account_name', account_names)
            query = query.gte('logistics_date', str(fecha_inicio))
            query = query.lte('logistics_date', str(fecha_fin))
            result = query.execute()
            
            all_records = result.data
            
            if all_records:
                df = pd.DataFrame(all_records)
                
                # Convertir logistics_date (ya viene filtrada por la query)
                df['logistics_date'] = pd.to_datetime(df['logistics_date'], errors='coerce')
                
                if not df.empty:
                    # CALCULAR COLUMNAS PARA DTPT GROUP
                    
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
                    
                    # Impuesto por facturación (1 USD si es approved)
                    df['Impuesto_facturacion'] = df['order_status_meli'].apply(lambda x: 1 if x == 'approved' else 0)
                    
                    # Meli USD
                    df['Meli_USD'] = df['net_received_amount'] / df['TRM_Colombia']
                    
                    # Calcular utilidad DTPT
                    def calc_utilidad_dtpt(row):
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
                                   row['Impuesto_facturacion'])
                        return 0
                    
                    df['Utilidad'] = df.apply(calc_utilidad_dtpt, axis=1)
                    
                    # DISTRIBUCIÓN DE UTILIDADES (especial para DTPT)
                    # Si la utilidad es >= 7.5, el socio recibe 7.5 y GSS el resto
                    # Si es < 7.5, el socio recibe todo (incluso si es negativo)
                    df['Utilidad_Socio'] = df['Utilidad'].apply(lambda x: 7.5 if x >= 7.5 else x)
                    df['Utilidad_Gss'] = df['Utilidad'].apply(lambda x: x - 7.5 if x >= 7.5 else 0)
                    
                    # MOSTRAR MÉTRICAS COMPACTAS
                    total_registros = len(df)
                    utilidad_total = df['Utilidad'].sum()
                    utilidad_socio = df['Utilidad_Socio'].sum()
                    utilidad_gss = df['Utilidad_Gss'].sum()
                    aprobadas = (df['order_status_meli'] == 'approved').sum()
                    refunded = (df['order_status_meli'] == 'refunded').sum()
                    trm_colombia = trm_dict.get('colombia', 4250)
                    ordenes_alto_valor = (df['Utilidad'] >= 7.5).sum()

                    # MOSTRAR MÉTRICAS
                    st.markdown("---")
                    col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
                    col1.metric("📊 Total", total_registros)
                    col2.metric("💰 Utilidad Total", f"${utilidad_total:,.2f}")
                    col3.metric("👥 Socio", f"${utilidad_socio:,.2f}")
                    col4.metric("🏢 GSS", f"${utilidad_gss:,.2f}")
                    col5.metric("✅ Aprobadas", aprobadas)
                    col6.metric("❌ Refunded", refunded)
                    col7.metric("🇨🇴 TRM", f"${trm_colombia:,.0f}")
                    
                    # Distribución por cuenta compacta
                    st.markdown("---")
                    st.subheader("📊 Distribución por Cuenta")
                    detodo_registros = len(df[df['account_name'] == '5-DETODOPARATODOS'])
                    comprafacil_registros = len(df[df['account_name'] == '6-COMPRAFACIL'])
                    compraya_registros = len(df[df['account_name'] == '7-COMPRA-YA'])
                    
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("DETODOPARATODOS", f"{detodo_registros} registros")
                    col2.metric("COMPRAFACIL", f"{comprafacil_registros} registros")
                    col3.metric("COMPRA-YA", f"{compraya_registros} registros")
                    col4.metric("📈 Órdenes >$7.5", ordenes_alto_valor)
                    
                    # MOSTRAR TABLA
                    st.markdown("---")
                    st.subheader("📋 Detalle del Reporte")
                    
                    # Columnas a mostrar
                    columnas_mostrar = [
                        'logistics_date', 'account_name', 'asignacion', 'prealert_id', 'order_id',
                        'order_status_meli', 'net_received_amount', 'declare_value', 
                        'quantity', 'logistics_total', 'aditionals_total',
                        'TRM_Colombia', 'Meli_USD', 'Impuesto_facturacion',
                        'Utilidad', 'Utilidad_Socio', 'Utilidad_Gss'
                    ]
                    
                    columnas_disponibles = [col for col in columnas_mostrar if col in df.columns]
                    df_mostrar = df[columnas_disponibles].copy()
                    
                    # FORMATEAR PARA DISPLAY CON INDICADORES VISUALES
                    # Formatear net_received_amount según país (Colombia - COP)
                    if 'net_received_amount' in df_mostrar.columns:
                        df_mostrar['💵 Net Received'] = df_mostrar['net_received_amount'].apply(
                            lambda x: f"${x * trm_dict.get('colombia', 4250):,.0f} COP" if pd.notna(x) and x != 0 else "$0 COP"
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
                    
                    # Para Colombia, Bodegal equivale a logistics_total
                    if 'logistics_total' in df_mostrar.columns:
                        df_mostrar['🔵 Bodegal'] = df_mostrar['logistics_total'].apply(
                            lambda x: f"${x:,.2f}" if pd.notna(x) else "$0.00"
                        )
                        df_mostrar = df_mostrar.drop('logistics_total', axis=1)
                    
                    # Para Colombia, Socio Cuenta sería Utilidad_Socio
                    if 'Utilidad_Socio' in df_mostrar.columns:
                        df_mostrar['🟣 Socio Cuenta'] = df_mostrar['Utilidad_Socio'].apply(
                            lambda x: f"${x:,.2f}" if pd.notna(x) else "$0.00"
                        )
                        df_mostrar = df_mostrar.drop('Utilidad_Socio', axis=1)
                    
                    # Impuesto Fact (Impuesto_facturacion para Colombia)
                    if 'Impuesto_facturacion' in df_mostrar.columns:
                        df_mostrar['🔴 Impuesto Fact.'] = df_mostrar['Impuesto_facturacion'].apply(
                            lambda x: f"${x:,.2f}" if pd.notna(x) else "$0.00"
                        )
                        df_mostrar = df_mostrar.drop('Impuesto_facturacion', axis=1)
                    
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
                    
                    nombre = f'dtpt_group_{fecha_inicio.strftime("%Y%m%d")}_{fecha_fin.strftime("%Y%m%d")}'
                    
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
                            df_mostrar.to_excel(writer, sheet_name='DTPT-GROUP', index=False)
                        
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
                    - TRM Colombia: ${trm_dict.get('colombia', 4250):,.0f}
                    - Total Impuesto: ${df['Impuesto_facturacion'].sum():,.2f}
                    - **Distribución de Utilidades:**
                      - Si Utilidad >= $7.50: Socio = $7.50, GSS = resto
                      - Si Utilidad < $7.50: Socio = todo (incluso negativos), GSS = $0
                    """)
                
                else:
                    st.warning(f"No se encontraron datos para el período {fecha_inicio} a {fecha_fin}")
                
            else:
                st.warning("No se encontraron registros para DTPT GROUP")
                
        except Exception as e:
            st.error(f"Error al cargar datos: {str(e)}")