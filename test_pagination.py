"""
Test de paginación para obtener TODOS los registros
"""

from supabase import create_client
import config

# Conectar a Supabase
supabase = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)

# Contar totales por cuenta
cxp_accounts = ['3-VEENDELO', '8-FABORCARGO', '2-MEGATIENDA SPA']

print("=" * 60)
print("CONTEO DE REGISTROS POR CUENTA:")
print("=" * 60)

total_general = 0

for account in cxp_accounts:
    # Contar registros de cada cuenta
    result = supabase.table('consolidated_orders').select('id').eq('account_name', account).execute()
    count = len(result.data) if result.data else 0
    print(f"{account}: {count:,} registros")
    total_general += count

print(f"\nTOTAL GENERAL: {total_general:,} registros")

# Ahora probar obtener todos con paginación
print("\n" + "=" * 60)
print("PROBANDO PAGINACIÓN:")
print("=" * 60)

all_records = []
page_size = 1000
current_page = 0

while True:
    offset = current_page * page_size
    print(f"Obteniendo página {current_page + 1} (offset={offset})...")
    
    result = supabase.table('consolidated_orders').select(
        'id, account_name, asignacion'
    ).in_('account_name', cxp_accounts).range(offset, offset + page_size - 1).execute()
    
    if result.data:
        all_records.extend(result.data)
        print(f"  → Obtenidos {len(result.data)} registros (Total acumulado: {len(all_records)})")
        
        if len(result.data) < page_size:
            print("  → Última página (menos de 1000 registros)")
            break
    else:
        print("  → No hay más registros")
        break
    
    current_page += 1
    
    # Evitar loop infinito
    if current_page > 20:
        print("  → Límite de seguridad alcanzado")
        break

print(f"\n✅ TOTAL REGISTROS OBTENIDOS: {len(all_records)}")

# Verificar algunos prefijos
if all_records:
    prefixes = {}
    for record in all_records[:1000]:
        asig = record.get('asignacion', '')
        if asig and len(asig) >= 4:
            prefix = asig[:4]
            prefixes[prefix] = prefixes.get(prefix, 0) + 1
    
    print("\nPREFIJOS ENCONTRADOS (primeros 1000):")
    for prefix, count in sorted(prefixes.items()):
        print(f"  {prefix}: {count} registros")