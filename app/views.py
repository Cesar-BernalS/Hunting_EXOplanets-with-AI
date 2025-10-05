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
from .predictor_adapter import predict_with_kepler_model
import json
from .models import ExoplanetDataset, ExoplanetCandidate, PredictionRequest, AnalysisSession, UserProfile
from .predictor_adapter import batch_probability_from_candidates
from .forms import ExoplanetPredictionForm, DatasetUploadForm, UserRegistrationForm, LoginForm
import logging
from pathlib import Path
import csv
from django.contrib.admin.views.decorators import staff_member_required

logger = logging.getLogger(__name__)

def index(request):
    """Página principal de la aplicación"""
    # Estadísticas generales (mezcla: ML y base de datos)
    total_candidates = ExoplanetCandidate.objects.count()
    # ML counters (predicted)
    predicted_confirmed = 0
    predicted_false = 0
    predicted_candidates = 0
    try:
        # Predecir sobre todos los candidatos (9k aprox)
        preds_all = batch_probability_from_candidates(list(ExoplanetCandidate.objects.all()))
        for p in preds_all:
            if p.get('label') == 'CONFIRMED':
                predicted_confirmed += 1
            elif p.get('label') == 'FALSE_POSITIVE':
                predicted_false += 1
        # Anything not falling clearly into confirmed/false is considered candidate for the counter
        predicted_candidates = max(0, total_candidates - predicted_confirmed - predicted_false)
    except Exception as e:
        logger.warning(f"Conteo ML en index falló: {e}")
    # DB counters (as provided by user data)
    candidates = ExoplanetCandidate.objects.filter(classification='CANDIDATE').count()
    # Mostrar contadores ML en las tarjetas de Confirmados y Falsos
    confirmed_exoplanets = predicted_confirmed if predicted_confirmed else ExoplanetCandidate.objects.filter(classification='CONFIRMED').count()
    false_positives = predicted_false if predicted_false else ExoplanetCandidate.objects.filter(classification='FALSE_POSITIVE').count()
    candidates = predicted_candidates if (predicted_confirmed or predicted_false) else candidates

    # Fallback 2: derive from original Kepler disposition stored in JSON if still zero
    if confirmed_exoplanets == 0 and false_positives == 0 and candidates == 0:
        try:
            # Case-insensitive and tolerant matching by normalizing values in Python if needed
            confirmed_exoplanets = ExoplanetCandidate.objects.filter(additional_data__koi_disposition__iexact='CONFIRMED').count()
            false_positives = ExoplanetCandidate.objects.filter(additional_data__koi_disposition__iexact='FALSE POSITIVE').count()
            candidates = ExoplanetCandidate.objects.filter(additional_data__koi_disposition__iexact='CANDIDATE').count()
            # If still zero candidates, compute as complement when dispositions exist
            if candidates == 0 and (confirmed_exoplanets or false_positives):
                candidates = max(0, total_candidates - confirmed_exoplanets - false_positives)
        except Exception as e:
            logger.warning(f"Conteo por koi_disposition falló: {e}")

    # Fallback 3: if DB has no candidates at all, read counts from kepler_clean.csv directly
    if total_candidates == 0 and confirmed_exoplanets == 0 and false_positives == 0 and candidates == 0:
        try:
            base_dir = Path(__file__).resolve().parent.parent
            csv_path = (base_dir / 'mlapp' / 'models_store' / 'current' / 'kepler_clean.csv')
            if not csv_path.exists():
                csv_path = (base_dir / 'models_store' / 'current' / 'kepler_clean.csv')
            if csv_path.exists():
                c_conf = c_fp = c_cand = 0
                with csv_path.open('r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        disp = (row.get('koi_disposition') or '').strip().upper()
                        if disp == 'CONFIRMED':
                            c_conf += 1
                        elif disp == 'FALSE POSITIVE':
                            c_fp += 1
                        elif disp == 'CANDIDATE':
                            c_cand += 1
                total_candidates = c_conf + c_fp + c_cand
                confirmed_exoplanets = c_conf
                false_positives = c_fp
                candidates = c_cand
        except Exception as e:
            logger.warning(f"Fallback CSV counters falló: {e}")
    
    # Datasets disponibles
    datasets = ExoplanetDataset.objects.filter(is_active=True)
    
    # Últimas predicciones (solo si existen)
    recent_predictions_count = PredictionRequest.objects.count()
    recent_predictions = PredictionRequest.objects.all()[:5] if recent_predictions_count > 0 else None
    
    context = {
        'total_candidates': total_candidates,
        'confirmed_exoplanets': confirmed_exoplanets,
        'candidates': candidates,
        'false_positives': false_positives,
        'datasets': datasets,
        'recent_predictions': recent_predictions,
    }
    
    return render(request, 'app/index.html', context)

def dataset_list(request):
    """Lista de datasets disponibles"""
    datasets = ExoplanetDataset.objects.filter(is_active=True)
    
    # Estadísticas por dataset con la misma lógica de la home
    dataset_stats = []

    # Fallback CSV counts by mission (read once)
    csv_counts_by_mission = {}
    try:
        base_dir = Path(__file__).resolve().parent.parent
        csv_path = (base_dir / 'mlapp' / 'models_store' / 'current' / 'kepler_clean.csv')
        if not csv_path.exists():
            csv_path = (base_dir / 'models_store' / 'current' / 'kepler_clean.csv')
        if csv_path.exists():
            from collections import defaultdict
            acc = defaultdict(lambda: {'total': 0, 'CONFIRMED': 0, 'FALSE POSITIVE': 0, 'CANDIDATE': 0})
            with csv_path.open('r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    mission = (row.get('mission') or 'Kepler').strip()
                    disp = (row.get('koi_disposition') or '').strip().upper()
                    acc[mission]['total'] += 1
                    if disp in ('CONFIRMED', 'FALSE POSITIVE', 'CANDIDATE'):
                        acc[mission][disp] += 1
            csv_counts_by_mission = acc
    except Exception as e:
        logger.warning(f"CSV counts fallback (datasets) falló: {e}")
    for dataset in datasets:
        qs = ExoplanetCandidate.objects.filter(dataset=dataset)
        total = qs.count()
        pred_conf = pred_fp = pred_cand = 0
        try:
            preds = batch_probability_from_candidates(list(qs[:5000]))  # limitar para seguridad
            for p in preds:
                if p.get('label') == 'CONFIRMED':
                    pred_conf += 1
                elif p.get('label') == 'FALSE_POSITIVE':
                    pred_fp += 1
            pred_cand = max(0, total - pred_conf - pred_fp)
        except Exception as e:
            logger.warning(f"Pred count dataset {dataset.id} falló: {e}")

        # BD labels
        db_conf = qs.filter(classification='CONFIRMED').count()
        db_cand = qs.filter(classification='CANDIDATE').count()
        db_fp = qs.filter(classification='FALSE_POSITIVE').count()

        # koi_disposition fallback
        disp_conf = qs.filter(additional_data__koi_disposition__iexact='CONFIRMED').count()
        disp_fp = qs.filter(additional_data__koi_disposition__iexact='FALSE POSITIVE').count()
        disp_cand = qs.filter(additional_data__koi_disposition__iexact='CANDIDATE').count()

        # Resolver con prioridad: ML -> BD -> koi_disposition
        confirmed = pred_conf or db_conf or disp_conf
        false_pos = pred_fp or db_fp or disp_fp
        candidates_cnt = (pred_cand if (pred_conf or pred_fp) else (db_cand or disp_cand))

        # Fallback CSV per mission if DB has zero total
        if total == 0 and dataset.mission in csv_counts_by_mission:
            m = csv_counts_by_mission[dataset.mission]
            total = m['total']
            confirmed = m['CONFIRMED']
            false_pos = m['FALSE POSITIVE']
            candidates_cnt = m['CANDIDATE']

        dataset_stats.append({
            'dataset': dataset,
            'total_candidates': total,
            'confirmed': confirmed,
            'candidates': candidates_cnt,
            'false_positives': false_pos,
            'success_pct': int(round((confirmed / total) * 100)) if total > 0 else 0,
        })
    
    context = {
        'dataset_stats': dataset_stats,
    }
    
    return render(request, 'app/dataset_list.html', context)

def candidate_list(request):
    """Lista de candidatos a exoplanetas con filtros opcionales y paginación (10 por página)."""
    candidates = ExoplanetCandidate.objects.all()

    # Filtros opcionales
    search_query = request.GET.get('search', '').strip()
    classification_filter = request.GET.get('classification', '').strip()
    dataset_filter = request.GET.get('dataset', '').strip()

    if dataset_filter:
        candidates = candidates.filter(dataset_id=dataset_filter)

    if classification_filter:
        candidates = candidates.filter(classification=classification_filter)
    else:
        # Por defecto mostrar solo CANDIDATE si no se especifica clasificación explícita
        candidates = candidates.filter(
            Q(classification__iexact='CANDIDATE') |
            Q(additional_data__koi_disposition__icontains='CANDIDATE') |
            Q(ml_prediction__iexact='CANDIDATE')
        )

    if search_query:
        candidates = candidates.filter(
            Q(name__icontains=search_query) |
            Q(koi_id__icontains=search_query) |
            Q(tess_id__icontains=search_query)
        )

    candidates = candidates.order_by('-created_at').distinct()

    paginator = Paginator(candidates, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Opciones para filtros (solo lo necesario)
    datasets = ExoplanetDataset.objects.filter(is_active=True)

    context = {
        'page_obj': page_obj,
        'datasets': datasets,
    }

    return render(request, 'app/candidate_list.html', context)

def candidate_detail(request, candidate_id):
    """Detalle de un candidato específico"""
    candidate = get_object_or_404(ExoplanetCandidate, id=candidate_id)
    # Predicción rápida para mostrar en cabecera (no persistente)
    try:
        from .predictor_adapter import predict_with_kepler_model
        label, prob, details = predict_with_kepler_model({
            'orbital_period': candidate.orbital_period,
            'transit_duration': candidate.transit_duration,
            'transit_depth': candidate.transit_depth,
            'stellar_effective_temperature': candidate.stellar_effective_temperature,
            'planetary_radius': candidate.planetary_radius,
            'stellar_radius': candidate.stellar_radius,
            'equilibrium_temperature': candidate.equilibrium_temperature,
            'impact_parameter': candidate.impact_parameter,
        })
        candidate.ml_prediction = label
        candidate.ml_confidence = float(prob) * 100.0
    except Exception as e:
        logger.warning(f"Predicción ML en detalle falló: {e}")

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
            # Construir features y predecir con el modelo local de Kepler
            prediction_data = form.cleaned_data
            try:
                label, prob, details = predict_with_kepler_model({
                    'orbital_period': prediction_data.get('orbital_period'),
                    'transit_duration': prediction_data.get('transit_duration'),
                    'transit_depth': prediction_data.get('transit_depth'),
                    'stellar_effective_temperature': prediction_data.get('stellar_effective_temperature'),
                    'planetary_radius': prediction_data.get('planetary_radius'),
                    'stellar_radius': prediction_data.get('stellar_radius'),
                    'equilibrium_temperature': prediction_data.get('equilibrium_temperature'),
                    'impact_parameter': prediction_data.get('impact_parameter'),
                })

                prediction_request = PredictionRequest.objects.create(
                    user=request.user if request.user.is_authenticated else None,
                    input_data=prediction_data,
                    prediction=label,
                    confidence=prob,
                    prediction_details=details,
                    api_endpoint='local-ml-model',
                    api_response={'prediction': label, 'confidence': prob, 'details': details}
                )

                messages.success(request, f'Predicción realizada: {label} (Confianza: {prob:.2%})')
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

def prediction_result(request, prediction_id):
    """Resultado de una predicción"""
    prediction = get_object_or_404(PredictionRequest, id=prediction_id)
    
    context = {
        'prediction': prediction,
    }
    
    return render(request, 'app/prediction_result.html', context)

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

def analytics_dashboard(request):
    """Dashboard de análisis y estadísticas"""
    # Estadísticas generales (mezcla ML/BD/disposition)
    qs_all = ExoplanetCandidate.objects.all()
    total_candidates = qs_all.count()

    # ML counts
    ml_conf = ml_fp = 0
    try:
        preds = batch_probability_from_candidates(list(qs_all[:9000]))
        for p in preds:
            if p.get('label') == 'CONFIRMED':
                ml_conf += 1
            elif p.get('label') == 'FALSE_POSITIVE':
                ml_fp += 1
    except Exception as e:
        logger.warning(f"Analítica ML falló: {e}")

    # DB/disposition fallback
    confirmed_count = ml_conf or qs_all.filter(classification='CONFIRMED').count() or qs_all.filter(additional_data__koi_disposition__iexact='CONFIRMED').count()
    false_positive_count = ml_fp or qs_all.filter(classification='FALSE_POSITIVE').count() or qs_all.filter(additional_data__koi_disposition__iexact='FALSE POSITIVE').count()
    candidate_count = max(0, total_candidates - confirmed_count - false_positive_count)
    
    # Estadísticas por misión (solo Kepler)
    mission_stats = []
    for mission in ['Kepler']:
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
    orbital_periods = list(qs_all.filter(orbital_period__isnull=False).values_list('orbital_period', flat=True)[:5000])
    
    # Distribución de radios planetarios
    planetary_radii = list(qs_all.filter(planetary_radius__isnull=False).values_list('planetary_radius', flat=True)[:5000])
    
    context = {
        'total_candidates': total_candidates,
        'confirmed_count': confirmed_count,
        'candidate_count': candidate_count,
        'false_positive_count': false_positive_count,
        'mission_stats': mission_stats,
        'orbital_periods': orbital_periods,
        'planetary_radii': planetary_radii,
    }

    # CSV fallback if everything is zero
    if total_candidates == 0 and confirmed_count == 0 and candidate_count == 0 and false_positive_count == 0:
        try:
            base_dir = Path(__file__).resolve().parent.parent
            csv_path = (base_dir / 'mlapp' / 'models_store' / 'current' / 'kepler_clean.csv')
            if not csv_path.exists():
                csv_path = (base_dir / 'models_store' / 'current' / 'kepler_clean.csv')
            if csv_path.exists():
                import pandas as pd
                df = pd.read_csv(csv_path)
                disp = df['koi_disposition'].str.upper().fillna('')
                total_candidates = int(len(df))
                confirmed_count = int((disp == 'CONFIRMED').sum())
                false_positive_count = int((disp == 'FALSE POSITIVE').sum())
                candidate_count = max(0, total_candidates - confirmed_count - false_positive_count)
                context.update({
                    'total_candidates': total_candidates,
                    'confirmed_count': confirmed_count,
                    'candidate_count': candidate_count,
                    'false_positive_count': false_positive_count,
                    'mission_stats': [{'mission': 'Kepler', 'total': total_candidates, 'confirmed': confirmed_count, 'candidates': candidate_count, 'false_positives': false_positive_count}],
                    'orbital_periods': df['koi_period'].dropna().tolist()[:5000] if 'koi_period' in df.columns else [],
                    'planetary_radii': df['koi_prad'].dropna().tolist()[:5000] if 'koi_prad' in df.columns else [],
                })
        except Exception as e:
            logger.warning(f"CSV fallback en dashboard falló: {e}")
    
    return render(request, 'mlapp/dashboard.html', context)


@login_required
def predict_api_test_page(request):
    """Página simple para probar el endpoint de predicción via fetch."""
    return render(request, 'mlapp/predict_api_test.html')

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
        
        # Ejecutar predicción con el modelo local
        label, prob, details = predict_with_kepler_model({
            'orbital_period': data.get('orbital_period'),
            'transit_duration': data.get('transit_duration'),
            'transit_depth': data.get('transit_depth'),
            'stellar_effective_temperature': data.get('stellar_effective_temperature'),
            'planetary_radius': data.get('planetary_radius'),
            'stellar_radius': data.get('stellar_radius'),
            'equilibrium_temperature': data.get('equilibrium_temperature'),
            'impact_parameter': data.get('impact_parameter'),
        })

        return JsonResponse({
            'prediction': label,
            'confidence': prob,
            'details': details,
        })
        
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


@login_required
@staff_member_required
def sync_kepler_data(request):
    """Sincroniza el dataset Kepler desde models_store/current al DB y rellena ML.

    Solo personal (staff). No cambia nada innecesario.
    """
    try:
        from app.management.commands.import_kepler_clean import Command as ImportCmd
        from app.management.commands.backfill_kepler_predictions import Command as BackfillCmd

        # Importar (no truncamos por defecto)
        import_cmd = ImportCmd()
        import_cmd.handle(truncate=False, limit=None)

        # Backfill solo donde falte
        backfill_cmd = BackfillCmd()
        backfill_cmd.handle(missing_only=True, limit=None)

        messages.success(request, 'Sincronización de Kepler completada correctamente.')
    except Exception as e:
        logger.error(f"Sync Kepler falló: {e}")
        messages.error(request, f'Error al sincronizar Kepler: {e}')
    return redirect('dataset_list')

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
