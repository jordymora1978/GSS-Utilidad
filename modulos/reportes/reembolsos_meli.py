"""
REEMBOLSOS MELI
Cálculo de Reversión basado en las fórmulas de Utilidad GSS de cada cuenta
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import io
import sys
import os
import calendar
import math

# Path configuration
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, parent_dir)

from supabase import create_client
import config

def generar_reporte(fecha_inicio=None, fecha_fin=None):
    """
    Genera el reporte de reembolsos MELI
    """
    
    # Si no se proporcionan fechas, usar las del mes actual
    if fecha_inicio is None or fecha_fin is None:
        hoy = datetime.now().date()
        fecha_inicio = hoy.replace(day=1)
        ultimo_dia = calendar.monthrange(hoy.year, hoy.month)[1]
        fecha_fin = hoy.replace(day=ultimo_dia)
    
    # Mostrar título del reporte específico
    st.markdown("""
    <div style="background-color: #1E1E1E; padding: 15px; border-radius: 10px; border-left: 5px solid #FF4B4B; margin-bottom: 20px;">
        <h2 style="margin: 0; color: white;">💳 Reporte: Reembolsos MeLi</h2>
    </div>
    """, unsafe_allow_html=True)
    
    st.caption("Órdenes con status refunded y amz_order_id | Excluye FABORCARGO | Fecha: refunded_date")

    # Configuración de Supabase 
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
                'chile': 950.0
            }

    # Mostrar las fechas que se están usando
    st.info(f"📅 **Período del reporte:** {fecha_inicio.strftime('%d/%m/%Y')} - {fecha_fin.strftime('%d/%m/%Y')}")
    
    with st.spinner("Generando reporte..."):
        
        # Cargar TRM
        trm_dict = cargar_trm()
        
        # --- FUNCIÓN DE CÁLCULO GENERAL PARA TODAS LAS CUENTAS ---
        def calcular_metricas_completas(row, trm_dict):
            account = row['account_name']
            
            # Inicializar valores por defecto
            trm = 0.0
            meli_usd = 0.0
            utilidad_gss = 0.0
            reversion_socio = 0.0
            reversion_gss = 0.0
            perdida = 0.0
            impuesto_facturacion = 0.0

            # Cálculos para TODOENCARGO-CO
            if account == '1-TODOENCARGO-CO':
                trm = trm_dict.get('colombia', 4300.0)
                meli_usd = row['net_received_amount'] / trm
                utilidad_gss = meli_usd - row['declare_value'] * row['quantity'] - row['logistics_total'] - row['aditionals_total']
                perdida = -(row['logistics_total'] + row['aditionals_total'] + row['declare_value'] * row['quantity'])
                reversion_socio = 0.0 # No aplica para esta cuenta
                reversion_gss = -utilidad_gss

            # Cálculos para MEGA TIENDAS PERUANAS
            elif account == '4-MEGA TIENDAS PERUANAS':
                trm = trm_dict.get('peru', 3.70)
                meli_usd = row['net_received_amount'] / trm
                socio_cuenta = 0.0 # Para órdenes reembolsadas
                utilidad_gss = meli_usd - row['declare_value'] * row['quantity'] - row['logistics_total'] - row['aditionals_total'] - socio_cuenta
                perdida = -(row['logistics_total'] + row['aditionals_total'] + row['declare_value'] * row['quantity'])
                reversion_socio = 0.0 # No aplica
                reversion_gss = -utilidad_gss

            # Cálculos para MEGATIENDA SPA / VEENDELO (Chile)
            elif account in ['2-MEGATIENDA SPA', '3-VEENDELO']:
                trm = trm_dict.get('chile', 950.0)
                meli_usd = row['net_received_amount'] / trm
                socio_cuenta = 0.0 # Para órdenes reembolsadas
                utilidad_gss = meli_usd - row['declare_value'] * row['quantity'] - row['cxp_amt_due'] - row['Bodegal'] - socio_cuenta
                perdida = -(row['declare_value'] * row['quantity'] + row['cxp_amt_due'] + row['Bodegal'])
                reversion_socio = 0.0 # No aplica
                reversion_gss = -utilidad_gss
            
            # --- CÁLCULOS CORREGIDOS PARA DTPT GROUP (5-DETODOPARATODOS, 6-COMPRAFACIL, 7-COMPRA-YA) ---
            elif account in ['5-DETODOPARATODOS', '6-COMPRAFACIL', '7-COMPRA-YA']:
                trm = trm_dict.get('colombia', 4300.0)
                meli_usd = row['net_received_amount'] / trm
                impuesto_facturacion = 1.0 # Para DTPT siempre es 1 (incluso en reembolsos)

                # CORREGIDO: La fórmula de Utilidad GSS debe incluir Impuesto_facturacion
                utilidad_gss = meli_usd - (row['declare_value'] * row['quantity']) - row['logistics_total'] - row['aditionals_total'] - impuesto_facturacion
                
                # Cuentas de DTPT Group no tienen 'Bodegal', siempre debe ser 0.
                row['Bodegal'] = 0.0

                # Calculamos las reversiones según la nueva lógica
                if utilidad_gss >= 7.5:
                    reversion_socio = 7.5
                    reversion_gss = utilidad_gss - 7.5
                else:
                    reversion_socio = utilidad_gss
                    reversion_gss = 0.0

                # La pérdida es la suma de los costos (valor negativo)
                perdida = -(row['logistics_total'] + row['aditionals_total'] + row['declare_value'] * row['quantity'] + impuesto_facturacion)

            return (trm, meli_usd, utilidad_gss, reversion_socio, reversion_gss, perdida, impuesto_facturacion)
        
        # --- CARGAR DATOS REALES DE SUPABASE - CORREGIDO ---
        try:
            # Query directa con filtros aplicados en Supabase
            query = supabase.table('consolidated_orders').select('*')
            query = query.eq('order_status_meli', 'refunded')
            query = query.gte('refunded_date', str(fecha_inicio))
            query = query.lte('refunded_date', str(fecha_fin))
            result = query.execute()
            
            if result.data:
                df = pd.DataFrame(result.data)
                
                # EXCLUIR FABORCARGO
                df = df[df['account_name'] != '8-FABORCARGO']
                
                # FILTRAR: Solo registros con amz_order_id con valor
                df = df[df['amz_order_id'].notna()]
                df = df[df['amz_order_id'] != '']
                
                # Convertir refunded_date (ya viene filtrada) y eliminar timezone
                df['refunded_date'] = pd.to_datetime(df['refunded_date'], errors='coerce')
                # Remover timezone si existe para compatibilidad con Excel
                if df['refunded_date'].dt.tz is not None:
                    df['refunded_date'] = df['refunded_date'].dt.tz_localize(None)
                
                if not df.empty:
                    # LIMPIAR VALORES MONETARIOS
                    columnas_monetarias = ['logistics_total', 'aditionals_total', 'declare_value', 
                                        'cxp_amt_due', 'net_received_amount', 'cxp_arancel', 'cxp_iva']
                    
                    for col in columnas_monetarias:
                        if col in df.columns:
                            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                    
                    # Asegurar que quantity existe
                    if 'quantity' in df.columns:
                        df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(1)
                    else:
                        df['quantity'] = 1

                    # Calcular Bodegal para cuentas de Chile y poner 0 para DTPT Group
                    df['Bodegal'] = df['logistic_type'].apply(lambda x: 3.5 if x == 'xd_drop_off' else 0)
                    df.loc[df['account_name'].isin(['5-DETODOPARATODOS', '6-COMPRAFACIL', '7-COMPRA-YA']), 'Bodegal'] = 0

                    # Aplicar cálculos con la nueva función
                    df[['TRM', 'Meli_USD', 'Utilidad_Gss', 'Reversion_Socio', 'Reversion_Gss', 'Perdida', 'Impuesto_Facturacion']] = df.apply(
                        lambda row: pd.Series(calcular_metricas_completas(row, trm_dict)), axis=1
                    )
                    
                    # MOSTRAR MÉTRICAS PRINCIPALES
                    st.markdown("---")
                    col1, col2, col3, col4, col5 = st.columns(5)
                    col1.metric("❌ Total Reembolsos", f"{len(df):,}")
                    col2.metric("💸 Pérdida Total", f"${df['Perdida'].sum():,.2f}")
                    col3.metric("📉 Utilidad GSS Total", f"${df['Utilidad_Gss'].sum():,.2f}")
                    col4.metric("🔄 Reversión Socio", f"${df['Reversion_Socio'].sum():,.2f}")
                    col5.metric("🔄 Reversión GSS", f"${df['Reversion_Gss'].sum():,.2f}")
                    
                    # ANÁLISIS POR CUENTA
                    st.markdown("---")
                    st.subheader("📊 Resumen por Cuenta")
                    
                    resumen = df.groupby('account_name').agg({
                        'order_id': 'count',
                        'Utilidad_Gss': 'sum',
                        'Reversion_Socio': 'sum',
                        'Reversion_Gss': 'sum',
                        'Perdida': 'sum'
                    }).round(2)
                    
                    resumen.columns = ['Cantidad', 'Utilidad GSS Total', 'Reversión Socio', 'Reversión GSS', 'Pérdida Total']
                    resumen = resumen.sort_values('Cantidad', ascending=False)
                    
                    st.dataframe(resumen, use_container_width=True)
                    
                    # ANÁLISIS POR PAÍS
                    st.markdown("---")
                    st.subheader("🌎 Resumen por País")
                    
                    col1, col2, col3 = st.columns(3)
                    
                    # Colombia
                    colombia_accounts = ['1-TODOENCARGO-CO', '5-DETODOPARATODOS', '6-COMPRAFACIL', '7-COMPRA-YA']
                    df_colombia = df[df['account_name'].isin(colombia_accounts)]
                    if not df_colombia.empty:
                        col1.metric(
                            "🇨🇴 Colombia", 
                            f"{len(df_colombia)} reembolsos",
                            f"Pérdida: ${df_colombia['Perdida'].sum():,.2f}"
                        )
                    
                    # Perú
                    df_peru = df[df['account_name'] == '4-MEGA TIENDAS PERUANAS']
                    if not df_peru.empty:
                        col2.metric(
                            "🇵🇪 Perú", 
                            f"{len(df_peru)} reembolsos",
                            f"Pérdida: ${df_peru['Perdida'].sum():,.2f}"
                        )
                    
                    # Chile (sin FABORCARGO)
                    chile_accounts = ['2-MEGATIENDA SPA', '3-VEENDELO']
                    df_chile = df[df['account_name'].isin(chile_accounts)]
                    if not df_chile.empty:
                        col3.metric(
                            "🇨🇱 Chile", 
                            f"{len(df_chile)} reembolsos",
                            f"Pérdida: ${df_chile['Perdida'].sum():,.2f}"
                        )
                    
                    # Mostrar tabla detallada
                    st.markdown("---")
                    st.subheader("📋 Detalle de Reembolsos")
                    
                    # COLUMNAS FIJAS + DINÁMICAS
                    columnas_fijas = [
                        'asignacion', 'order_id', 'refunded_date', 
                        'order_status_meli', 'net_received_amount',
                        'declare_value', 'quantity', 
                        'logistics_total', 'aditionals_total', 
                        'cxp_amt_due', 'Bodegal', 'Impuesto_Facturacion'
                    ]
                    
                    # Columnas dinámicas (se mostrarán en azul)
                    columnas_dinamicas = ['TRM', 'Meli_USD', 'Utilidad_Gss', 'Reversion_Socio', 'Reversion_Gss', 'Perdida']
                    
                    columnas_mostrar = ['account_name'] + columnas_fijas + columnas_dinamicas
                    
                    columnas_disponibles = [col for col in columnas_mostrar if col in df.columns]
                    df_mostrar = df[columnas_disponibles].copy()
                    
                    # Aplicar formato de moneda
                    # Columnas en DÓLARES
                    columnas_dolares = ['declare_value', 'logistics_total', 'aditionals_total', 
                                        'cxp_amt_due', 'Bodegal', 'Impuesto_Facturacion',
                                        'Meli_USD', 'Utilidad_Gss', 'Reversion_Socio', 
                                        'Reversion_Gss', 'Perdida']
                    
                    for col in columnas_dolares:
                        if col in df_mostrar.columns:
                            df_mostrar[col] = df_mostrar[col].apply(lambda x: f"${x:,.2f}" if pd.notnull(x) else "$0.00")
                    
                    # Columna en PESOS (net_received_amount)
                    if 'net_received_amount' in df_mostrar.columns:
                        df_mostrar['net_received_amount'] = df_mostrar['net_received_amount'].apply(
                            lambda x: f"${x:,.0f}" if pd.notnull(x) else "$0"
                        )
                    
                    # Formato para TRM (sin símbolo $)
                    if 'TRM' in df_mostrar.columns:
                        df_mostrar['TRM'] = df_mostrar['TRM'].apply(
                            lambda x: f"{x:,.2f}" if pd.notnull(x) else "0"
                        )
                    
                    # Renombrar columnas dinámicas para indicar que son calculadas
                    rename_dict = {
                        'TRM': '🔵 TRM',
                        'Meli_USD': '🔵 Meli_USD', 
                        'Utilidad_Gss': '🔵 Utilidad_Gss',
                        'Reversion_Socio': '🔵 Reversion_Socio',
                        'Reversion_Gss': '🔵 Reversion_Gss',
                        'Perdida': '🔵 Perdida'
                    }
                    df_mostrar = df_mostrar.rename(columns=rename_dict)
                    
                    # Ordenar por fecha
                    df_mostrar = df_mostrar.sort_values('refunded_date', ascending=False)
                    
                    # Mostrar tabla con formato
                    st.dataframe(df_mostrar, use_container_width=True, height=500)
                    
                    # EXPORTAR
                    st.markdown("---")
                    col1, col2 = st.columns(2)
                    
                    nombre = f'reembolsos_meli_{fecha_inicio.strftime("%Y%m%d")}_{fecha_fin.strftime("%Y%m%d")}'
                    
                    with col1:
                        # Crear copia del dataframe para CSV sin formato
                        df_export = df[columnas_disponibles].copy()
                        csv = df_export.to_csv(index=False, encoding='utf-8-sig')
                        st.download_button(
                            "📥 Descargar CSV",
                            csv,
                            f'{nombre}.csv',
                            'text/csv'
                        )
                    
                    with col2:
                        buffer = io.BytesIO()
                        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                            # Preparar dataframe para Excel - remover timezone de todas las columnas datetime
                            df_excel = df_export.copy()
                            for col in df_excel.columns:
                                if pd.api.types.is_datetime64_any_dtype(df_excel[col]):
                                    if hasattr(df_excel[col].dtype, 'tz') and df_excel[col].dtype.tz is not None:
                                        df_excel[col] = df_excel[col].dt.tz_localize(None)
                            
                            # Exportar a Excel
                            df_excel.to_excel(writer, sheet_name='REEMBOLSOS', index=False)
                            resumen.to_excel(writer, sheet_name='RESUMEN')
                    
                        st.download_button(
                            "📥 Descargar Excel",
                            buffer.getvalue(),
                            f'{nombre}.xlsx',
                            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                        )
                    
                    # Información adicional
                    st.warning(f"""
                    ⚠️ **Resumen de Reembolsos:**
                    - Período: {fecha_inicio} a {fecha_fin}
                    - Filtros: order_status_meli='refunded' Y amz_order_id con valor
                    - Excluye: FABORCARGO
                    - Total reembolsos: {len(df):,}
                    - Pérdida total: ${df['Perdida'].sum():,.2f}
                    - Reversión Socio total: ${df['Reversion_Socio'].sum():,.2f}
                    - Reversión GSS total: ${df['Reversion_Gss'].sum():,.2f}
                    """)
                
                else:
                    st.success(f"✅ No se encontraron reembolsos con amz_order_id para el período {fecha_inicio} a {fecha_fin}")
            
            else:
                st.success("✅ No se encontraron órdenes reembolsadas en la base de datos")
                
        except Exception as e:
            st.error(f"Error al cargar datos: {str(e)}")