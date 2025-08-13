# Sistema Contable Multipaís

Aplicación web desarrollada en Streamlit para la gestión y análisis de datos contables multi-país.

## Características

- 📊 **Reportes Unificados**: 7 tipos de reportes diferentes con selector integrado
- 🌍 **Multi-país**: Soporte para múltiples países y monedas
- 🎨 **Interfaz Minimalista**: Diseño limpio con componentes nativos de Streamlit
- 📅 **Filtros de Fecha**: Filtrado inteligente por período (por defecto mes anterior)
- 🔍 **Análisis Detallado**: Métricas y visualizaciones por país y tipo

## Estructura del Proyecto

```
sistema-contable-multipais/
├── pages/
│   ├── 1_💼_Consolidador.py
│   ├── 2_💱_Gestion_TRM.py
│   └── 3_📊_Reportes.py        # Página principal de reportes
├── modulos/
│   └── reportes/               # Módulos de cada reporte
│       ├── global_co.py
│       ├── todoencargo_co.py
│       ├── iservy_co.py
│       ├── global_ch.py
│       ├── todoencargo_ch.py
│       ├── iservy_ch.py
│       └── global_us.py
├── main.py                     # Aplicación principal
└── requirements.txt
```

## Configuración Rápida

1. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Iniciar aplicación:**
   ```bash
   streamlit run streamlit_app.py
   # Disponible en http://localhost:8501
   ```

## Reportes Disponibles

1. **Global Colombia**: Análisis completo Colombia
2. **Todo Encargo Colombia**: Reportes específicos Colombia
3. **iServy Colombia**: Datos de iServy Colombia
4. **Global Chile**: Análisis completo Chile
5. **Todo Encargo Chile**: Reportes específicos Chile
6. **iServy Chile**: Datos de iServy Chile
7. **Global Estados Unidos**: Análisis completo USA

## Uso

1. Navegar a la página **📊 Reportes**
2. Seleccionar el tipo de reporte del dropdown
3. Ajustar fechas si es necesario (por defecto: mes anterior)
4. Ver métricas y análisis generados automáticamente

## Características Técnicas

- **Framework**: Streamlit
- **Temas**: Soporte completo para tema claro/oscuro
- **Componentes**: Solo elementos nativos de Streamlit
- **Filtrado**: Optimización SQL para mejor rendimiento
- **Interfaz**: Diseño minimalista sin colores personalizados
