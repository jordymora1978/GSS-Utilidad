"""
Configuración central del sistema contable multipaís
"""

# CONFIGURACIÓN DE SUPABASE
import os
from dotenv import load_dotenv

# Cargar variables de entorno para desarrollo local
load_dotenv()

# Configuración compatible con Streamlit Cloud y desarrollo local
try:
    # Para Streamlit Cloud (usa st.secrets)
    import streamlit as st
    SUPABASE_URL = st.secrets.get("SUPABASE_URL", os.getenv("SUPABASE_URL", "https://pvbzzpeyhhxexyabizbv.supabase.co"))
    SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", os.getenv("SUPABASE_KEY", "your-key-here"))
except ImportError:
    # Para desarrollo local (usa .env)
    SUPABASE_URL = os.getenv("SUPABASE_URL", "https://pvbzzpeyhhxexyabizbv.supabase.co")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY", "your-key-here")

# MAPEO DE CUENTAS A TIPOS DE UTILIDAD
ACCOUNT_UTILITY_MAPPING = {
    '1-TODOENCARGO-CO': 'tipo1_todoencargo',
    '2-MEGATIENDA SPA': 'tipo3_mega_chile', 
    '3-VEENDELO': 'tipo3_mega_chile',
    '4-MEGA TIENDAS PERUANAS': 'tipo2_mega_peru',
    '5-DETODOPARATODOS': 'tipo4_dtpt',
    '6-COMPRAFACIL': 'tipo4_dtpt',
    '7-COMPRA-YA': 'tipo4_dtpt',
    '8-FABORCARGO': 'tipo5_faborcargo'
}

# PAÍSES Y MONEDAS
PAISES_TRM = {
    'CO': {'nombre': 'Colombia', 'moneda': 'COP', 'simbolo': '$'},
    'CL': {'nombre': 'Chile', 'moneda': 'CLP', 'simbolo': '$'},
    'PE': {'nombre': 'Perú', 'moneda': 'PEN', 'simbolo': 'S/'}
}

# TABLA DE PESO PARA FABORCARGO (ANEXO A)
TABLA_PESO_FABORCARGO = [
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
