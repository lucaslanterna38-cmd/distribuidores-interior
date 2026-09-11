import streamlit as st
import pandas as pd

# Configurar la página en modo ancho (Obligatorio que sea la primera instrucción de Streamlit)
st.set_page_config(layout="wide")

# ==========================================
# 1. SISTEMA DE AUTENTICACIÓN SEGURO
# ==========================================
# Llama a las contraseñas guardadas en los Advanced Settings de Streamlit
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
# 2. PROCESAMIENTO DE DATOS
# ==========================================
@st.cache_data
def cargar_y_procesar_datos():
    # Volcado_Dist tiene sus títulos en la Fila 1 (por defecto)
    df_dist = pd.read_excel('datos.xlsx', sheet_name='Volcado_Dist', index_col=0)
    
    # ¡CORRECCIÓN!: Agregamos header=1 porque los títulos en esta hoja están en la Fila 2
    df_promedios = pd.read_excel('datos.xlsx', sheet_name='Distribuidores por Marca en $', header=1, index_col=0)
    
    # Limpiar espacios extra al principio o final de los nombres de las marcas
    df_dist.index = df_dist.index.astype(str).str.strip()
    df_promedios.index = df_promedios.index.astype(str).str.strip()
    
    # Limpiar columna Año si existe
    if 'Año' in df_dist.columns: df_dist = df_dist.drop(columns=['Año'])
    
    df_dist = df_dist.fillna(0)
    
    # Calcular porcentajes de cada distribuidor sobre su venta total
    totales_dist = df_dist.sum()
    df_dist_pct = df_dist.div(totales_dist)
    
    # Extraer la columna PROMEDIO TOTAL
    col_promedio = next((col for col in df_promedios.columns if str(col).strip().upper() == 'PROMEDIO TOTAL'), None)
    
    if col_promedio:
        # Convertimos forzosamente a números por si Excel envía los datos como texto (ej: "0,00%")
        promedio_total_serie = pd.to_numeric(df_promedios[col_promedio], errors='coerce').fillna(0)
    else:
        # Fallback de seguridad
        promedio_total_serie = pd.Series(0, index=df_dist_pct.index)
        st.warning("No se encontró la columna 'PROMEDIO TOTAL' en la hoja 'Distribuidores por Marca en $'.")
    
    # Combinar el DataFrame de porcentajes con la columna Promedio Total
    df_final = df_dist_pct.copy()
    df_final = df_final.join(promedio_total_serie.rename('Promedio Total'), how='left')
    
    # Rellenar cualquier otro posible nulo residual con 0
    df_final = df_final.fillna(0)
    
    return df_final
# ==========================================
# 3. LÓGICA DE VISUALIZACIÓN Y COLORES
# ==========================================
def aplicar_color_gerencia(row):
    # Pinta la celda evaluando cada distribuidor contra el Promedio Total de esa fila
    estilos = [''] * len(row)
    promedio = row['Promedio Total']
    
    for i, col in enumerate(row.index):
        if col != 'Promedio Total':
            val = row[col]
            # Si ambos son 0 (o tan bajos que se redondean a 0%), se pinta rojo
            if val <= 1e-6 and promedio <= 1e-6:
                estilos[i] = 'background-color: #f8d7da; color: #721c24;' # Rojo
            elif val >= promedio:
                estilos[i] = 'background-color: #d4edda; color: #155724;' # Verde
            else:
                estilos[i] = 'background-color: #f8d7da; color: #721c24;' # Rojo
    return estilos

def aplicar_color_individual(row):
    # Pinta solo la columna del distribuidor
    estilos = [''] * len(row)
    val = row.iloc[0] # El porcentaje del distribuidor
    promedio = row['Promedio Total']
    
    # Si ambos son 0 (o tan bajos que se redondean a 0%), se pinta rojo
    if val <= 1e-6 and promedio <= 1e-6:
        estilos[0] = 'background-color: #f8d7da; color: #721c24;' # Rojo
    elif val >= promedio:
        estilos[0] = 'background-color: #d4edda; color: #155724;' # Verde
    else:
        estilos[0] = 'background-color: #f8d7da; color: #721c24;' # Rojo
        
    return estilos

# ==========================================
# 4. RENDERIZADO DE LA APLICACIÓN
# ==========================================
if st.session_state['usuario_actual'] is None:
    login()
else:
    st.sidebar.button("Cerrar Sesión", on_click=logout)
    df = cargar_y_procesar_datos()
    
    # Configuración de formato a %
    formato_dict = {col: "{:.2%}" for col in df.columns}
    
    if st.session_state['rol'] == 'gerencia':
        st.title("Vista Gerencial - Todos los Distribuidores")
        st.write("Visualización de equilibrio de portafolio por marcas.")
        
        # Aplicar estilos y formato
        df_estilizado = df.style.apply(aplicar_color_gerencia, axis=1).format(formato_dict)
        st.dataframe(df_estilizado, height=800, use_container_width=True)
        
    elif st.session_state['rol'] == 'distribuidor':
        usuario_codigo = st.session_state['usuario_actual']
        
        # Lógica para encontrar el nombre completo de la columna usando los 6 dígitos
        dist_nombre = next((col for col in df.columns if str(col).startswith(usuario_codigo)), None)
        
        if dist_nombre:
            st.title(f"Tablero de Desempeño: {dist_nombre}")
            st.write("Compara tu venta de cada marca contra el Promedio Total esperado.")
            
            # Filtrar solo la columna del distribuidor encontrado y el promedio
            df_individual = df[[dist_nombre, 'Promedio Total']]
            
            # Aplicar estilos y formato
            formato_ind = {dist_nombre: "{:.2%}", 'Promedio Total': "{:.2%}"}
            df_ind_estilizado = df_individual.style.apply(aplicar_color_individual, axis=1).format(formato_ind)
            
            st.dataframe(df_ind_estilizado, height=800, use_container_width=True)
        else:
            st.error("No se encontraron datos para este código de distribuidor en el archivo.")
