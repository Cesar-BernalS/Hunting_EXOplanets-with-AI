from django.urls import path
from . import views

urlpatterns = [
    # Páginas principales
    path('', views.index, name='index'),
    path('datasets/', views.dataset_list, name='dataset_list'),
    path('candidates/', views.candidate_list, name='candidate_list'),
    path('candidates/<int:candidate_id>/', views.candidate_detail, name='candidate_detail'),
    
    # Predicciones
    path('predict/', views.prediction_form, name='prediction_form'),
    path('predict/result/<int:prediction_id>/', views.prediction_result, name='prediction_result'),
    path('predictions/', views.prediction_history, name='prediction_history'),
    
    # Análisis y estadísticas
    path('analytics/', views.analytics_dashboard, name='analytics_dashboard'),
    path('analytics/test-api/', views.predict_api_test_page, name='predict_api_test_page'),
    
    # Carga de datos
    path('upload/', views.upload_dataset, name='upload_dataset'),
    path('admin/sync-kepler/', views.sync_kepler_data, name='sync_kepler_data'),
    
    # API endpoints
    path('api/predict/', views.api_predict, name='api_predict'),
    
    # Autenticación
    path('login/', views.user_login, name='login'),
    path('register/', views.user_register, name='register'),
    path('logout/', views.user_logout, name='logout'),
    path('profile/', views.user_profile, name='profile'),
]
