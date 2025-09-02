import streamlit as st
from streamlit_folium import st_folium
import pandas as pd
from functions import generar_mapa_ruta


st.set_page_config(page_title="Historial de Rutas", layout="wide")
st.title("📚 Historial y rutas guardadas")

# Inicializa el historial si no existe
if "rutas_guardadas" not in st.session_state:
    st.session_state.rutas_guardadas = []

# Mostrar historial si hay rutas
if not st.session_state.rutas_guardadas:
    st.info("ℹ️ Aún no has guardado ninguna ruta.")
else:
    # Botón para borrar todo el historial
    if st.button("🗑️ Borrar todo el historial de rutas"):
        st.session_state.rutas_guardadas = []
        st.success("✅ Historial borrado correctamente.")
        st.stop()

    # Mostrar rutas una por una con opción de eliminar
    for idx, ruta in enumerate(reversed(st.session_state.rutas_guardadas)):
        ruta_index = len(st.session_state.rutas_guardadas) - idx - 1
        with st.container():
            st.markdown(f"### 🗓️ Ruta {ruta_index + 1} (guardada el {ruta['fecha_hora']})")

            # Botón para eliminar solo esta ruta
            if st.button("🗑️ Eliminar", key=f"borrar_ruta_{ruta_index}"):
                del st.session_state.rutas_guardadas[ruta_index]
                st.success("✅ Ruta eliminada.")
                st.rerun()

            st.markdown(f"**🟢 Inicio:** {ruta.get('origen', 'No especificado')}")
            st.markdown(f"**🔴 Fin:** {ruta.get('destino', 'No especificado')}")
            st.markdown(f"**Distancia total {ruta['distancia_km']:.2f} km**")
            st.markdown(f"**Tiempo estimado {ruta['duracion_min']:.2f} min**")

            st.markdown("**📍 Lugares visitados en la ruta**")
            df_lugares = pd.DataFrame(ruta["lugares"]).drop(columns=["ID", "Web"], errors="ignore")
            st.dataframe(df_lugares, use_container_width=True)

            st.markdown("**🗺️ Mapa de la ruta optimizada**")
            mapa = generar_mapa_ruta(
                ruta["ruta_geojson"],
                ruta["coords"],
                pd.DataFrame(ruta["lugares"])
            )
            st_folium(mapa, width=1000, height=600, key=f"mapa_{ruta_index}")

            st.markdown("**🧭 Instrucciones de la ruta**")
            for paso in ruta["instrucciones"]:
                st.markdown(f"- {paso}")
    
            st.markdown("---")