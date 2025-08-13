"""
🔄 Script para actualizar TODOS los registros CXP usando diferentes estrategias de matching
"""

import streamlit as st
import pandas as pd
from supabase import create_client
import config
import re

st.set_page_config(page_title="🔄 Actualizar TODOS CXP", layout="wide")

st.title("🔄 Actualización COMPLETA de CXP")
st.caption("Diferentes estrategias para actualizar TODOS los registros")

# Conectar a Supabase
supabase = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)

# Función para limpiar IDs
def clean_id(value):
    if pd.isna(value) or value is None:
        return None
    str_value = str(value).strip()
    str_value = str_value.replace("'", "").replace('"', "").replace(" ", "")
    if str_value.endswith('.0'):
        str_value = str_value[:-2]
    return str_value if str_value and str_value != 'nan' else None

# Función para extraer número de referencia
def extract_number(ref):
    """Extrae solo el número de una referencia como VEEN5390 -> 5390"""
    if not ref:
        return None
    # Buscar números en la cadena
    numbers = re.findall(r'\d+', str(ref))
    return numbers[0] if numbers else None

st.header("📁 Cargar archivo CXP")

uploaded_file = st.file_uploader(
    "Sube tu archivo CXP con valores correctos", 
    type=['csv', 'xlsx']
)

if uploaded_file:
    # Cargar archivo
    if uploaded_file.name.endswith('.csv'):
        cxp_df = pd.read_csv(uploaded_file)
    else:
        cxp_df = pd.read_excel(uploaded_file)
    
    st.success(f"✅ Archivo cargado: {len(cxp_df)} registros")
    
    # Mostrar columnas
    st.write("Columnas detectadas:", list(cxp_df.columns))
    
    # Crear diferentes índices para matching
    st.header("🔍 Preparando estrategias de matching")
    
    # Índice 1: Por Ref# completo
    cxp_by_ref = {}
    # Índice 2: Por número solo
    cxp_by_number = {}
    # Índice 3: Por diferentes prefijos
    cxp_by_veen = {}
    cxp_by_fbc = {}
    cxp_by_mega = {}
    
    for _, row in cxp_df.iterrows():
        ref = clean_id(row.get('Ref #', row.get('ref_number', '')))
        if ref:
            # Índice completo
            cxp_by_ref[ref] = row
            
            # Índice por número
            number = extract_number(ref)
            if number:
                cxp_by_number[number] = row
                
                # Índices por prefijo + número
                if ref.startswith('VEEN'):
                    cxp_by_veen[number] = row
                elif ref.startswith('FBC'):
                    cxp_by_fbc[number] = row
                elif ref.startswith('MEGA'):
                    cxp_by_mega[number] = row
    
    st.write(f"📊 Referencias indexadas:")
    st.write(f"- Total: {len(cxp_by_ref)}")
    st.write(f"- VEEN: {len(cxp_by_veen)}")
    st.write(f"- FBC: {len(cxp_by_fbc)}")
    st.write(f"- MEGA: {len(cxp_by_mega)}")
    
    # Obtener TODOS los registros de BD
    st.header("📥 Obteniendo registros de la base de datos")
    
    cxp_accounts = ['3-VEENDELO', '8-FABORCARGO', '2-MEGATIENDA SPA']
    all_records = []
    
    for account in cxp_accounts:
        st.write(f"Obteniendo {account}...")
        page = 0
        while True:
            offset = page * 1000
            result = supabase.table('consolidated_orders').select(
                'id, account_name, serial_number, asignacion, order_id, cxp_amt_due'
            ).eq('account_name', account).range(offset, offset + 999).execute()
            
            if not result.data:
                break
            all_records.extend(result.data)
            if len(result.data) < 1000:
                break
            page += 1
        
        st.write(f"✅ {account}: {len([r for r in all_records if r['account_name'] == account])} registros")
    
    st.success(f"📊 Total registros en BD: {len(all_records)}")
    
    # Analizar y preparar actualizaciones
    st.header("🔄 Matching y preparación de actualizaciones")
    
    updates_to_perform = []
    matched_by_asignacion = 0
    matched_by_serial = 0
    matched_by_order = 0
    no_match = 0
    
    for record in all_records:
        db_id = record['id']
        account = record['account_name']
        serial_number = clean_id(record.get('serial_number'))
        asignacion = clean_id(record.get('asignacion'))
        order_id = clean_id(record.get('order_id'))
        current_amt = record.get('cxp_amt_due')
        
        matched = False
        cxp_row = None
        match_type = ""
        
        # Estrategia 1: Match por asignacion
        if asignacion and asignacion in cxp_by_ref:
            cxp_row = cxp_by_ref[asignacion]
            matched_by_asignacion += 1
            match_type = "asignacion"
            matched = True
        
        # Estrategia 2: Match por serial_number
        if not matched and serial_number:
            # Intentar match directo por número
            if serial_number in cxp_by_number:
                cxp_row = cxp_by_number[serial_number]
                matched_by_serial += 1
                match_type = "serial"
                matched = True
            # Intentar con prefijo según cuenta
            elif account == '3-VEENDELO' and serial_number in cxp_by_veen:
                cxp_row = cxp_by_veen[serial_number]
                matched_by_serial += 1
                match_type = "serial+VEEN"
                matched = True
            elif account == '8-FABORCARGO' and serial_number in cxp_by_fbc:
                cxp_row = cxp_by_fbc[serial_number]
                matched_by_serial += 1
                match_type = "serial+FBC"
                matched = True
            elif account == '2-MEGATIENDA SPA' and serial_number in cxp_by_mega:
                cxp_row = cxp_by_mega[serial_number]
                matched_by_serial += 1
                match_type = "serial+MEGA"
                matched = True
        
        # Estrategia 3: Match por order_id
        if not matched and order_id and order_id in cxp_by_ref:
            cxp_row = cxp_by_ref[order_id]
            matched_by_order += 1
            match_type = "order_id"
            matched = True
        
        if matched and cxp_row is not None:
            # Preparar actualización
            update_data = {
                'id': db_id,
                'match_type': match_type,
                'old_amt': current_amt
            }
            
            # Obtener valores del archivo
            amt_due = None
            for col in ['Amt. Due', 'amt_due', 'Amount Due']:
                if col in cxp_row:
                    val = str(cxp_row[col]).replace('$', '').replace(',', '').strip()
                    try:
                        amt_due = float(val)
                        break
                    except:
                        pass
            
            dest_delivery = None
            for col in ['Dest. Delivery', 'dest_delivery', 'Destination Delivery']:
                if col in cxp_row:
                    val = str(cxp_row[col]).replace('$', '').replace(',', '').strip()
                    try:
                        dest_delivery = float(val)
                        break
                    except:
                        pass
            
            goods_value = None
            for col in ['Goods Value', 'goods_value', 'Declare Value']:
                if col in cxp_row:
                    val = str(cxp_row[col]).replace('$', '').replace(',', '').strip()
                    try:
                        goods_value = float(val)
                        break
                    except:
                        pass
            
            if amt_due is not None:
                update_data['cxp_amt_due'] = amt_due
            if dest_delivery is not None:
                update_data['cxp_dest_delivery'] = dest_delivery
            if goods_value is not None:
                update_data['cxp_goods_value'] = goods_value
                update_data['declare_value'] = goods_value
            
            updates_to_perform.append(update_data)
        else:
            no_match += 1
    
    # Mostrar estadísticas
    st.header("📊 Estadísticas de Matching")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Por asignacion", matched_by_asignacion)
    with col2:
        st.metric("Por serial", matched_by_serial)
    with col3:
        st.metric("Por order_id", matched_by_order)
    with col4:
        st.metric("Sin match", no_match)
    
    total_matches = matched_by_asignacion + matched_by_serial + matched_by_order
    st.success(f"✅ TOTAL MATCHES: {total_matches} de {len(all_records)} ({total_matches/len(all_records)*100:.1f}%)")
    
    # Mostrar algunos ejemplos
    if updates_to_perform:
        st.subheader("🔍 Ejemplos de actualizaciones")
        examples = []
        for update in updates_to_perform[:10]:
            examples.append({
                'ID': update['id'],
                'Match Type': update['match_type'],
                'Old amt_due': update.get('old_amt'),
                'New amt_due': update.get('cxp_amt_due'),
                'New dest_delivery': update.get('cxp_dest_delivery')
            })
        st.dataframe(pd.DataFrame(examples))
    
    # Botón para actualizar
    if st.button(f"🚀 ACTUALIZAR {len(updates_to_perform)} REGISTROS", type="primary"):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        total_updated = 0
        errors = 0
        
        for i, update in enumerate(updates_to_perform):
            try:
                update_copy = update.copy()
                db_id = update_copy.pop('id')
                update_copy.pop('match_type', None)
                update_copy.pop('old_amt', None)
                
                # Limpiar valores None
                clean_update = {k: v for k, v in update_copy.items() if v is not None}
                
                if clean_update:
                    result = supabase.table('consolidated_orders').update(clean_update).eq('id', db_id).execute()
                    if result.data:
                        total_updated += 1
                else:
                    errors += 1
                    
            except Exception as e:
                errors += 1
                if errors <= 5:
                    st.error(f"Error: {str(e)[:100]}")
            
            if i % 100 == 0:
                progress_bar.progress(i / len(updates_to_perform))
                status_text.text(f"Procesando... {total_updated} actualizados, {errors} errores")
        
        progress_bar.progress(1.0)
        
        st.success(f"✅ COMPLETADO: {total_updated} registros actualizados")
        if errors > 0:
            st.warning(f"⚠️ {errors} errores durante la actualización")
        
        st.balloons()