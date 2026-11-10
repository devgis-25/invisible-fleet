import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

import inspect
from django.db import connection
from django.db.backends.base.schema import BaseDatabaseSchemaEditor

editor_class = type(connection.schema_editor())

print("========== HIERARCHIE ==========")
for cls in editor_class.__mro__:
    print(cls.__module__, cls.__name__)

print("\n========== METHODES SQL ==========")
for method in ["table_sql", "column_sql", "_iter_column_sql"]:
    actual = getattr(editor_class, method)
    base = getattr(BaseDatabaseSchemaEditor, method)
    print(f"\n{method}")
    print("Même implémentation que Django :", actual is base)
    print(inspect.getsource(actual))

print("\n========== TEMPLATES ==========")
with connection.schema_editor(collect_sql=True) as editor:
    print("CREATE TABLE:", repr(editor.sql_create_table))
    print("CHECK:", repr(editor.sql_check_constraint))
    print("COLUMN SEPARATOR: inspecter column_sql")



from django.db.migrations.loader import MigrationLoader

loader = MigrationLoader(connection, replace_migrations=False)
state = loader.project_state([("analytics", "0001_initial")])
HistoricalMetric = state.apps.get_model("analytics", "CellMonthlyMetric")

with connection.schema_editor(collect_sql=True) as editor:
    editor.deferred_sql = []
    sql, _ = editor.table_sql(HistoricalMetric)

for needle in ["NOT NULLCHECK", "NOT NULLPRIMARY", "integer NOT NULL"]:
    position = sql.find(needle)
    print("\nRECHERCHE :", repr(needle), "POSITION :", position)
    if position >= 0:
        fragment = sql[max(0, position - 30):position + len(needle) + 30]
        print("FRAGMENT :", repr(fragment))
        print("CODES :", [ord(char) for char in fragment])