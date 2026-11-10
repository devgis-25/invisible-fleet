
import csv
import hashlib
from collections import Counter
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.contrib.gis.geos import Point
from django.db import transaction
from django.utils import timezone

from ingestion.models import ImportBatch
from maritime.models import (
    AISObservation,
    SARObservation,
    MaritimeCell,
)


BATCH_SIZE_DEFAULT = 5000

DATASETS = {
    "AIS": {
        "file": "data/processed/ais_presence_2024-01_2026-10.csv",
        "dataset_key": "public-global-presence:v5.0",
        "category": "all_flags",
    },
    "SAR": {
        "file": "data/processed/sar_detections_2024-01_2026-10.csv",
        "dataset_key": "public-global-sar-presence:v5.0",
        "category": "mixed",
    },
}


def calculate_sha256(file_path):
    """Calcule l'empreinte SHA-256 sans charger le fichier entier."""
    sha256 = hashlib.sha256()

    with open(file_path, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            sha256.update(chunk)

    return sha256.hexdigest()


def parse_row(row, data_type, line_number):
    """Convertit et valide une ligne CSV."""

    try:
        period_text = row["date"].strip()
        period = date.fromisoformat(f"{period_text}-01")

        latitude = Decimal(row["lat"])
        longitude = Decimal(row["lon"])

        if not latitude.is_finite() or not longitude.is_finite():
            raise ValueError("Coordonnées non finies.")

        if not Decimal("-90") <= latitude <= Decimal("90"):
            raise ValueError("Latitude hors limites.")

        if not Decimal("-180") <= longitude <= Decimal("180"):
            raise ValueError("Longitude hors limites.")

        vessel_ids = int(row["vesselIDs"])

        if vessel_ids < 0:
            raise ValueError("vesselIDs négatif.")

        if data_type == "AIS":
            flag = row["flag"].strip() or None
            hours = int(row["hours"])
            category = row["category"].strip()

            if flag is not None and len(flag) != 3:
                raise ValueError(
                    f"Code pavillon invalide : {flag!r}"
                )

            if hours < 0:
                raise ValueError("Nombre d'heures négatif.")

            if category != "all_flags":
                raise ValueError(f"Catégorie AIS inattendue : {category}")

            value = {
                "period": period,
                "latitude": latitude,
                "longitude": longitude,
                "flag": flag,
                "hours": hours,
                "vessel_ids": vessel_ids,
                "category": category,
            }

        else:
            detections = int(row["detections"])
            category = row["category"].strip()

            if detections < 0:
                raise ValueError("Nombre de détections négatif.")

            if category not in ("matched", "unmatched"):
                raise ValueError(f"Catégorie SAR invalide : {category}")

            value = {
                "period": period,
                "latitude": latitude,
                "longitude": longitude,
                "detections": detections,
                "vessel_ids": vessel_ids,
                "category": category,
            }

        return value

    except (KeyError, ValueError, InvalidOperation) as exc:
        raise ValueError(
            f"Erreur CSV ligne {line_number} : {exc}"
        ) from exc


def validate_csv(file_path, data_type):
    """Effectue une première lecture complète sans modifier la base."""

    required_columns = {
        "AIS": {
            "date", "flag", "hours", "lat",
            "lon", "vesselIDs", "source", "category",
        },
        "SAR": {
            "date", "detections", "lat",
            "lon", "vesselIDs", "source", "category",
        },
    }

    total_rows = 0
    unique_cells = set()
    categories = Counter()
    periods = []

    with open(file_path, "r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        missing = required_columns[data_type] - set(reader.fieldnames or [])

        if missing:
            raise ValueError(
                f"Colonnes manquantes dans {file_path.name} : {sorted(missing)}"
            )

        for line_number, row in enumerate(reader, start=2):
            if row.get("source", "").strip() != data_type:
                raise ValueError(
                    f"Ligne {line_number} : source inattendue."
                )

            parsed = parse_row(row, data_type, line_number)

            total_rows += 1
            periods.append(parsed["period"])
            unique_cells.add(
                (parsed["latitude"], parsed["longitude"])
            )
            categories[parsed["category"]] += 1

    if total_rows == 0:
        raise ValueError(f"Le fichier {file_path.name} est vide.")

    return {
        "total_rows": total_rows,
        "unique_cells": unique_cells,
        "categories": dict(categories),
        "period_start": min(periods),
        "period_end": max(periods),
    }


class Command(BaseCommand):
    help = "Importe les données historiques AIS et SAR dans PostGIS."

    def add_arguments(self, parser):
        parser.add_argument(
            "--ais-only",
            action="store_true",
            help="Importer uniquement les données AIS.",
        )
        parser.add_argument(
            "--sar-only",
            action="store_true",
            help="Importer uniquement les données SAR.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Valider les fichiers sans modifier la base.",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=BATCH_SIZE_DEFAULT,
            help="Nombre d'observations par insertion.",
        )

    def handle(self, *args, **options):
        if options["ais_only"] and options["sar_only"]:
            raise CommandError(
                "Choisis --ais-only ou --sar-only, pas les deux."
            )

        batch_size = options["batch_size"]

        if batch_size < 1:
            raise CommandError("--batch-size doit être supérieur à zéro.")

        if options["ais_only"]:
            selected = ["AIS"]
        elif options["sar_only"]:
            selected = ["SAR"]
        else:
            selected = ["AIS", "SAR"]

        for data_type in selected:
            self.import_dataset(
                data_type=data_type,
                batch_size=batch_size,
                dry_run=options["dry_run"],
            )

    def import_dataset(self, data_type, batch_size, dry_run):
        config = DATASETS[data_type]
        file_path = Path(settings.BASE_DIR) / config["file"]

        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING(
            f"IMPORT {data_type}"
        ))

        if not file_path.exists():
            raise CommandError(f"Fichier introuvable : {file_path}")

        self.stdout.write(f"Fichier : {file_path}")

        try:
            validation = validate_csv(file_path, data_type)
            file_hash = calculate_sha256(file_path)
        except Exception as exc:
            raise CommandError(f"Validation impossible : {exc}") from exc

        total_rows = validation["total_rows"]
        unique_cells = validation["unique_cells"]

        self.stdout.write(f"Lignes validées : {total_rows:,}")
        self.stdout.write(f"Cellules géographiques : {len(unique_cells):,}")
        self.stdout.write(f"Période : {validation['period_start']} → {validation['period_end']}")
        self.stdout.write(f"Catégories : {validation['categories']}")
        self.stdout.write(f"SHA-256 : {file_hash}")

        if dry_run:
            self.stdout.write(self.style.SUCCESS(
                "DRY-RUN : validation réussie, aucune donnée importée."
            ))
            return

        batch, created = ImportBatch.objects.get_or_create(
            file_sha256=file_hash,
            defaults={
                "source": ImportBatch.Source.GFW,
                "data_type": data_type,
                "dataset_key": config["dataset_key"],
                "dataset_version": "v5.0",
                "category": config["category"],
                "period_start": validation["period_start"],
                "period_end": validation["period_end"],
                "file_path": str(file_path.relative_to(settings.BASE_DIR)),
                "metadata": {
                    "categories": validation["categories"],
                    "unique_cells": len(unique_cells),
                    "encoding": "utf-8-sig",
                },
            },
        )

        if not created:
            if batch.data_type != data_type or batch.source != ImportBatch.Source.GFW:
                raise CommandError(
                    "Cette empreinte SHA-256 est déjà associée à un autre type de lot."
                )

            if batch.status == ImportBatch.Status.SUCCESS:
                self.stdout.write(self.style.WARNING(
                    "Ce fichier a déjà été importé avec succès. Import ignoré."
                ))
                return

            batch.status = ImportBatch.Status.PENDING
            batch.total_rows = 0
            batch.inserted_rows = 0
            batch.updated_rows = 0
            batch.rejected_rows = 0
            batch.error_message = ""
            batch.metadata = {
                "categories": validation["categories"],
                "unique_cells": len(unique_cells),
                "encoding": "utf-8-sig",
            }

        batch.status = ImportBatch.Status.RUNNING
        batch.started_at = timezone.now()
        batch.finished_at = None
        batch.save()

        try:
            with transaction.atomic():
                # 1. Créer les cellules manquantes.
                cell_objects = [
                    MaritimeCell(
                        latitude=latitude,
                        longitude=longitude,
                        center=Point(
                            float(longitude),
                            float(latitude),
                            srid=4326,
                        ),
                    )
                    for latitude, longitude in unique_cells
                ]

                MaritimeCell.objects.bulk_create(
                    cell_objects,
                    batch_size=batch_size,
                    ignore_conflicts=True,
                )

                # 2. Construire le dictionnaire des cellules.
                cell_map = {
                    (cell.latitude, cell.longitude): cell
                    for cell in MaritimeCell.objects.all()
                }

                if not unique_cells.issubset(cell_map.keys()):
                    raise RuntimeError(
                        "Certaines cellules n'ont pas été créées correctement."
                    )

                # 3. Insérer les observations progressivement.
                inserted = 0
                buffer = []

                with open(
                    file_path,
                    "r",
                    encoding="utf-8-sig",
                    newline="",
                ) as file:
                    reader = csv.DictReader(file)

                    for line_number, row in enumerate(reader, start=2):
                        parsed = parse_row(row, data_type, line_number)

                        cell = cell_map[
                            (parsed["latitude"], parsed["longitude"])
                        ]

                        if data_type == "AIS":
                            observation = AISObservation(
                                period=parsed["period"],
                                flag=parsed["flag"],
                                hours=parsed["hours"],
                                vessel_ids=parsed["vessel_ids"],
                                cell=cell,
                                category=parsed["category"],
                                import_batch=batch,
                            )
                        else:
                            observation = SARObservation(
                                period=parsed["period"],
                                detections=parsed["detections"],
                                vessel_ids=parsed["vessel_ids"],
                                cell=cell,
                                category=parsed["category"],
                                import_batch=batch,
                            )

                        buffer.append(observation)

                        if len(buffer) >= batch_size:
                            self.bulk_insert(data_type, buffer, batch_size)
                            inserted += len(buffer)
                            buffer.clear()

                if buffer:
                    self.bulk_insert(data_type, buffer, batch_size)
                    inserted += len(buffer)

                if inserted != total_rows:
                    raise RuntimeError(
                        f"Nombre de lignes incohérent : "
                        f"{inserted} insérées sur {total_rows} attendues."
                    )

                # 4. Marquer le lot comme terminé dans la transaction.
                batch.total_rows = total_rows
                batch.inserted_rows = inserted
                batch.updated_rows = 0
                batch.rejected_rows = 0
                batch.status = ImportBatch.Status.SUCCESS
                batch.finished_at = timezone.now()
                batch.error_message = ""
                batch.save()

            self.stdout.write(self.style.SUCCESS(
                f"Import {data_type} terminé : {inserted:,} observations."
            ))

        except Exception as exc:
            batch.status = ImportBatch.Status.FAILED
            batch.error_message = str(exc)[:10000]
            batch.finished_at = timezone.now()
            batch.save()

            raise CommandError(
                f"Échec de l'import {data_type} : {exc}"
            ) from exc

    @staticmethod
    def bulk_insert(data_type, buffer, batch_size):
        if data_type == "AIS":
            AISObservation.objects.bulk_create(
                buffer,
                batch_size=batch_size,
            )
        else:
            SARObservation.objects.bulk_create(
                buffer,
                batch_size=batch_size,
            )
