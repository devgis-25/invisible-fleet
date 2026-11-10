
from django.db import models


class ImportBatch(models.Model):
    """
    Trace un import d'un fichier source dans la base.
    """

    class Source(models.TextChoices):
        GFW = "GFW", "Global Fishing Watch"
        MARINE_REGIONS = "MARINE_REGIONS", "Marine Regions"

    class DataType(models.TextChoices):
        AIS = "AIS", "AIS"
        SAR = "SAR", "SAR"
        EEZ = "EEZ", "EEZ"

    class Status(models.TextChoices):
        PENDING = "pending", "En attente"
        RUNNING = "running", "En cours"
        SUCCESS = "success", "Terminé"
        FAILED = "failed", "Échec"

    source = models.CharField(
        max_length=30,
        choices=Source.choices
    )

    data_type = models.CharField(
        max_length=10,
        choices=DataType.choices
    )

    dataset_key = models.CharField(
        max_length=150,
        blank=True
    )

    dataset_version = models.CharField(
        max_length=50,
        blank=True
    )

    category = models.CharField(
        max_length=30,
        blank=True
    )

    period_start = models.DateField()
    period_end = models.DateField()

    file_path = models.CharField(max_length=500)

    file_sha256 = models.CharField(
        max_length=64,
        unique=True
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True
    )

    total_rows = models.PositiveIntegerField(default=0)
    inserted_rows = models.PositiveIntegerField(default=0)
    updated_rows = models.PositiveIntegerField(default=0)
    rejected_rows = models.PositiveIntegerField(default=0)

    error_message = models.TextField(blank=True)

    metadata = models.JSONField(default=dict, blank=True)

    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ingestion_batches"
        verbose_name = "Lot d'import"
        verbose_name_plural = "Lots d'import"
        ordering = ["-created_at"]

        indexes = [
            models.Index(fields=["data_type", "period_start"]),
            models.Index(fields=["source", "dataset_version"]),
        ]

        constraints = [
            models.CheckConstraint(
                condition=models.Q(period_end__gte=models.F("period_start")),
                name="valid_ingestion_period"
            )
        ]

    def __str__(self):
        return (
            f"{self.source} - {self.data_type} - "
            f"{self.period_start} / {self.period_end}"
        )
