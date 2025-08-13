"""
Módulo para gestionar las Tasas Representativas del Mercado (TRM)
de Colombia, Chile y Perú
"""
import streamlit as st
import pandas as pd
from datetime import datetime, date
from supabase import create_client
import config

# Conexión a Supabase
supabase = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)

def obtener_trm_fecha(pais: str, fecha: date) -> float:
    """
    Obtiene la TRM de un país para una fecha específica
    Si no encuentra la fecha exacta, busca la más cercana anterior
    """
    try:
        # Intentar fecha exacta
        resultado = supabase.table('trm_rates').select('rate_to_usd').eq(
            'country', pais
        ).eq('date', fecha.isoformat()).execute()
        
        if resultado.data:
            return float(resultado.data[0]['rate_to_usd'])
        
        # Si no hay TRM para esa fecha, buscar la más reciente anterior
        resultado = supabase.table('trm_rates').select('rate_to_usd, date').eq(
            'country', pais
        ).lte('date', fecha.isoformat()).order(
            'date', desc=True
        ).limit(1).execute()
        
        if resultado.data:
            st.warning(f"⚠️ No hay TRM para {fecha}. Usando TRM del {resultado.data[0]['date']}")
            return float(resultado.data[0]['rate_to_usd'])
        else:
            st.error(f"❌ No se encontró TRM para {pais}")
            return None
            
    except Exception as e:
        st.error(f"Error obteniendo TRM: {str(e)}")
        return None

def guardar_trm(pais: str, fecha: date, valor: float, usuario: str = "Sistema"):
    """
    Guarda o actualiza la TRM para un país y fecha
    """
    try:
        datos = {
            'country': pais,
            'currency_code': config.PAISES_TRM[pais]['moneda'],
            'date': fecha.isoformat(),
            'rate_to_usd': valor,
            'created_by': usuario
        }
        
        # Intentar insertar
        resultado = supabase.table('trm_rates').insert(datos).execute()
        return True, "TRM guardada exitosamente"
        
    except Exception as e:
        # Si ya existe, actualizar
        if "duplicate key" in str(e):
            try:
                resultado = supabase.table('trm_rates').update({
                    'rate_to_usd': valor,
                    'updated_at': datetime.now().isoformat()
                }).eq('country', pais).eq('date', fecha.isoformat()).execute()
                return True, "TRM actualizada exitosamente"
            except Exception as update_error:
                return False, f"Error actualizando: {str(update_error)}"
        else:
            return False, f"Error guardando: {str(e)}"

def obtener_historial_trm(pais: str = None, dias: int = 30) -> pd.DataFrame:
    """
    Obtiene el historial de TRM de los últimos días
    """
    try:
        query = supabase.table('trm_rates').select('*')
        
        if pais:
            query = query.eq('country', pais)
            
        # Ordenar por fecha descendente
        resultado = query.order('date', desc=True).limit(dias * 3).execute()
        
        if resultado.data:
            df = pd.DataFrame(resultado.data)
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date', ascending=False)
            return df
        else:
            return pd.DataFrame()
            
    except Exception as e:
        st.error(f"Error obteniendo historial: {str(e)}")
        return pd.DataFrame()

def mostrar_interfaz_trm():
    """
    Interfaz de Streamlit para gestionar TRM
    """
    st.header("💱 Gestión de TRM")
    
    # Tabs para diferentes acciones
    tab1, tab2, tab3 = st.tabs(["📝 Actualizar TRM", "📊 Ver Historial", "📈 Gráficos"])
    
    with tab1:
        st.subheader("Actualizar TRM del día")
        
        # Selector de fecha
        fecha_trm = st.date_input(
            "Fecha de la TRM",
            value=date.today(),
            max_value=date.today()
        )
        
        # Columnas para los 3 países
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("### 🇨🇴 Colombia")
            trm_colombia = st.number_input(
                "TRM Colombia (COP)",
                min_value=0.0,
                max_value=10000.0,
                value=4300.0,
                step=0.01,
                format="%.2f"
            )
        
        with col2:
            st.markdown("### 🇨🇱 Chile")
            trm_chile = st.number_input(
                "TRM Chile (CLP)",
                min_value=0.0,
                max_value=2000.0,
                value=990.0,
                step=0.01,
                format="%.2f"
            )
        
        with col3:
            st.markdown("### 🇵🇪 Perú")
            trm_peru = st.number_input(
                "TRM Perú (PEN)",
                min_value=0.0,
                max_value=10.0,
                value=3.70,
                step=0.01,
                format="%.2f"
            )
        
        # Botón para guardar
        if st.button("💾 Guardar TRM", type="primary", use_container_width=True):
            exitos = 0
            errores = []
            
            # Guardar cada TRM
            for pais, valor in [('CO', trm_colombia), ('CL', trm_chile), ('PE', trm_peru)]:
                exito, mensaje = guardar_trm(pais, fecha_trm, valor)
                if exito:
                    exitos += 1
                else:
                    errores.append(f"{config.PAISES_TRM[pais]['nombre']}: {mensaje}")
            
            # Mostrar resultados
            if exitos == 3:
                st.success("✅ Todas las TRM se guardaron correctamente")
                st.balloons()
            elif exitos > 0:
                st.warning(f"⚠️ Se guardaron {exitos} de 3 TRM")
                for error in errores:
                    st.error(error)
            else:
                st.error("❌ No se pudo guardar ninguna TRM")
    
    with tab2:
        st.subheader("Historial de TRM")
        
        # Selector de país
        pais_seleccionado = st.selectbox(
            "Seleccionar país",
            options=['TODOS'] + list(config.PAISES_TRM.keys()),
            format_func=lambda x: 'Todos los países' if x == 'TODOS' else config.PAISES_TRM[x]['nombre']
        )
        
        # Obtener historial
        df_historial = obtener_historial_trm(
            pais=None if pais_seleccionado == 'TODOS' else pais_seleccionado
        )
        
        if not df_historial.empty:
            # Formatear el DataFrame para mostrar
            df_mostrar = df_historial[['date', 'country', 'currency_code', 'rate_to_usd']].copy()
            df_mostrar['date'] = df_mostrar['date'].dt.strftime('%Y-%m-%d')
            df_mostrar['country'] = df_mostrar['country'].map(
                lambda x: config.PAISES_TRM.get(x, {}).get('nombre', x)
            )
            df_mostrar.columns = ['Fecha', 'País', 'Moneda', 'TRM']
            
            st.dataframe(df_mostrar, use_container_width=True)
        else:
            st.info("No hay datos de TRM registrados")
    
    with tab3:
        st.subheader("Gráficos de TRM")
        
        if not df_historial.empty:
            # Gráfico de evolución
            import plotly.express as px
            
            fig = px.line(
                df_historial,
                x='date',
                y='rate_to_usd',
                color='country',
                title='Evolución de TRM',
                labels={
                    'date': 'Fecha',
                    'rate_to_usd': 'TRM',
                    'country': 'País'
                }
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay datos para graficar")

# Función para pruebas
if __name__ == "__main__":
    mostrar_interfaz_trm()
