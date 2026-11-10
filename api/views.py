
from django.db.models import Sum, Count
from django.utils.dateparse import parse_date
from datetime import datetime
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from analytics.models import CellMonthlyMetric
from analytics.services.maai import (
    calculate_temporal_maai,
    shift_month,
)
import json

from maritime.models import MaritimeZone

class AnalyticsOverviewView(APIView):
    """
    Vue synthétique des indicateurs maritimes.

    Par défaut, les statistiques excluent les cellules
    entièrement extérieures à la ZEE.
    """

    def get(self, request):
        classification = request.query_params.get(
            "classification", "all"
        ).lower()

        start = request.query_params.get("start")
        end = request.query_params.get("end")

        allowed_classifications = ["all", "core", "boundary"]

        if classification not in allowed_classifications:
            raise ValidationError({
                "classification": (
                    "Valeur invalide. Valeurs autorisées : "
                    "all, core, boundary."
                )
            })

        queryset = CellMonthlyMetric.objects.all()

        # Filtrage spatial
        if classification != "all":
            queryset = queryset.filter(
                zone_intersection__classification=classification
            )
        else:
            queryset = queryset.exclude(
                zone_intersection__classification="outside"
            )

        # Filtrage temporel
        if start:
            start_date = parse_date(start)

            if not start_date:
                raise ValidationError({
                    "start": "Format invalide. Utiliser YYYY-MM-DD."
                })

            queryset = queryset.filter(period__gte=start_date)

        if end:
            end_date = parse_date(end)

            if not end_date:
                raise ValidationError({
                    "end": "Format invalide. Utiliser YYYY-MM-DD."
                })

            queryset = queryset.filter(period__lte=end_date)

        if start and end and start_date > end_date:
            raise ValidationError({
                "period": "La date de début doit précéder la date de fin."
            })

        # Agrégation
        data = queryset.aggregate(
            ais_hours=Sum("ais_hours"),
            ais_observations=Sum("ais_observation_count"),
            ais_vessel_ids_sum=Sum("ais_vessel_ids_sum"),

            sar_matched=Sum("sar_matched_detections"),
            sar_unmatched=Sum("sar_unmatched_detections"),

            sar_matched_observations=Sum(
                "sar_matched_observation_count"
            ),
            sar_unmatched_observations=Sum(
                "sar_unmatched_observation_count"
            ),

            active_cells=Count(
                "zone_intersection__cell_id",
                distinct=True
            ),

            months_covered=Count(
                "period",
                distinct=True
            ),
        )

        ais_hours = data["ais_hours"] or 0
        ais_observations = data["ais_observations"] or 0

        sar_matched = data["sar_matched"] or 0
        sar_unmatched = data["sar_unmatched"] or 0

        sar_total = sar_matched + sar_unmatched

        unmatched_rate = (
            round((sar_unmatched / sar_total) * 100, 2)
            if sar_total > 0
            else 0
        )

        return Response({
            "filters": {
                "classification": classification,
                "start": start,
                "end": end,
            },
            "ais": {
                "presence_hours": ais_hours,
                "observation_count": ais_observations,
                "vessel_ids_sum": data["ais_vessel_ids_sum"] or 0,
            },
            "sar": {
                "total_detections": sar_total,
                "matched_detections": sar_matched,
                "unmatched_detections": sar_unmatched,
                "unmatched_rate_percent": unmatched_rate,
                "matched_observations": (
                    data["sar_matched_observations"] or 0
                ),
                "unmatched_observations": (
                    data["sar_unmatched_observations"] or 0
                ),
            },
            "spatial": {
                "active_cells": data["active_cells"] or 0,
                "months_covered": data["months_covered"] or 0,
            },
        })




class AnalyticsTimelineView(APIView):
    """
    Évolution mensuelle des indicateurs AIS/SAR.
    """

    def get(self, request):
        classification = request.query_params.get(
            "classification", "all"
        ).lower()

        start = request.query_params.get("start")
        end = request.query_params.get("end")

        allowed_classifications = ["all", "core", "boundary"]

        if classification not in allowed_classifications:
            raise ValidationError({
                "classification": (
                    "Valeur invalide : all, core ou boundary."
                )
            })

        queryset = CellMonthlyMetric.objects.all()

        # Filtrage spatial
        if classification == "all":
            queryset = queryset.exclude(
                zone_intersection__classification="outside"
            )
        else:
            queryset = queryset.filter(
                zone_intersection__classification=classification
            )

        # Filtrage temporel
        start_date = None
        end_date = None

        if start:
            start_date = parse_date(start)
            if start_date is None:
                raise ValidationError({
                    "start": "Format attendu : YYYY-MM-DD."
                })
            queryset = queryset.filter(period__gte=start_date)

        if end:
            end_date = parse_date(end)
            if end_date is None:
                raise ValidationError({
                    "end": "Format attendu : YYYY-MM-DD."
                })
            queryset = queryset.filter(period__lte=end_date)

        if start_date and end_date and start_date > end_date:
            raise ValidationError({
                "period": "La date de début doit précéder la date de fin."
            })

        # Agrégation mensuelle
        monthly_data = (
            queryset
            .values("period")
            .annotate(
                ais_hours=Sum("ais_hours"),
                ais_observations=Sum("ais_observation_count"),

                sar_matched=Sum("sar_matched_detections"),
                sar_unmatched=Sum("sar_unmatched_detections"),

                active_cells=Count(
                    "zone_intersection__cell_id",
                    distinct=True,
                ),
            )
            .order_by("period")
        )

        results = []

        for row in monthly_data:
            matched = row["sar_matched"] or 0
            unmatched = row["sar_unmatched"] or 0
            total_sar = matched + unmatched

            unmatched_rate = (
                round(unmatched / total_sar * 100, 2)
                if total_sar
                else 0
            )

            results.append({
                "period": row["period"].strftime("%Y-%m"),
                "ais_hours": row["ais_hours"] or 0,
                "ais_observations": row["ais_observations"] or 0,
                "sar_matched": matched,
                "sar_unmatched": unmatched,
                "sar_total": total_sar,
                "sar_unmatched_rate_percent": unmatched_rate,
                "active_cells": row["active_cells"] or 0,
            })

        return Response({
            "filters": {
                "classification": classification,
                "start": start,
                "end": end,
            },
            "months_count": len(results),
            "results": results,
        })





class AnalyticsMapView(APIView):
    """
    GeoJSON des cellules maritimes sous forme de polygones.
    Chaque cellule est un carré de 0.1 degré.
    """

    CELL_HALF_SIZE = 0.05

    def get(self, request):
        classification = request.query_params.get(
            "classification", "all"
        ).lower()

        period_param = request.query_params.get("period")

        allowed_classifications = [
            "all", "core", "boundary", "outside"
        ]

        if classification not in allowed_classifications:
            raise ValidationError({
                "classification": (
                    "Valeurs autorisées : all, core, boundary, outside."
                )
            })

        # Déterminer le mois
        if period_param:
            try:
                period = datetime.strptime(
                    period_param, "%Y-%m"
                ).date().replace(day=1)
            except ValueError:
                raise ValidationError({
                    "period": "Format attendu : YYYY-MM."
                })
        else:
            period = (
                CellMonthlyMetric.objects
                .order_by("-period")
                .values_list("period", flat=True)
                .first()
            )

        if period is None:
            return Response({
                "type": "FeatureCollection",
                "features": [],
                "meta": {
                    "message": "Aucune donnée disponible."
                }
            })

        queryset = (
            CellMonthlyMetric.objects
            .filter(period=period)
            .select_related(
                "zone_intersection",
                "zone_intersection__cell",
            )
        )

        if classification == "all":
            queryset = queryset.exclude(
                zone_intersection__classification="outside"
            )
        else:
            queryset = queryset.filter(
                zone_intersection__classification=classification
            )

        features = []
        half = self.CELL_HALF_SIZE

        for metric in queryset.iterator(chunk_size=1000):
            intersection = metric.zone_intersection
            cell = intersection.cell

            latitude = float(cell.latitude)
            longitude = float(cell.longitude)

            west = longitude - half
            east = longitude + half
            south = latitude - half
            north = latitude + half

            # Anneau polygonal fermé, conforme à GeoJSON.
            coordinates = [[
                [west, south],
                [east, south],
                [east, north],
                [west, north],
                [west, south],
            ]]

            matched = metric.sar_matched_detections
            unmatched = metric.sar_unmatched_detections
            sar_total = matched + unmatched

            unmatched_rate = (
                round(unmatched / sar_total * 100, 2)
                if sar_total
                else 0
            )

            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": coordinates,
                },
                "properties": {
                    "cell_id": cell.id,
                    "latitude": latitude,
                    "longitude": longitude,

                    "classification": intersection.classification,
                    "overlap_percentage": float(
                        intersection.overlap_percentage
                    ),
                    "center_inside": intersection.center_inside,

                    "period": period.strftime("%Y-%m"),

                    "ais_hours": metric.ais_hours,
                    "ais_observations": (
                        metric.ais_observation_count
                    ),
                    "ais_flag_count": metric.ais_flag_count,

                    "sar_matched": matched,
                    "sar_unmatched": unmatched,
                    "sar_total": sar_total,
                    "sar_unmatched_rate_percent": unmatched_rate,
                },
            })

        return Response({
            "type": "FeatureCollection",
            "meta": {
                "period": period.strftime("%Y-%m"),
                "classification": classification,
                "feature_count": len(features),
                "geometry_type": "Polygon",
                "cell_resolution_degrees": 0.1,
                "cell_half_size_degrees": half,
                "crs": "EPSG:4326",
                "description": (
                    "Polygones carrés représentant les cellules "
                    "spatiales GFW de 0.1 degré. Les valeurs AIS/SAR "
                    "sont agrégées par cellule et ne représentent "
                    "pas des positions exactes de navires."
                ),
            },
            "features": features,
        })



class MaritimeZoneView(APIView):
    def get(self, request):
        zone = MaritimeZone.objects.filter(
            marine_regions_id=8371
        ).first()

        if zone is None:
            return Response(
                {"detail": "La ZEE sénégalaise est introuvable."},
                status=404
            )

        return Response({
            "type": "Feature",
            "geometry": json.loads(zone.geometry.geojson),
            "properties": {
                "name": zone.name,
                "marine_regions_id": zone.marine_regions_id,
                "area_km2": float(zone.area_km2),
                "source": zone.source,
                "source_version": zone.source_version,
            }
        })
        
        





class AnalyticsRankingView(APIView):
    """
    Classements et indice exploratoire d'attention analytique
    des cellules de la ZEE sénégalaise.

    L'indice ne constitue pas une preuve d'activité illégale.
    """

    def get(self, request):
        from bisect import bisect_left, bisect_right
        from math import log1p

        classification = request.query_params.get(
            "classification", "all"
        ).lower()

        period_param = request.query_params.get("period")
        limit_param = request.query_params.get("limit", "10")

        allowed_classifications = ["all", "core", "boundary"]

        if classification not in allowed_classifications:
            raise ValidationError({
                "classification": "Valeurs autorisées : all, core, boundary."
            })

        try:
            limit = int(limit_param)
        except (TypeError, ValueError):
            raise ValidationError({
                "limit": "La limite doit être un nombre entier."
            })

        if limit < 1 or limit > 50:
            raise ValidationError({
                "limit": "La limite doit être comprise entre 1 et 50."
            })

        if period_param:
            try:
                period = datetime.strptime(
                    period_param, "%Y-%m"
                ).date().replace(day=1)
            except ValueError:
                raise ValidationError({
                    "period": "Format attendu : YYYY-MM."
                })
        else:
            period = (
                CellMonthlyMetric.objects
                .order_by("-period")
                .values_list("period", flat=True)
                .first()
            )

        if period is None:
            return Response({
                "filters": {
                    "period": None,
                    "classification": classification,
                    "limit": limit,
                },
                "rankings": {
                    "ais_presence": [],
                    "sar_unmatched": [],
                    "attention_index": [],
                },
                "meta": {
                    "message": "Aucune donnée disponible."
                },
            })

        # -------------------------------------------------
        # 1. Calcul de la période historique de référence
        # -------------------------------------------------

        # Les onze mois précédant le mois analysé.
        month_index = period.year * 12 + period.month - 1 - 11

        baseline_start = datetime(
            month_index // 12,
            month_index % 12 + 1,
            1,
        ).date()

        queryset = (
            CellMonthlyMetric.objects
            .filter(period=period)
            .select_related(
                "zone_intersection",
                "zone_intersection__cell",
            )
        )

        if classification == "all":
            queryset = queryset.exclude(
                zone_intersection__classification="outside"
            )
        else:
            queryset = queryset.filter(
                zone_intersection__classification=classification
            )

        cells = []

        for metric in queryset.iterator(chunk_size=1000):
            intersection = metric.zone_intersection
            cell = intersection.cell

            matched = metric.sar_matched_detections or 0
            unmatched = metric.sar_unmatched_detections or 0
            sar_total = matched + unmatched

            unmatched_rate = (
                unmatched / sar_total
                if sar_total > 0 else 0
            )

            cells.append({
                "cell_id": cell.id,
                "latitude": float(cell.latitude),
                "longitude": float(cell.longitude),
                "classification": intersection.classification,
                "overlap_percentage": float(
                    intersection.overlap_percentage
                ),
                "ais_hours": int(metric.ais_hours or 0),
                "ais_observations": int(
                    metric.ais_observation_count or 0
                ),
                "ais_flag_count": int(metric.ais_flag_count or 0),
                "sar_matched": int(matched),
                "sar_unmatched": int(unmatched),
                "sar_total": int(sar_total),
                "sar_unmatched_rate_percent": round(
                    unmatched_rate * 100, 2
                ),
            })

        # -------------------------------------------------
        # 2. Récupération des onze mois historiques
        # -------------------------------------------------

        history_queryset = (
            CellMonthlyMetric.objects
            .filter(
                period__gte=baseline_start,
                period__lt=period,
            )
            .exclude(
                zone_intersection__classification="outside"
            )
        )

        if classification != "all":
            history_queryset = history_queryset.filter(
                zone_intersection__classification=classification
            )

        history_rows = history_queryset.values_list(
            "zone_intersection__cell_id",
            "period",
            "ais_hours",
            "sar_unmatched_detections",
        )

        history_by_cell = {}

        for cell_id, month, ais_hours, sar_unmatched in history_rows:
            history_by_cell.setdefault(cell_id, []).append({
                "period": month,
                "ais_hours": int(ais_hours or 0),
                "sar_unmatched": int(sar_unmatched or 0),
            })

        # -------------------------------------------------
        # 3. Construction des variables analytiques
        # -------------------------------------------------

        analysis = []

        for cell in cells:
            history = history_by_cell.get(cell["cell_id"], [])

            historical_ais = [
                item["ais_hours"] for item in history
            ]

            baseline_median = (
                sorted(historical_ais)[len(historical_ais) // 2]
                if historical_ais else 0
            )

            # Médiane exacte, y compris si le nombre de mois est pair.
            if historical_ais:
                ordered = sorted(historical_ais)
                middle = len(ordered) // 2
                if len(ordered) % 2 == 0:
                    baseline_median = (
                        ordered[middle - 1] + ordered[middle]
                    ) / 2
                else:
                    baseline_median = ordered[middle]

            baseline_months = len(history)

            relative_increase = 0

            if baseline_months >= 6:
                relative_increase = max(
                    0,
                    cell["ais_hours"] - baseline_median
                ) / max(baseline_median, 1)

            sar_total = cell["sar_total"]

            # Réduction de l'influence des taux basés sur
            # un nombre très faible de détections.
            sar_confidence = (
                sar_total / (sar_total + 3)
                if sar_total > 0 else 0
            )

            analysis.append({
                **cell,
                "historical_ais_median": round(
                    baseline_median, 2
                ),
                "baseline_months": baseline_months,
                "ais_relative_increase_percent": round(
                    relative_increase * 100, 2
                ),
                "_ais_log": log1p(cell["ais_hours"]),
                "_sar_volume_log": log1p(
                    cell["sar_unmatched"]
                ),
                "_sar_rate": (
                    cell["sar_unmatched_rate_percent"] / 100
                ) * sar_confidence,
                "_ais_change_log": log1p(relative_increase),
                "_sar_confidence": sar_confidence,
            })

        # -------------------------------------------------
        # 4. Normalisation par rang percentile
        # -------------------------------------------------


        def robust_scores(values):
            """
            Normalisation logarithmique robuste.

            - Les valeurs nulles restent à zéro.
            - Le 95e percentile des valeurs positives devient 100.
            - Les valeurs extrêmes sont plafonnées à 100.
            - Les distributions clairsemées sont mieux gérées.
            """
            positive = sorted(value for value in values if value > 0)

            if not positive:
                return [0.0 for _ in values]

            p95_index = max(
                0,
                min(
                    len(positive) - 1,
                    int(len(positive) * 0.95),
                ),
            )

            reference = positive[p95_index]

            denominator = log1p(reference)

            if denominator <= 0:
                return [0.0 for _ in values]

            return [
                round(
                    min(100.0, log1p(value) / denominator * 100),
                    2,
                ) if value > 0 else 0.0
                for value in values
            ]

        ais_scores = robust_scores([
            item["_ais_log"] for item in analysis
        ])

        sar_volume_scores = robust_scores([
            item["_sar_volume_log"] for item in analysis
        ])

        sar_rate_scores = robust_scores([
            item["_sar_rate"] for item in analysis
        ])

        ais_change_scores = robust_scores([
            item["_ais_change_log"] for item in analysis
        ])

        # -------------------------------------------------
        # 5. Calcul de l'indice MAAI
        # -------------------------------------------------

        attention_ranking = []

        for index, item in enumerate(analysis):
            components = {
                "ais_intensity": round(ais_scores[index], 2),
                "sar_unmatched_volume": round(
                    sar_volume_scores[index], 2
                ),
                "sar_unmatched_rate": round(
                    sar_rate_scores[index], 2
                ),
                "ais_increase": round(
                    ais_change_scores[index], 2
                ),
            }

            score = (
                components["ais_intensity"] * 0.30
                + components["sar_unmatched_volume"] * 0.30
                + components["sar_unmatched_rate"] * 0.15
                + components["ais_increase"] * 0.25
            )

            attention_ranking.append({
                "cell_id": item["cell_id"],
                "latitude": item["latitude"],
                "longitude": item["longitude"],
                "classification": item["classification"],
                "attention_index": round(score, 2),
                "components": components,
                "ais_hours": item["ais_hours"],
                "ais_historical_median": item[
                    "historical_ais_median"
                ],
                "ais_relative_increase_percent": item[
                    "ais_relative_increase_percent"
                ],
                "sar_matched": item["sar_matched"],
                "sar_unmatched": item["sar_unmatched"],
                "sar_unmatched_rate_percent": item[
                    "sar_unmatched_rate_percent"
                ],
                "sar_confidence": round(
                    item["_sar_confidence"], 3
                ),
                "baseline_months": item["baseline_months"],
            })

        attention_ranking.sort(
            key=lambda item: item["attention_index"],
            reverse=True,
        )

        for index, item in enumerate(
            attention_ranking, start=1
        ):
            item["rank"] = index

        # -------------------------------------------------
        # 6. Classements historiques conservés
        # -------------------------------------------------

        ais_ranking = [
            dict(cell)
            for cell in sorted(
                [c for c in cells if c["ais_hours"] > 0],
                key=lambda c: (
                    c["ais_hours"],
                    c["ais_observations"],
                ),
                reverse=True,
            )[:limit]
        ]

        sar_ranking = [
            dict(cell)
            for cell in sorted(
                [c for c in cells if c["sar_unmatched"] > 0],
                key=lambda c: (
                    c["sar_unmatched"],
                    c["sar_unmatched_rate_percent"],
                ),
                reverse=True,
            )[:limit]
        ]

        for index, item in enumerate(ais_ranking, start=1):
            item["rank"] = index

        for index, item in enumerate(sar_ranking, start=1):
            item["rank"] = index

        return Response({
            "filters": {
                "period": period.strftime("%Y-%m"),
                "classification": classification,
                "limit": limit,
                "baseline_start": baseline_start.strftime("%Y-%m"),
                "baseline_end": (
                    period.replace(day=1)
                ).strftime("%Y-%m"),
            },
            "rankings": {
                "ais_presence": ais_ranking,
                "sar_unmatched": sar_ranking,
                "attention_index": attention_ranking[:limit],
            },
            "meta": {
                "cells_analyzed": len(cells),
                "ais_ranked_cells": len(ais_ranking),
                "sar_ranked_cells": len(sar_ranking),
                "attention_ranked_cells": min(
                    len(attention_ranking), limit
                ),
                "methodology": {
                    "name": "MAAI",
                    "version": "0.1",
                    "weights": {
                        "ais_intensity": 0.30,
                        "sar_unmatched_volume": 0.30,
                        "sar_unmatched_rate": 0.15,
                        "ais_increase": 0.25,
                    },
                    "normalization": "log_p95_cap",
                    "historical_baseline_months": 11,
                    "minimum_baseline_months": 6,
                    "sar_confidence_formula": "n / (n + 3)",
                },
                "description": (
                    "Indice exploratoire de priorisation analytique. "
                    "Un score élevé indique une combinaison de signaux "
                    "à examiner et ne constitue pas une preuve "
                    "d'activité illégale."
                ),
            },
        })

class AnalyticsTemporalView(APIView):
    """
    Analyse temporelle de la persistance des cellules prioritaires.
    """

    def get(self, request):
        classification = request.query_params.get(
            "classification", "all"
        ).lower()

        start_param = request.query_params.get("start_period")
        end_param = request.query_params.get("end_period")

        top_n_param = request.query_params.get("top_n", "10")
        limit_param = request.query_params.get("limit", "20")

        if classification not in ("all", "core", "boundary"):
            raise ValidationError({
                "classification": (
                    "Valeurs autorisées : all, core, boundary."
                )
            })

        try:
            top_n = int(top_n_param)
            result_limit = int(limit_param)
        except (TypeError, ValueError):
            raise ValidationError({
                "limit": "top_n et limit doivent être des entiers."
            })

        if not 1 <= top_n <= 50:
            raise ValidationError({
                "top_n": "La valeur doit être comprise entre 1 et 50."
            })

        if not 1 <= result_limit <= 100:
            raise ValidationError({
                "limit": "La valeur doit être comprise entre 1 et 100."
            })

        available_periods = list(
            CellMonthlyMetric.objects
            .order_by()
            .values_list("period", flat=True)
            .distinct()
            .order_by("period")
        )

        if not available_periods:
            return Response({
                "filters": {},
                "monthly": [],
                "cells": [],
                "meta": {
                    "message": "Aucune donnée mensuelle disponible."
                },
            })

        latest_available = available_periods[-1]

        def parse_month(value, parameter_name):
            try:
                return datetime.strptime(
                    value, "%Y-%m"
                ).date().replace(day=1)
            except (ValueError, TypeError):
                raise ValidationError({
                    parameter_name: "Format attendu : YYYY-MM."
                })

        end_period = (
            parse_month(end_param, "end_period")
            if end_param
            else latest_available
        )

        start_period = (
            parse_month(start_param, "start_period")
            if start_param
            else shift_month(end_period, -11)
        )

        if start_period > end_period:
            raise ValidationError({
                "period": (
                    "La période de début doit précéder "
                    "la période de fin."
                )
            })

        if end_period > latest_available:
            raise ValidationError({
                "end_period": (
                    "La période demandée dépasse "
                    "les dernières données disponibles."
                )
            })

        periods = [
            period
            for period in available_periods
            if start_period <= period <= end_period
        ]

        if not periods:
            return Response({
                "filters": {
                    "start_period": start_period.strftime("%Y-%m"),
                    "end_period": end_period.strftime("%Y-%m"),
                    "classification": classification,
                },
                "monthly": [],
                "cells": [],
                "meta": {
                    "message": "Aucune donnée pour cette période."
                },
            })

        result = calculate_temporal_maai(
            periods=periods,
            classification=classification,
            top_n=top_n,
            result_limit=result_limit,
        )

        return Response({
            "filters": {
                "start_period": start_period.strftime("%Y-%m"),
                "end_period": end_period.strftime("%Y-%m"),
                "classification": classification,
                "top_n": top_n,
                "limit": result_limit,
            },
            "monthly": result["monthly"],
            "cells": result["cells"],
            "meta": result["meta"],
        })
