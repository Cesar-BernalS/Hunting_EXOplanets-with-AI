from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
import json
import requests
from .models import ExoplanetDataset, ExoplanetCandidate, PredictionRequest, AnalysisSession, UserProfile
from .forms import ExoplanetPredictionForm, DatasetUploadForm, UserRegistrationForm, LoginForm
import logging

logger = logging.getLogger(__name__)

@login_required
def index(request):
    """Página principal de la aplicación"""
    # Estadísticas generales
    total_candidates = ExoplanetCandidate.objects.count()
    confirmed_exoplanets = ExoplanetCandidate.objects.filter(classification='CONFIRMED').count()
    candidates = ExoplanetCandidate.objects.filter(classification='CANDIDATE').count()
    false_positives = ExoplanetCandidate.objects.filter(classification='FALSE_POSITIVE').count()
    
    # Datasets disponibles
    datasets = ExoplanetDataset.objects.filter(is_active=True)
    
    # Últimas predicciones
    recent_predictions = PredictionRequest.objects.all()[:5]
    
    context = {
        'total_candidates': total_candidates,
        'confirmed_exoplanets': confirmed_exoplanets,
        'candidates': candidates,
        'false_positives': false_positives,
        'datasets': datasets,
        'recent_predictions': recent_predictions,
    }
    
    return render(request, 'app/index.html', context)

@login_required
def dataset_list(request):
    """Lista de datasets disponibles"""
    datasets = ExoplanetDataset.objects.filter(is_active=True)
    
    # Estadísticas por dataset
    dataset_stats = []
    for dataset in datasets:
        stats = {
            'dataset': dataset,
            'total_candidates': ExoplanetCandidate.objects.filter(dataset=dataset).count(),
            'confirmed': ExoplanetCandidate.objects.filter(dataset=dataset, classification='CONFIRMED').count(),
            'candidates': ExoplanetCandidate.objects.filter(dataset=dataset, classification='CANDIDATE').count(),
            'false_positives': ExoplanetCandidate.objects.filter(dataset=dataset, classification='FALSE_POSITIVE').count(),
        }
        dataset_stats.append(stats)
    
    context = {
        'dataset_stats': dataset_stats,
    }
    
    return render(request, 'app/dataset_list.html', context)

@login_required
def candidate_list(request):
    """Lista de candidatos a exoplanetas con filtros"""
    candidates = ExoplanetCandidate.objects.all()
    
    # Filtros
    search_query = request.GET.get('search', '')
    classification_filter = request.GET.get('classification', '')
    dataset_filter = request.GET.get('dataset', '')
    
    if search_query:
        candidates = candidates.filter(
            Q(name__icontains=search_query) |
            Q(koi_id__icontains=search_query) |
            Q(tess_id__icontains=search_query)
        )
    
    if classification_filter:
        candidates = candidates.filter(classification=classification_filter)
    
    if dataset_filter:
        candidates = candidates.filter(dataset_id=dataset_filter)
    
    # Paginación
    paginator = Paginator(candidates, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Opciones para filtros
    datasets = ExoplanetDataset.objects.filter(is_active=True)
    classifications = ExoplanetCandidate.CLASSIFICATION_CHOICES
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'classification_filter': classification_filter,
        'dataset_filter': dataset_filter,
        'datasets': datasets,
        'classifications': classifications,
    }
    
    return render(request, 'app/candidate_list.html', context)

@login_required
def candidate_detail(request, candidate_id):
    """Detalle de un candidato específico"""
    candidate = get_object_or_404(ExoplanetCandidate, id=candidate_id)
    
    # Obtener predicciones relacionadas
    predictions = PredictionRequest.objects.filter(
        input_data__contains={'name': candidate.name}
    )[:5]
    
    context = {
        'candidate': candidate,
        'predictions': predictions,
    }
    
    return render(request, 'app/candidate_detail.html', context)

@login_required
def prediction_form(request):
    """Formulario para hacer predicciones"""
    if request.method == 'POST':
        form = ExoplanetPredictionForm(request.POST)
        if form.is_valid():
            # Aquí se conectaría con la API externa
            # Por ahora simulamos la respuesta
            prediction_data = form.cleaned_data
            
            # Simular llamada a API externa
            try:
                # TODO: Reemplazar con la URL real de la API
                api_url = "https://your-api-endpoint.com/predict"
                
                # Simular respuesta de la API
                mock_response = {
                    'prediction': 'CONFIRMED',
                    'confidence': 0.85,
                    'details': {
                        'probability_confirmed': 0.85,
                        'probability_candidate': 0.10,
                        'probability_false_positive': 0.05
                    }
                }
                
                # Guardar solicitud de predicción
                prediction_request = PredictionRequest.objects.create(
                    user=request.user if request.user.is_authenticated else None,
                    input_data=prediction_data,
                    prediction=mock_response['prediction'],
                    confidence=mock_response['confidence'],
                    prediction_details=mock_response['details'],
                    api_endpoint=api_url,
                    api_response=mock_response
                )
                
                messages.success(request, f'Predicción realizada: {mock_response["prediction"]} (Confianza: {mock_response["confidence"]:.2%})')
                return redirect('prediction_result', prediction_id=prediction_request.id)
                
            except Exception as e:
                logger.error(f"Error en predicción: {str(e)}")
                messages.error(request, 'Error al realizar la predicción. Inténtalo de nuevo.')
    else:
        form = ExoplanetPredictionForm()
    
    context = {
        'form': form,
    }
    
    return render(request, 'app/prediction_form.html', context)

@login_required
def prediction_result(request, prediction_id):
    """Resultado de una predicción"""
    prediction = get_object_or_404(PredictionRequest, id=prediction_id)
    
    context = {
        'prediction': prediction,
    }
    
    return render(request, 'app/prediction_result.html', context)

@login_required
def prediction_history(request):
    """Historial de predicciones"""
    predictions = PredictionRequest.objects.all()
    
    # Filtros
    user_filter = request.GET.get('user', '')
    prediction_filter = request.GET.get('prediction', '')
    
    if user_filter and request.user.is_authenticated:
        predictions = predictions.filter(user=request.user)
    
    if prediction_filter:
        predictions = predictions.filter(prediction=prediction_filter)
    
    # Paginación
    paginator = Paginator(predictions, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'user_filter': user_filter,
        'prediction_filter': prediction_filter,
    }
    
    return render(request, 'app/prediction_history.html', context)

@login_required
def analytics_dashboard(request):
    """Dashboard de análisis y estadísticas"""
    # Estadísticas generales
    total_candidates = ExoplanetCandidate.objects.count()
    confirmed_count = ExoplanetCandidate.objects.filter(classification='CONFIRMED').count()
    candidate_count = ExoplanetCandidate.objects.filter(classification='CANDIDATE').count()
    false_positive_count = ExoplanetCandidate.objects.filter(classification='FALSE_POSITIVE').count()
    
    # Estadísticas por misión
    mission_stats = []
    for mission in ['Kepler', 'K2', 'TESS']:
        datasets = ExoplanetDataset.objects.filter(mission=mission, is_active=True)
        candidates = ExoplanetCandidate.objects.filter(dataset__in=datasets)
        
        mission_stats.append({
            'mission': mission,
            'total': candidates.count(),
            'confirmed': candidates.filter(classification='CONFIRMED').count(),
            'candidates': candidates.filter(classification='CANDIDATE').count(),
            'false_positives': candidates.filter(classification='FALSE_POSITIVE').count(),
        })
    
    # Distribución de períodos orbitales
    orbital_periods = ExoplanetCandidate.objects.filter(
        orbital_period__isnull=False
    ).values_list('orbital_period', flat=True)
    
    # Distribución de radios planetarios
    planetary_radii = ExoplanetCandidate.objects.filter(
        planetary_radius__isnull=False
    ).values_list('planetary_radius', flat=True)
    
    context = {
        'total_candidates': total_candidates,
        'confirmed_count': confirmed_count,
        'candidate_count': candidate_count,
        'false_positive_count': false_positive_count,
        'mission_stats': mission_stats,
        'orbital_periods': list(orbital_periods),
        'planetary_radii': list(planetary_radii),
    }
    
    return render(request, 'app/analytics_dashboard.html', context)

@csrf_exempt
@require_http_methods(["POST"])
def api_predict(request):
    """API endpoint para predicciones (para conectar con la API externa)"""
    try:
        data = json.loads(request.body)
        
        # Validar datos de entrada
        required_fields = [
            'orbital_period', 'transit_duration', 'planetary_radius',
            'stellar_radius', 'stellar_mass', 'stellar_effective_temperature',
            'transit_depth', 'impact_parameter', 'equilibrium_temperature'
        ]
        
        for field in required_fields:
            if field not in data:
                return JsonResponse({'error': f'Campo requerido faltante: {field}'}, status=400)
        
        # TODO: Conectar con la API externa real
        # Por ahora simulamos la respuesta
        mock_response = {
            'prediction': 'CONFIRMED',
            'confidence': 0.85,
            'details': {
                'probability_confirmed': 0.85,
                'probability_candidate': 0.10,
                'probability_false_positive': 0.05
            }
        }
        
        return JsonResponse(mock_response)
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)
    except Exception as e:
        logger.error(f"Error en API predict: {str(e)}")
        return JsonResponse({'error': 'Error interno del servidor'}, status=500)

@login_required
def upload_dataset(request):
    """Formulario para subir datasets - Solo para investigadores"""
    try:
        profile = request.user.profile
        if not profile.is_researcher():
            messages.error(request, 'Solo los investigadores pueden subir datasets. Actualiza tu perfil para obtener acceso.')
            return redirect('profile')
    except UserProfile.DoesNotExist:
        messages.error(request, 'Por favor completa tu perfil primero.')
        return redirect('profile')
    
    if request.method == 'POST':
        form = DatasetUploadForm(request.POST, request.FILES)
        if form.is_valid():
            # Procesar archivo subido
            # TODO: Implementar procesamiento de archivos CSV/Excel
            messages.success(request, 'Dataset subido exitosamente')
            return redirect('dataset_list')
    else:
        form = DatasetUploadForm()
    
    context = {
        'form': form,
    }
    
    return render(request, 'app/upload_dataset.html', context)

def user_login(request):
    """Vista de inicio de sesión"""
    if request.user.is_authenticated:
        return redirect('index')
    
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            remember_me = form.cleaned_data.get('remember_me', False)
            
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                if not remember_me:
                    request.session.set_expiry(0)  # Sesión expira al cerrar navegador
                else:
                    request.session.set_expiry(1209600)  # 2 semanas
                
                messages.success(request, f'¡Bienvenido, {user.get_full_name() or user.username}!')
                return redirect('index')
            else:
                messages.error(request, 'Credenciales inválidas. Inténtalo de nuevo.')
        else:
            messages.error(request, 'Por favor corrige los errores en el formulario.')
    else:
        form = LoginForm()
    
    context = {
        'form': form,
    }
    
    return render(request, 'app/login.html', context)

def user_register(request):
    """Vista de registro de usuarios"""
    if request.user.is_authenticated:
        return redirect('index')
    
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'¡Cuenta creada exitosamente! Bienvenido, {user.username}.')
            return redirect('index')
        else:
            messages.error(request, 'Por favor corrige los errores en el formulario.')
    else:
        form = UserRegistrationForm()
    
    context = {
        'form': form,
    }
    
    return render(request, 'app/register.html', context)

def user_logout(request):
    """Vista de cierre de sesión"""
    logout(request)
    messages.info(request, 'Has cerrado sesión exitosamente.')
    return redirect('index')

@login_required
def user_profile(request):
    """Vista del perfil de usuario"""
    user = request.user
    
    # Obtener o crear perfil
    try:
        profile = user.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=user)
    
    # Estadísticas del usuario
    user_predictions = PredictionRequest.objects.filter(user=user).count()
    user_datasets = ExoplanetDataset.objects.filter(created_at__gte=user.date_joined).count()
    
    context = {
        'user': user,
        'profile': profile,
        'user_predictions': user_predictions,
        'user_datasets': user_datasets,
    }
    
    return render(request, 'app/profile.html', context)
