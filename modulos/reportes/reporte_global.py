"""
REPORTE GLOBAL
Consolida todas las 8 cuentas de Mercado Libre
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
    Genera el reporte global consolidado
    """
    
    # Si no se proporcionan fechas, usar las del mes actual
    if fecha_inicio is None or fecha_fin is None:
        hoy = datetime.now().date()
        fecha_inicio = hoy.replace(day=1)
        ultimo_dia = calendar.monthrange(hoy.year, hoy.month)[1]
        fecha_fin = hoy.replace(day=ultimo_dia)
    
    # Mostrar título del reporte específico
    st.title("🌍 Reporte: Reporte Global")
    
    st.caption("Consolidado de todas las 8 cuentas | Fecha unificada")

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
        
        # CARGAR DATOS - FILTRAR DIRECTAMENTE EN LA CONSULTA PARA MEJOR RENDIMIENTO
        try:
            all_records = []
            
            # Cuentas que usan logistics_date (Anicam) - filtrar por logistics_date
            logistics_accounts = ['1-TODOENCARGO-CO', '4-MEGA TIENDAS PERUANAS', 
                                 '5-DETODOPARATODOS', '6-COMPRAFACIL', '7-COMPRA-YA']
            
            st.info("🔄 Cargando cuentas Anicam (logistics_date)...")
            for account in logistics_accounts:
                query = supabase.table('consolidated_orders').select('*')
                query = query.eq('account_name', account)
                query = query.gte('logistics_date', str(fecha_inicio))
                query = query.lte('logistics_date', str(fecha_fin))
                result = query.execute()
                if result.data:
                    all_records.extend(result.data)
            
            # Cuentas que usan cxp_date (Chilexpress) - filtrar por cxp_date
            cxp_accounts = ['2-MEGATIENDA SPA', '3-VEENDELO', '8-FABORCARGO']
            
            st.info("🔄 Cargando cuentas Chilexpress (cxp_date)...")
            for account in cxp_accounts:
                query = supabase.table('consolidated_orders').select('*')
                query = query.eq('account_name', account)
                query = query.gte('cxp_date', str(fecha_inicio))
                query = query.lte('cxp_date', str(fecha_fin))
                result = query.execute()
                if result.data:
                    all_records.extend(result.data)
            
            if all_records:
                df = pd.DataFrame(all_records)
                
                # CREAR FECHA UNIFICADA
                df['fecha_unificada'] = pd.NaT
                
                # Asignar fecha unificada según el tipo de cuenta
                mask_logistics = df['account_name'].isin(logistics_accounts)
                mask_cxp = df['account_name'].isin(cxp_accounts)
                
                if mask_logistics.any():
                    df.loc[mask_logistics, 'fecha_unificada'] = pd.to_datetime(
                        df.loc[mask_logistics, 'logistics_date'], errors='coerce'
                    )
                
                if mask_cxp.any():
                    df.loc[mask_cxp, 'fecha_unificada'] = pd.to_datetime(
                        df.loc[mask_cxp, 'cxp_date'], errors='coerce'
                    )
                
                # Filtrar registros con fechas válidas
                df = df[df['fecha_unificada'].notna()]
                
                if not df.empty:
                    # CALCULAR COLUMNAS PARA REPORTE GLOBAL
                    
                    # Limpiar valores monetarios
                    columnas_monetarias = ['declare_value', 'net_received_amount', 'logistics_total', 
                                          'aditionals_total', 'cxp_amt_due', 'cxp_arancel', 'cxp_iva',
                                          'logistic_weight_lbs']
                    
                    for col in columnas_monetarias:
                        if col in df.columns:
                            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                    
                    # Asegurar que quantity existe
                    if 'quantity' in df.columns:
                        df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(1)
                    else:
                        df['quantity'] = 1
                    
                    # CALCULAR BODEGAL (para todas las cuentas)
                    if 'logistic_type' in df.columns:
                        df['Bodegal'] = df['logistic_type'].apply(lambda x: 3.5 if x == 'xd_drop_off' else 0)
                    else:
                        df['Bodegal'] = 0
                    
                    # CALCULAR SOCIO_CUENTA solo para cuentas específicas
                    def calc_socio_cuenta(row):
                        cuentas_socio = ['2-MEGATIENDA SPA', '4-MEGA TIENDAS PERUANAS', '3-VEENDELO']
                        if row['account_name'] in cuentas_socio and row['order_status_meli'] == 'approved':
                            return 1
                        return 0
                    
                    df['Socio_cuenta'] = df.apply(calc_socio_cuenta, axis=1)
                    
                    # CALCULAR IMPUESTO POR FACTURACIÓN (solo para DTPT GROUP)
                    dtpt_accounts = ['5-DETODOPARATODOS', '6-COMPRAFACIL', '7-COMPRA-YA']
                    df['Impuesto_facturacion'] = df.apply(
                        lambda row: 1 if row['account_name'] in dtpt_accounts and row['order_status_meli'] == 'approved' else 0,
                        axis=1
                    )
                    
                    # Amazon (declare_value * quantity)
                    df['Amazon'] = df['declare_value'] * df['quantity']
                    
                    # TRM según país
                    def get_trm(account):
                        if account in ['1-TODOENCARGO-CO', '5-DETODOPARATODOS', '6-COMPRAFACIL', '7-COMPRA-YA']:
                            return trm_dict.get('colombia', 4300.0)
                        elif account == '4-MEGA TIENDAS PERUANAS':
                            return trm_dict.get('peru', 3.70)
                        else:  # Chile accounts
                            return trm_dict.get('chile', 990.0)
                    
                    df['TRM'] = df['account_name'].apply(get_trm)
                    
                    # Meli USD
                    df['Meli_USD'] = df['net_received_amount'] / df['TRM']
                    
                    # Calcular utilidades por cuenta (simplificado)
                    def calc_utilidad_gss(row):
                        account = row['account_name']
                        
                        if account == '8-FABORCARGO':
                            # Fórmula especial FABORCARGO (simplificada)
                            if row['cxp_amt_due'] > 0:
                                return row['cxp_arancel'] + row['cxp_iva'] - row['cxp_amt_due']
                            return 0
                        
                        elif account in ['2-MEGATIENDA SPA', '3-VEENDELO']:
                            # Chile accounts
                            if row.get('order_status_meli', '') == 'refunded':
                                return -(row['Amazon'] + row['cxp_amt_due'] + row['Bodegal'])
                            elif row['cxp_amt_due'] > 0:
                                return (row['Meli_USD'] - row['Amazon'] - row['cxp_amt_due'] - 
                                      row['Bodegal'] - row['Socio_cuenta'])
                            return 0
                        
                        elif account == '4-MEGA TIENDAS PERUANAS':
                            # Perú
                            if row.get('order_status_meli', '') == 'refunded':
                                return -(row['Amazon'] + row['logistics_total'] + row['aditionals_total'])
                            elif row['logistics_total'] > 0:
                                return (row['Meli_USD'] - row['Amazon'] - row['logistics_total'] - 
                                      row['aditionals_total'] - row['Socio_cuenta'])
                            return 0
                        
                        elif account in dtpt_accounts:
                            # DTPT GROUP
                            if row.get('order_status_meli', '') == 'refunded':
                                return -(row['Amazon'] + row['logistics_total'] + row['aditionals_total'])
                            elif row['logistics_total'] > 0:
                                utilidad_base = (row['Meli_USD'] - row['Amazon'] - row['logistics_total'] - 
                                               row['aditionals_total'] - row['Impuesto_facturacion'])
                                # Para GSS: si utilidad >= 7.5, GSS recibe utilidad - 7.5
                                return utilidad_base - 7.5 if utilidad_base >= 7.5 else 0
                            return 0
                        
                        elif account == '1-TODOENCARGO-CO':
                            # TODOENCARGO-CO
                            if row.get('order_status_meli', '') == 'refunded':
                                return -(row['Amazon'] + row['logistics_total'] + row['aditionals_total'])
                            elif row['logistics_total'] > 0:
                                return row['Meli_USD'] - row['Amazon'] - row['logistics_total'] - row['aditionals_total']
                            return 0
                        
                        return 0
                    
                    df['Utilidad_Gss'] = df.apply(calc_utilidad_gss, axis=1)
                    
                    # MOSTRAR MÉTRICAS PRINCIPALES COMPACTAS
                    total_registros = len(df)
                    utilidad_global_gss = df['Utilidad_Gss'].sum()
                    aprobadas = (df['order_status_meli'] == 'approved').sum()
                    refunded = (df['order_status_meli'] == 'refunded').sum()

                    # Calcular métricas por país
                    colombia_accounts = ['1-TODOENCARGO-CO', '5-DETODOPARATODOS', '6-COMPRAFACIL', '7-COMPRA-YA']
                    df_colombia = df[df['account_name'].isin(colombia_accounts)]
                    utilidad_colombia = df_colombia['Utilidad_Gss'].sum()
                    
                    df_peru = df[df['account_name'] == '4-MEGA TIENDAS PERUANAS']
                    utilidad_peru = df_peru['Utilidad_Gss'].sum()
                    
                    chile_accounts = ['2-MEGATIENDA SPA', '3-VEENDELO', '8-FABORCARGO']
                    df_chile = df[df['account_name'].isin(chile_accounts)]
                    utilidad_chile = df_chile['Utilidad_Gss'].sum()

                    # MOSTRAR MÉTRICAS PRINCIPALES
                    st.markdown("---")
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("📊 Total Global", f"{total_registros:,}")
                    col2.metric("💰 Utilidad GSS", f"${utilidad_global_gss:,.2f}")
                    col3.metric("✅ Aprobadas", f"{aprobadas:,}")
                    col4.metric("❌ Refunded", f"{refunded:,}")
                    
                    # MÉTRICAS POR PAÍS COMPACTAS
                    st.markdown("---")
                    st.subheader("🌎 Métricas por País")
                    
                    col1, col2, col3 = st.columns(3)
                    col1.metric("🇨🇴 Colombia", f"{len(df_colombia)} reg.", f"${utilidad_colombia:,.2f}")
                    col2.metric("🇵🇪 Perú", f"{len(df_peru)} reg.", f"${utilidad_peru:,.2f}")
                    col3.metric("🇨🇱 Chile", f"{len(df_chile)} reg.", f"${utilidad_chile:,.2f}")
                    
                    # MÉTRICAS POR CUENTA
                    st.markdown("---")
                    st.subheader("📊 Detalle por Cuenta")
                    
                    # Crear resumen por cuenta
                    resumen_cuentas = df.groupby('account_name').agg({
                        'order_id': 'count',
                        'Utilidad_Gss': 'sum',
                        'Amazon': 'sum',
                        'Meli_USD': 'sum'
                    }).round(2)
                    
                    resumen_cuentas.columns = ['Cantidad', 'Utilidad GSS', 'Amazon Total', 'Meli USD Total']
                    st.dataframe(resumen_cuentas, use_container_width=True)
                    
                    # MOSTRAR TABLA DETALLADA
                    st.markdown("---")
                    st.subheader("📋 Detalle del Reporte Global")
                    
                    # Renombrar columnas con indicadores visuales
                    df_display = df.copy()
                    
                    # Función para formatear net_received_amount según país
                    def format_net_received_by_country(row):
                        value = row['net_received_amount']
                        account = row['account_name']
                        
                        if pd.isna(value) or value == 0:
                            return ""
                        
                        # Colombia accounts
                        if account in ['1-TODOENCARGO-CO', '5-DETODOPARATODOS', '6-COMPRAFACIL', '7-COMPRA-YA']:
                            return f"${value:,.0f} COP"
                        # Perú accounts
                        elif account == '4-MEGA TIENDAS PERUANAS':
                            return f"S/{value:,.2f}"
                        # Chile accounts
                        else:
                            return f"${value:,.0f} CLP"
                    
                    # Aplicar formato a net_received_amount
                    df_display['net_received_formatted'] = df.apply(format_net_received_by_country, axis=1)
                    
                    # Renombrar columnas con indicadores
                    column_rename = {
                        'fecha_unificada': '📅 Fecha',
                        'account_name': '🏢 Cuenta',
                        'asignacion': '🏷️ Asignación',
                        'order_id': '📦 Order ID',
                        'order_status_meli': '📊 Estado',
                        'net_received_formatted': '💵 Net Received',
                        'declare_value': '🟢 Declare Value',
                        'Amazon': '🟠 Amazon',
                        'TRM': '💱 TRM',
                        'Meli_USD': '🟡 Meli USD',
                        'Bodegal': '🔵 Bodegal',
                        'Socio_cuenta': '🟣 Socio Cuenta',
                        'Impuesto_facturacion': '🔴 Impuesto Fact.',
                        'Utilidad_Gss': '⚪ Utilidad GSS'
                    }
                    
                    # Columnas a mostrar con nuevos nombres
                    columnas_mostrar = [
                        'fecha_unificada', 'account_name', 'asignacion', 'order_id',
                        'order_status_meli', 'net_received_formatted', 
                        'Amazon', 'TRM', 'Meli_USD',
                        'Bodegal', 'Socio_cuenta', 'Impuesto_facturacion', 
                        'Utilidad_Gss'
                    ]
                    
                    columnas_disponibles = [col for col in columnas_mostrar if col in df_display.columns]
                    df_mostrar = df_display[columnas_disponibles]
                    
                    # Renombrar columnas
                    df_mostrar = df_mostrar.rename(columns={k: v for k, v in column_rename.items() if k in df_mostrar.columns})
                    
                    # Mostrar sin formato de estilo
                    st.dataframe(df_mostrar, use_container_width=True, height=500)
                    
                    # EXPORTAR
                    st.markdown("---")
                    col1, col2 = st.columns(2)
                    
                    nombre = f'reporte_global_{fecha_inicio.strftime("%Y%m%d")}_{fecha_fin.strftime("%Y%m%d")}'
                    
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
                            df_mostrar.to_excel(writer, sheet_name='GLOBAL', index=False)
                        
                        st.download_button(
                            "📥 Descargar Excel",
                            buffer.getvalue(),
                            f'{nombre}.xlsx',
                            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                        )
                    
                    # Información adicional
                    st.info(f"""
                    📌 **Resumen Global:**
                    - Período: {fecha_inicio} a {fecha_fin}
                    - Total de cuentas: 8
                    - Total registros: {len(df):,}
                    - Utilidad Global GSS: ${df['Utilidad_Gss'].sum():,.2f}
                    - TRM Colombia: ${trm_dict.get('colombia', 4300):,.0f}
                    - TRM Perú: ${trm_dict.get('peru', 3.70):,.2f}
                    - TRM Chile: ${trm_dict.get('chile', 990):,.0f}
                    """)
                
                else:
                    st.warning(f"No se encontraron datos para el período {fecha_inicio} a {fecha_fin}")
                
            else:
                st.warning("No se encontraron registros en la base de datos")
                
        except Exception as e:
            st.error(f"Error al cargar datos: {str(e)}")