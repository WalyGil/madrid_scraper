import streamlit as st
from streamlit_folium import st_folium
import folium
import googlemaps
import requests
from urllib.parse import urlparse
import re
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
from pathlib import Path
import time

# Configuración de la página
st.set_page_config(page_title="Buscador de Colaboradores", layout="wide")

# Tipos de colaboradores
COLABORADORES = [
    "Inmobiliarias",
    "Administradores de fincas",
    "Empresas de desocupación",
    "Abogados",
    "Residencias de ancianos",
    "Gestorías",
    "Reformistas",
    "Servicios domésticos",
    "Empresas religiosas",
    "Empresas de mudanzas",
    "Bares",
    "Fruterías",
    "Peluquerías",
    "Centros de masajes",
    "Salones de uñas",
    "Ferreterías"
]

# Zonas geográficas
MUNICIPIOS = [
    "Alcobendas", "Alcorcón", "Coslada", "Fuenlabrada", "Getafe",
    "Leganés", "Móstoles", "Parla", "San Fernando de Henares",
    "San Sebastián de los Reyes", "Torrejón de Ardoz"
]

DISTRITOS = [
    "Tetuán", "Latina", "Carabanchel", "Usera", "Puente de Vallecas",
    "Moratalaz", "Ciudad Lineal", "Hortaleza", "Villaverde",
    "Villa de Vallecas", "Vicálvaro", "San Blas-Canillejas", "Barajas"
]

def extract_social_media(text, website):
    """Extrae enlaces de redes sociales"""
    social_media = {
        'facebook': None,
        'instagram': None,
        'linkedin': None,
        'tiktok': None
    }
    
    patterns = {
        'facebook': r'facebook\.com/[\w\.]+',
        'instagram': r'instagram\.com/[\w\.]+',
        'linkedin': r'linkedin\.com/[\w\-]+',
        'tiktok': r'tiktok\.com/@[\w\.]+'
    }
    
    for platform, pattern in patterns.items():
        match = re.search(pattern, text)
        if match:
            social_media[platform] = match.group(0)
    
    return social_media

def extract_phones(text):
    """Extrae números de teléfono fijos y móviles"""
    fijo_pattern = r'9\d{8}'
    movil_pattern = r'[67]\d{8}'
    
    fijos = re.findall(fijo_pattern, text)
    moviles = re.findall(movil_pattern, text)
    
    return {
        'fijos': fijos if fijos else ['Sin datos por el momento'],
        'moviles': moviles if moviles else ['Sin datos por el momento']
    }

def get_business_details(place_id, gmaps):
    """Obtiene detalles detallados del negocio"""
    try:
        details = gmaps.place(place_id,
            fields=['name', 'formatted_address', 'website', 
                   'formatted_phone_number', 'rating', 'reviews',
                   'postal_code'])
        
        result = details.get('result', {})
        
        # Obtener contenido de la página web si existe
        website_content = ""
        if 'website' in result:
            try:
                response = requests.get(result['website'], timeout=10)
                website_content = response.text
            except:
                website_content = ""
        
        # Extraer datos
        social_media = extract_social_media(website_content, result.get('website', ''))
        phones = extract_phones(website_content + str(result.get('formatted_phone_number', '')))
        emails = extract_emails(website_content)
        
        return {
            'nombre': result.get('name', 'Sin datos por el momento'),
            'direccion': result.get('formatted_address', 'Sin datos por el momento'),
            'website': result.get('website', 'Sin datos por el momento'),
            'codigo_postal': result.get('postal_code', 'Sin datos por el momento'),
            'telefono_fijo': ', '.join(phones['fijos']),
            'telefono_movil': ', '.join(phones['moviles']),
            'email': ', '.join(emails) if emails else 'Sin datos por el momento',
            'facebook': social_media['facebook'] or 'Sin datos por el momento',
            'instagram': social_media['instagram'] or 'Sin datos por el momento',
            'linkedin': social_media['linkedin'] or 'Sin datos por el momento',
            'tiktok': social_media['tiktok'] or 'Sin datos por el momento',
            'rating': result.get('rating', 'Sin datos por el momento')
        }
    except Exception as e:
        st.error(f"Error al obtener detalles: {str(e)}")
        return None

# Interfaz principal
st.title("🏢 Buscador de Colaboradores")

# Selección de filtros
col1, col2 = st.columns(2)

with col1:
    tipo_colaborador = st.selectbox(
        "Tipo de Colaborador",
        COLABORADORES
    )
    
    zona_tipo = st.radio(
        "Tipo de Zona",
        ["Municipio", "Distrito"]
    )
    
    if zona_tipo == "Municipio":
        zona = st.selectbox("Seleccione Municipio", MUNICIPIOS)
    else:
        zona = st.selectbox("Seleccione Distrito", DISTRITOS)

with col2:
    radio_busqueda = st.slider(
        "Radio de búsqueda (km)",
        min_value=1,
        max_value=20,
        value=5
    )
    
    max_resultados = st.slider(
        "Máximo de resultados",
        min_value=5,
        max_value=50,
        value=20
    )

# Botón de búsqueda
if st.button("🔍 Buscar"):
    try:
        # Inicializar Google Maps
        gmaps = googlemaps.Client(key="AIzaSyDUqEMMfHqSQX0KafmepBiZR6SMS_UcTtQ")
        
        # Geocodificar la zona seleccionada
        geocode_result = gmaps.geocode(f"{zona}, Madrid, España")
        
        if geocode_result:
            location = geocode_result[0]['geometry']['location']
            
            with st.spinner("Buscando negocios..."):
                # Realizar búsqueda
                places_result = gmaps.places_nearby(
                    location=(location['lat'], location['lng']),
                    radius=radio_busqueda * 1000,
                    keyword=tipo_colaborador,
                    language='es',
                    max_results=max_resultados
                )
                
                if places_result and places_result.get('results'):
                    businesses = []
                    
                    progress_bar = st.progress(0)
                    for i, place in enumerate(places_result['results'][:max_resultados]):
                        details = get_business_details(place['place_id'], gmaps)
                        if details:
                            businesses.append(details)
                        progress_bar.progress((i + 1) / max_resultados)
                        time.sleep(0.1)  # Para evitar límites de la API
                    
                    if businesses:
                        # Crear DataFrame
                        df = pd.DataFrame(businesses)
                        
                        # Mostrar resultados
                        st.write(f"Se encontraron {len(businesses)} negocios:")
                        st.dataframe(df)
                        
                        # Botón de descarga
                        csv = df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            "📥 Descargar resultados (CSV)",
                            csv,
                            f"colaboradores_{tipo_colaborador}_{zona}.csv",
                            "text/csv",
                            key='download-csv'
                        )
                    else:
                        st.warning("No se encontraron negocios que cumplan con los criterios.")
                else:
                    st.warning("No se encontraron resultados en la zona seleccionada.")
        else:
            st.error("No se pudo encontrar la ubicación especificada.")
            
    except Exception as e:
        st.error(f"Error durante la búsqueda: {str(e)}")

# Footer
st.markdown("""
    <div style='text-align: center; margin-top: 20px;'>
        <br>
        <p>Desarrollado con ❤️ por Marce Data</p>
    </div>
""", unsafe_allow_html=True)
