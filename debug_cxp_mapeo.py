"""
🔍 DEBUG: Diagnóstico completo del mapeo CXP
Analiza por qué no está funcionando el match entre Ref # y asignacion
"""

import streamlit as st
import pandas as pd
from supabase import create_client
import config
import re

# Page config
st.set_page_config(
    page_title="🔍 Debug CXP Mapeo",
    page_icon="🔍",
    layout="wide"
)

st.title("🔍 Debug: Mapeo CXP - Diagnóstico Completo")
st.caption("Analiza el match entre archivo CXP y base de datos")

# Initialize Supabase
@st.cache_resource
def init_supabase():
    return create_client(config.SUPABASE_URL, config.SUPABASE_KEY)

supabase = init_supabase()

# Funciones auxiliares
def clean_id_aggressive(value):
    """Limpieza agresiva para IDs"""
    if pd.isna(value) or value is None:
        return None
    
    str_value = str(value).strip()
    str_value = str_value.replace("'", "")
    str_value = str_value.replace('"', "")
    str_value = str_value.replace(" ", "")
    str_value = str_value.replace("\t", "")
    str_value = str_value.replace("\n", "")
    
    # No remover puntos aquí para preservar decimales en referencias
    if str_value.endswith('.0'):
        str_value = str_value[:-2]
    
    return str_value if str_value and str_value != 'nan' else None

def calculate_asignacion(account_name, serial_number):
    """Calcula la asignación como en el consolidador"""
    if pd.isna(account_name) or pd.isna(serial_number):
        return None
    
    clean_serial = clean_id_aggressive(serial_number)
    if not clean_serial:
        return None
    
    account_mapping = {
        '1-TODOENCARGO-CO': 'TDC',
        '2-MEGATIENDA SPA': 'MEGA',
        '4-MEGA TIENDAS PERUANAS': 'MGA-PE',
        '5-DETODOPARATODOS': 'DTPT',
        '6-COMPRAFACIL': 'CFA',
        '7-COMPRA-YA': 'CPYA',
        '8-FABORCARGO': 'FBC',
        '3-VEENDELO': 'VEEN'
    }
    
    prefix = account_mapping.get(account_name, '')
    return f"{prefix}{clean_serial}" if prefix else clean_serial

# Interface principal
st.markdown("---")

# Sección 1: Cargar archivo CXP
st.header("1️⃣ Cargar archivo CXP para análisis")

uploaded_file = st.file_uploader(
    "Sube tu archivo CXP", 
    type=['csv', 'xlsx'], 
    help="Archivo con columnas: Ref #, Amt. Due, etc."
)

if uploaded_file:
    # Leer archivo
    try:
        if uploaded_file.name.endswith('.csv'):
            cxp_df = pd.read_csv(uploaded_file)
        else:
            cxp_df = pd.read_excel(uploaded_file)
        
        st.success(f"✅ Archivo CXP cargado: {len(cxp_df)} registros")
        
        # Mostrar columnas del archivo
        st.subheader("📋 Columnas en tu archivo CXP:")
        st.write(list(cxp_df.columns))
        
        # Mostrar preview
        st.subheader("👀 Preview del archivo CXP:")
        st.dataframe(cxp_df.head(10), use_container_width=True)
        
        # Verificar columna Ref #
        if 'Ref #' in cxp_df.columns:
            st.success("✅ Columna 'Ref #' encontrada")
            
            # Analizar valores de Ref #
            ref_values = cxp_df['Ref #'].dropna().unique()
            st.info(f"📊 Valores únicos en 'Ref #': {len(ref_values)}")
            
            # Mostrar ejemplos
            st.subheader("🔍 Ejemplos de valores en 'Ref #':")
            sample_refs = []
            for ref in ref_values[:20]:
                cleaned = clean_id_aggressive(ref)
                sample_refs.append({
                    'Original': ref,
                    'Limpio': cleaned,
                    'Tipo': type(ref).__name__
                })
            
            st.dataframe(pd.DataFrame(sample_refs), use_container_width=True)
            
        else:
            st.error("❌ No se encontró columna 'Ref #' en el archivo")
            st.info("Columnas disponibles:")
            for col in cxp_df.columns:
                if 'ref' in col.lower():
                    st.write(f"  • {col} ← Posible columna de referencia")
        
        st.markdown("---")
        
        # Sección 2: Analizar base de datos
        st.header("2️⃣ Analizar registros en base de datos")
        
        if st.button("🔍 Analizar BD", type="primary"):
            with st.spinner("Analizando base de datos..."):
                
                # Obtener registros de VEENDELO y FABORCARGO
                cxp_accounts = ['3-VEENDELO', '8-FABORCARGO']
                result = supabase.table('consolidated_orders').select(
                    'id, account_name, serial_number, asignacion, order_id'
                ).in_('account_name', cxp_accounts).execute()
                
                if result.data:
                    bd_df = pd.DataFrame(result.data)
                    st.success(f"✅ Registros encontrados en BD: {len(bd_df)}")
                    
                    # Analizar por cuenta
                    st.subheader("📊 Distribución por cuenta:")
                    account_counts = bd_df['account_name'].value_counts()
                    st.dataframe(account_counts)
                    
                    # Calcular asignaciones faltantes
                    missing_asignaciones = 0
                    calculated_asignaciones = []
                    
                    for idx, row in bd_df.iterrows():
                        if pd.isna(row.get('asignacion')) or not row.get('asignacion'):
                            asignacion = calculate_asignacion(
                                row.get('account_name'),
                                row.get('serial_number')
                            )
                            bd_df.loc[idx, 'asignacion'] = asignacion
                            missing_asignaciones += 1
                        
                        asig = bd_df.loc[idx, 'asignacion']
                        if asig and len(calculated_asignaciones) < 20:
                            calculated_asignaciones.append({
                                'Account': row.get('account_name'),
                                'Serial#': row.get('serial_number'),
                                'Asignacion': clean_id_aggressive(asig),
                                'Order ID': row.get('order_id')
                            })
                    
                    if missing_asignaciones > 0:
                        st.warning(f"⚠️ Se calcularon {missing_asignaciones} asignaciones faltantes")
                    
                    st.subheader("🔍 Ejemplos de Asignaciones en BD:")
                    st.dataframe(pd.DataFrame(calculated_asignaciones), use_container_width=True)
                    
                    # Sección 3: Comparar archivo vs BD
                    if 'Ref #' in cxp_df.columns:
                        st.markdown("---")
                        st.header("3️⃣ Análisis de Match: Archivo CXP vs BD")
                        
                        # Obtener valores únicos de ambos lados
                        archivo_refs = set()
                        for ref in cxp_df['Ref #'].dropna():
                            cleaned = clean_id_aggressive(ref)
                            if cleaned:
                                archivo_refs.add(cleaned)
                        
                        bd_asignaciones = set()
                        for asig in bd_df['asignacion'].dropna():
                            cleaned = clean_id_aggressive(asig)
                            if cleaned:
                                bd_asignaciones.add(cleaned)
                        
                        # Calcular matches
                        matches = archivo_refs.intersection(bd_asignaciones)
                        archivo_sin_match = archivo_refs - bd_asignaciones
                        bd_sin_match = bd_asignaciones - archivo_refs
                        
                        # Mostrar estadísticas
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            st.metric("📁 Ref # únicos (archivo)", len(archivo_refs))
                        
                        with col2:
                            st.metric("🗄️ Asignaciones únicas (BD)", len(bd_asignaciones))
                        
                        with col3:
                            st.metric("✅ Matches encontrados", len(matches))
                        
                        with col4:
                            match_percentage = (len(matches) / len(archivo_refs) * 100) if archivo_refs else 0
                            st.metric("📊 % de Match", f"{match_percentage:.1f}%")
                        
                        # Mostrar matches encontrados
                        if matches:
                            st.success(f"✅ Se encontraron {len(matches)} coincidencias")
                            st.subheader("🔍 Ejemplos de matches exitosos:")
                            match_examples = list(matches)[:15]
                            st.write(match_examples)
                        
                        # Mostrar problemas
                        if archivo_sin_match:
                            st.warning(f"⚠️ {len(archivo_sin_match)} Ref # del archivo SIN MATCH en BD")
                            
                            with st.expander("Ver Ref # sin match (primeros 20)"):
                                sin_match_list = list(archivo_sin_match)[:20]
                                st.write(sin_match_list)
                                
                                # Buscar patrones
                                st.subheader("🔍 Análisis de patrones:")
                                patterns = {}
                                for ref in sin_match_list:
                                    if ref:
                                        prefix = ref[:4] if len(ref) >= 4 else ref[:2]
                                        patterns[prefix] = patterns.get(prefix, 0) + 1
                                
                                st.write("Prefijos más comunes sin match:")
                                for prefix, count in sorted(patterns.items(), key=lambda x: x[1], reverse=True):
                                    st.write(f"  • '{prefix}...': {count} referencias")
                        
                        if bd_sin_match:
                            st.info(f"ℹ️ {len(bd_sin_match)} Asignaciones de BD sin archivo correspondiente")
                            
                            with st.expander("Ver Asignaciones BD sin archivo (primeros 20)"):
                                bd_sin_match_list = list(bd_sin_match)[:20]
                                st.write(bd_sin_match_list)
                        
                        # Sección 4: Diagnóstico de errores
                        st.markdown("---")
                        st.header("4️⃣ Diagnóstico de posibles problemas")
                        
                        problemas = []
                        
                        # Problema 1: Formato de referencias
                        if len(matches) < len(archivo_refs) * 0.5:  # Menos del 50% de match
                            problemas.append({
                                'Problema': 'Match bajo (< 50%)',
                                'Descripción': 'Posible problema en formato de referencias',
                                'Solución': 'Revisar formato de Ref # vs asignacion'
                            })
                        
                        # Problema 2: Prefijos incorrectos
                        archivo_prefijos = set()
                        for ref in list(archivo_refs)[:100]:
                            if len(ref) >= 3:
                                prefix = ref[:4]
                                archivo_prefijos.add(prefix)
                        
                        bd_prefijos = set()
                        for asig in list(bd_asignaciones)[:100]:
                            if len(asig) >= 3:
                                prefix = asig[:4]
                                bd_prefijos.add(prefix)
                        
                        prefijos_comunes = archivo_prefijos.intersection(bd_prefijos)
                        
                        if len(prefijos_comunes) < len(archivo_prefijos) * 0.8:
                            problemas.append({
                                'Problema': 'Prefijos no coinciden',
                                'Descripción': f'Archivo: {list(archivo_prefijos)[:5]}, BD: {list(bd_prefijos)[:5]}',
                                'Solución': 'Verificar mapeo de account_name a prefijos'
                            })
                        
                        # Problema 3: Cuentas incorrectas
                        if len(bd_df) == 0:
                            problemas.append({
                                'Problema': 'No hay registros de VEENDELO/FABORCARGO',
                                'Descripción': 'La BD no tiene registros de estas cuentas',
                                'Solución': 'Verificar que existan registros de estas cuentas en la BD'
                            })
                        
                        # Mostrar problemas
                        if problemas:
                            st.error("❌ Problemas detectados:")
                            for i, problema in enumerate(problemas, 1):
                                st.write(f"**{i}. {problema['Problema']}**")
                                st.write(f"   • Descripción: {problema['Descripción']}")
                                st.write(f"   • Solución: {problema['Solución']}")
                                st.write("---")
                        else:
                            st.success("✅ No se detectaron problemas obvios")
                        
                        # Sección 5: Sugerencias de corrección
                        st.markdown("---")
                        st.header("5️⃣ Sugerencias de corrección")
                        
                        if len(matches) > 0:
                            st.success("✅ Hay matches válidos - El problema puede estar en la actualización")
                            
                            sugerencias = [
                                "1. **Verificar permisos de BD**: Asegurar que Supabase permita actualizaciones",
                                "2. **Revisar errores de datos**: Algunos registros pueden tener datos inválidos",
                                "3. **Probar con lote pequeño**: Actualizar solo 10-20 registros primero",
                                "4. **Revisar logs de errores**: Ver detalles específicos de los 760 errores"
                            ]
                            
                            for sug in sugerencias:
                                st.write(sug)
                        else:
                            st.error("❌ No hay matches - Problema en el mapeo")
                            
                            sugerencias_mapeo = [
                                "1. **Revisar formato de Ref #**: Verificar si tiene espacios, caracteres especiales",
                                "2. **Verificar cálculo de asignacion**: Puede estar mal el prefijo",
                                "3. **Revisar Serial# en BD**: Verificar que los Serial# sean correctos",
                                "4. **Mapeo manual**: Usar una muestra pequeña para probar el mapeo"
                            ]
                            
                            for sug in sugerencias_mapeo:
                                st.write(sug)
                        
                else:
                    st.error("❌ No se encontraron registros de VEENDELO o FABORCARGO en la BD")
        
    except Exception as e:
        st.error(f"❌ Error procesando archivo: {str(e)}")
        st.exception(e)

else:
    st.info("📤 Sube tu archivo CXP para comenzar el diagnóstico")

st.markdown("---")
st.info("""
💡 **Cómo usar este diagnóstico:**

1. **Sube tu archivo CXP** con las columnas corregidas
2. **Haz clic en "Analizar BD"** para ver el mapeo
3. **Revisa el % de Match** - debe ser alto (>80%)
4. **Si el match es bajo**, revisa los problemas detectados
5. **Si el match es alto pero hay errores**, el problema está en la actualización
""")