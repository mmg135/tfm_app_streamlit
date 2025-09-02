import requests
import pandas as pd
from typing import List, Optional, Dict, Literal
import os
from dotenv import load_dotenv
import openrouteservice
from openrouteservice.optimization import Vehicle, Job
import folium
from folium.features import DivIcon
from folium import FeatureGroup
from groq import Groq

load_dotenv();

# Carga de API Keys desde variables de entorno
ORS_API_KEY = os.getenv('ORS_API_KEY') 
FOURSQUARE_API_KEY = os.getenv('FOURSQUARE_API_KEY') 
GROQ_API_KEY = os.getenv('GROQ_API_KEY')


def buscar_lugares(
    query: str,
    radius: int,
    latitude: float,
    longitude: float
):
    """
        Busca lugares específicos en una ubicación determinada usando la API de Foursquare 
        y valida los resultados con un modelo de lenguaje LLM.

        Parámetros:
        -----------
        query : str
            Término de búsqueda que se enviará a la API de Foursquare. 
        
        radius : int
            Radio de búsqueda en metros desde las coordenadas indicadas.

        latitude : float
             Latitud del punto central de búsqueda.

        longitude : float
             Longitud del punto central de búsqueda.

        Proceso:
        --------
        - Consulta la API de Foursquare para obtener lugares que coincidan con el término (query) y área especificados.  
        - Extrae información relevante (nombre, dirección, categoría, coordenadas, etc.).
        - Utiliza un modelo LLM (en este caso, Groq con LLaMA 3) para validar si realmente coniciden con la query.
        - Filtra los resultados y descarta los lugares no válidos.

        Devuelve:
        --------
        df_filtrado: pd.DataFrame 
            Un DataFrame con los lugares validados, conteniendo las columnas:
            'ID', 'Nombre', 'Dirección', 'Categoría', 'Lat', 'Lng', 'Teléfono', 'Web'.
    """

    # Configuración de la API de Foursquare
    url = "https://places-api.foursquare.com/places/search"
    headers = {
        "accept": "application/json",
        "X-Places-Api-Version": "2025-06-17",
        "authorization": f"Bearer {FOURSQUARE_API_KEY}"
    }
    params = {
        "query": query,
        "ll": f"{latitude},{longitude}",
        "radius": radius,
        "limit": 50
    }
    
    # Petición a la API de Foursquare
    response = requests.get(url, headers=headers, params=params)
    data = response.json()

    # Procesamiento de resultados obtenidos de la API
    lugares = []
    for lugar in data.get("results", []):
        lugares.append({
            "ID": lugar.get("fsq_place_id","No disponible"),
            "Nombre": lugar.get("name", "No disponible"),
            "Dirección": lugar.get("location", {}).get("formatted_address", "No disponible"),
            "Categoría": next((c.get("name") for c in lugar.get("categories", []) if c.get("name")), "No disponible"),
            "Lat": lugar.get("latitude", "No disponible"),
            "Lng": lugar.get("longitude", "No disponible"),
            "Teléfono": lugar.get("tel", "No disponible"),
            "Web": lugar.get("website", "No disponible")
        })

    df = pd.DataFrame(lugares).replace(['', ' ', None], 'No disponible')

    # Inicializa el cliente Groq para validación LLM
    groq_client = Groq()

    # Almacenamos los lugares validados 
    lugares_confirmados = []

    for _, row in df.iterrows():
        nombre = row["Nombre"]
        categoria = row["Categoría"]

        # Prompt de validación al LLM
        prompt = f"""
        El lugar tiene el nombre "{nombre}" y la categoría "{categoria}".
        ¿Este lugar es un/a {query}? Responde solo "sí" o "no".
        """
        try:
            completion = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=5
            )
            respuesta = completion.choices[0].message.content.strip().lower()
            es_lugar = "sí" in respuesta

        except Exception as e:
            print(f"Error al validar '{nombre}':", e)
            es_lugar = False  # Por seguridad, descartar si falla

        if es_lugar:
            lugares_confirmados.append(row)

    # Crear DataFrame final con los lugares confirmados
    df_filtrado = pd.DataFrame(lugares_confirmados).reset_index(drop=True)

    return df_filtrado


def obtener_ruta_optimizada(
    df: pd.DataFrame, 
    profile: Literal["driving-car", "foot-walking", "cycling-regular", "driving-hgv", "wheelchair"],
    punto_inicio: List[float], 
    punto_final: Optional[List[float]] = None
):
    """
    Calcula una ruta optimizada para visitar múltiples ubicaciones usando la API de OpenRouteService.
    Permite definir puntos de inicio y fin personalizados. 
    El punto de inicio es obligatorio y el punto de fin es opcional.

    Parámetros:
    -----------
    df : pd.DataFrame
        DataFrame que debe contener al menos las columnas 'Lat' y 'Lng',
        correspondientes a la latitud y longitud de cada lugar a visitar.

    profile: {"driving-car", "foot-walking", "cycling-regular", "driving-hgv", "wheelchair"}
        Perfil de transporte usado por ORS. Cada perfil aplica reglas distintas:
        - "driving-car"     : coche particular (carreteras normales).
        - "foot-walking"    : caminando (calles peatonales, accesos).
        - "cycling-regular" : bicicleta (evita autopistas, prioriza carriles bici).
        - "driving-hgv"     : camión (considera restricciones de peso, altura).
        - "wheelchair"      : accesible en silla de ruedas (pendientes y superficies adaptadas).
    
    punto_inicio : list [lng, lat]
        Coordenadas del punto desde donde debe comenzar la ruta. Parámetro obligatorio.

    punto_final : list [lng, lat], opcional
        Coordenadas donde debe finalizar la ruta.
        Si no se proporciona, ORS optimizará libremente el punto final.

    Proceso:
    --------
    - Define las ubicaciones a visitar como "jobs".
    - Crea un "vehicle" desde el punto de inicio indicado.
    - Llama al servicio de optimización de OpenRouteService.
    - Obtiene el orden óptimo de visitas.
    - Calcula la ruta final con instrucciones paso a paso.

    Devuelve:
    --------
    tuple:
        ruta : geojson (dict)
            Ruta en formato GeoJSON con información detallada del recorrido.
        coordenadas_ordenadas : List[List[float]]
            Lista de coordenadas [lng, lat] en orden de visita.
        instrucciones: List[str] 
            Lista de instrucciones legibles paso a paso para seguir la ruta.
    """

    # Inicializar el cliente de la API ORS
    client = openrouteservice.Client(key=ORS_API_KEY)

    # Verificación de puntos mínimos
    if len(df) < 1:
        raise ValueError("Se necesita al menos un lugar para calcular una ruta.")
    
    # Extraer lista de coordenadas desde el DataFrame
    coords_lugares = df[["Lng", "Lat"]].values.tolist()

    # Definir vehículo con punto de inicio
    vehicle_kwargs = {
        'id': 1,
        'profile': profile,
        'start': punto_inicio
    }

    # Si no se especifica punto de fin, ORS elegirá libremente el mejor punto de fin según la optimización.
    if punto_final:
        vehicle_kwargs['end'] = punto_final

    vehicle = Vehicle(**vehicle_kwargs)
        

    # Crear 'jobs' (puntos a visitar) excepto el primero y el último
    jobs = [
        Job(id=i+1, location=coord)
        for i, coord in enumerate(coords_lugares)
    ]

    # Obtener resultado de optimización
    result = client.optimization(
        jobs=jobs,
        vehicles=[vehicle]
    )

    # Extraer orden de visitas (IDs de los jobs)
    orden_ids = [step["job"] for step in result["routes"][0]["steps"] if step["type"] == "job"]

    # Obtener coordenadas optimizadas: inicio + coordenadas de los lugares en orden
    coords_ordenadas = [punto_inicio] + [coords_lugares[i - 1] for i in orden_ids]  # i - 1 porque job.id = i+1

    if punto_final:
        coords_ordenadas.append(punto_final)

    # Obtener la ruta completa con instrucciones en GeoJSON
    ruta = client.directions(
        coordinates=coords_ordenadas,
        profile=profile,
        format='geojson',
        instructions=True
    )

    # Extraer instrucciones legibles
    instrucciones = []
    for feature in ruta["features"]:
        steps = feature["properties"].get("segments", [])[0].get("steps", [])
        for i, step in enumerate(steps):
            instrucciones.append(f"{i+1}. {step['instruction']} ({step['distance']:.0f} m)")

    return ruta, coords_ordenadas, instrucciones


def obtener_coordenadas_desde_nombre(nombre_lugar: str):
    """
    Obtiene las coordenadas [longitud, latitud] de un lugar a partir de su dirección,
    usando el servicio de geocodificación de OpenStreetMap (Nominatim).

    Parámetros
    ----------
    nombre_lugar : str
        Dirección del lugar (Calle, Número, Ciudad, Provincia, País).

    Devuelve
    -------
    list [lng, lat] o None
        Lista con las coordenadas en el formato [longitud, latitud],
        o None si no se encuentra el lugar.
    """

    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": nombre_lugar,
        "format": "json",
        "limit": 1
    }
    headers = {
        "User-Agent": "PlanificadorDeRutasApp/1.0 (maria.martinez135@alu.uclm.es)"  # requerido por Nominatim
    }

    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()

        if not data:
            return None

        lat = float(data[0]["lat"])
        lon = float(data[0]["lon"])
        return [lon, lat]

    except Exception as e:
        print(f"Error al obtener coordenadas para '{nombre_lugar}': {e}")
        return None
    


def generar_mapa_ruta(
    ruta: Dict,
    coords_ordenadas: List[List[float]],
    df_lugares: pd.DataFrame
):
    """
    Genera un mapa interactivo con la ruta optimizada entre varios lugares,
    marcando el orden de visita y diferenciando el punto de inicio y fin.

    Parámetros:
    -----------
    ruta : Dict
        Objeto GeoJSON generado por la API de OpenRouteService que contiene la geometría de 
        la ruta optimizada y los pasos detallados del trayecto.

    coords_ordenadas : list of [lng, lat]
        Lista de coordenadas ordenadas que representan el recorrido optimizado,
        incluyendo el punto de inicio y fin (pueden o no estar en df_lugares)

    df_lugares : pd.DataFrame
        DataFrame con los lugares validados a visitar, que debe contener al menos las columnas:
         'Nombre', 'Dirección', 'Lat', 'Lng'.

    Comportamiento:
    ---------------
    - El mapa se centra en el primer punto del recorrido.
    - Dibuja la ruta en rojo usando geometría GeoJSON.
    - Coloca marcadores numerados en todos los puntos de la ruta.
    - Usa colores diferenciados según el tipo de punto:
        * Rosa (#FF69B4) → Inicio y fin son el mismo punto.
        * Verde (#28a745) → Punto de inicio.
        * Rojo  (#dc3545) → Punto final.
        * Azul  (#007BFF) → Puntos intermedios.
    - Muestra información contextual (nombre y dirección) si el punto se encuentra en el DataFrame de lugares.
    - Incluye un control de capas para alternar la visibilidad de los marcadores y la ruta.
    - No usa agrupadores de marcadores (`MarkerCluster`).

    Devuelve:
    --------
    folium.Map
        Objeto de tipo `folium.Map` que representa el mapa interactivo generado. 
        Puede visualizarse directamente en Jupyter o guardarse como archivo HTML con `.save('mapa.html')`.

    """
    # Definir punto de inicio y final de la ruta
    punto_inicio = coords_ordenadas[0]
    punto_final = coords_ordenadas[-1]
    mismo_punto = (punto_inicio == punto_final)

    # Crear mapa centrado en el punto de inicio de la ruta (location=[latitud, longitud])
    mapa = folium.Map(
        location=[punto_inicio[1], punto_inicio[0]],
        zoom_start=13,
        control_scale=True
    )

    # Crear capas para marcadores de los lugares y la ruta
    capa_ruta = FeatureGroup(name="Ruta (línea roja)", show=True)
    capa_marcadores = FeatureGroup(name="Lugares a visitar", show=True)

    # Decidir si usar MarkerCluster según número de puntos
    if len(coords_ordenadas) > 30:
        marker_container = folium.plugins.MarkerCluster() 
        marker_container.add_to(capa_marcadores)  # añadir el cluster a la capa
    else:             
        marker_container = capa_marcadores

    # Iterar por cada punto de la ruta
    for i, (lon, lat) in enumerate(coords_ordenadas):
        es_inicio = (i == 0)
        es_final = (i == len(coords_ordenadas) - 1)

        # Evitar duplicado si el punto de inicio y fin es el mismo
        if mismo_punto and es_final and not es_inicio:
            continue

        # Buscar si el punto está en los lugares reconocidos
        lugar = df_lugares[
            (df_lugares["Lat"].round(6) == round(lat, 6)) &
            (df_lugares["Lng"].round(6) == round(lon, 6))
        ]

        # Determinar color del marcador
        if mismo_punto and es_inicio:
            color = "#FF69B4"  # Rosa (inicio y fin)
            nombre = "Inicio y fin del recorrido"
            direccion = ""
        elif es_inicio:
            color = "#28a745"  # Verde
            nombre = "Punto de inicio"
            direccion = ""
        elif es_final:
            color = "#dc3545"  # Rojo
            nombre = "Destino final"
            direccion = ""
        else:
            color = "#007BFF"  # Azul
            nombre = "Punto sin datos"
            direccion = ""

        # Si hay lugar reconocido, actualizar info
        if not lugar.empty:
            nombre = lugar.iloc[0]["Nombre"]
            direccion = lugar.iloc[0]["Dirección"]

        # Crear marcador con número circular
        folium.Marker(
            location=[lat, lon],
            icon=DivIcon(
                icon_size=(30, 30),
                icon_anchor=(15, 15),
                html=f"""<div style="font-size:12pt;
                                    color:white;
                                    background:{color};
                                    border-radius:50%;
                                    width:30px;
                                    height:30px;
                                    text-align:center;
                                    line-height:30px;">
                            {i+1}
                        </div>"""
            ),
            popup=f"<b>{i+1}. {nombre}</b><br>{direccion}",
            tooltip=f"{i+1}. {nombre}"
        ).add_to(marker_container)

    # Dibujar la ruta en color rojo usando GeoJSON
    folium.GeoJson(
        ruta,
        name="Ruta",
        style_function=lambda x: {"color": "red", "weight": 4, "opacity": 0.8}
    ).add_to(capa_ruta)

    # Añadir las capas al mapa
    capa_ruta.add_to(mapa)
    capa_marcadores.add_to(mapa)

    # Añadir control de capas para visibilidad
    folium.LayerControl(collapsed=False).add_to(mapa)

    return mapa
