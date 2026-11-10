import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

from django.db import connection
from django.db.migrations.loader import MigrationLoader
from analytics.models import CellMonthlyMetric

loader = MigrationLoader(connection, replace_migrations=False)
state = loader.project_state([("analytics", "0001_initial")])
HistoricalMetric = state.apps.get_model("analytics", "CellMonthlyMetric")

print("\n========== MODELE ACTUEL ==========")
print(CellMonthlyMetric._meta.local_fields)

print("\n========== MODELE HISTORIQUE ==========")
print(HistoricalMetric._meta.local_fields)

with connection.schema_editor(collect_sql=True) as editor:
    editor.deferred_sql = []
    current_sql, _ = editor.table_sql(CellMonthlyMetric)
    historical_sql, _ = editor.table_sql(HistoricalMetric)

print("\n========== SQL MODELE ACTUEL ==========")
print(repr(current_sql))

print("\n========== SQL MODELE HISTORIQUE ==========")
print(repr(historical_sql))

print("\n========== COMPARAISON ==========")
print("SQL identiques :", current_sql == historical_sql)

for label, sql in [
    ("ACTUEL", current_sql),
    ("HISTORIQUE", historical_sql),
]:
    print(f"\n{label}")
    print("NOT NULLPRIMARY KEY :", "NOT NULLPRIMARY KEY" in sql)
    print("NOT NULLCHECK :", "NOT NULLCHECK" in sql)
    print("integer NOT NULL :", "integer NOT NULL" in sql)
    print('"ais_observation_count"integer :', '"ais_observation_count"integer' in sql)
