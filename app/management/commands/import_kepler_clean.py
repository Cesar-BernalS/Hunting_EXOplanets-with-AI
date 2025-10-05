import csv
import json
from pathlib import Path
from typing import Optional

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.conf import settings

from app.models import ExoplanetDataset, ExoplanetCandidate
from app.predictor_adapter import predict_with_kepler_model
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Importa candidatos Kepler desde mlapp/models_store/current/kepler_clean (CSV o JSONL)'

    def add_arguments(self, parser):
        parser.add_argument('--truncate', action='store_true', help='Borra candidatos Kepler existentes antes de importar')
        parser.add_argument('--limit', type=int, default=None, help='Límite opcional de filas a importar')

    def handle(self, *args, **options):
        artifacts_dir = Path(settings.BASE_DIR) / 'mlapp' / 'models_store' / 'current'
        fallback_dir = Path(settings.BASE_DIR) / 'models_store' / 'current'
        csv_path = (artifacts_dir / 'kepler_clean.csv') if (artifacts_dir / 'kepler_clean.csv').exists() else (fallback_dir / 'kepler_clean.csv')
        jsonl_path = artifacts_dir / 'kepler_clean.jsonl'

        if not csv_path.exists() and not jsonl_path.exists():
            raise CommandError('No se encontró kepler_clean.csv ni kepler_clean.jsonl en models_store/current')

        dataset, _ = ExoplanetDataset.objects.get_or_create(
            mission='Kepler',
            name='Kepler Clean',
            defaults={
                'description': 'Dataset importado desde kepler_clean',
                'source_url': 'https://archive.stsci.edu/kepler/'
            }
        )

        if options['truncate']:
            self.stdout.write('Eliminando candidatos existentes de Kepler...')
            ExoplanetCandidate.objects.filter(dataset__mission='Kepler').delete()

        imported = 0
        limit = options.get('limit')

        with transaction.atomic():
            if csv_path.exists():
                imported = self._import_csv(csv_path, dataset, limit)
            else:
                imported = self._import_jsonl(jsonl_path, dataset, limit)

        self.stdout.write(self.style.SUCCESS(f'Importación completada: {imported} candidatos'))

    def _row_to_candidate_kwargs(self, row) -> Optional[dict]:
        """Mapear fila a campos del modelo de forma robusta"""
        def f(*names, default=None):
            for name in names:
                if name in row and row[name] not in (None, ''):
                    return row[name]
            return default

        def to_float(value, default=0.0):
            try:
                if value is None or value == '':
                    return float(default)
                return float(str(value).replace(',', '.'))
            except Exception:
                return float(default)

        try:
            base = {
                'name': f('name', 'kepoi_name', 'kepid', 'koi_name', default='Kepler-Candidate'),
                'koi_id': f('koi_id', 'kepoi_name'),
                'tess_id': None,
                'orbital_period': to_float(f('orbital_period', 'koi_period')),
                'transit_duration': to_float(f('transit_duration', 'koi_duration')),
                'planetary_radius': to_float(f('planetary_radius', 'koi_prad')),
                'stellar_radius': to_float(f('stellar_radius', 'koi_srad')),
                'stellar_mass': to_float(f('stellar_mass', 'koi_smass'), 1.0),
                'stellar_effective_temperature': to_float(f('stellar_effective_temperature', 'koi_steff')),
                'transit_depth': to_float(f('transit_depth', 'koi_depth', 'koi_depth_err1'), 0.0),
                'impact_parameter': to_float(f('impact_parameter', 'koi_impact'), 0.0),
                'equilibrium_temperature': to_float(f('equilibrium_temperature', 'koi_teq'), 0.0),
                'classification': ExoplanetCandidate.UNKNOWN,
                'additional_data': row,
            }

            # Preparar features para ML
            features = {
                'orbital_period': base['orbital_period'],
                'transit_duration': base['transit_duration'],
                'planetary_radius': base['planetary_radius'],
                'stellar_radius': base['stellar_radius'],
                'stellar_mass': base['stellar_mass'],
                'stellar_effective_temperature': base['stellar_effective_temperature'],
                'transit_depth': base['transit_depth'],
                'impact_parameter': base['impact_parameter'],
                'equilibrium_temperature': base['equilibrium_temperature'],
            }

            # Agregar columnas originales
            for k, v in row.items():
                if k not in features and v not in (None, ''):
                    features[k] = v

            try:
                label, conf, _details = predict_with_kepler_model(features)
                base['ml_prediction'] = label
                base['ml_confidence'] = conf * 100.0
            except Exception as e:
                base['ml_prediction'] = None
                base['ml_confidence'] = None
                logger.warning(f"Predicción falló para {base['name']}: {e}")

            return base
        except Exception as e:
            logger.error(f"Fila irrecuperable: {row}. Error: {e}")
            return None

    def _import_csv(self, path: Path, dataset: ExoplanetDataset, limit: Optional[int]) -> int:
        count = 0
        with path.open('r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                data = self._row_to_candidate_kwargs(row)
                if not data:
                    continue
                ExoplanetCandidate.objects.create(dataset=dataset, **data)
                count += 1
                if limit and count >= limit:
                    break
        return count

    def _import_jsonl(self, path: Path, dataset: ExoplanetDataset, limit: Optional[int]) -> int:
        count = 0
        with path.open('r', encoding='utf-8') as f:
            for line in f:
                row = json.loads(line)
                data = self._row_to_candidate_kwargs(row)
                if not data:
                    continue
                ExoplanetCandidate.objects.create(dataset=dataset, **data)
                count += 1
                if limit and count >= limit:
                    break
        return count