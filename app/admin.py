from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import ExoplanetDataset, ExoplanetCandidate, PredictionRequest, AnalysisSession, UserProfile

@admin.register(ExoplanetDataset)
class ExoplanetDatasetAdmin(admin.ModelAdmin):
    list_display = ['name', 'mission', 'is_active', 'created_at']
    list_filter = ['mission', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    list_editable = ['is_active']
    ordering = ['-created_at']

@admin.register(ExoplanetCandidate)
class ExoplanetCandidateAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'dataset', 'classification', 'orbital_period', 
        'planetary_radius', 'ml_prediction', 'ml_confidence', 'created_at'
    ]
    list_filter = [
        'classification', 'ml_prediction', 'dataset__mission', 
        'dataset', 'created_at'
    ]
    search_fields = ['name', 'koi_id', 'tess_id']
    list_editable = ['classification', 'ml_prediction']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'koi_id', 'tess_id', 'dataset')
        }),
        ('Características Físicas', {
            'fields': (
                'orbital_period', 'transit_duration', 'planetary_radius',
                'stellar_radius', 'stellar_mass', 'stellar_effective_temperature'
            )
        }),
        ('Parámetros de Tránsito', {
            'fields': (
                'transit_depth', 'impact_parameter', 'equilibrium_temperature'
            )
        }),
        ('Clasificación', {
            'fields': ('classification', 'ml_prediction', 'ml_confidence')
        }),
        ('Datos Adicionales', {
            'fields': ('additional_data',),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('dataset')

@admin.register(PredictionRequest)
class PredictionRequestAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'user', 'prediction', 'confidence', 'api_endpoint', 'created_at'
    ]
    list_filter = ['prediction', 'created_at', 'user']
    search_fields = ['input_data__name', 'user__username']
    readonly_fields = ['created_at', 'api_response']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Información de la Solicitud', {
            'fields': ('user', 'api_endpoint', 'created_at')
        }),
        ('Datos de Entrada', {
            'fields': ('input_data',)
        }),
        ('Resultados', {
            'fields': ('prediction', 'confidence', 'prediction_details')
        }),
        ('Respuesta de la API', {
            'fields': ('api_response',),
            'classes': ('collapse',)
        })
    )

@admin.register(AnalysisSession)
class AnalysisSessionAdmin(admin.ModelAdmin):
    list_display = ['session_id', 'user', 'selected_dataset', 'created_at']
    list_filter = ['created_at', 'user', 'selected_dataset']
    search_fields = ['session_id', 'user__username']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Información de la Sesión', {
            'fields': ('user', 'session_id', 'created_at', 'updated_at')
        }),
        ('Configuración', {
            'fields': ('selected_dataset', 'analysis_parameters')
        }),
        ('Resultados', {
            'fields': ('analysis_results',),
            'classes': ('collapse',)
        })
    )

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'user_type', 'institution', 'created_at']
    list_filter = ['user_type', 'created_at']
    search_fields = ['user__username', 'user__email', 'user__first_name', 'user__last_name', 'institution']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Usuario', {
            'fields': ('user',)
        }),
        ('Información del Perfil', {
            'fields': ('user_type', 'institution', 'bio')
        }),
    )

# Personalización del admin
admin.site.site_header = "ExoPlanet AI - Administración"
admin.site.site_title = "ExoPlanet AI Admin"
admin.site.index_title = "Panel de Administración"
