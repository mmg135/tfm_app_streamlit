import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from streamlit_folium import st_folium
import hashlib
from functions import (
    buscar_lugares,
    obtener_ruta_optimizada,
    obtener_coordenadas_desde_nombre,
    generar_mapa_ruta
)

st.set_page_config(page_title="Planificador de Ruta", layout="wide")
st.title("🗓️ Planificador de Ruta")

# ----------- Inicialización de estado  -----------
for key in ["df_lugares", "df_filtrado", "df_editado",
            "ruta", "coords_ordenadas", "instrucciones", 
            "seleccion_confirmada", "busqueda_realizada", 
            "tipo_lugar", "direccion_central", "origen", "destino"]:
    if key not in st.session_state:
        st.session_state[key] = None  #si no exite lo inicializa como None

st.session_state.seleccion_confirmada = st.session_state.seleccion_confirmada or False  #si es True, se mantiene; si era None (o cualquier valor falsy), pasa a False
st.session_state.busqueda_realizada = st.session_state.busqueda_realizada or False      #si es True, se mantiene; si era None (o cualquier valor falsy), pasa a False

# ----------- Formulario de búsqueda -----------
with st.form("form_planificador"):
    st.subheader("🔍 Parámetros de búsqueda")

    st.text_input(
        "**¿Qué tipo de lugar deseas visitar?** (obligatorio)",
        placeholder="Ej: taller de chapa o mecánica de automóviles",
        key="tipo_lugar",
    )

    st.text_input(
        "**Dirección de búsqueda** (obligatorio)",
        placeholder="Ciudad, Provincia, País",
        key="direccion_central",
    )

    st.slider("**Radio de búsqueda (en km)**", 1, 500, 10, step=5, key="radio_km")
    radio_busqueda = st.session_state.get("radio_km", 10) * 1000

    col1, col2 = st.columns(2)
    with col1:
        st.text_input(
            "**🟢 Punto de inicio ruta** (obligatorio)",
            placeholder="Calle, Número, Ciudad, Provincia, País",
            key="origen",
        )
    with col2:
        st.text_input(
            "**🔴 Punto de fin ruta** (opcional)",
            placeholder="Calle, Número, Ciudad, Provincia, País",
            key="destino",
        )

    #st.date_input("**Fecha estimada del recorrido** (opcional)", key="fecha")
    #st.time_input("**Hora estimada de inicio** (opcional)", key="hora")

    opciones_transporte = {
        "🚗 Coche": "driving-car",
        "🚶 A pie": "foot-walking",
        "🚴 Bicicleta": "cycling-regular",
        "🚚 Vehículo pesado": "driving-hgv",
        "♿ Silla de ruedas": "wheelchair",
    }

    st.selectbox(
        "**Modo de transporte** (obligatorio)",
        list(opciones_transporte.keys()),
        index=0,
        key="modo_seleccionado",
        help="Elige cómo quieres desplazarte para que la ruta se adapte a tu medio de transporte.",
    )
    modo_transporte = opciones_transporte[
        st.session_state.get("modo_seleccionado", list(opciones_transporte.keys())[0])
    ]

    submitted = st.form_submit_button("🔍 Buscar lugares y continuar")

# ----------- Botón para limpiar búsqueda -----------
if st.button("🧹 Limpiar búsqueda"):
    # Borrar los valores de los widgets del formulario de búsqueda
    for k in ["tipo_lugar", "direccion_central", "radio_km", "origen", "destino", "fecha", "hora", "modo_seleccionado"]:
        if k in st.session_state:
            del st.session_state[k]

    # Borrar datos de resultados asociados
    for k in ["df_lugares", "df_filtrado", "ruta", "coords_ordenadas", "instrucciones", "busqueda_realizada", "seleccion_confirmada", "editor_lugares"]:
        if k in st.session_state:
            del st.session_state[k]

    st.rerun() 

# ----------- Procesamiento si se envía el formulario -----------
if submitted:
    if not (
        st.session_state.tipo_lugar.strip() and 
        st.session_state.direccion_central.strip() and
        st.session_state.origen.strip() and 
        st.session_state.modo_seleccionado                                     #se usa .strip() para evitar entradas vacías
    ):  
        st.warning("❗ Por favor, completa al menos el **tipo de lugar**, la **dirección de búsqueda** , el **punto de inicio** y el **modo de transporte** de la ruta.")
    else:
        with st.spinner("Buscando lugares..."):
            coords_centro = obtener_coordenadas_desde_nombre(st.session_state.direccion_central) #obtine las coordenadas (lat, lng) de la dirección de búsqueda

            if not coords_centro:
                st.error("❌ No se pudo obtener las coordenadas de la dirección de búsqueda proporcionada.")
            else:
                df_lugares = buscar_lugares(
                    query=st.session_state.tipo_lugar,
                    radius=radio_busqueda,
                    latitude=coords_centro[1],
                    longitude=coords_centro[0]
                )

                if df_lugares.empty:
                    st.warning("⚠️ No se encontraron lugares válidos.")
                else:
                    st.success(f"✅ Se encontraron {len(df_lugares)} lugares válidos.")
                    st.session_state.df_lugares = df_lugares
                    st.session_state.df_lugares["Seleccionado"] = False  #añade columna inicializada a False
                    st.session_state.df_filtrado = None
                    st.session_state.ruta = None
                    st.session_state.seleccion_confirmada = False
                    st.session_state.busqueda_realizada = True

# ----------- Mostrar editor si hay resultados -----------
if st.session_state.busqueda_realizada:

    # --- Se confirmó la selección del DataFrame (df_lugares) ---
    if st.session_state.seleccion_confirmada:   
        if st.button("🔁 Volver a editar selección"):
            st.session_state.seleccion_confirmada = False
            st.session_state.ruta = None
            st.session_state.instrucciones = None
            st.session_state.coords_ordenadas = None

    # --- Muestra la interfaz de selección si hay un DataFrame de lugares cargado (df_lugares) y el usuario aún no ha confirmado su selección ---
    if (
        st.session_state.busqueda_realizada
        and st.session_state.df_lugares is not None
        and not st.session_state.df_lugares.empty
        and not st.session_state.seleccion_confirmada
    ): 
        st.markdown("## 🗂️ Selecciona los lugares que deseas visitar")

         #Aseguramos la columna Seleccionado
        if "Seleccionado" not in st.session_state.df_lugares.columns:
            st.session_state.df_lugares["Seleccionado"] = False

        df_lugares = st.session_state.df_lugares

        edited_df = st.data_editor(
            st.session_state.df_lugares,
            use_container_width=True,
            key="editor_lugares",
            column_order=[c for c in df_lugares.columns if c not in ["ID", "Web"]], #"ID" y "Web" se ocultan para simplificar la vista
            column_config={
                "Seleccionado": st.column_config.CheckboxColumn(label="¿Incluir?", default=False)
            },
            disabled=["Nombre", "Dirección", "Categoría", "Lat", "Lng", "Teléfono"],
            hide_index=True
        )

        st.session_state.df_editado = edited_df

        #DataFrame con solo los lugares seleccionados
        st.session_state.df_filtrado = (
            edited_df[edited_df["Seleccionado"]]
            .drop(columns=["Seleccionado"], errors="ignore")
            .reset_index(drop=True)
        )
        

        # ----------- Añadir lugar manualmente -----------
        st.markdown("### ➕ Añadir lugar manualmente")
        with st.expander("**📍 Añadir nuevo lugar**"):
            nuevo_nombre = st.text_input("**Nombre del lugar** (obligatorio)")
            nueva_direccion = st.text_input("**Dirección** (obligatorio)", placeholder="Calle, Número, Ciudad, Provincia, País")
            nueva_categoria = st.text_input("**Categoría** (obligatorio)", value="")
            nuevo_tel = st.text_input("**Teléfono** (opcional)", value="")
            nueva_web = st.text_input("**Web** (opcional)", value="")

            if st.button("✅ Añadir lugar manual"):
                if not (nuevo_nombre.strip() and nueva_direccion.strip() and nueva_categoria.strip()):
                    st.warning("⚠️ Por favor, introduce **nombre**, **dirección** y **categoría**.")
                else:
                    coordenadas = obtener_coordenadas_desde_nombre(nueva_direccion)

                    if not coordenadas:
                        st.error("❌ No se pudieron obtener las coordenadas con esa dirección.")
                    else:
                        nueva_lat, nueva_lng = coordenadas[1], coordenadas[0]

                        nuevo = {
                            "ID": f"manual_{hashlib.md5(nuevo_nombre.encode()).hexdigest()[:6]}",
                            "Nombre": nuevo_nombre,
                            "Dirección": nueva_direccion,
                            "Categoría": nueva_categoria,
                            "Lat": nueva_lat,
                            "Lng": nueva_lng,
                            "Teléfono": nuevo_tel or "No disponible",
                            "Web": nueva_web or "No disponible",
                            "Seleccionado": True
                        }
                        df_nuevo = pd.DataFrame([nuevo])

                        # Si ya había un df_editado, lo usamos para mantener selecciones
                        if st.session_state.df_editado is not None:
                            df_actual = st.session_state.df_editado.copy()
                        else:
                            df_actual = st.session_state.df_lugares.copy()

                        # Concatenamos el nuevo lugar respetando lo anterior
                        df_actual = pd.concat([df_actual, df_nuevo], ignore_index=True)

                        # Actualizamos ambos estados
                        st.session_state.df_lugares = df_actual
                        st.session_state.df_editado = df_actual

                        st.success(f"✅ Se añadió el lugar '{nuevo_nombre}' correctamente.")
                        st.rerun()

        # ----------- Confirmar selección y generar ruta -----------
        if st.session_state.df_filtrado is not None and not st.session_state.df_filtrado.empty:
            if st.button("✅ Confirmar selección y generar ruta"):
                origen_guardado = st.session_state.get("origen")
                destino_guardado = st.session_state.get("destino")

                punto_inicio = obtener_coordenadas_desde_nombre(origen_guardado) if origen_guardado else None
                if origen_guardado and not punto_inicio:
                    st.warning("⚠️ No se pudo obtener coordenadas del punto de inicio.")

                punto_final = obtener_coordenadas_desde_nombre(destino_guardado) if destino_guardado else None
                if destino_guardado and not punto_final:
                    st.warning("⚠️ No se pudo obtener coordenadas del punto de fin.")

                with st.spinner("Calculando ruta optimizada..."):
                    try:
                        ruta, coords_ordenadas, instrucciones = obtener_ruta_optimizada(
                            st.session_state.df_filtrado,
                            punto_inicio=punto_inicio,
                            punto_final=punto_final,
                            profile=modo_transporte
                        )
                        st.session_state.ruta = ruta
                        st.session_state.coords_ordenadas = coords_ordenadas
                        st.session_state.instrucciones = instrucciones
                        st.session_state.seleccion_confirmada = True
                        st.success("✅ Ruta optimizada generada correctamente.")
                    except Exception as e:
                        st.error(f"❌ Error al calcular la ruta: {e}")
        else:
            st.info("Selecciona al menos un lugar para continuar.")

# ----------- Mostrar mapa e instrucciones si hay ruta confirmada -----------
if (
    st.session_state.seleccion_confirmada
    and st.session_state.ruta is not None
    and st.session_state.coords_ordenadas is not None
    and st.session_state.df_filtrado is not None
    and not st.session_state.df_filtrado.empty
):
    st.markdown("## 🗺️ Mapa de la ruta optimizada")
    mapa = generar_mapa_ruta(
        st.session_state.ruta,
        st.session_state.coords_ordenadas,
        st.session_state.df_filtrado
    )
    st_folium(mapa, width=1000, height=600)
      
    resumen = st.session_state.ruta['features'][0]['properties']['summary']# viene del resultado de OpenRouteService
    distancia_km = resumen["distance"] / 1000   # metros -> km
    duracion_min = resumen["duration"] / 60 # segundos -> min
    st.metric("Distancia total", f"{distancia_km:.2f} km")
    st.metric("Tiempo estimado", f"{duracion_min:.1f} min")

    st.markdown("## 🧭 Instrucciones de la ruta")
    for paso in st.session_state.instrucciones:
        st.markdown(f"- {paso}")

    # ----------- Guardar ruta -----------
    st.markdown("### 💾 Guardar esta ruta")
    if st.button("💾 Guardar ruta en historial"):
        if "rutas_guardadas" not in st.session_state:
            st.session_state.rutas_guardadas = []

        nueva_ruta = {
            "lugares": st.session_state.df_filtrado.to_dict(orient="records"),
            "coords": st.session_state.coords_ordenadas,
            "instrucciones": st.session_state.instrucciones,
            "ruta_geojson": st.session_state.ruta,
            "fecha_hora": f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "origen": st.session_state.get("origen", "No especificado"),
            "destino": st.session_state.get("destino", "No especificado"),
            "distancia_km": distancia_km, 
            "duracion_min": duracion_min   
        }

        # Crear un hash único para detectar duplicados (dos rutas que contienen exactamente los mismos lugares y coordenadas producirán el mismo hash)
        ruta_str = str(nueva_ruta["lugares"]) + str(nueva_ruta["coords"])   #texto único que representa esa ruta
        ruta_hash = hashlib.sha256(ruta_str.encode()).hexdigest()           #genera un hash único de 64 caracteres (hexadecimal) usando el algoritmo SHA-256
        nueva_ruta["hash"] = ruta_hash

        # Verificar si ya existe una ruta con ese hash
        hashes_existentes = [ruta.get("hash") for ruta in st.session_state.rutas_guardadas]
        if ruta_hash in hashes_existentes:
            st.warning("⚠️ Esta ruta ya ha sido guardada previamente.")
        else:
            st.session_state.rutas_guardadas.append(nueva_ruta)
            st.success("✅ Ruta guardada correctamente. Puedes consultarla en el Historial.")



