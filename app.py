# ==========================================
# 2. PROCESAMIENTO DE DATOS
# ==========================================
@st.cache_data
def cargar_y_procesar_datos():
    # Usamos index_col=0 en lugar de 'Marca' para leer siempre la primera columna sin importar espacios en blanco
    df_dist = pd.read_excel('datos.xlsx', sheet_name='Volcado_Dist', index_col=0)
    df_promedios = pd.read_excel('datos.xlsx', sheet_name='Distribuidores por Marca en $', index_col=0)
    
    # Limpiar espacios extra al principio o final de los nombres de las marcas
    df_dist.index = df_dist.index.astype(str).str.strip()
    df_promedios.index = df_promedios.index.astype(str).str.strip()
    
    # Limpiar columna Año si existe
    if 'Año' in df_dist.columns: df_dist = df_dist.drop(columns=['Año'])
    
    df_dist = df_dist.fillna(0)
    
    # Calcular porcentajes de cada distribuidor sobre su venta total
    totales_dist = df_dist.sum()
    df_dist_pct = df_dist.div(totales_dist)
    
    # Extraer la columna PROMEDIO TOTAL directamente de la primera hoja
    col_promedio = next((col for col in df_promedios.columns if str(col).strip().upper() == 'PROMEDIO TOTAL'), None)
    
    if col_promedio:
        promedio_total_serie = df_promedios[col_promedio].fillna(0)
    else:
        # Fallback de seguridad por si no la encuentra
        promedio_total_serie = pd.Series(0, index=df_dist_pct.index)
        st.warning("No se encontró la columna 'PROMEDIO TOTAL' en la hoja 'Distribuidores por Marca en $'.")
    
    # Combinar el DataFrame de porcentajes con la columna Promedio Total
    df_final = df_dist_pct.copy()
    df_final = df_final.join(promedio_total_serie.rename('Promedio Total'), how='left')
    
    # Rellenar cualquier otro posible nulo residual con 0
    df_final = df_final.fillna(0)
    
    return df_final
