"""
Eliminación directa usando consultas SQL personalizadas
ADVERTENCIA: Este script es muy potente, úsalo con cuidado
"""

import streamlit as st
from supabase import create_client
import config
import pandas as pd

st.set_page_config(page_title="⚡ SQL Directo", layout="wide")

st.title("⚡ ELIMINACIÓN SQL DIRECTA")
st.error("⚠️ **PELIGRO**: Este modo permite eliminar con SQL directo. ¡SIN VALIDACIONES!")

# Conectar a Supabase
supabase = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)

st.header("📝 Ejemplos de consultas SQL")

with st.expander("Ver ejemplos de eliminación"):
    st.code("""
# Eliminar por cuenta específica
DELETE FROM consolidated_orders WHERE account_name = '3-VEENDELO';

# Eliminar por múltiples cuentas
DELETE FROM consolidated_orders 
WHERE account_name IN ('3-VEENDELO', '8-FABORCARGO', '2-MEGATIENDA SPA');

# Eliminar por valor de columna
DELETE FROM consolidated_orders WHERE total_amount > 1000000;
DELETE FROM consolidated_orders WHERE status = 'cancelled';

# Eliminar por rango de fechas
DELETE FROM consolidated_orders 
WHERE order_date BETWEEN '2024-01-01' AND '2024-12-31';

# Eliminar con múltiples condiciones
DELETE FROM consolidated_orders 
WHERE account_name = '3-VEENDELO' 
  AND total_amount > 500000 
  AND order_date < '2024-01-01';

# Eliminar registros NULL
DELETE FROM consolidated_orders WHERE payment_date IS NULL;

# Eliminar con LIKE (contiene texto)
DELETE FROM consolidated_orders WHERE description LIKE '%error%';
DELETE FROM consolidated_orders WHERE customer_name LIKE 'TEST%';

# Eliminar excepto algunos
DELETE FROM consolidated_orders 
WHERE account_name = '3-VEENDELO' 
  AND id NOT IN (SELECT id FROM consolidated_orders 
                 WHERE account_name = '3-VEENDELO' 
                 ORDER BY order_date DESC LIMIT 100);
    """, language="sql")

st.markdown("---")

# Modo interactivo
st.header("🎯 Ejecutor SQL")

# Primero, mostrar estructura de la tabla
if st.checkbox("📊 Ver estructura de la tabla"):
    result = supabase.table('consolidated_orders').select('*').limit(1).execute()
    if result.data:
        st.write("**Columnas disponibles:**")
        cols = list(result.data[0].keys())
        col_info = pd.DataFrame({
            'Columna': cols,
            'Tipo': ['text' if isinstance(result.data[0][col], str) else 
                    'number' if isinstance(result.data[0][col], (int, float)) else 
                    'date' if 'date' in col else 'other' 
                    for col in cols]
        })
        st.dataframe(col_info)

# Constructor de consultas
st.subheader("🔨 Constructor de Consultas")

col1, col2 = st.columns(2)

with col1:
    where_column = st.text_input("Columna WHERE:", placeholder="account_name")
    where_operator = st.selectbox("Operador:", 
        ["=", "!=", ">", "<", ">=", "<=", "LIKE", "IN", "NOT IN", "IS NULL", "IS NOT NULL"])

with col2:
    if where_operator not in ["IS NULL", "IS NOT NULL"]:
        where_value = st.text_area("Valor(es):", 
            placeholder="'3-VEENDELO' o ('valor1', 'valor2') para IN",
            height=100)
    else:
        where_value = ""

# Condiciones adicionales
if st.checkbox("➕ Agregar más condiciones"):
    and_or = st.radio("Lógica:", ["AND", "OR"])
    
    col3, col4 = st.columns(2)
    with col3:
        where2_column = st.text_input("Segunda columna:", placeholder="total_amount")
        where2_operator = st.selectbox("Operador 2:", 
            ["=", "!=", ">", "<", ">=", "<=", "LIKE", "IN", "NOT IN", "IS NULL", "IS NOT NULL"],
            key="op2")
    
    with col4:
        if where2_operator not in ["IS NULL", "IS NOT NULL"]:
            where2_value = st.text_input("Valor 2:", placeholder="1000000")
        else:
            where2_value = ""

# Generar consulta
if st.button("🔧 Generar consulta DELETE"):
    if where_column:
        query = f"DELETE FROM consolidated_orders WHERE {where_column} "
        
        if where_operator in ["IS NULL", "IS NOT NULL"]:
            query += where_operator
        elif where_operator in ["IN", "NOT IN"]:
            query += f"{where_operator} {where_value}"
        elif where_operator == "LIKE":
            query += f"LIKE {where_value}"
        else:
            query += f"{where_operator} {where_value}"
        
        if st.session_state.get('add_condition') and 'where2_column' in locals():
            if where2_column:
                query += f" {and_or} {where2_column} "
                if where2_operator in ["IS NULL", "IS NOT NULL"]:
                    query += where2_operator
                elif where2_operator in ["IN", "NOT IN"]:
                    query += f"{where2_operator} {where2_value}"
                elif where2_operator == "LIKE":
                    query += f"LIKE {where2_value}"
                else:
                    query += f"{where2_operator} {where2_value}"
        
        query += ";"
        
        st.code(query, language="sql")
        st.session_state['generated_query'] = query

st.markdown("---")

# Ejecutor manual
st.subheader("⚠️ Ejecutor Manual Directo")
st.warning("**ÚLTIMA ADVERTENCIA**: Lo que escribas aquí se ejecutará DIRECTAMENTE. No hay vuelta atrás.")

sql_query = st.text_area("Escribe tu consulta SQL DELETE:", 
    value=st.session_state.get('generated_query', ''),
    height=150,
    placeholder="DELETE FROM consolidated_orders WHERE ...")

# Validación de seguridad básica
if sql_query:
    # Verificar que sea una consulta DELETE
    if not sql_query.strip().upper().startswith('DELETE'):
        st.error("❌ Solo se permiten consultas DELETE")
    else:
        # Mostrar vista previa con SELECT
        if st.button("👁️ Vista previa (primeros 10)"):
            try:
                # Convertir DELETE a SELECT para preview
                preview_query = sql_query.replace('DELETE', 'SELECT *', 1)
                preview_query = preview_query.rstrip(';') + ' LIMIT 10;'
                
                st.info(f"Vista previa con: {preview_query}")
                
                # Nota: Supabase Python client no soporta SQL raw directamente
                # Necesitarías usar PostgREST o la API directa
                st.warning("⚠️ Vista previa requiere acceso SQL directo no disponible en el cliente Python de Supabase")
                st.info("Usa las otras herramientas para vista previa o ejecuta con cuidado")
                
            except Exception as e:
                st.error(f"Error en vista previa: {e}")
        
        # Confirmación final
        st.error("🚨 ZONA DE PELIGRO 🚨")
        confirm = st.text_input("Escribe 'ELIMINAR PERMANENTEMENTE' para confirmar:")
        
        if confirm == "ELIMINAR PERMANENTEMENTE":
            if st.button("💀 EJECUTAR DELETE", type="primary"):
                st.error("⚠️ Ejecución SQL directa requiere:")
                st.code("""
# Opción 1: Usar Supabase Dashboard
# Ve a: https://app.supabase.com/project/[tu-proyecto]/editor
# Ejecuta la consulta en el SQL Editor

# Opción 2: Usar PostgreSQL directamente
import psycopg2
conn = psycopg2.connect(database_url)
cursor = conn.cursor()
cursor.execute(sql_query)
conn.commit()

# Opción 3: Usar Supabase RPC (si tienes una función)
supabase.rpc('execute_delete', {'query': sql_query}).execute()
                """, language="python")
                
                st.info("El cliente Python de Supabase no soporta SQL raw por seguridad. Usa el Dashboard de Supabase o las herramientas integradas.")

st.markdown("---")
st.caption("💡 Para eliminaciones complejas, considera usar el Dashboard de Supabase directamente")