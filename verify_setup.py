"""
Script de verificación para instalaciones de GSS App
Verifica que todo esté configurado correctamente
"""
import os
import sys

def verify_setup():
    """Verificar configuración del sistema"""
    print("🔍 GSS App - Verificación de Configuración")
    print("=" * 50)
    
    issues = []
    
    # 1. Verificar .env
    if os.path.exists('.env'):
        print("✅ Archivo .env encontrado")
        try:
            with open('.env', 'r') as f:
                content = f.read()
                if 'SUPABASE_URL=' in content and 'SUPABASE_KEY=' in content:
                    print("✅ Variables de Supabase configuradas")
                else:
                    issues.append("❌ Variables de Supabase no configuradas en .env")
        except:
            issues.append("❌ Error leyendo archivo .env")
    else:
        issues.append("❌ Archivo .env no encontrado")
        print("💡 Ejecuta: cp .env.example .env")
    
    # 2. Verificar dependencias
    try:
        import streamlit
        import pandas  
        import bcrypt
        import supabase
        from dotenv import load_dotenv
        print("✅ Dependencias principales instaladas")
    except ImportError as e:
        issues.append(f"❌ Dependencia faltante: {e}")
        print("💡 Ejecuta: pip install -r requirements.txt")
    
    # 3. Verificar conexión a Supabase (si está configurado)
    if os.path.exists('.env'):
        try:
            from dotenv import load_dotenv
            load_dotenv()
            
            url = os.getenv('SUPABASE_URL')
            key = os.getenv('SUPABASE_KEY')
            
            if url and key and url != 'https://your-project.supabase.co':
                from supabase import create_client
                supabase = create_client(url, key)
                
                # Test simple de conexión
                result = supabase.table('users').select('count').execute()
                print("✅ Conexión a Supabase exitosa")
                
                if result.data:
                    print(f"✅ Usuarios encontrados en la base de datos")
                else:
                    print("⚠️  Base de datos conectada pero sin usuarios")
                    print("💡 Ejecuta el script setup_users_database.sql en Supabase")
                    
            else:
                issues.append("❌ Credenciales de Supabase no configuradas")
                
        except Exception as e:
            issues.append(f"❌ Error conectando a Supabase: {e}")
    
    # 4. Verificar estructura de archivos
    required_files = [
        'streamlit_app.py',
        'requirements.txt', 
        'setup_users_database.sql',
        'modulos/auth.py',
        'pages/1_📦_Consolidador.py'
    ]
    
    for file in required_files:
        if os.path.exists(file):
            print(f"✅ {file}")
        else:
            issues.append(f"❌ Archivo faltante: {file}")
    
    print("\n" + "=" * 50)
    
    if not issues:
        print("🎉 ¡Configuración completa!")
        print("🚀 Ejecuta: streamlit run streamlit_app.py")
        return True
    else:
        print("⚠️  Se encontraron problemas:")
        for issue in issues:
            print(f"   {issue}")
        print("\n💡 Revisa la documentación en README.md")
        return False

if __name__ == "__main__":
    verify_setup()