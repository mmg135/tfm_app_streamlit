import streamlit as st
import pandas as pd
from datetime import datetime
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

# ----------- Inicialización de estado -----------
for key in ["df_lugares", "df_filtrado", "ruta", "coords_ordenadas", "instrucciones", "seleccion_confirmada", "busqueda_realizada"]:
    if key not in st.session_state:
        st.session_state[key] = None

st.session_state.seleccion_confirmada = st.session_state.seleccion_confirmada or False
st.session_state.busqueda_realizada = st.session_state.busqueda_realizada or False

# ----------- Formulario de búsqueda -----------
with st.form("form_planificador"):
    st.subheader("🔍 Parámetros de búsqueda")


    tipo_lugar = st.text_input("**¿Qué tipo de lugar deseas visitar?** (ogligatorio) ", placeholder="Ej: taller de chapa o mecánica de automóviles")
    direccion_central = st.text_input("**Dirección de búsqueda** (ogligatorio)", placeholder="Calle, Ciudad, Provincia, País")
    radio = st.slider("**Radio de búsqueda (en km)**", 1, 500, 10, step=5)
    radio_busqueda = radio * 1000

    col1, col2 = st.columns(2)
    with col1:
        origen = st.text_input("**🟢 Punto de inicio ruta** (ogligatorio)", placeholder="Calle, Ciudad, Provincia, País")
    with col2:
        destino = st.text_input("**🔴 Punto de fin ruta** (opcional)", placeholder="Calle, Ciudad, Provincia, País")

    fecha = st.date_input("**Fecha estimada del recorrido** (opcional)")
    hora = st.time_input("**Hora estimada de inicio** (opcional)")

    submitted = st.form_submit_button("🔍 Buscar lugares y continuar")

# ----------- Procesamiento si se envía el formulario -----------
if submitted:
    if not (tipo_lugar and direccion_central and origen):
        st.warning("❗ Por favor, completa al menos el **tipo de lugar**, la **dirección de búsqueda** y **punto de inicio** de la ruta.")
    else:
        with st.spinner("Buscando lugares..."):
            coords_centro = obtener_coordenadas_desde_nombre(direccion_central)

            if not coords_centro:
                st.error("❌ No se pudo obtener coordenadas desde la dirección proporcionada.")
            else:
                df_lugares = buscar_lugares(
                    query=tipo_lugar,
                    radius=radio_busqueda,
                    latitude=coords_centro[1],
                    longitude=coords_centro[0]
                )

                if df_lugares.empty:
                    st.warning("⚠️ No se encontraron lugares válidos.")
                else:
                    st.success(f"✅ Se encontraron {len(df_lugares)} lugares válidos.")
                    st.session_state.df_lugares = df_lugares
                    st.session_state.df_filtrado = None
                    st.session_state.ruta = None
                    st.session_state.seleccion_confirmada = False
                    st.session_state.busqueda_realizada = True

# ----------- Mostrar editor si hay resultados -----------
if st.session_state.busqueda_realizada:

    if st.session_state.seleccion_confirmada:
        if st.button("🔁 Volver a editar selección"):
            st.session_state.seleccion_confirmada = False
            st.session_state.ruta = None
            st.session_state.instrucciones = None
            st.session_state.coords_ordenadas = None

    if st.session_state.df_lugares is not None and not st.session_state.seleccion_confirmada:
        st.markdown("## 🗂️ Selecciona los lugares que deseas visitar")

        df_mostrar = st.session_state.df_lugares.drop(columns=["ID", "Web"], errors="ignore")

        # Añadir columna Seleccionado con True solo si estaba en la selección anterior
        if "Seleccionado" not in df_mostrar.columns or st.session_state.df_filtrado is not None:
            nombres_filtrados = set(st.session_state.df_filtrado["Nombre"]) if st.session_state.df_filtrado is not None else set()
            df_mostrar["Seleccionado"] = df_mostrar["Nombre"].isin(nombres_filtrados)

        edited_df = st.data_editor(
            df_mostrar,
            use_container_width=True,
            column_config={
                "Seleccionado": st.column_config.CheckboxColumn(label="¿Incluir?", default=True)
            },
            disabled=["Nombre", "Dirección", "Categoría", "Lat", "Lng", "Teléfono"]
        )

        df_filtrado = edited_df[edited_df["Seleccionado"]].drop(columns=["Seleccionado"]).reset_index(drop=True)
        st.session_state.df_filtrado = df_filtrado

        # ----------- Añadir lugar manualmente -----------
        st.markdown("### ➕ Añadir lugar manualmente")
        with st.expander("**📍 Añadir nuevo lugar**"):
            nuevo_nombre = st.text_input("**Nombre del lugar**")
            nueva_direccion = st.text_input("**Dirección (usa el formato recomendado)**", placeholder="Calle, Ciudad, Provincia, País")
            nueva_categoria = st.text_input("**Categoría**", value="")
            nuevo_tel = st.text_input("**Teléfono (opcional)**", value="")

            if st.button("✅ Añadir lugar manual"):
                if not nuevo_nombre or not nueva_direccion:
                    st.warning("⚠️ Por favor, introduce nombre y dirección.")
                else:
                    direccion_completa = f"{nuevo_nombre}, {nueva_direccion}"
                    coordenadas = obtener_coordenadas_desde_nombre(direccion_completa)

                    if not coordenadas:
                        st.error("❌ No se pudieron obtener las coordenadas desde el nombre y la dirección.")
                    else:
                        nueva_lat, nueva_lng = coordenadas[1], coordenadas[0]

                        nuevo = {
                            "Nombre": nuevo_nombre,
                            "Dirección": nueva_direccion,
                            "Categoría": nueva_categoria,
                            "Lat": nueva_lat,
                            "Lng": nueva_lng,
                            "Teléfono": nuevo_tel,
                        }

                        # Añadir al DataFrame original y marcarlo como seleccionado
                        df_nuevo = pd.DataFrame([nuevo])
                        df_nuevo["Seleccionado"] = True  # para que el editor lo muestre marcado
                        if "Seleccionado" not in st.session_state.df_lugares.columns:
                            st.session_state.df_lugares["Seleccionado"] = True

                        st.session_state.df_lugares = pd.concat([st.session_state.df_lugares, df_nuevo], ignore_index=True)
                        st.success(f"✅ Se añadió el lugar '{nuevo_nombre}' correctamente.")

        # ----------- Confirmar selección y generar ruta -----------
        if not df_filtrado.empty:
            if st.button("✅ Confirmar selección y generar ruta"):
                punto_inicio = obtener_coordenadas_desde_nombre(origen) 
                if origen and not punto_inicio:
                    st.warning("⚠️ No se pudo obtener coordenadas del punto de inicio.")

                punto_final = obtener_coordenadas_desde_nombre(destino) if destino else None
                if destino and not punto_final:
                    st.warning("⚠️ No se pudo obtener coordenadas del punto de fin.")

                with st.spinner("Calculando ruta optimizada..."):
                    try:
                        ruta, coords_ordenadas, instrucciones = obtener_ruta_optimizada(
                            df_filtrado,
                            punto_inicio=punto_inicio,
                            punto_final=punto_final
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

# ----------- Mostrar instrucciones y mapa si hay ruta confirmada -----------
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
            "fecha_hora": f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        }

        # Crear un hash único para detectar duplicados 
        # Dos rutas que contienen exactamente los mismos lugares y coordenadas producirán el mismo hash
        ruta_str = str(nueva_ruta["lugares"]) + str(nueva_ruta["coords"]) #texto único que representa esa ruta
        ruta_hash = hashlib.sha256(ruta_str.encode()).hexdigest()         #genera un hash único de 64 caracteres (hexadecimal) usando el algoritmo SHA-256.
        nueva_ruta["hash"] = ruta_hash

        # Verificar si ya existe una ruta con ese hash
        hashes_existentes = [ruta.get("hash") for ruta in st.session_state.rutas_guardadas]
        if ruta_hash in hashes_existentes:
            st.warning("⚠️ Esta ruta ya ha sido guardada previamente.")
        else:
            st.session_state.rutas_guardadas.append(nueva_ruta)
            st.success("✅ Ruta guardada correctamente. Puedes consultarla en el Historial.")
