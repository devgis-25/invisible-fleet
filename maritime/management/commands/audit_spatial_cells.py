
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction


class Command(BaseCommand):
    help = (
        "Calcule et persiste les intersections entre les cellules "
        "GFW et la ZEE sénégalaise."
    )

    ZONE_MRGID = 8371
    THRESHOLD = 75
    ANALYSIS_SRID = 32628
    CELL_HALF_SIZE = 0.05
    METHOD = "square_grid_0.1_degree"

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, name
                FROM maritime_zones
                WHERE marine_regions_id = %s
                """,
                [self.ZONE_MRGID],
            )
            zones = cursor.fetchall()

            if len(zones) != 1:
                raise CommandError(
                    f"Une seule ZEE avec MRGID {self.ZONE_MRGID} "
                    f"était attendue. Résultat : {len(zones)}."
                )

            zone_id, zone_name = zones[0]

            cursor.execute("SELECT COUNT(*) FROM maritime_cells")
            cell_count = cursor.fetchone()[0]

            if cell_count == 0:
                raise CommandError("Aucune cellule maritime trouvée.")

        self.stdout.write(
            self.style.NOTICE(
                f"Zone : {zone_name} (MRGID {self.ZONE_MRGID})"
            )
        )
        self.stdout.write(f"Cellules à analyser : {cell_count}")
        self.stdout.write(
            f"Seuil : {self.THRESHOLD}% | SRID : {self.ANALYSIS_SRID}"
        )

        sql = """
            WITH zone AS (
                SELECT
                    id AS zone_id,
                    geometry AS geometry_4326,
                    ST_Transform(geometry, %s) AS geometry_projected
                FROM maritime_zones
                WHERE id = %s
            ),

            cell_geometries AS (
                SELECT
                    c.id AS cell_id,
                    z.zone_id,

                    ST_Transform(
                        ST_MakeEnvelope(
                            c.longitude::double precision - %s,
                            c.latitude::double precision - %s,
                            c.longitude::double precision + %s,
                            c.latitude::double precision + %s,
                            4326
                        ),
                        %s
                    ) AS cell_geometry,

                    z.geometry_projected AS zone_geometry,

                    ST_Covers(
                        z.geometry_4326,
                        c.center
                    ) AS center_inside

                FROM maritime_cells c
                CROSS JOIN zone z
            ),

            areas AS (
                SELECT
                    cell_id,
                    zone_id,
                    center_inside,

                    ST_Area(cell_geometry) AS cell_area,
                    ST_Area(
                        ST_Intersection(
                            cell_geometry,
                            zone_geometry
                        )
                    ) AS intersection_area

                FROM cell_geometries
            ),

            measurements AS (
                SELECT
                    cell_id,
                    zone_id,
                    center_inside,
                    cell_area,
                    intersection_area,

                    CASE
                        WHEN cell_area > 0
                        THEN intersection_area / cell_area * 100
                        ELSE 0
                    END AS overlap_percentage

                FROM areas
            )

            INSERT INTO cell_zone_intersections (
                cell_id,
                zone_id,
                cell_area_km2,
                intersection_area_km2,
                overlap_percentage,
                center_inside,
                classification,
                threshold_percent,
                analysis_srid,
                method,
                computed_at
            )

            SELECT
                cell_id,
                zone_id,

                ROUND(
                    (cell_area / 1000000.0)::numeric,
                    6
                ),

                ROUND(
                    (intersection_area / 1000000.0)::numeric,
                    6
                ),

                ROUND(overlap_percentage::numeric, 4),

                center_inside,

                CASE
                    WHEN overlap_percentage >= %s
                        THEN 'core'
                    WHEN overlap_percentage > 0
                        THEN 'boundary'
                    ELSE 'outside'
                END,

                %s,
                %s,
                %s,
                CURRENT_TIMESTAMP

            FROM measurements

            ON CONFLICT (cell_id, zone_id)

            DO UPDATE SET
                cell_area_km2 = EXCLUDED.cell_area_km2,
                intersection_area_km2 = EXCLUDED.intersection_area_km2,
                overlap_percentage = EXCLUDED.overlap_percentage,
                center_inside = EXCLUDED.center_inside,
                classification = EXCLUDED.classification,
                threshold_percent = EXCLUDED.threshold_percent,
                analysis_srid = EXCLUDED.analysis_srid,
                method = EXCLUDED.method,
                computed_at = CURRENT_TIMESTAMP
        """

        params = [
            self.ANALYSIS_SRID,
            zone_id,
            self.CELL_HALF_SIZE,
            self.CELL_HALF_SIZE,
            self.CELL_HALF_SIZE,
            self.CELL_HALF_SIZE,
            self.ANALYSIS_SRID,
            self.THRESHOLD,
            self.THRESHOLD,
            self.ANALYSIS_SRID,
            self.METHOD,
        ]

        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                affected_rows = cursor.rowcount

                cursor.execute(
                    """
                    SELECT
                        classification,
                        COUNT(*) AS cells,
                        ROUND(SUM(cell_area_km2), 3),
                        ROUND(SUM(intersection_area_km2), 3),
                        ROUND(SUM(overlap_percentage), 3)
                    FROM cell_zone_intersections
                    WHERE zone_id = %s
                    GROUP BY classification
                    ORDER BY classification
                    """,
                    [zone_id],
                )

                results = cursor.fetchall()

                cursor.execute(
                    """
                    SELECT
                        COUNT(*),
                        COUNT(*) FILTER (WHERE center_inside),
                        COUNT(*) FILTER (WHERE NOT center_inside)
                    FROM cell_zone_intersections
                    WHERE zone_id = %s
                    """,
                    [zone_id],
                )

                total, centers_inside, centers_outside = cursor.fetchone()

                if total != cell_count:
                    raise CommandError(
                        f"Résultat incomplet : {total}/{cell_count} cellules."
                    )

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Analyse spatiale terminée."))
        self.stdout.write(f"Lignes insérées ou actualisées : {affected_rows}")
        self.stdout.write(f"Cellules enregistrées : {total}")
        self.stdout.write(f"Centroïdes dans la ZEE : {centers_inside}")
        self.stdout.write(f"Centroïdes hors ZEE : {centers_outside}")

        self.stdout.write("")
        self.stdout.write("RÉPARTITION SPATIALE")

        for classification, count, cell_area, intersection_area, _ in results:
            self.stdout.write(
                f"{classification:10} | "
                f"{count:5} cellules | "
                f"Surface cellules : {cell_area} km² | "
                f"Intersection : {intersection_area} km²"
            )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "Les résultats sont enregistrés dans "
                "cell_zone_intersections."
            )
        )
