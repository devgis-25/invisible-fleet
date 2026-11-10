
from django.contrib.gis.db import models
from django.db.models import CheckConstraint, Q, UniqueConstraint


class MaritimeZone(models.Model):
    """
    Zone maritime de référence : ZEE, zone de régime conjoint, etc.
    """

    name = models.CharField(max_length=255)

    marine_regions_id = models.PositiveIntegerField(
        unique=True,
        help_text="Identifiant MRGID de Marine Regions."
    )

    area_km2 = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True
    )

    source = models.CharField(
        max_length=100,
        default="Marine Regions"
    )

    source_version = models.CharField(
        max_length=50,
        blank=True
    )

    geometry = models.MultiPolygonField(
        srid=4326,
        spatial_index=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "maritime_zones"
        verbose_name = "Zone maritime"
        verbose_name_plural = "Zones maritimes"

    def __str__(self):
        return self.name


class MaritimeCell(models.Model):
    """
    Cellule de la grille spatiale Global Fishing Watch.
    """

    latitude = models.DecimalField(
        max_digits=5,
        decimal_places=2
    )

    longitude = models.DecimalField(
        max_digits=6,
        decimal_places=2
    )

    center = models.PointField(
        srid=4326,
        spatial_index=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "maritime_cells"
        verbose_name = "Cellule maritime"
        verbose_name_plural = "Cellules maritimes"

        constraints = [
            UniqueConstraint(
                fields=["latitude", "longitude"],
                name="unique_maritime_cell_coordinates"
            )
        ]

        indexes = [
            models.Index(fields=["latitude", "longitude"])
        ]

    def __str__(self):
        return f"{self.latitude}, {self.longitude}"


class AISObservation(models.Model):
    """
    Présence maritime agrégée issue des données AIS de GFW.
    """

    period = models.DateField(
        help_text="Premier jour du mois concerné."
    )

    flag = models.CharField(
        max_length=3,
        db_index=True,
        null=True,
        blank=True,
        help_text="Code du pavillon déclaré par GFW. NULL si non renseigné."
    )

    hours = models.PositiveIntegerField(
        help_text="Heures de présence AIS agrégées."
    )
    
    import_batch = models.ForeignKey(
        "ingestion.ImportBatch",
        on_delete=models.PROTECT,
        related_name="ais_observations",
        null=True,
        blank=True
    )

    vessel_ids = models.PositiveIntegerField(
        help_text="Compte vesselIDs fourni par GFW."
    )

    cell = models.ForeignKey(
        MaritimeCell,
        on_delete=models.PROTECT,
        related_name="ais_observations"
    )

    category = models.CharField(
        max_length=30,
        default="all_flags"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ais_observations"
        verbose_name = "Observation AIS"
        verbose_name_plural = "Observations AIS"

        constraints = [
                UniqueConstraint(
                fields=["period", "flag", "cell", "category"],
                name="unique_ais_period_flag_cell_category",
                nulls_distinct=False,
            )
        ]

        indexes = [
            models.Index(fields=["period", "flag"]),
            models.Index(fields=["period", "category"])
        ]

    def __str__(self):
        return f"AIS {self.flag} - {self.period}"


class SARObservation(models.Model):
    """
    Détections satellitaires SAR issues de GFW.
    """

    class MatchingCategory(models.TextChoices):
        MATCHED = "matched", "Matched"
        UNMATCHED = "unmatched", "Unmatched"

    period = models.DateField(
        help_text="Premier jour du mois concerné."
    )

    detections = models.PositiveIntegerField()

    vessel_ids = models.PositiveIntegerField(
        help_text="Compte vesselIDs fourni par GFW."
    )
    
    import_batch = models.ForeignKey(
        "ingestion.ImportBatch",
        on_delete=models.PROTECT,
        related_name="sar_observations",
        null=True,
        blank=True
    )

    cell = models.ForeignKey(
        MaritimeCell,
        on_delete=models.PROTECT,
        related_name="sar_observations"
    )

    category = models.CharField(
        max_length=20,
        choices=MatchingCategory.choices
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "sar_observations"
        verbose_name = "Observation SAR"
        verbose_name_plural = "Observations SAR"

        constraints = [
            UniqueConstraint(
                fields=["period", "cell", "category"],
                name="unique_sar_period_cell_category"
            )
        ]

        indexes = [
            models.Index(fields=["period", "category"])
        ]

    def __str__(self):
        return f"SAR {self.category} - {self.period}"




class CellZoneIntersection(models.Model):

    class Classification(models.TextChoices):
        CORE = "core", "Zone principale"
        BOUNDARY = "boundary", "Zone frontalière"
        OUTSIDE = "outside", "Hors zone"

    cell = models.ForeignKey(
        MaritimeCell,
        on_delete=models.CASCADE,
        related_name="zone_intersections",
    )

    zone = models.ForeignKey(
        MaritimeZone,
        on_delete=models.CASCADE,
        related_name="cell_intersections",
    )

    # Surface totale de la cellule, en km²
    cell_area_km2 = models.DecimalField(
        max_digits=14,
        decimal_places=6,
    )

    # Surface de la cellule située dans la zone, en km²
    intersection_area_km2 = models.DecimalField(
        max_digits=14,
        decimal_places=6,
    )

    # Pourcentage de recouvrement entre 0 et 100
    overlap_percentage = models.DecimalField(
        max_digits=7,
        decimal_places=4,
    )

    center_inside = models.BooleanField()

    classification = models.CharField(
        max_length=20,
        choices=Classification.choices,
    )

    # Paramètres de reproductibilité
    threshold_percent = models.PositiveSmallIntegerField(default=75)
    analysis_srid = models.PositiveIntegerField(default=32628)

    method = models.CharField(
        max_length=100,
        default="square_grid_0.1_degree",
    )

    computed_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "cell_zone_intersections"

        verbose_name = "Intersection cellule-zone"
        verbose_name_plural = "Intersections cellules-zones"

        constraints = [
            UniqueConstraint(
                fields=["cell", "zone"],
                name="unique_cell_zone_intersection",
            ),
            CheckConstraint(
                condition=Q(
                    overlap_percentage__gte=0,
                    overlap_percentage__lte=100,
                ),
                name="valid_cell_overlap_percentage",
            ),
        ]

        indexes = [
            models.Index(fields=["zone", "classification"]),
            models.Index(fields=["classification", "overlap_percentage"]),
        ]

    def __str__(self):
        return (
            f"Cellule {self.cell_id} - "
            f"{self.zone.name} ({self.overlap_percentage}%)"
        )
