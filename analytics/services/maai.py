
from datetime import datetime

from django.db.models import Q
from django.utils import timezone

from analytics.models import CellMonthlyMetric


WEIGHTS = {
    "ais_intensity": 0.30,
    "sar_unmatched_volume": 0.30,
    "sar_unmatched_rate": 0.15,
    "ais_increase": 0.25,
}

BASELINE_MONTHS = 11
MINIMUM_BASELINE_MONTHS = 6


def shift_month(period, offset):
    """Décale une date du nombre de mois demandé."""
    month_index = period.year * 12 + period.month - 1 + offset

    return datetime(
        month_index // 12,
        month_index % 12 + 1,
        1,
    ).date()


def robust_scores(values):
    """
    Normalisation logarithmique robuste.

    Le 95e percentile des valeurs positives devient 100.
    Les valeurs extrêmes sont plafonnées à 100.
    Les valeurs nulles restent nulles.
    """
    from math import log1p

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


def calculate_maai(period, classification="all"):
    """
    Calcule le MAAI pour une période mensuelle.

    Retourne :
    - le classement complet ;
    - les cellules analysées ;
    - les métadonnées méthodologiques.

    Le score est exploratoire et ne constitue pas
    une preuve d'activité illégale.
    """

    if classification not in ("all", "core", "boundary"):
        raise ValueError("Classification invalide.")

    period = period.replace(day=1)

    baseline_start = shift_month(
        period,
        -BASELINE_MONTHS,
    )

    # -------------------------------------------------
    # 1. Données du mois analysé
    # -------------------------------------------------

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
                unmatched_rate * 100,
                2,
            ),
        })

    if not cells:
        return {
            "period": period,
            "baseline_start": baseline_start,
            "cells": [],
            "ranking": [],
            "meta": {
                "cells_analyzed": 0,
                "minimum_baseline_months": MINIMUM_BASELINE_MONTHS,
                "historical_baseline_months": BASELINE_MONTHS,
            },
        }

    # -------------------------------------------------
    # 2. Historique des onze mois précédents
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
    )

    history_by_cell = {}

    for cell_id, month, ais_hours in history_rows:
        history_by_cell.setdefault(cell_id, []).append({
            "period": month,
            "ais_hours": int(ais_hours or 0),
        })

    # -------------------------------------------------
    # 3. Variables analytiques
    # -------------------------------------------------

    from math import log1p

    analysis = []

    for cell in cells:
        history = history_by_cell.get(cell["cell_id"], [])

        historical_ais = [
            item["ais_hours"]
            for item in history
        ]

        baseline_median = 0

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

        if baseline_months >= MINIMUM_BASELINE_MONTHS:
            relative_increase = max(
                0,
                cell["ais_hours"] - baseline_median,
            ) / max(baseline_median, 1)

        sar_total = cell["sar_total"]

        sar_confidence = (
            sar_total / (sar_total + 3)
            if sar_total > 0 else 0
        )

        analysis.append({
            **cell,
            "historical_ais_median": round(
                baseline_median,
                2,
            ),
            "baseline_months": baseline_months,
            "ais_relative_increase_percent": round(
                relative_increase * 100,
                2,
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
    # 4. Normalisation
    # -------------------------------------------------

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
    # 5. Calcul du MAAI
    # -------------------------------------------------

    attention_ranking = []

    for index, item in enumerate(analysis):
        components = {
            "ais_intensity": ais_scores[index],
            "sar_unmatched_volume": sar_volume_scores[index],
            "sar_unmatched_rate": sar_rate_scores[index],
            "ais_increase": ais_change_scores[index],
        }

        score = sum(
            components[key] * WEIGHTS[key]
            for key in WEIGHTS
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
                item["_sar_confidence"],
                3,
            ),
            "baseline_months": item["baseline_months"],
        })

    attention_ranking.sort(
        key=lambda item: item["attention_index"],
        reverse=True,
    )

    for index, item in enumerate(attention_ranking, start=1):
        item["rank"] = index

    return {
        "period": period,
        "baseline_start": baseline_start,
        "cells": cells,
        "ranking": attention_ranking,
        "meta": {
            "cells_analyzed": len(cells),
            "historical_baseline_months": BASELINE_MONTHS,
            "minimum_baseline_months": MINIMUM_BASELINE_MONTHS,
            "weights": WEIGHTS,
            "normalization": "log_p95_cap",
        },
    }




def calculate_temporal_maai(
    periods,
    classification="all",
    top_n=10,
    result_limit=20,
):
    """
    Analyse la persistance des cellules prioritaires sur plusieurs mois.

    Une cellule est prioritaire lorsqu'elle figure dans le Top N
    MAAI d'un mois exploitable.

    Les mois sont calculés individuellement avec le moteur MAAI
    existant : chaque mois conserve sa propre référence historique.
    """

    from collections import defaultdict

    cell_history = defaultdict(list)
    monthly_results = []
    eligible_months = []

    for period in periods:
        result = calculate_maai(
            period=period,
            classification=classification,
        )

        # Une cellule doit disposer d'au moins six mois
        # de référence pour participer à l'analyse temporelle.
        valid_ranking = [
            item
            for item in result["ranking"]
            if item["baseline_months"] >= MINIMUM_BASELINE_MONTHS
        ]

        if not valid_ranking:
            monthly_results.append({
                "period": period.strftime("%Y-%m"),
                "eligible": False,
                "cells_analyzed": len(result["cells"]),
                "eligible_cells": 0,
                "top_cells": [],
            })
            continue

        eligible_months.append(period)

        # Le classement mensuel est déjà trié par score.
        priority_cells = valid_ranking[:top_n]
        priority_ids = {
            item["cell_id"] for item in priority_cells
        }

        for item in valid_ranking:
            cell_history[item["cell_id"]].append({
                "period": period.strftime("%Y-%m"),
                "score": item["attention_index"],
                "rank": item["rank"],
                "in_top_n": item["cell_id"] in priority_ids,
                "ais_hours": item["ais_hours"],
                "sar_unmatched": item["sar_unmatched"],
            })

        monthly_results.append({
            "period": period.strftime("%Y-%m"),
            "eligible": True,
            "cells_analyzed": len(result["cells"]),
            "eligible_cells": len(valid_ranking),
            "top_cells": [
                {
                    "cell_id": item["cell_id"],
                    "attention_index": item["attention_index"],
                }
                for item in priority_cells
            ],
        })

    total_eligible_months = len(eligible_months)

    if total_eligible_months == 0:
        return {
            "monthly": monthly_results,
            "cells": [],
            "meta": {
                "eligible_months": 0,
                "requested_months": len(periods),
                "top_n": top_n,
            },
        }

    # -------------------------------------------------
    # Agrégation temporelle par cellule
    # -------------------------------------------------

    temporal_ranking = []

    for cell_id, history in cell_history.items():
        observed_scores = [
            item["score"] for item in history
        ]

        priority_months = sum(
            1 for item in history if item["in_top_n"]
        )

        mean_score = (
            sum(observed_scores) / len(observed_scores)
            if observed_scores else 0
        )

        peak_score = (
            max(observed_scores)
            if observed_scores else 0
        )

        first_score = observed_scores[0]
        last_score = observed_scores[-1]
        trend_delta = last_score - first_score

        if trend_delta > 5:
            trend = "increasing"
        elif trend_delta < -5:
            trend = "decreasing"
        else:
            trend = "stable"

        observed_months = len(history)

        persistence_rate = (
            priority_months / observed_months * 100
            if observed_months
            else 0
        )

        coverage_rate = (
            observed_months / total_eligible_months * 100
            if total_eligible_months
            else 0
        )

        if persistence_rate >= 60:
            recurrence = "persistent"
        elif persistence_rate >= 30:
            recurrence = "recurring"
        else:
            recurrence = "occasional"

        latest = history[-1]

        temporal_ranking.append({
            "cell_id": cell_id,
            "latitude": None,
            "longitude": None,
            "classification": None,
            "priority_months": priority_months,
            "observed_months": observed_months,
            "eligible_months": total_eligible_months,
            "persistence_rate_percent": round(persistence_rate, 2),
            "coverage_rate_percent": round(coverage_rate, 2),
            "mean_attention_index": round(mean_score, 2),
            "peak_attention_index": round(peak_score, 2),
            "first_attention_index": round(first_score, 2),
            "last_attention_index": round(last_score, 2),
            "trend_delta": round(trend_delta, 2),
            "trend": trend,
            "recurrence": recurrence,
            "last_period": latest["period"],
            "monthly_history": history,
        })

    temporal_ranking.sort(
    key=lambda item: (
        item["persistence_rate_percent"],
        item["priority_months"],
        item["mean_attention_index"],
        item["peak_attention_index"],
    ),
    reverse=True,
    )

    # Compléter les coordonnées depuis le classement mensuel
    # le plus récent disponible.
    latest_period = eligible_months[-1]

    latest_result = calculate_maai(
        period=latest_period,
        classification=classification,
    )

    latest_cells = {
        item["cell_id"]: item
        for item in latest_result["ranking"]
    }

    for item in temporal_ranking:
        current = latest_cells.get(item["cell_id"])

        if current:
            item["latitude"] = current["latitude"]
            item["longitude"] = current["longitude"]
            item["classification"] = current["classification"]

    return {
        "monthly": monthly_results,
        "cells": temporal_ranking[:result_limit],
        "meta": {
            "eligible_months": total_eligible_months,
            "requested_months": len(periods),
            "top_n": top_n,
            "result_count": min(
                len(temporal_ranking),
                result_limit,
            ),
            "recurrence_thresholds": {
                "persistent_percent": 60,
                "recurring_percent": 30,
            },
            "methodology": (
                "Persistance calculée à partir des apparitions "
                "dans le Top N MAAI mensuel. Les périodes sans "
                "six mois de référence sont exclues."
            ),
        },
    }
