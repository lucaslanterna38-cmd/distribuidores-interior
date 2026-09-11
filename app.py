import streamlit as st
import pandas as pd

# Configurar la página en modo ancho
st.set_page_config(layout="wide")

# ==========================================
# 1. SISTEMA DE AUTENTICACIÓN SEGURO
# ==========================================
try:
    USUARIOS = st.secrets["credenciales"]
except FileNotFoundError:
    st.error("Error: No se encontraron las credenciales seguras. Configura los 'Secrets' en Streamlit.")
    st.stop()

if 'usuario_actual' not in st.session_state:
    st.session_state['usuario_actual'] = None
    st.session_state['rol'] = None

def login():
    st.title("Acceso al Tablero Comercial")
    usuario = st.text_input("Usuario (Código de 6 dígitos)")
    password = st.text_input("Contraseña", type="password")
    
    if st.button("Ingresar"):
        if usuario in USUARIOS and USUARIOS[usuario]["pass"] == password:
            st.session_state['usuario_actual'] = usuario
            st.session_state['rol'] = USUARIOS[usuario]["rol"]
            st.rerun()
        else:
            st.error("Usuario o contraseña incorrectos")

def logout():
    st.session_state['usuario_actual'] = None
    st.session_state['rol'] = None
    st.rerun()

# ==========================================
# 2. PROCESAMIENTO DE DATOS (BÚSQUEDA ROBUSTA)
# ==========================================
@st.cache_data
def cargar_y_procesar_datos():
    # 1. Leer Volcado_Dist
    df_dist = pd.read_excel('datos.xlsx', sheet_name='Volcado_Dist', index_col=0)
    if 'Año' in df_dist.columns: 
        df_dist = df_dist.drop(columns=['Año'])
    df_dist = df_dist.fillna(0)
    
    totales_dist = df_dist.sum()
    df_dist_pct = df_dist.div(totales_dist)
    
    # 2. Leer promedios y encabezados
    df_raw = pd.read_excel('datos.xlsx', sheet_name='Distribuidores por Marca en $', header=None)
    
    def limpiar_porcentaje(val):
        if pd.isna(val): return 0.0
        if isinstance(val, (int, float)): return float(val)
        texto = str(val).strip()
        es_porcentaje = '%' in texto
        texto = texto.replace('%', '').replace(',', '.').strip()
        try:
            num = float(texto)
            return num / 100.0 if es_porcentaje else num
        except ValueError:
            return 0.0

    col_promedio_idx = None
    col_marca_idx = None
    row_idx = None
    
    for r in range(min(15, len(df_raw))):
        for c in range(len(df_raw.columns)):
            val = str(df_raw.iloc[r, c]).strip().upper()
            if 'PROMEDIO TOTAL' in val:
                col_promedio_idx = c
                row_idx = r
            if 'MARCA' in val:
                col_marca_idx = c
                
    # Identificar qué distribuidores realmente interesan según la hoja principal
    distribuidores_validos = []
    if row_idx is not None:
        encabezados = df_raw.iloc[row_idx].astype(str).str.strip().tolist()
        distribuidores_validos = [h for h in encabezados if h.split(';')[0].isdigit() and len(h.split(';')[0]) == 6]
                
    promedio_dict = {}
    if col_promedio_idx is not None and col_marca_idx is not None:
        for r in range(row_idx + 1, len(df_raw)):
            marca = str(df_raw.iloc[r, col_marca_idx]).strip().upper()
            if marca and marca != 'NAN':
                val = df_raw.iloc[r, col_promedio_idx]
                promedio_dict[marca] = limpiar_porcentaje(val)
    else:
        st.warning("No se encontró la columna 'PROMEDIO TOTAL' o 'MARCA' en la hoja principal.")
        
    # 3. Filtrar columnas basura y asignar los promedios
    columnas_a_mantener = [c for c in df_dist_pct.columns if c in distribuidores_validos]
    df_final = df_dist_pct[columnas_a_mantener].copy()
    
    promedios_alineados = []
    for marca_original in df_final.index:
        marca_limpia = str(marca_original).strip().upper()
        promedios_alineados.append(promedio_dict.get(marca_limpia, 0.0))
        
    df_final['Promedio Total'] = promedios_alineados
    
    return df_final

# ==========================================
# 3. LÓGICA DE VISUALIZACIÓN Y COLORES
# ==========================================
def aplicar_color_gerencia(row):
    estilos = [''] * len(row)
    promedio = row['Promedio Total']
    
    for i, col in enumerate(row.index):
        if col != 'Promedio Total':
            val = row[col]
            if val <= 1e-6 and promedio <= 1e-6:
                estilos[i] = 'background-color: #f8d7da; color: #721c24;'
            elif val >= promedio:
                estilos[i] = 'background-color: #d4edda; color: #155724;'
            else:
                estilos[i] = 'background-color: #f8d7da; color: #721c24;'
    return estilos

def aplicar_color_individual(row):
    estilos = [''] * len(row)
    val = row.iloc[0]
    promedio = row['Promedio Total']
    
    if val <= 1e-6 and promedio <= 1e-6:
        estilos[0] = 'background-color: #f8d7da; color: #721c24;'
    elif val >= promedio:
        estilos[0] = 'background-color: #d4edda; color: #155724;'
    else:
        estilos[0] = 'background-color: #f8d7da; color: #721c24;'
        
    return estilos

# ==========================================
# 4. RENDERIZADO DE LA APLICACIÓN
# ==========================================
if st.session_state['usuario_actual'] is None:
    login()
else:
    st.sidebar.button("Cerrar Sesión", on_click=logout)
    df = cargar_y_procesar_datos()
    
    formato_dict = {col: "{:.2%}" for col in df.columns}
    
    if st.session_state['rol'] == 'gerencia':
        st.title("Vista Gerencial - Todos los Distribuidores")
        st.write("Visualización de equilibrio de portafolio por marcas.")
        
        df_estilizado = df.style.apply(aplicar_color_gerencia, axis=1).format(formato_dict)
        st.dataframe(df_estilizado, height=800, use_container_width=True)
        
    elif st.session_state['rol'] == 'distribuidor':
        usuario_codigo = st.session_state['usuario_actual']
        
        dist_nombre = next((col for col in df.columns if str(col).startswith(usuario_codigo)), None)
        
        if dist_nombre:
            st.title(f"Tablero de Desempeño: {dist_nombre}")
            st.write("Compara tu venta de cada marca contra el Promedio Total esperado.")
            
            df_individual = df[[dist_nombre, 'Promedio Total']]
            
            formato_ind = {dist_nombre: "{:.2%}", 'Promedio Total': "{:.2%}"}
            df_ind_estilizado = df_individual.style.apply(aplicar_color_individual, axis=1).format(formato_ind)
            
            st.dataframe(df_ind_estilizado, height=800, use_container_width=True)
        else:
            st.error("No se encontraron datos para este código de distribuidor en el archivo.")
