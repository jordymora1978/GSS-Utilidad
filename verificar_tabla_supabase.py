"""
🔍 Verificar estructura real de la tabla consolidated_orders en Supabase
"""

import streamlit as st
from supabase import create_client
import config
import pandas as pd

# Conectar a Supabase
supabase = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)

st.title("🔍 Verificar Estructura de Tabla Supabase")

try:
    # Obtener una muestra de registros para ver las columnas
    result = supabase.table('consolidated_orders').select('*').limit(1).execute()
    
    if result.data:
        # Convertir a DataFrame para ver la estructura
        df = pd.DataFrame(result.data)
        
        st.success(f"✅ Conexión exitosa a Supabase")
        
        st.subheader("📋 Columnas en la tabla consolidated_orders:")
        columnas = list(df.columns)
        columnas.sort()
        
        for i, col in enumerate(columnas, 1):
            st.write(f"{i:2d}. {col}")
        
        st.subheader("🔍 ¿Columnas relacionadas con delivery/dest?")
        delivery_cols = [col for col in columnas if 'delivery' in col.lower() or 'dest' in col.lower()]
        if delivery_cols:
            for col in delivery_cols:
                st.write(f"✅ {col}")
        else:
            st.warning("❌ No se encontraron columnas con 'delivery' o 'dest'")
        
        st.subheader("🔍 ¿Columnas relacionadas con declare/goods?")
        declare_cols = [col for col in columnas if 'declare' in col.lower() or 'goods' in col.lower() or 'value' in col.lower()]
        if declare_cols:
            for col in declare_cols:
                st.write(f"✅ {col}")
        else:
            st.warning("❌ No se encontraron columnas con 'declare', 'goods' o 'value'")
        
        # Contar registros totales
        st.subheader("📊 Estadísticas de la tabla:")
        count_result = supabase.table('consolidated_orders').select('*', count='exact', head=True).execute()
        total_count = count_result.count if hasattr(count_result, 'count') else 0
        st.metric("Total registros", f"{total_count:,}")
        
        # Contar por account_name
        accounts_result = supabase.table('consolidated_orders').select('account_name').execute()
        if accounts_result.data:
            accounts_df = pd.DataFrame(accounts_result.data)
            account_counts = accounts_df['account_name'].value_counts()
            
            st.subheader("📈 Registros por cuenta:")
            for account, count in account_counts.head(10).items():
                st.write(f"• {account}: {count:,}")
        
        # Verificar registros de las cuentas problemáticas
        st.subheader("🎯 Registros de cuentas CXP:")
        cxp_accounts = ['3-VEENDELO', '8-FABORCARGO', '2-MEGATIENDA SPA']
        
        for account in cxp_accounts:
            count_result = supabase.table('consolidated_orders').select('*', count='exact', head=True).eq('account_name', account).execute()
            account_count = count_result.count if hasattr(count_result, 'count') else 0
            st.write(f"• {account}: {account_count:,} registros")
        
    else:
        st.error("❌ No se pudieron obtener datos de la tabla")
        
except Exception as e:
    st.error(f"❌ Error conectando a Supabase: {str(e)}")
    st.exception(e)