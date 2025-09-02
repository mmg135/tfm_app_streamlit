import streamlit as st
import pandas as pd
import os
from groq import Groq
from functions import generar_mapa_ruta

st.set_page_config(page_title="Asistente de Rutas", layout="wide")
st.title("💬 Chat con el Asistente de Rutas")

if "rutas_guardadas" not in st.session_state or not st.session_state.rutas_guardadas:
    st.info("ℹ️ No tienes rutas guardadas.")
    st.stop()

# -------- Selección de ruta --------
opciones = [
    f"Ruta {i+1} - guardada el {ruta['fecha_hora']} ({len(ruta['lugares'])} lugares a visitar)"
    for i, ruta in enumerate(st.session_state.rutas_guardadas)
]
sel_index = st.selectbox("Selecciona una ruta del historial", range(len(opciones)), format_func=lambda i: opciones[i])

# Detectar cambio de ruta seleccionada
if "ruta_index_actual" not in st.session_state:
    st.session_state.ruta_index_actual = sel_index

if sel_index != st.session_state.ruta_index_actual:
    st.session_state.chat_messages = []  # Reinicia el chat si cambió de ruta
    st.session_state.ruta_index_actual = sel_index

ruta_sel = st.session_state.rutas_guardadas[sel_index]

# -------- Mostrar info de la ruta --------
st.markdown("### Información de la ruta seleccionada")
st.markdown(f"**🟢 Inicio:** {ruta_sel.get('origen', 'No especificado')}")
st.markdown(f"**🔴 Fin:** {ruta_sel.get('destino', 'No especificado')}")
st.markdown(f"**Distancia total {ruta_sel['distancia_km']:.2f} km**")
st.markdown(f"**Tiempo estimado {ruta_sel['distancia_km']:.2f} min**")
st.markdown("##### 📍 Lugares a visitar en la ruta")
df = pd.DataFrame(ruta_sel["lugares"]).drop(columns=["ID", "Web"], errors="ignore")
st.dataframe(df, use_container_width=True)
st.markdown("##### Chat")

# -------- Inicializar chat --------
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []

# Mostrar historial del chat
for msg in st.session_state.chat_messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# -------- Entrada de chat --------
if prompt := st.chat_input("¿Qué quieres saber sobre esta ruta?"):
    st.session_state.chat_messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Contexto
    contexto = (
        "Aquí tienes los datos de la ruta seleccionada:\n"
        f"- Punto de inicio: {ruta_sel.get('origen', 'No especificado')}\n"
        f"- Punto de fin: {ruta_sel.get('destino', 'No especificado')}\n"
        f"- Información de los lugares a visitar (no incluye inicio y fin): {df.to_dict(orient='records')}\n"
        f"- Instrucciones: {ruta_sel['instrucciones']}\n"
        f"- Coordenadas ordenadas de los lugares (incluyendo inicio y fin): {ruta_sel['coords']}\n"
        f"- Distancia total: {ruta_sel['distancia_km']:.2f} km \n"
        f"- Tiempo estimado: {ruta_sel['duracion_min']:.2f} min \n"
    )

    # Conexión con Groq
    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "Eres un asistente experto en rutas."},
            {"role": "system", "content": contexto},
            *st.session_state.chat_messages
        ]
    )

    answer = response.choices[0].message.content
    st.session_state.chat_messages.append({"role": "assistant", "content": answer})
    with st.chat_message("assistant"):
        st.markdown(answer)