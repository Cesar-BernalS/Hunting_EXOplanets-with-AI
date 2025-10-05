from django.db import models
from django.contrib.auth.models import User
import json

class UserProfile(models.Model):
    """Modelo de perfil de usuario que extiende el User de Django"""
    RESEARCHER = 'RESEARCHER'
    NOVICE = 'NOVICE'
    
    USER_TYPE_CHOICES = [
        (RESEARCHER, 'Investigador'),
        (NOVICE, 'Novato'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    user_type = models.CharField(
        max_length=20,
        choices=USER_TYPE_CHOICES,
        default=NOVICE,
        verbose_name="Tipo de Usuario"
    )
    institution = models.CharField(max_length=200, blank=True, null=True, verbose_name="Institución")
    bio = models.TextField(blank=True, null=True, verbose_name="Biografía")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Perfil de Usuario"
        verbose_name_plural = "Perfiles de Usuario"
    
    def __str__(self):
        return f"{self.user.username} - {self.get_user_type_display()}"
    
    def is_researcher(self):
        return self.user_type == self.RESEARCHER
    
    def is_novice(self):
        return self.user_type == self.NOVICE

class ExoplanetDataset(models.Model):
    """Modelo para almacenar información sobre datasets de exoplanetas"""
    name = models.CharField(max_length=200, verbose_name="Nombre del Dataset")
    mission = models.CharField(max_length=50, verbose_name="Misión")  # Kepler, K2, TESS
    description = models.TextField(verbose_name="Descripción")
    source_url = models.URLField(verbose_name="URL de Origen")
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.mission} - {self.name}"

class ExoplanetCandidate(models.Model):
    """Modelo para almacenar datos de candidatos a exoplanetas"""
    dataset = models.ForeignKey(ExoplanetDataset, on_delete=models.CASCADE, verbose_name="Dataset")
    
    # Identificación básica
    name = models.CharField(max_length=100, verbose_name="Nombre")
    koi_id = models.CharField(max_length=50, blank=True, null=True, verbose_name="KOI ID")
    tess_id = models.CharField(max_length=50, blank=True, null=True, verbose_name="TESS ID")
    
    # Características físicas
    orbital_period = models.FloatField(help_text="Período orbital en días", verbose_name="Período Orbital")
    transit_duration = models.FloatField(help_text="Duración del tránsito en horas", verbose_name="Duración del Tránsito")
    planetary_radius = models.FloatField(help_text="Radio planetario en radios terrestres", verbose_name="Radio Planetario")
    stellar_radius = models.FloatField(help_text="Radio estelar en radios solares", verbose_name="Radio Estelar")
    stellar_mass = models.FloatField(help_text="Masa estelar en masas solares", verbose_name="Masa Estelar")
    stellar_effective_temperature = models.FloatField(help_text="Temperatura efectiva estelar en Kelvin", verbose_name="Temperatura Estelar")
    
    # Parámetros de tránsito
    transit_depth = models.FloatField(help_text="Profundidad del tránsito (adimensional)", verbose_name="Profundidad del Tránsito")
    impact_parameter = models.FloatField(help_text="Parámetro de impacto", verbose_name="Parámetro de Impacto")
    equilibrium_temperature = models.FloatField(help_text="Temperatura de equilibrio en Kelvin", verbose_name="Temperatura de Equilibrio")
    
    # Clasificación
    CONFIRMED = 'CONFIRMED'
    CANDIDATE = 'CANDIDATE'
    FALSE_POSITIVE = 'FALSE_POSITIVE'
    UNKNOWN = 'UNKNOWN'
    
    CLASSIFICATION_CHOICES = [
        (CONFIRMED, 'Exoplaneta Confirmado'),
        (CANDIDATE, 'Candidato Planetario'),
        (FALSE_POSITIVE, 'Falso Positivo'),
        (UNKNOWN, 'Desconocido'),
    ]
    
    classification = models.CharField(
        max_length=20,
        choices=CLASSIFICATION_CHOICES,
        default=UNKNOWN,
        verbose_name="Clasificación"
    )
    
    # Predicción ML
    ml_prediction = models.CharField(
        max_length=20,
        choices=CLASSIFICATION_CHOICES,
        blank=True,
        null=True,
        verbose_name="Predicción ML"
    )
    ml_confidence = models.FloatField(blank=True, null=True, help_text="Puntuación de confianza del modelo ML", verbose_name="Confianza ML")
    
    # Datos adicionales como JSON
    additional_data = models.JSONField(default=dict, blank=True, verbose_name="Datos Adicionales")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Candidato a Exoplaneta"
        verbose_name_plural = "Candidatos a Exoplanetas"
    
    def __str__(self):
        return f"{self.name} - {self.classification}"

class PredictionRequest(models.Model):
    """Modelo para almacenar solicitudes de predicción de usuarios"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Usuario")
    
    # Datos de entrada
    input_data = models.JSONField(verbose_name="Datos de Entrada")
    
    # Resultados de predicción
    prediction = models.CharField(max_length=20, verbose_name="Predicción")
    confidence = models.FloatField(verbose_name="Confianza")
    prediction_details = models.JSONField(default=dict, blank=True, verbose_name="Detalles de Predicción")
    
    # Información de la API externa
    api_endpoint = models.URLField(verbose_name="Endpoint de API")
    api_response = models.JSONField(default=dict, blank=True, verbose_name="Respuesta de API")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Solicitud de Predicción"
        verbose_name_plural = "Solicitudes de Predicción"
    
    def __str__(self):
        return f"Predicción {self.id} - {self.prediction}"

class AnalysisSession(models.Model):
    """Modelo para almacenar sesiones de análisis para rastrear interacciones del usuario"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Usuario")
    session_id = models.CharField(max_length=100, verbose_name="ID de Sesión")
    
    # Datos de sesión
    selected_dataset = models.ForeignKey(ExoplanetDataset, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Dataset Seleccionado")
    
    # Parámetros de análisis
    analysis_parameters = models.JSONField(default=dict, blank=True, verbose_name="Parámetros de Análisis")
    
    # Resultados
    analysis_results = models.JSONField(default=dict, blank=True, verbose_name="Resultados del Análisis")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Sesión de Análisis"
        verbose_name_plural = "Sesiones de Análisis"
    
    def __str__(self):
        return f"Sesión {self.session_id}"
