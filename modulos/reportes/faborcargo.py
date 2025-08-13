"""
Reporte FABORCARGO
Proveedor: Chilexpress | País: Chile
Cálculo especial basado en peso
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

# TABLA DE PESO FABORCARGO - ANEXO A
TABLA_PESO_LOCAL = [
    {'desde': 0.01, 'hasta': 0.50, 'gss_logistica': 24.01},
    {'desde': 0.51, 'hasta': 1.00, 'gss_logistica': 33.09},
    {'desde': 1.01, 'hasta': 1.50, 'gss_logistica': 42.17},
    {'desde': 1.51, 'hasta': 2.00, 'gss_logistica': 51.25},
    {'desde': 2.01, 'hasta': 2.50, 'gss_logistica': 61.94},
    {'desde': 2.51, 'hasta': 3.00, 'gss_logistica': 71.02},
    {'desde': 3.01, 'hasta': 3.50, 'gss_logistica': 80.91},
    {'desde': 3.51, 'hasta': 4.00, 'gss_logistica': 89.99},
    {'desde': 4.01, 'hasta': 4.50, 'gss_logistica': 99.87},
    {'desde': 4.51, 'hasta': 5.00, 'gss_logistica': 108.95},
    {'desde': 5.01, 'hasta': 5.50, 'gss_logistica': 117.19},
    {'desde': 5.51, 'hasta': 6.00, 'gss_logistica': 126.12},
    {'desde': 6.01, 'hasta': 6.50, 'gss_logistica': 135.85},
    {'desde': 6.51, 'hasta': 7.00, 'gss_logistica': 144.78},
    {'desde': 7.01, 'hasta': 7.50, 'gss_logistica': 154.52},
    {'desde': 7.51, 'hasta': 8.00, 'gss_logistica': 163.75},
    {'desde': 8.01, 'hasta': 8.50, 'gss_logistica': 173.18},
    {'desde': 8.51, 'hasta': 9.00, 'gss_logistica': 182.11},
    {'desde': 9.01, 'hasta': 9.50, 'gss_logistica': 191.85},
    {'desde': 9.51, 'hasta': 10.00, 'gss_logistica': 200.78},
    {'desde': 10.01, 'hasta': 10.50, 'gss_logistica': 207.36},
    {'desde': 10.51, 'hasta': 11.00, 'gss_logistica': 216.14},
    {'desde': 11.01, 'hasta': 11.50, 'gss_logistica': 225.73},
    {'desde': 11.51, 'hasta': 12.00, 'gss_logistica': 234.51},
    {'desde': 12.01, 'hasta': 12.50, 'gss_logistica': 244.09},
    {'desde': 12.51, 'hasta': 13.00, 'gss_logistica': 252.87},
    {'desde': 13.01, 'hasta': 13.50, 'gss_logistica': 262.46},
    {'desde': 13.51, 'hasta': 14.00, 'gss_logistica': 271.24},
    {'desde': 14.01, 'hasta': 14.50, 'gss_logistica': 280.82},
    {'desde': 14.51, 'hasta': 15.00, 'gss_logistica': 289.60},
    {'desde': 15.01, 'hasta': 15.50, 'gss_logistica': 294.54},
    {'desde': 15.51, 'hasta': 16.00, 'gss_logistica': 303.17},
    {'desde': 16.01, 'hasta': 16.50, 'gss_logistica': 312.60},
    {'desde': 16.51, 'hasta': 17.00, 'gss_logistica': 321.23},
    {'desde': 17.01, 'hasta': 17.50, 'gss_logistica': 330.67},
    {'desde': 17.51, 'hasta': 18.00, 'gss_logistica': 339.30},
    {'desde': 18.01, 'hasta': 18.50, 'gss_logistica': 348.73},
    {'desde': 18.51, 'hasta': 19.00, 'gss_logistica': 357.36},
    {'desde': 19.01, 'hasta': 19.50, 'gss_logistica': 366.80},
    {'desde': 19.51, 'hasta': 20.00, 'gss_logistica': 373.72}
]

def generar_reporte(fecha_inicio=None, fecha_fin=None):
    """
    Genera el reporte de FABORCARGO
    """
    
    # Si no se proporcionan fechas, usar las del mes actual
    if fecha_inicio is None or fecha_fin is None:
        hoy = datetime.now().date()
        fecha_inicio = hoy.replace(day=1)
        ultimo_dia = calendar.monthrange(hoy.year, hoy.month)[1]
        fecha_fin = hoy.replace(day=ultimo_dia)
    
    # Mostrar título del reporte específico
    st.title("📦 Reporte: FaborCargo")
    
    st.caption("Proveedor: Chilexpress | País: Chile | Campo: cxp_date")
    st.caption("⚖️ Cálculo basado en peso con tabla GSS Logística")

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

    # Usar tabla de config si existe, sino usar la local
    if hasattr(config, 'TABLA_PESO_FABORCARGO'):
        TABLA_PESO = config.TABLA_PESO_FABORCARGO
    else:
        TABLA_PESO = TABLA_PESO_LOCAL
        st.warning("⚠️ Usando tabla de peso local. Verifica que TABLA_PESO_FABORCARGO esté en config.py")

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
            # Query directa con filtro de fecha (FABORCARGO usa cxp_date como Chile)
            query = supabase.table('consolidated_orders').select('*')
            query = query.eq('account_name', '8-FABORCARGO')
            query = query.gte('cxp_date', str(fecha_inicio))
            query = query.lte('cxp_date', str(fecha_fin))
            result = query.execute()
            
            all_records = result.data
            
            if all_records:
                df = pd.DataFrame(all_records)
                
                # Usar cxp_date (Chilexpress) - ya viene filtrada por la query
                df['cxp_date'] = pd.to_datetime(df['cxp_date'], errors='coerce')
                
                if not df.empty:
                    # CALCULAR COLUMNAS PARA FABORCARGO
                    
                    # Limpiar valores monetarios
                    columnas_monetarias = ['declare_value', 'net_received_amount', 
                                          'cxp_amt_due', 'cxp_arancel', 'cxp_iva', 'logistic_weight_lbs']
                    
                    for col in columnas_monetarias:
                        if col in df.columns:
                            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                    
                    # Asegurar que quantity existe
                    if 'quantity' in df.columns:
                        df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(1)
                    else:
                        df['quantity'] = 1
                    
                    # TRM Chile
                    df['TRM_Chile'] = trm_dict.get('chile', 850.0)
                    
                    # Bodegal (3.5 USD si logistic_type es xd_drop_off)
                    if 'logistic_type' in df.columns:
                        df['Bodegal'] = df['logistic_type'].apply(lambda x: 3.5 if x == 'xd_drop_off' else 0)
                    else:
                        df['Bodegal'] = 0
                    
                    # NOTA: FABORCARGO NO MANEJA Socio_cuenta
                    
                    # CÁLCULO ESPECIAL DE PESO
                    # Convertir libras a kilos y redondear a 0.5
                    def redondear_05(valor):
                        return math.ceil(valor * 2) / 2
                    
                    if 'logistic_weight_lbs' in df.columns:
                        df['logistic_weight_kgs'] = (df['logistic_weight_lbs'] / 2.205).apply(redondear_05)
                    else:
                        df['logistic_weight_kgs'] = 0
                    
                    # Buscar GSS Logística usando la tabla
                    def buscar_gss_logistica(peso):
                        # Si el peso es 0 o negativo, retornar 0
                        if peso <= 0:
                            return 0
                        
                        # Buscar en la tabla
                        for rango in TABLA_PESO:
                            if rango['desde'] <= peso <= rango['hasta']:
                                return rango['gss_logistica']
                        
                        # Si el peso es mayor al último rango, usar el último valor
                        if peso > TABLA_PESO[-1]['hasta']:
                            return TABLA_PESO[-1]['gss_logistica']
                        
                        return 0
                    
                    df['Gss_Logistica'] = df['logistic_weight_kgs'].apply(buscar_gss_logistica)
                    
                    # CALCULAR UTILIDAD FABORCARGO (fórmula especial)
                    def calc_utilidad_fabor(row):
                        # FABORCARGO siempre usa la misma fórmula
                        # Utilidad Gss = Gss_Logistica + cxp_arancel + cxp_iva - cxp_amt_due
                        if row['cxp_amt_due'] > 0:
                            return (row['Gss_Logistica'] + 
                                   row['cxp_arancel'] + 
                                   row['cxp_iva'] - 
                                   row['cxp_amt_due'])
                        return 0
                    
                    df['Utilidad_Gss'] = df.apply(calc_utilidad_fabor, axis=1)
                    
                    # MOSTRAR MÉTRICAS COMPACTAS
                    total_registros = len(df)
                    utilidad_total = df['Utilidad_Gss'].sum()
                    aprobadas = (df['order_status_meli'] == 'approved').sum()
                    refunded = (df['order_status_meli'] == 'refunded').sum()
                    trm_chile = trm_dict.get('chile', 850)
                    peso_promedio = df['logistic_weight_kgs'].mean()
                    total_bodegal = df['Bodegal'].sum()
                    gss_logistica_promedio = df['Gss_Logistica'].mean()

                    # MOSTRAR MÉTRICAS
                    st.markdown("---")
                    col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
                    col1.metric("📊 Total", total_registros)
                    col2.metric("💰 Utilidad", f"${utilidad_total:,.2f}")
                    col3.metric("✅ Aprobadas", aprobadas)
                    col4.metric("❌ Refunded", refunded)
                    col5.metric("🇨🇱 TRM Chile", f"${trm_chile:,.0f}")
                    col6.metric("⚖️ Peso Prom.", f"{peso_promedio:.2f} kg")
                    col7.metric("📦 Bodegal", f"${total_bodegal:,.2f}")
                    
                    # MOSTRAR TABLA
                    st.markdown("---")
                    st.subheader("📋 Detalle del Reporte")
                    
                    # Columnas a mostrar (sin Socio_cuenta)
                    columnas_mostrar = [
                        'cxp_date', 'asignacion', 'order_status_meli', 
                        'net_received_amount', 'cxp_ref_number', 'cxp_consignee',
                        'cxp_arancel', 'cxp_iva', 'cxp_amt_due',
                        'declare_value', 'quantity', 'logistic_weight_lbs',
                        'logistic_weight_kgs', 'TRM_Chile', 'Bodegal', 
                        'Gss_Logistica', 'Utilidad_Gss'
                    ]
                    
                    columnas_disponibles = [col for col in columnas_mostrar if col in df.columns]
                    df_mostrar = df[columnas_disponibles].copy()
                    
                    # Formatear columnas monetarias a dólares
                    columnas_dolares = ['cxp_arancel', 'cxp_iva', 'cxp_amt_due', 
                                       'declare_value', 'net_received_amount']
                    for col in columnas_dolares:
                        if col in df_mostrar.columns:
                            df_mostrar[col] = df_mostrar[col].apply(lambda x: f"${x:,.2f}" if pd.notna(x) else "$0.00")
                    
                    # Formatear columnas calculadas (con emoji)
                    if 'Bodegal' in df_mostrar.columns:
                        df_mostrar['🔵 Bodegal'] = df_mostrar['Bodegal'].apply(lambda x: f"${x:,.2f}")
                        df_mostrar.drop('Bodegal', axis=1, inplace=True)
                    
                    if 'Gss_Logistica' in df_mostrar.columns:
                        df_mostrar['🔵 Gss_Logistica'] = df_mostrar['Gss_Logistica'].apply(lambda x: f"${x:,.2f}")
                        df_mostrar.drop('Gss_Logistica', axis=1, inplace=True)
                    
                    if 'Utilidad_Gss' in df_mostrar.columns:
                        df_mostrar['🔵 Utilidad_Gss'] = df_mostrar['Utilidad_Gss'].apply(lambda x: f"${x:,.2f}")
                        df_mostrar.drop('Utilidad_Gss', axis=1, inplace=True)
                    
                    if 'TRM_Chile' in df_mostrar.columns:
                        df_mostrar['🇨🇱 TRM_Chile'] = df_mostrar['TRM_Chile'].apply(lambda x: f"${x:,.0f}")
                        df_mostrar.drop('TRM_Chile', axis=1, inplace=True)
                    
                    # Formatear peso
                    if 'logistic_weight_kgs' in df_mostrar.columns:
                        df_mostrar['logistic_weight_kgs'] = df_mostrar['logistic_weight_kgs'].apply(lambda x: f"{x:.2f} kg")
                    
                    if 'logistic_weight_lbs' in df_mostrar.columns:
                        df_mostrar['logistic_weight_lbs'] = df_mostrar['logistic_weight_lbs'].apply(lambda x: f"{x:.2f} lbs")
                    
                    # Mostrar dataframe
                    st.dataframe(df_mostrar, use_container_width=True, height=500)
                    
                    # EXPORTAR
                    st.markdown("---")
                    col1, col2 = st.columns(2)
                    
                    nombre = f'faborcargo_{fecha_inicio.strftime("%Y%m%d")}_{fecha_fin.strftime("%Y%m%d")}'
                    
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
                            df_mostrar.to_excel(writer, sheet_name='FABORCARGO', index=False)
                        
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
                    - TRM Chile: ${trm_dict.get('chile', 850):,.0f}
                    - Peso promedio: {df['logistic_weight_kgs'].mean():.2f} kg
                    - **Fórmula especial FABORCARGO:**
                      ```
                      Utilidad = Gss_Logistica + cxp_arancel + cxp_iva - cxp_amt_due
                      ```
                    - GSS Logística según tabla de peso (40 rangos)
                    - Peso en kg = (peso_lbs / 2.205) redondeado a 0.5
                    - ⚠️ Esta cuenta NO maneja Socio_cuenta
                    """)
                
                else:
                    st.warning(f"No se encontraron datos para el período {fecha_inicio} a {fecha_fin}")
                
            else:
                st.warning("No se encontraron registros para FABORCARGO")
                
        except Exception as e:
            st.error(f"Error al cargar datos: {str(e)}")