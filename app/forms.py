"""
Formularios para la aplicación de detección de exoplanetas
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from .models import ExoplanetDataset, ExoplanetCandidate, UserProfile

class ExoplanetPredictionForm(forms.Form):
    """Formulario para realizar predicciones de exoplanetas"""
    
    # Información básica
    name = forms.CharField(
        max_length=100,
        label="Nombre del Candidato",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: Kepler-442b'
        })
    )
    
    # Características físicas
    orbital_period = forms.FloatField(
        label="Período Orbital (días)",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.001',
            'placeholder': 'Ej: 112.305'
        }),
        help_text="Período orbital en días terrestres"
    )
    
    transit_duration = forms.FloatField(
        label="Duración del Tránsito (horas)",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'placeholder': 'Ej: 2.5'
        }),
        help_text="Duración del tránsito en horas"
    )
    
    planetary_radius = forms.FloatField(
        label="Radio Planetario (radios terrestres)",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'placeholder': 'Ej: 1.34'
        }),
        help_text="Radio del planeta en radios terrestres"
    )
    
    stellar_radius = forms.FloatField(
        label="Radio Estelar (radios solares)",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'placeholder': 'Ej: 0.6'
        }),
        help_text="Radio de la estrella en radios solares"
    )
    
    stellar_mass = forms.FloatField(
        label="Masa Estelar (masas solares)",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'placeholder': 'Ej: 0.61'
        }),
        help_text="Masa de la estrella en masas solares"
    )
    
    stellar_effective_temperature = forms.FloatField(
        label="Temperatura Efectiva Estelar (K)",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '1',
            'placeholder': 'Ej: 4402'
        }),
        help_text="Temperatura efectiva de la estrella en Kelvin"
    )
    
    # Parámetros de tránsito
    transit_depth = forms.FloatField(
        label="Profundidad del Tránsito",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.000001',
            'placeholder': 'Ej: 0.0001'
        }),
        help_text="Profundidad del tránsito (adimensional)"
    )
    
    impact_parameter = forms.FloatField(
        label="Parámetro de Impacto",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'placeholder': 'Ej: 0.3'
        }),
        help_text="Parámetro de impacto (0-1)"
    )
    
    equilibrium_temperature = forms.FloatField(
        label="Temperatura de Equilibrio (K)",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '1',
            'placeholder': 'Ej: 233'
        }),
        help_text="Temperatura de equilibrio del planeta en Kelvin"
    )
    
    def clean_impact_parameter(self):
        """Validar que el parámetro de impacto esté entre 0 y 1"""
        impact = self.cleaned_data.get('impact_parameter')
        if impact is not None and (impact < 0 or impact > 1):
            raise forms.ValidationError("El parámetro de impacto debe estar entre 0 y 1")
        return impact
    
    def clean_orbital_period(self):
        """Validar que el período orbital sea positivo"""
        period = self.cleaned_data.get('orbital_period')
        if period is not None and period <= 0:
            raise forms.ValidationError("El período orbital debe ser mayor que 0")
        return period

class DatasetUploadForm(forms.ModelForm):
    """Formulario para subir datasets de exoplanetas"""
    
    file = forms.FileField(
        label="Archivo de Dataset",
        help_text="Sube un archivo CSV o Excel con los datos de exoplanetas",
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.csv,.xlsx,.xls'
        })
    )
    
    class Meta:
        model = ExoplanetDataset
        fields = ['name', 'mission', 'description', 'source_url']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Kepler Confirmed Planets'
            }),
            'mission': forms.Select(attrs={
                'class': 'form-control'
            }, choices=[
                ('', 'Selecciona una misión'),
                ('Kepler', 'Kepler'),
                ('K2', 'K2'),
                ('TESS', 'TESS'),
                ('Other', 'Otra')
            ]),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descripción del dataset...'
            }),
            'source_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://exoplanetarchive.ipac.caltech.edu/...'
            })
        }
    
    def clean_file(self):
        """Validar el archivo subido"""
        file = self.cleaned_data.get('file')
        if file:
            # Verificar extensión
            allowed_extensions = ['.csv', '.xlsx', '.xls']
            file_extension = file.name.lower().split('.')[-1]
            if f'.{file_extension}' not in allowed_extensions:
                raise forms.ValidationError(
                    f"Tipo de archivo no soportado. Extensiones permitidas: {', '.join(allowed_extensions)}"
                )
            
            # Verificar tamaño (máximo 10MB)
            if file.size > 10 * 1024 * 1024:
                raise forms.ValidationError("El archivo es demasiado grande. Máximo 10MB.")
        
        return file

class CandidateFilterForm(forms.Form):
    """Formulario para filtrar candidatos a exoplanetas"""
    
    search = forms.CharField(
        required=False,
        label="Buscar",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nombre, KOI ID, TESS ID...'
        })
    )
    
    classification = forms.ChoiceField(
        required=False,
        label="Clasificación",
        choices=[('', 'Todas')] + ExoplanetCandidate.CLASSIFICATION_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    dataset = forms.ModelChoiceField(
        required=False,
        label="Dataset",
        queryset=ExoplanetDataset.objects.filter(is_active=True),
        empty_label="Todos los datasets",
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    # Filtros numéricos
    min_orbital_period = forms.FloatField(
        required=False,
        label="Período Orbital Mínimo (días)",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.1',
            'placeholder': 'Ej: 1.0'
        })
    )
    
    max_orbital_period = forms.FloatField(
        required=False,
        label="Período Orbital Máximo (días)",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.1',
            'placeholder': 'Ej: 365.0'
        })
    )
    
    min_planetary_radius = forms.FloatField(
        required=False,
        label="Radio Planetario Mínimo (R⊕)",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.1',
            'placeholder': 'Ej: 0.5'
        })
    )
    
    max_planetary_radius = forms.FloatField(
        required=False,
        label="Radio Planetario Máximo (R⊕)",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.1',
            'placeholder': 'Ej: 10.0'
        })
    )
    
    def clean(self):
        """Validar rangos numéricos"""
        cleaned_data = super().clean()
        
        min_period = cleaned_data.get('min_orbital_period')
        max_period = cleaned_data.get('max_orbital_period')
        
        if min_period and max_period and min_period > max_period:
            raise forms.ValidationError("El período orbital mínimo no puede ser mayor que el máximo")
        
        min_radius = cleaned_data.get('min_planetary_radius')
        max_radius = cleaned_data.get('max_planetary_radius')
        
        if min_radius and max_radius and min_radius > max_radius:
            raise forms.ValidationError("El radio planetario mínimo no puede ser mayor que el máximo")
        
        return cleaned_data

class UserRegistrationForm(UserCreationForm):
    """Formulario personalizado para registro de usuarios"""
    
    user_type = forms.ChoiceField(
        choices=UserProfile.USER_TYPE_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-control'
        }),
        label="Tipo de Usuario"
    )
    
    institution = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Universidad, Instituto, etc.'
        }),
        label="Institución"
    )
    
    bio = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Cuéntanos sobre tu experiencia con exoplanetas...'
        }),
        label="Biografía"
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name')
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre de usuario'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'tu@email.com'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Apellido'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Contraseña'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Confirmar contraseña'})
    
    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            # Crear perfil de usuario
            UserProfile.objects.create(
                user=user,
                user_type=self.cleaned_data['user_type'],
                institution=self.cleaned_data['institution'],
                bio=self.cleaned_data['bio']
            )
        return user

class LoginForm(forms.Form):
    """Formulario de inicio de sesión"""
    
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nombre de usuario',
            'autofocus': True
        }),
        label="Nombre de Usuario"
    )
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Contraseña'
        }),
        label="Contraseña"
    )
    
    remember_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label="Recordarme"
    )
    
    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        
        if username and password:
            user = authenticate(username=username, password=password)
            if not user:
                raise forms.ValidationError("Credenciales inválidas. Inténtalo de nuevo.")
            if not user.is_active:
                raise forms.ValidationError("Esta cuenta está desactivada.")
        
        return self.cleaned_data

class PredictionFilterForm(forms.Form):
    """Formulario para filtrar predicciones"""
    
    user = forms.BooleanField(
        required=False,
        label="Solo mis predicciones",
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    prediction = forms.ChoiceField(
        required=False,
        label="Tipo de Predicción",
        choices=[('', 'Todas')] + ExoplanetCandidate.CLASSIFICATION_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    min_confidence = forms.FloatField(
        required=False,
        label="Confianza Mínima",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'min': '0',
            'max': '1',
            'placeholder': 'Ej: 0.8'
        })
    )
    
    date_from = forms.DateField(
        required=False,
        label="Desde",
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    date_to = forms.DateField(
        required=False,
        label="Hasta",
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
