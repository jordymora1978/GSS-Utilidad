"""
Script avanzado para eliminar registros con múltiples opciones
"""

import streamlit as st
import pandas as pd
from supabase import create_client
import config
import time

st.set_page_config(page_title="🗑️ Eliminación Avanzada", layout="wide")

st.title("🗑️ ELIMINACIÓN AVANZADA DE REGISTROS")
st.error("**ADVERTENCIA**: Todas las operaciones son IRREVERSIBLES")

# Conectar a Supabase
supabase = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)

# Tabs para diferentes opciones
tab1, tab2, tab3, tab4 = st.tabs(["Por Cuenta", "Por Columna/Valor", "Por Rango de Fechas", "SQL Personalizado"])

with tab1:
    st.header("🏢 Eliminar por Cuenta")
    
    # Obtener lista de cuentas únicas
    result = supabase.table('consolidated_orders').select('account_name').execute()
    if result.data:
        accounts = list(set([r['account_name'] for r in result.data if r['account_name']]))
        accounts.sort()
        
        selected_accounts = st.multiselect("Selecciona las cuentas:", accounts)
        
        if selected_accounts:
            # Contar registros
            for account in selected_accounts:
                count_result = supabase.table('consolidated_orders').select('id', count='exact').eq('account_name', account).execute()
                st.info(f"• {account}: {count_result.count if hasattr(count_result, 'count') else 'N/A'} registros")
            
            if st.checkbox("Confirmar eliminación por cuenta"):
                if st.button("🗑️ Eliminar", key="del_account"):
                    with st.spinner("Eliminando..."):
                        total = 0
                        for account in selected_accounts:
                            # Eliminar con paginación
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
                            
                            # Eliminar en lotes
                            for i in range(0, len(ids_to_delete), 100):
                                batch = ids_to_delete[i:i+100]
                                for id_del in batch:
                                    try:
                                        supabase.table('consolidated_orders').delete().eq('id', id_del).execute()
                                        total += 1
                                    except:
                                        pass
                            
                            st.success(f"✅ {account}: {len(ids_to_delete)} eliminados")
                        
                        st.success(f"🎯 Total eliminado: {total} registros")

with tab2:
    st.header("📊 Eliminar por Columna y Valor")
    
    # Obtener columnas disponibles
    result = supabase.table('consolidated_orders').select('*').limit(1).execute()
    if result.data:
        columns = list(result.data[0].keys())
        columns.sort()
        
        col1, col2 = st.columns(2)
        
        with col1:
            selected_column = st.selectbox("Selecciona columna:", columns)
        
        with col2:
            operator = st.selectbox("Operador:", 
                ["igual a (=)", "diferente de (!=)", "mayor que (>)", 
                 "menor que (<)", "contiene (LIKE)", "es NULL", "no es NULL"])
        
        if operator not in ["es NULL", "no es NULL"]:
            value = st.text_input(f"Valor para {selected_column}:")
        else:
            value = None
        
        # Vista previa
        if st.button("👁️ Vista previa", key="preview_col"):
            with st.spinner("Obteniendo vista previa..."):
                try:
                    query = supabase.table('consolidated_orders').select('*')
                    
                    if operator == "igual a (=)":
                        query = query.eq(selected_column, value)
                    elif operator == "diferente de (!=)":
                        query = query.neq(selected_column, value)
                    elif operator == "mayor que (>)":
                        query = query.gt(selected_column, value)
                    elif operator == "menor que (<)":
                        query = query.lt(selected_column, value)
                    elif operator == "contiene (LIKE)":
                        query = query.like(selected_column, f"%{value}%")
                    elif operator == "es NULL":
                        query = query.is_(selected_column, 'null')
                    elif operator == "no es NULL":
                        query = query.not_.is_(selected_column, 'null')
                    
                    result = query.limit(10).execute()
                    
                    if result.data:
                        st.write(f"Mostrando primeros 10 de los registros que coinciden:")
                        st.dataframe(pd.DataFrame(result.data))
                    else:
                        st.warning("No se encontraron registros con ese criterio")
                except Exception as e:
                    st.error(f"Error: {e}")
        
        if st.checkbox("Confirmar eliminación por columna/valor"):
            if st.button("🗑️ Eliminar", key="del_col"):
                with st.spinner("Eliminando..."):
                    try:
                        # Obtener IDs a eliminar
                        query = supabase.table('consolidated_orders').select('id')
                        
                        if operator == "igual a (=)":
                            query = query.eq(selected_column, value)
                        elif operator == "diferente de (!=)":
                            query = query.neq(selected_column, value)
                        elif operator == "mayor que (>)":
                            query = query.gt(selected_column, value)
                        elif operator == "menor que (<)":
                            query = query.lt(selected_column, value)
                        elif operator == "contiene (LIKE)":
                            query = query.like(selected_column, f"%{value}%")
                        elif operator == "es NULL":
                            query = query.is_(selected_column, 'null')
                        elif operator == "no es NULL":
                            query = query.not_.is_(selected_column, 'null')
                        
                        # Obtener todos con paginación
                        ids_to_delete = []
                        offset = 0
                        limit = 1000
                        
                        while True:
                            result = query.range(offset, offset + limit - 1).execute()
                            if not result.data:
                                break
                            ids_to_delete.extend([r['id'] for r in result.data])
                            if len(result.data) < limit:
                                break
                            offset += limit
                        
                        # Eliminar
                        deleted = 0
                        for id_del in ids_to_delete:
                            try:
                                supabase.table('consolidated_orders').delete().eq('id', id_del).execute()
                                deleted += 1
                            except:
                                pass
                        
                        st.success(f"✅ Eliminados {deleted} registros")
                    except Exception as e:
                        st.error(f"Error: {e}")

with tab3:
    st.header("📅 Eliminar por Rango de Fechas")
    
    col1, col2 = st.columns(2)
    
    with col1:
        date_column = st.selectbox("Columna de fecha:", 
            ['order_date', 'payment_date', 'created_at', 'updated_at'])
        fecha_inicio = st.date_input("Fecha inicio:")
    
    with col2:
        st.write("&nbsp;")  # Espaciador
        st.write("&nbsp;")  # Espaciador
        fecha_fin = st.date_input("Fecha fin:")
    
    if st.button("👁️ Vista previa fechas", key="preview_date"):
        with st.spinner("Obteniendo vista previa..."):
            try:
                result = supabase.table('consolidated_orders').select('*')\
                    .gte(date_column, str(fecha_inicio))\
                    .lte(date_column, str(fecha_fin))\
                    .limit(10).execute()
                
                if result.data:
                    st.write(f"Mostrando primeros 10 registros entre {fecha_inicio} y {fecha_fin}:")
                    st.dataframe(pd.DataFrame(result.data))
                else:
                    st.warning("No se encontraron registros en ese rango")
            except Exception as e:
                st.error(f"Error: {e}")
    
    if st.checkbox("Confirmar eliminación por fechas"):
        if st.button("🗑️ Eliminar", key="del_date"):
            with st.spinner("Eliminando..."):
                try:
                    # Obtener IDs en el rango
                    ids_to_delete = []
                    offset = 0
                    limit = 1000
                    
                    while True:
                        result = supabase.table('consolidated_orders').select('id')\
                            .gte(date_column, str(fecha_inicio))\
                            .lte(date_column, str(fecha_fin))\
                            .range(offset, offset + limit - 1).execute()
                        
                        if not result.data:
                            break
                        ids_to_delete.extend([r['id'] for r in result.data])
                        if len(result.data) < limit:
                            break
                        offset += limit
                    
                    # Eliminar
                    deleted = 0
                    for id_del in ids_to_delete:
                        try:
                            supabase.table('consolidated_orders').delete().eq('id', id_del).execute()
                            deleted += 1
                        except:
                            pass
                    
                    st.success(f"✅ Eliminados {deleted} registros del {fecha_inicio} al {fecha_fin}")
                except Exception as e:
                    st.error(f"Error: {e}")

with tab4:
    st.header("🔧 Condiciones Múltiples")
    st.info("Combina múltiples condiciones para eliminación precisa")
    
    conditions = []
    num_conditions = st.number_input("Número de condiciones:", 1, 5, 1)
    
    for i in range(num_conditions):
        st.write(f"**Condición {i+1}:**")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            col = st.selectbox(f"Columna {i+1}:", columns if 'columns' in locals() else [], key=f"col_{i}")
        with col2:
            op = st.selectbox(f"Operador {i+1}:", 
                ["=", "!=", ">", "<", "LIKE", "IS NULL", "IS NOT NULL"], key=f"op_{i}")
        with col3:
            if op not in ["IS NULL", "IS NOT NULL"]:
                val = st.text_input(f"Valor {i+1}:", key=f"val_{i}")
            else:
                val = None
        
        if i > 0:
            logic = st.radio(f"Lógica con condición anterior:", ["AND", "OR"], key=f"logic_{i}")
        else:
            logic = None
        
        conditions.append({"column": col, "operator": op, "value": val, "logic": logic})
    
    if st.button("👁️ Vista previa múltiple", key="preview_multi"):
        st.info("Vista previa para condiciones múltiples requiere implementación adicional")
    
    if st.checkbox("Confirmar eliminación con condiciones múltiples"):
        if st.button("🗑️ Eliminar", key="del_multi"):
            st.warning("⚠️ La eliminación con condiciones múltiples requiere implementación adicional de la API")
            st.info("Considera usar las otras pestañas o contacta al administrador para consultas SQL complejas")

st.markdown("---")
st.caption("💡 Tip: Siempre haz un respaldo antes de eliminar datos masivamente")