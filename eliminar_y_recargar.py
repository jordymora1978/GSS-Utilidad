"""
⚠️ Script para ELIMINAR y RECARGAR registros CXP
CUIDADO: Esto eliminará TODOS los registros de las cuentas seleccionadas
"""

import streamlit as st
import pandas as pd
from supabase import create_client
import config
import time

st.set_page_config(page_title="⚠️ Eliminar y Recargar", layout="wide")

st.title("⚠️ ELIMINAR Y RECARGAR REGISTROS CXP")
st.error("**ADVERTENCIA**: Esta operación es IRREVERSIBLE")

# Conectar a Supabase
supabase = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)

# Paso 1: Contar registros actuales
st.header("📊 Estado actual")

cxp_accounts = ['3-VEENDELO', '8-FABORCARGO', '2-MEGATIENDA SPA']

for account in cxp_accounts:
    # Contar TODOS los registros usando paginación
    total_count = 0
    offset = 0
    limit = 1000
    
    while True:
        result = supabase.table('consolidated_orders').select('id').eq('account_name', account).range(offset, offset + limit - 1).execute()
        
        if not result.data:
            break
            
        total_count += len(result.data)
        
        if len(result.data) < limit:
            break
            
        offset += limit
    
    st.write(f"• {account}: {total_count} registros")

st.markdown("---")

# Opción de eliminar
st.header("🗑️ Paso 1: Eliminar registros (OPCIONAL)")

if st.checkbox("⚠️ Quiero eliminar TODOS los registros de estas cuentas"):
    st.error("¿Estás SEGURO? Esto eliminará TODOS los registros")
    
    confirm_text = st.text_input("Escribe 'ELIMINAR TODO' para confirmar:")
    
    if confirm_text == "ELIMINAR TODO":
        if st.button("🗑️ ELIMINAR AHORA", type="primary"):
            with st.spinner("Eliminando registros..."):
                total_deleted = 0
                
                for account in cxp_accounts:
                    # Obtener TODOS los IDs usando paginación
                    ids_to_delete = []
                    offset = 0
                    limit = 1000
                    
                    while True:
                        result = supabase.table('consolidated_orders').select('id').eq('account_name', account).range(offset, offset + limit - 1).execute()
                        
                        if not result.data:
                            break
                            
                        ids_to_delete.extend([r['id'] for r in result.data])
                        
                        if len(result.data) < limit:
                            break
                            
                        offset += limit
                    
                    if ids_to_delete:
                        # Eliminar en lotes
                        batch_size = 100
                        for i in range(0, len(ids_to_delete), batch_size):
                            batch = ids_to_delete[i:i+batch_size]
                            for id_to_del in batch:
                                try:
                                    supabase.table('consolidated_orders').delete().eq('id', id_to_del).execute()
                                    total_deleted += 1
                                except:
                                    pass
                            time.sleep(0.1)  # Evitar saturar API
                        
                        st.success(f"✅ {account}: {len(ids_to_delete)} registros eliminados")
                
                st.success(f"✅ TOTAL ELIMINADOS: {total_deleted} registros")
                st.balloons()

st.markdown("---")

# Paso 2: Cargar nuevos datos
st.header("📥 Paso 2: Cargar archivo con datos correctos")

st.info("""
Sube un archivo CSV/Excel con TODOS los registros y valores correctos.
El archivo debe tener las columnas necesarias para crear registros completos.
""")

uploaded_file = st.file_uploader("Sube el archivo con datos correctos", type=['csv', 'xlsx'])

if uploaded_file:
    # Cargar archivo
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)
    
    st.success(f"✅ Archivo cargado: {len(df)} registros")
    st.dataframe(df.head(10))
    
    # Aquí implementarías la lógica de carga según tu estructura
    st.info("Implementa aquí la lógica de carga según tu estructura de datos")