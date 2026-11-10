#analytics/models.py
from django.db import models
from django.db.models import UniqueConstraint


class CellMonthlyMetric(models.Model):
    """
    Agrégation mensuelle AIS/SAR pour une cellule
    et une intersection avec une zone maritime.
    """

    zone_intersection = models.ForeignKey(
        "maritime.CellZoneIntersection",
        on_delete=models.PROTECT,
        related_name="monthly_metrics",
    )

    period = models.DateField(
        help_text="Premier jour du mois concerné."
    )

    # AIS
    ais_hours = models.PositiveBigIntegerField(default=0)

    ais_vessel_ids_sum = models.PositiveBigIntegerField(
        default=0,
        help_text="Somme des comptes vesselIDs fournis par GFW."
    )

    ais_observation_count = models.PositiveIntegerField(default=0)

    ais_flag_count = models.PositiveSmallIntegerField(default=0)

    # SAR matched
    sar_matched_detections = models.PositiveBigIntegerField(default=0)
    sar_matched_vessel_ids_sum = models.PositiveBigIntegerField(default=0)
    sar_matched_observation_count = models.PositiveIntegerField(default=0)

    # SAR unmatched
    sar_unmatched_detections = models.PositiveBigIntegerField(default=0)
    sar_unmatched_vessel_ids_sum = models.PositiveBigIntegerField(default=0)
    sar_unmatched_observation_count = models.PositiveIntegerField(default=0)

    generated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "cell_monthly_metrics"

        verbose_name = "Indicateur maritime mensuel"
        verbose_name_plural = "Indicateurs maritimes mensuels"

        constraints = [
            UniqueConstraint(
                fields=["zone_intersection", "period"],
                name="unique_cell_zone_monthly_metric",
            ),
        ]

        indexes = [
            models.Index(
                fields=["period"],
                name="cell_metric_period_idx",
            ),
            models.Index(
                fields=["period", "zone_intersection"],
                name="cell_metric_period_zone_idx",
            ),
        ]

    def __str__(self):
        return f"{self.zone_intersection.cell} - {self.period}"
