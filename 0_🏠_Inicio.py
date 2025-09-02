import streamlit as st
from datetime import date

# ---------------- CONFIGURACIÓN DE LA PÁGINA ----------------
st.set_page_config(
    page_title="Inicio",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------- LOGO ----------------
st.logo(
    "./images/logo_cidaen.png",
    size="large",
    link="https://www.cidaen.es/"
)

# ---------------- ENCABEZADO ----------------
st.title("🧠 Asistente inteligente de rutas")
st.header("Planifica, organiza y conversa sobre tus recorridos de forma óptima e interactiva")

st.subheader(
    "Esta aplicación combina la potencia de **Foursquare API** para descubrir lugares, "
    "**OpenRouteService** para calcular rutas optimizadas y **Groq** para que un asistente "
    "inteligente te ayude a resolver cualquier duda sobre tus trayectos."
)

st.markdown("---")

# ---------------- QUÉ PUEDES HACER ----------------
st.markdown("## ¿Qué puedes hacer con esta app?")
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### 🔍 Buscar lugares")
    st.markdown(
        "- Encuentra sitios cercanos según un tipo (ej. talleres, restaurantes, museos).\n"
        "- Define una dirección y un radio de búsqueda."
    )

with col2:
    st.markdown("### 🗺️ Generar rutas")
    st.markdown(
        "- Selecciona tus destinos de la lista o añádelos manualmente.\n"
        "- Calcula la ruta óptima según tu medio de transporte.\n"
        "- Visualízala en un mapa interactivo con instrucciones paso a paso."
    )

with col3:
    st.markdown("### 💬 Conversar con el asistente")
    st.markdown(
        "- Pregunta al asistente información sobre tus rutas guardadas.\n"
        "- Consulta distancias, tiempos, lugares visitados, instrucciones y más.\n"
        "- Ideal para resolver dudas rápidamente."
    )

st.markdown("---")

# ---------------- GUÍA DE USO ----------------
st.markdown("## ¿Cómo usar la aplicación?")
st.markdown(
    """
    1️⃣ Ve a **🗺️ Planificador de ruta** e introduce:
    - Tipo de lugar que quieres visitar.  
    - Dirección de búsqueda.  
    - Radio de búsqueda.  
    - Punto de inicio (**obligatorio**) y punto final (**opcional**) de la ruta.  
    - Modo de transporte.

    2️⃣ Selecciona de la lista los lugares que quieras incluir.  
    3️⃣ (Opcional) Añade manualmente lugares que no aparezcan en la búsqueda.  
    4️⃣ Genera la **ruta optimizada** y visualízala en el mapa.  
    5️⃣ Guarda la ruta en tu historial.  
    6️⃣ Ve al **💬 Chat con el asistente** y conversa sobre cualquier ruta guardada.
    """
)

st.markdown("---")

# ---------------- BOTONES DE NAVEGACIÓN ----------------
st.markdown("## Comienza ahora 🚀")

col1, col2, col3 = st.columns(3)

with col1:
    st.page_link("pages/1_🗺️_Planificador de ruta.py", label="Planificador de ruta", icon="🗺️")

with col2:
    st.page_link("pages/3_📂_Historial y guardado de rutas.py", label="Historial de rutas", icon="📜")

with col3:
    st.page_link("pages/2_🤖 _Chat con el asistente.py", label="Chat con el asistente", icon="💬")

st.markdown("---")

# ---------------- MENSAJE FINAL ----------------
st.success("🎯 ¡Listo para empezar! Explora, organiza y conversa con tu asistente de rutas para planificar tu día de la forma más inteligente y rápida.")