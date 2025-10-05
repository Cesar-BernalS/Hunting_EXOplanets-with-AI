import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.conf import settings
from django.db.models import F

from app.models import ExoplanetCandidate
from app.predictor import _MODEL


class Command(BaseCommand):
    help = 'Calibra el umbral para aproximar una fracción objetivo de confirmados en Kepler usando el modelo actual.'

    def add_arguments(self, parser):
        parser.add_argument('--target', type=float, default=0.5, help='Fracción objetivo de confirmados (0-1). Default 0.5')
        parser.add_argument('--limit', type=int, default=5000, help='Número máximo de muestras para calibración (para rapidez)')

    def handle(self, *args, **options):
        target = float(options['target'])
        limit = int(options['limit'])

        # Asegurar modelo cargado y config mutable
        _MODEL.ensure_loaded()

        # Tomar una muestra de candidatos Kepler
        qs = ExoplanetCandidate.objects.filter(dataset__mission='Kepler').only(
            'orbital_period', 'transit_duration', 'planetary_radius', 'stellar_radius', 'stellar_mass',
            'stellar_effective_temperature', 'transit_depth', 'impact_parameter', 'equilibrium_temperature'
        )[:limit]

        probs = []
        for c in qs.iterator(chunk_size=1000):
            label, conf, details = _MODEL.predict({
                'orbital_period': c.orbital_period,
                'transit_duration': c.transit_duration,
                'planetary_radius': c.planetary_radius,
                'stellar_radius': c.stellar_radius,
                'stellar_mass': c.stellar_mass,
                'stellar_effective_temperature': c.stellar_effective_temperature,
                'transit_depth': c.transit_depth,
                'impact_parameter': c.impact_parameter,
                'equilibrium_temperature': c.equilibrium_temperature,
            })
            probs.append(details.get('probability_confirmed', 0.0))

        if not probs:
            self.stdout.write(self.style.WARNING('No hay muestras para calibrar'))
            return

        # Ordenar probabilidades y seleccionar el percentil para alcanzar la fracción objetivo
        probs_sorted = sorted(probs)
        idx = max(0, min(len(probs_sorted) - 1, int((1 - target) * len(probs_sorted))))
        new_thr = float(probs_sorted[idx])

        # Guardar umbral en final_config.json
        cfg_path = _MODEL.artifacts_dir / 'final_config.json'
        try:
            cfg = json.loads(cfg_path.read_text(encoding='utf-8'))
        except Exception:
            cfg = {}
        cfg['threshold'] = new_thr
        cfg_path.write_text(json.dumps(cfg, indent=2), encoding='utf-8')

        self.stdout.write(self.style.SUCCESS(f'Umbral calibrado a {new_thr:.4f} para objetivo ~{target*100:.1f}% confirmados'))


