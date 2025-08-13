"""
Script simple para verificar columnas de Supabase
"""

from supabase import create_client
import config
import pandas as pd

def check_table_structure():
    try:
        # Conectar a Supabase
        supabase = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
        
        # Obtener una muestra
        result = supabase.table('consolidated_orders').select('*').limit(1).execute()
        
        if result.data:
            df = pd.DataFrame(result.data)
            columnas = sorted(list(df.columns))
            
            print("=" * 60)
            print("COLUMNAS EN TABLA consolidated_orders:")
            print("=" * 60)
            
            for i, col in enumerate(columnas, 1):
                print(f"{i:2d}. {col}")
            
            print("\n" + "=" * 60)
            print("COLUMNAS CON 'DELIVERY' O 'DEST':")
            print("=" * 60)
            
            delivery_cols = [col for col in columnas if 'delivery' in col.lower() or 'dest' in col.lower()]
            if delivery_cols:
                for col in delivery_cols:
                    print(f"✅ {col}")
            else:
                print("❌ NO ENCONTRADAS")
            
            print("\n" + "=" * 60)
            print("COLUMNAS CON 'DECLARE', 'GOODS', 'VALUE':")
            print("=" * 60)
            
            value_cols = [col for col in columnas if any(word in col.lower() for word in ['declare', 'goods', 'value'])]
            if value_cols:
                for col in value_cols:
                    print(f"✅ {col}")
            else:
                print("❌ NO ENCONTRADAS")
            
            # Contar registros totales
            print("\n" + "=" * 60)
            print("ESTADÍSTICAS:")
            print("=" * 60)
            
            count_result = supabase.table('consolidated_orders').select('*', count='exact', head=True).execute()
            total_count = count_result.count if hasattr(count_result, 'count') else 0
            print(f"Total registros: {total_count:,}")
            
            # Contar cuentas CXP
            cxp_accounts = ['3-VEENDELO', '8-FABORCARGO', '2-MEGATIENDA SPA']
            
            for account in cxp_accounts:
                count_result = supabase.table('consolidated_orders').select('*', count='exact', head=True).eq('account_name', account).execute()
                account_count = count_result.count if hasattr(count_result, 'count') else 0
                print(f"{account}: {account_count:,} registros")
        
        else:
            print("❌ No se pudieron obtener datos")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    check_table_structure()