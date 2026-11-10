
from collections import defaultdict

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Count, Sum

from analytics.models import CellMonthlyMetric
from maritime.models import (
    AISObservation,
    SARObservation,
    CellZoneIntersection,
)


class Command(BaseCommand):
    help = (
        "Construit les indicateurs mensuels AIS/SAR "
        "par cellule et intersection avec la ZEE."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Calcule les agrégations sans modifier la base.",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=2000,
            help="Nombre de métriques écrites par lot.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        batch_size = options["batch_size"]

        if batch_size < 1:
            raise CommandError("--batch-size doit être supérieur à zéro.")

        self.stdout.write("1/4 - Préparation des cellules...")

        intersections_by_cell = defaultdict(list)

        for cell_id, intersection_id in (
            CellZoneIntersection.objects.values_list("cell_id", "id")
            .iterator(chunk_size=5000)
        ):
            intersections_by_cell[cell_id].append(intersection_id)

        if not intersections_by_cell:
            raise CommandError(
                "Aucune intersection cellule-zone. "
                "Exécute d'abord audit_spatial_cells."
            )

        self.stdout.write(
            f"  {len(intersections_by_cell)} cellules référencées."
        )

        # Une entrée par couple cellule/mois.
        metrics = defaultdict(
            lambda: {
                "ais_hours": 0,
                "ais_vessel_ids_sum": 0,
                "ais_observation_count": 0,
                "ais_flag_count": 0,
                "sar_matched_detections": 0,
                "sar_matched_vessel_ids_sum": 0,
                "sar_matched_observation_count": 0,
                "sar_unmatched_detections": 0,
                "sar_unmatched_vessel_ids_sum": 0,
                "sar_unmatched_observation_count": 0,
            }
        )

        self.stdout.write("2/4 - Agrégation AIS...")

        ais_aggregates = (
            AISObservation.objects
            .values("cell_id", "period")
            .annotate(
                total_hours=Sum("hours"),
                vessel_ids_sum=Sum("vessel_ids"),
                observation_count=Count("id"),
                flag_count=Count("flag", distinct=True),
            )
            .iterator(chunk_size=5000)
        )

        ais_groups = 0

        for row in ais_aggregates:
            key = (row["cell_id"], row["period"])

            if key[0] not in intersections_by_cell:
                continue

            metrics[key].update({
                "ais_hours": row["total_hours"] or 0,
                "ais_vessel_ids_sum": row["vessel_ids_sum"] or 0,
                "ais_observation_count": row["observation_count"] or 0,
                "ais_flag_count": row["flag_count"] or 0,
            })

            ais_groups += 1

        self.stdout.write(
            f"  {ais_groups} groupes AIS cellule/mois."
        )

        self.stdout.write("3/4 - Agrégation SAR...")

        sar_aggregates = (
            SARObservation.objects
            .values("cell_id", "period", "category")
            .annotate(
                total_detections=Sum("detections"),
                vessel_ids_sum=Sum("vessel_ids"),
                observation_count=Count("id"),
            )
            .iterator(chunk_size=5000)
        )

        sar_groups = 0

        for row in sar_aggregates:
            cell_id = row["cell_id"]
            period = row["period"]
            category = row["category"]

            if cell_id not in intersections_by_cell:
                continue

            key = (cell_id, period)

            if category == "matched":
                prefix = "sar_matched"
            elif category == "unmatched":
                prefix = "sar_unmatched"
            else:
                raise CommandError(
                    f"Catégorie SAR inconnue : {category!r}"
                )

            metrics[key].update({
                f"{prefix}_detections": (
                    row["total_detections"] or 0
                ),
                f"{prefix}_vessel_ids_sum": (
                    row["vessel_ids_sum"] or 0
                ),
                f"{prefix}_observation_count": (
                    row["observation_count"] or 0
                ),
            })

            sar_groups += 1

        self.stdout.write(
            f"  {sar_groups} groupes SAR cellule/mois/catégorie."
        )

        # Une ligne par intersection et par mois.
        objects = []

        for (cell_id, period), values in metrics.items():
            for intersection_id in intersections_by_cell[cell_id]:
                objects.append(
                    CellMonthlyMetric(
                        zone_intersection_id=intersection_id,
                        period=period,
                        **values,
                    )
                )

        self.stdout.write(
            f"4/4 - {len(objects)} métriques mensuelles calculées."
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "DRY RUN : aucune modification en base."
                )
            )
            return

        # Remplacement atomique : si l'écriture échoue,
        # les anciennes métriques restent intactes.
        with transaction.atomic():
            deleted_count, _ = CellMonthlyMetric.objects.all().delete()

            for start in range(0, len(objects), batch_size):
                batch = objects[start:start + batch_size]
                CellMonthlyMetric.objects.bulk_create(
                    batch,
                    batch_size=batch_size,
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Terminé : {len(objects)} métriques créées. "
                f"{deleted_count} anciennes lignes remplacées."
            )
        )
