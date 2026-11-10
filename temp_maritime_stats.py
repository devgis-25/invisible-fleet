from analytics.models import CellMonthlyMetric
from django.db.models import Max

period = CellMonthlyMetric.objects.aggregate(
    latest=Max("period")
)["latest"]

rows = list(
    CellMonthlyMetric.objects
    .filter(period=period)
    .exclude(zone_intersection__classification="outside")
    .values_list(
        "ais_hours",
        "ais_observation_count",
        "sar_matched_detections",
        "sar_unmatched_detections",
        "sar_unmatched_observation_count",
    )
)

def stats(values):
    values = sorted(int(v or 0) for v in values)
    n = len(values)
    return {
        "min": values[0],
        "median": values[n // 2],
        "p90": values[int((n - 1) * 0.90)],
        "p95": values[int((n - 1) * 0.95)],
        "max": values[-1],
        "positive": sum(v > 0 for v in values),
    }

names = [
    "AIS hours",
    "AIS observations",
    "SAR matched",
    "SAR unmatched",
    "SAR unmatched observations",
]

print("\nPERIODE :", period)
print("CELLULES :", len(rows))

for index, name in enumerate(names):
    print(f"\n{name}")
    print(stats([row[index] for row in rows]))
