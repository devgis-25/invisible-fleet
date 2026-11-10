
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.db import connection


print("=" * 65)
print("INSPECTION DU SCHEMA POSTGIS")
print("=" * 65)

with connection.cursor() as cursor:

    # 1. Tables métier
    cursor.execute("""
        SELECT tablename
        FROM pg_tables
        WHERE schemaname = 'public'
          AND (
              tablename LIKE 'maritime%'
              OR tablename LIKE 'ais%'
              OR tablename LIKE 'sar%'
          )
        ORDER BY tablename;
    """)

    tables = cursor.fetchall()

    print("\nTABLES :")
    for table in tables:
        print(" -", table[0])

    # 2. Index spatiaux et autres index
    cursor.execute("""
        SELECT tablename, indexname, indexdef
        FROM pg_indexes
        WHERE schemaname = 'public'
          AND tablename IN (
              'maritime_zones',
              'maritime_cells'
          )
        ORDER BY tablename, indexname;
    """)

    indexes = cursor.fetchall()

    print("\nINDEX :")
    for table, name, definition in indexes:
        print(f"\n{table} | {name}")
        print(definition)

    # 3. Colonnes géométriques
    cursor.execute("""
        SELECT f_table_name, f_geometry_column,
               type, srid, coord_dimension
        FROM geometry_columns
        WHERE f_table_schema = 'public'
        ORDER BY f_table_name;
    """)

    geometries = cursor.fetchall()

    print("\nCOLONNES GEOGRAPHIQUES :")
    for geometry in geometries:
        print(geometry)

print("\nInspection terminée.")
