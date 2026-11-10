
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.conf import settings
from django.contrib.gis.gdal import DataSource
from django.contrib.gis.geos import GEOSGeometry
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from maritime.models import MaritimeZone


class Command(BaseCommand):
    help = "Importe une zone maritime depuis Marine Regions EEZ."

    def add_arguments(self, parser):
        parser.add_argument(
            "--mrgid",
            type=int,
            default=8371,
            help="Identifiant Marine Regions (défaut : 8371).",
        )

    def handle(self, *args, **options):
        mrgid = options["mrgid"]

        file_path = (
            Path(settings.BASE_DIR)
            / "data"
            / "raw"
            / "boundaries"
            / "eez_v12.gpkg"
        )

        if not file_path.exists():
            raise CommandError(f"GeoPackage introuvable : {file_path}")

        self.stdout.write(f"Source : {file_path}")
        self.stdout.write(f"Recherche MRGID : {mrgid}")

        try:
            datasource = DataSource(str(file_path))
            layer = datasource["eez_v12"]
        except Exception as exc:
            raise CommandError(
                f"Impossible de lire le GeoPackage : {exc}"
            ) from exc

        if layer.srs is None or layer.srs.srid != 4326:
            raise CommandError(
                "Le GeoPackage doit être en EPSG:4326."
            )

        feature = None

        for item in layer:
            if int(item.get("MRGID")) == mrgid:
                feature = item
                break

        if feature is None:
            raise CommandError(f"MRGID {mrgid} introuvable.")

        name = feature.get("GEONAME")
        source_area = feature.get("AREA_KM2")
        source_type = feature.get("POL_TYPE")
        iso_territory = feature.get("ISO_TER1")

        if not name or not source_area:
            raise CommandError(
                "Nom ou superficie manquant dans la source."
            )

        if mrgid == 8371 and iso_territory != "SEN":
            raise CommandError(
                "Le territoire de l'entité ne correspond pas à SEN."
            )

        try:
            area_km2 = Decimal(str(source_area))
            geometry = GEOSGeometry(
                feature.geom.wkt,
                srid=layer.srs.srid,
            )
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise CommandError(
                f"Conversion des données impossible : {exc}"
            ) from exc

        if geometry.geom_type != "MultiPolygon":
            raise CommandError(
                f"Géométrie inattendue : {geometry.geom_type}"
            )

        if geometry.srid != 4326:
            raise CommandError("SRID incorrect après conversion.")

        if geometry.empty:
            raise CommandError("La géométrie est vide.")

        if not geometry.valid:
            raise CommandError(
                "La géométrie est invalide. "
                "Aucune correction automatique ne sera appliquée."
            )

        self.stdout.write(f"Nom : {name}")
        self.stdout.write(f"Type : {source_type}")
        self.stdout.write(f"Superficie source : {area_km2} km²")
        self.stdout.write(f"Géométrie : {geometry.geom_type}")
        self.stdout.write(f"SRID : {geometry.srid}")
        self.stdout.write("Validité géométrique : OK")

        with transaction.atomic():
            zone, created = MaritimeZone.objects.update_or_create(
                marine_regions_id=mrgid,
                defaults={
                    "name": name,
                    "area_km2": area_km2,
                    "source": "Marine Regions",
                    "source_version": "World EEZ v12",
                    "geometry": geometry,
                },
            )

        action = "créée" if created else "mise à jour"

        self.stdout.write(
            self.style.SUCCESS(
                f"Zone {action} avec succès : {zone.name} "
                f"(MRGID {zone.marine_regions_id})."
            )
        )
