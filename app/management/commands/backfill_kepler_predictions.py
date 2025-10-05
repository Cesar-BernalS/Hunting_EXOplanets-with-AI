from django.core.management.base import BaseCommand
from django.db import transaction

from app.models import ExoplanetCandidate
from app.predictor_adapter import predict_with_kepler_model


class Command(BaseCommand):
    help = 'Calcula y guarda ml_prediction y ml_confidence para candidatos Kepler existentes.'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=None, help='Limitar cantidad a procesar')
        parser.add_argument('--missing-only', action='store_true', help='Solo actualizar donde falta ml_prediction')

    def handle(self, *args, **options):
        qs = ExoplanetCandidate.objects.filter(dataset__mission='Kepler')
        if options.get('missing_only'):
            qs = qs.filter(ml_prediction__isnull=True)

        limit = options.get('limit')
        if limit:
            qs = qs[:limit]

        updated = 0
        with transaction.atomic():
            for cand in qs.iterator(chunk_size=1000):
                features = {
                    'orbital_period': cand.orbital_period,
                    'transit_duration': cand.transit_duration,
                    'planetary_radius': cand.planetary_radius,
                    'stellar_radius': cand.stellar_radius,
                    'stellar_mass': cand.stellar_mass,
                    'stellar_effective_temperature': cand.stellar_effective_temperature,
                    'transit_depth': cand.transit_depth,
                    'impact_parameter': cand.impact_parameter,
                    'equilibrium_temperature': cand.equilibrium_temperature,
                }
                # Add original koi_* if present in additional_data, improving feature coverage
                ad = cand.additional_data or {}
                for k in list(ad.keys()):
                    if k.startswith('koi_') and ad[k] not in (None, '') and k not in features:
                        features[k] = ad[k]
                label, conf, _ = predict_with_kepler_model(features)
                cand.ml_prediction = label
                cand.ml_confidence = conf * 100.0
                cand.save(update_fields=['ml_prediction', 'ml_confidence'])
                updated += 1

        self.stdout.write(self.style.SUCCESS(f'Actualizados {updated} candidatos'))


