#!/usr/bin/env python
"""
Script para crear datos de ejemplo para la aplicación de exoplanetas
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from app.models import ExoplanetDataset, ExoplanetCandidate
import random

def create_sample_data():
    print("Creando datos de ejemplo...")
    
    # Crear datasets de ejemplo
    datasets = [
        {
            'name': 'Kepler Confirmed Planets',
            'mission': 'Kepler',
            'description': 'Planetas confirmados descubiertos por la misión Kepler',
            'source_url': 'https://exoplanetarchive.ipac.caltech.edu/',
            'is_active': True
        },
        {
            'name': 'K2 Candidates',
            'mission': 'K2',
            'description': 'Candidatos a exoplanetas de la misión K2',
            'source_url': 'https://exoplanetarchive.ipac.caltech.edu/',
            'is_active': True
        },
        {
            'name': 'TESS Objects of Interest',
            'mission': 'TESS',
            'description': 'Objetos de interés de la misión TESS',
            'source_url': 'https://exoplanetarchive.ipac.caltech.edu/',
            'is_active': True
        }
    ]
    
    created_datasets = []
    for dataset_data in datasets:
        dataset, created = ExoplanetDataset.objects.get_or_create(
            name=dataset_data['name'],
            defaults=dataset_data
        )
        created_datasets.append(dataset)
        print(f"Dataset: {dataset.name} - {'Creado' if created else 'Ya existe'}")
    
    # Crear candidatos de ejemplo
    sample_candidates = [
        {
            'name': 'Kepler-442b',
            'koi_id': 'KOI-4742.01',
            'orbital_period': 112.305,
            'transit_duration': 2.5,
            'planetary_radius': 1.34,
            'stellar_radius': 0.6,
            'stellar_mass': 0.61,
            'stellar_effective_temperature': 4402,
            'transit_depth': 0.0001,
            'impact_parameter': 0.3,
            'equilibrium_temperature': 233,
            'classification': 'CONFIRMED'
        },
        {
            'name': 'Kepler-186f',
            'koi_id': 'KOI-571.05',
            'orbital_period': 129.9,
            'transit_duration': 3.0,
            'planetary_radius': 1.11,
            'stellar_radius': 0.47,
            'stellar_mass': 0.48,
            'stellar_effective_temperature': 3788,
            'transit_depth': 0.0002,
            'impact_parameter': 0.2,
            'equilibrium_temperature': 188,
            'classification': 'CONFIRMED'
        },
        {
            'name': 'TOI-715b',
            'tess_id': 'TOI-715',
            'orbital_period': 19.3,
            'transit_duration': 1.8,
            'planetary_radius': 1.55,
            'stellar_radius': 0.61,
            'stellar_mass': 0.64,
            'stellar_effective_temperature': 3240,
            'transit_depth': 0.0003,
            'impact_parameter': 0.4,
            'equilibrium_temperature': 174,
            'classification': 'CANDIDATE'
        },
        {
            'name': 'Kepler-452b',
            'koi_id': 'KOI-7016.01',
            'orbital_period': 384.8,
            'transit_duration': 4.2,
            'planetary_radius': 1.63,
            'stellar_radius': 1.11,
            'stellar_mass': 1.04,
            'stellar_effective_temperature': 5757,
            'transit_depth': 0.0002,
            'impact_parameter': 0.1,
            'equilibrium_temperature': 265,
            'classification': 'CONFIRMED'
        },
        {
            'name': 'TOI-1231b',
            'tess_id': 'TOI-1231',
            'orbital_period': 24.2,
            'transit_duration': 2.1,
            'planetary_radius': 3.65,
            'stellar_radius': 0.48,
            'stellar_mass': 0.48,
            'stellar_effective_temperature': 3300,
            'transit_depth': 0.0008,
            'impact_parameter': 0.5,
            'equilibrium_temperature': 330,
            'classification': 'CANDIDATE'
        }
    ]
    
    # Crear candidatos adicionales con datos aleatorios
    for i in range(20):
        mission = random.choice(['Kepler', 'K2', 'TESS'])
        dataset = random.choice([d for d in created_datasets if d.mission == mission])
        
        candidate_data = {
            'name': f'{mission}-{random.randint(100, 9999)}{chr(97 + random.randint(0, 25))}',
            'orbital_period': round(random.uniform(1, 500), 2),
            'transit_duration': round(random.uniform(0.5, 10), 2),
            'planetary_radius': round(random.uniform(0.5, 10), 2),
            'stellar_radius': round(random.uniform(0.3, 2), 2),
            'stellar_mass': round(random.uniform(0.3, 2), 2),
            'stellar_effective_temperature': random.randint(3000, 7000),
            'transit_depth': round(random.uniform(0.00001, 0.01), 6),
            'impact_parameter': round(random.uniform(0, 1), 2),
            'equilibrium_temperature': random.randint(100, 1000),
            'classification': random.choice(['CONFIRMED', 'CANDIDATE', 'FALSE_POSITIVE']),
            'dataset': dataset
        }
        
        if mission in ['Kepler', 'K2']:
            candidate_data['koi_id'] = f'KOI-{random.randint(1000, 9999)}.{random.randint(1, 9):02d}'
        else:
            candidate_data['tess_id'] = f'TOI-{random.randint(100, 9999)}'
        
        candidate = ExoplanetCandidate.objects.create(**candidate_data)
        print(f"Candidato creado: {candidate.name}")
    
    print(f"\n¡Datos de ejemplo creados exitosamente!")
    print(f"- {ExoplanetDataset.objects.count()} datasets")
    print(f"- {ExoplanetCandidate.objects.count()} candidatos")

if __name__ == '__main__':
    create_sample_data()
