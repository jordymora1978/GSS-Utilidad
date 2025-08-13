"""
Página principal de Reportes con selector de reportes
"""

import streamlit as st
import sys
import os
import importlib
from datetime import datetime, timedelta
import calendar

# Path configuration
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

# Page config
st.set_page_config(
    page_title="📊 Reportes",
    page_icon="📊",
    layout="wide"
)

# Lista de reportes disponibles
REPORTES = {
    "📦 TodoEncargo Colombia": "todoencargo_co",
    "🇵🇪 Mega Tiendas Peruanas": "mega_tiendas_peruanas",
    "🛒 MegaTienda Veendelo": "megatienda_veendelo",
    "🏢 DTPT Group": "dtpt_group",
    "📦 FaborCargo": "faborcargo",
    "🌍 Reporte Global": "reporte_global",
    "💳 Reembolsos MeLi": "reembolsos_meli"
}

MESES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}

# Selector inicial para mostrar el título
reporte_inicial = list(REPORTES.keys())[0]

# Crear el título del reporte que se actualiza dinámicamente
titulo_placeholder = st.empty()

# Todos los controles en una sola línea
col_reporte, col_periodo, col_mes, col_año, col_boton = st.columns([3, 1.5, 1.5, 1.5, 2])

with col_reporte:
    reporte_seleccionado = st.selectbox(
        "Reporte:",
        options=list(REPORTES.keys()),
        help="Seleccione el reporte que desea generar"
    )

# Mostrar el título del reporte seleccionado
titulo_placeholder.info(f"📊 **{reporte_seleccionado}**")

with col_periodo:
    tipo_periodo = st.selectbox(
        "Período:",
        ["Por mes", "Rango"],
        help="Tipo de período para el reporte"
    )

if tipo_periodo == "Por mes":
    with col_mes:
        # Por defecto, seleccionar el mes anterior para que haya datos
        mes_default = datetime.now().month - 1 if datetime.now().month > 1 else 12
        mes_seleccionado = st.selectbox(
            "Mes:",
            options=range(1, 13),
            format_func=lambda x: MESES[x],
            index=mes_default - 1
        )
    with col_año:
        # Si estamos en enero y seleccionamos diciembre, usar el año anterior
        año_default = datetime.now().year
        if datetime.now().month == 1 and mes_default == 12:
            año_default = datetime.now().year - 1
        
        año_seleccionado = st.selectbox(
            "Año:",
            options=range(2020, datetime.now().year + 1),
            index=año_default - 2020
        )
    # Calcular fechas para el mes seleccionado
    fecha_inicio = datetime(año_seleccionado, mes_seleccionado, 1).date()
    ultimo_dia = calendar.monthrange(año_seleccionado, mes_seleccionado)[1]
    fecha_fin = datetime(año_seleccionado, mes_seleccionado, ultimo_dia).date()
else:
    with col_mes:
        fecha_inicio = st.date_input(
            "Desde:",
            datetime.now().date() - timedelta(days=30)
        )
    with col_año:
        fecha_fin = st.date_input(
            "Hasta:",
            datetime.now().date()
        )

with col_boton:
    st.markdown("<br>", unsafe_allow_html=True)  # Espaciado para alinear el botón
    generar_btn = st.button(
        "🔄 Generar Reporte",
        use_container_width=True
    )

st.markdown("---")

# Área de reporte usando todo el ancho
if generar_btn:
    # Cargar el módulo del reporte seleccionado
    modulo_nombre = REPORTES[reporte_seleccionado]
    
    try:
        # Importar dinámicamente el módulo del reporte
        modulo_path = f"modulos.reportes.{modulo_nombre}"
        
        # Verificar si el módulo existe
        modulo_file = os.path.join(parent_dir, "modulos", "reportes", f"{modulo_nombre}.py")
        
        if os.path.exists(modulo_file):
            # Importar y ejecutar el módulo
            if modulo_path in sys.modules:
                # Recargar si ya está importado para reflejar cambios
                importlib.reload(sys.modules[modulo_path])
            
            modulo = importlib.import_module(modulo_path)
            
            # Ejecutar la función principal del reporte con las fechas
            if hasattr(modulo, 'generar_reporte'):
                # Intentar pasar las fechas como parámetros
                try:
                    modulo.generar_reporte(fecha_inicio, fecha_fin)
                except TypeError:
                    # Si la función no acepta parámetros, llamar sin ellos
                    with st.expander("⚠️ Nota", expanded=True):
                        st.warning("Este reporte generará sus propios controles de fecha. Las fechas seleccionadas arriba podrían no aplicar.")
                    modulo.generar_reporte()
            else:
                st.warning(f"El módulo {modulo_nombre} no tiene una función 'generar_reporte'")
        else:
            st.warning(f"""
            ⚠️ El módulo del reporte **{reporte_seleccionado}** aún no está disponible.
            
            Archivo esperado: `modulos/reportes/{modulo_nombre}.py`
            """)
            
    except Exception as e:
        st.error(f"Error al cargar el reporte: {str(e)}")
        with st.expander("Detalles del error"):
            st.exception(e)
else:
    st.info("👆 Configure los parámetros y haga clic en 'Generar Reporte' para comenzar")

# Footer con información
st.markdown("---")
st.caption("Sistema de Reportes Multipaís - Todos los reportes en un solo lugar")