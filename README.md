# 🌟 Caza de Exoplanetas con IA

Una aplicación web moderna para la detección y análisis de exoplanetas utilizando inteligencia artificial y datos de las misiones espaciales de la NASA.

## 🚀 Características

- **Predicción con IA**: Analiza candidatos a exoplanetas utilizando algoritmos de machine learning
- **Datos de la NASA**: Integración con datasets de las misiones Kepler, K2 y TESS
- **Interfaz Moderna**: Diseño responsive con visualizaciones interactivas
- **Análisis Visual**: Dashboard con estadísticas y gráficos de los datos
- **API RESTful**: Endpoints para integración con modelos externos
- **Administración**: Panel de administración completo para gestión de datos

## 🛠️ Tecnologías Utilizadas

- **Backend**: Django 5.2.7
- **Frontend**: Bootstrap 5, Chart.js, Plotly.js
- **Base de Datos**: SQLite (desarrollo)
- **Lenguaje**: Python 3.13+

## 📦 Instalación

1. **Clonar el repositorio**:
```bash
git clone https://github.com/tu-usuario/Hunting_EXOplanets-with-AI.git
cd Hunting_EXOplanets-with-AI
```

2. **Crear entorno virtual**:
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

3. **Instalar dependencias**:
```bash
pip install -r requirements.txt
```

4. **Configurar la base de datos**:
```bash
python manage.py migrate
```

5. **Crear superusuario**:
```bash
python manage.py createsuperuser
```

6. **Cargar datos de ejemplo** (opcional):
```bash
python create_sample_data.py
```

7. **Ejecutar el servidor**:
```bash
python manage.py runserver
```

8. **Abrir en el navegador**:
```
http://127.0.0.1:8000
```

## 🎯 Uso de la Aplicación

### Página Principal
- Vista general de estadísticas de exoplanetas
- Acceso rápido a las principales funcionalidades
- Información sobre datasets disponibles

### Predicción de Exoplanetas
1. Ve a "Predecir" en el menú principal
2. Completa el formulario con los parámetros del candidato:
   - Período orbital (días)
   - Duración del tránsito (horas)
   - Radio planetario (radios terrestres)
   - Características estelares
   - Parámetros de tránsito
3. El sistema analizará los datos y proporcionará una predicción con nivel de confianza

### Explorar Candidatos
- Lista completa de candidatos a exoplanetas
- Filtros por clasificación, dataset y búsqueda de texto
- Vista detallada de cada candidato
- Opción de analizar candidatos existentes con IA

### Dashboard de Análisis
- Estadísticas generales de la base de datos
- Gráficos de distribución de características
- Comparación entre misiones espaciales
- Visualizaciones interactivas

### Subir Datasets
- Carga archivos CSV o Excel con datos de exoplanetas
- Mapeo automático de columnas
- Validación de formato y datos

## 🔌 Integración con API Externa

La aplicación está preparada para conectarse con un modelo de IA externo. Para configurar la conexión:

1. **Modifica la URL de la API** en `app/views.py`:
```python
# Línea 135 - Reemplaza con tu endpoint real
api_url = "https://tu-api-endpoint.com/predict"
```

2. **Configura el formato de datos** según tu API:
```python
# En la función prediction_form, ajusta el formato de envío
prediction_data = {
    'orbital_period': form.cleaned_data['orbital_period'],
    'transit_duration': form.cleaned_data['transit_duration'],
    # ... otros campos
}
```

3. **Procesa la respuesta** de tu API:
```python
# Ajusta según el formato de respuesta de tu modelo
response = requests.post(api_url, json=prediction_data)
result = response.json()
```

## 📊 Estructura de la Base de Datos

### ExoplanetDataset
- Información sobre datasets de misiones espaciales
- Campos: nombre, misión, descripción, URL fuente

### ExoplanetCandidate
- Datos de candidatos a exoplanetas
- Características físicas y parámetros de tránsito
- Clasificación y predicciones ML

### PredictionRequest
- Historial de predicciones realizadas
- Datos de entrada y resultados
- Información de la API externa

### AnalysisSession
- Sesiones de análisis de usuarios
- Parámetros y resultados de análisis

## 🎨 Personalización

### Temas y Colores
Los colores y estilos se pueden personalizar en `app/templates/app/base.html`:
```css
:root {
    --primary-color: #1a1a2e;
    --secondary-color: #16213e;
    --accent-color: #0f3460;
    --highlight-color: #e94560;
}
```

### Agregar Nuevas Visualizaciones
1. Crea nuevas vistas en `app/views.py`
2. Añade templates en `app/templates/app/`
3. Configura URLs en `app/urls.py`

## 🚀 Despliegue en Producción

1. **Configurar variables de entorno**:
```bash
export DEBUG=False
export SECRET_KEY='tu-clave-secreta'
export DATABASE_URL='postgresql://...'
```

2. **Configurar base de datos PostgreSQL**:
```python
# En settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'exoplanet_ai',
        'USER': 'usuario',
        'PASSWORD': 'contraseña',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

3. **Configurar archivos estáticos**:
```python
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
```

4. **Usar un servidor WSGI** como Gunicorn:
```bash
pip install gunicorn
gunicorn myproject.wsgi:application
```

## 🤝 Contribuir

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📝 Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.

## 📞 Contacto

- **Desarrollador**: [Tu Nombre]
- **Email**: tu-email@ejemplo.com
- **Proyecto**: [https://github.com/tu-usuario/Hunting_EXOplanets-with-AI](https://github.com/tu-usuario/Hunting_EXOplanets-with-AI)

## 🙏 Agradecimientos

- NASA por los datasets de exoplanetas
- Comunidad de Django por el framework
- Desarrolladores de las librerías utilizadas

---

⭐ ¡Si te gusta este proyecto, no olvides darle una estrella! ⭐
 Los datos de varias misiones espaciales dedicadas a la
 exploración de exoplanetas han permitido el descubrimiento
 de miles de nuevos planetas fuera de nuestro sistema solar,
 pero la mayoría de estos exoplanetas fueron identificados de
 manera manual. Con los avances en inteligencia artificial y
 aprendizaje automático (IA/ML), ahora es posible analizar
 automáticamente grandes conjuntos de datos recopilados
 por estas misiones para identificar exoplanetas.
 Tu reto es crear un modelo de IA/ML entrenado con uno o
 más de los conjuntos de datos de exoplanetas de código
 abierto que ofrece la NASA, y que sea capaz de analizar
 nuevos datos para identificar exoplanetas con precisión.
