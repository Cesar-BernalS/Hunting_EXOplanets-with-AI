from django.core.management.base import BaseCommand
from app.models import ExoplanetDataset, ExoplanetCandidate


class Command(BaseCommand):
    help = 'Elimina datasets pre-cargados (K2, TESS, Kepler Confirmed Planets) y sus candidatos.'

    def handle(self, *args, **options):
        targets = [
            ('K2', None),
            ('TESS', None),
            ('Kepler', 'Kepler Confirmed Planets'),
        ]
        total_deleted = 0
        for mission, name in targets:
            qs = ExoplanetDataset.objects.filter(mission=mission)
            if name:
                qs = qs.filter(name=name)
            for ds in qs:
                cnt = ExoplanetCandidate.objects.filter(dataset=ds).count()
                ExoplanetCandidate.objects.filter(dataset=ds).delete()
                ds.delete()
                total_deleted += cnt
                self.stdout.write(f"Eliminado dataset {mission} - {name or ds.name} y {cnt} candidatos")
        self.stdout.write(self.style.SUCCESS(f'Completado. Total candidatos eliminados: {total_deleted}'))


