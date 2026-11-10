
import os
from pathlib import Path

# Bibliothèques géospatiales QGIS pour GeoDjango sous Windows
if os.name == "nt":
    QGIS_ROOT = Path(r"C:\Program Files\QGIS 3.44.9")

    QGIS_BIN = QGIS_ROOT / "bin"
    GDAL_DATA = QGIS_ROOT / "apps" / "gdal" / "share" / "gdal"
    PROJ_DATA = QGIS_ROOT / "share" / "proj"

    # Conserver les références pour maintenir les répertoires DLL accessibles
    _DLL_HANDLES = [os.add_dll_directory(str(QGIS_BIN))]

    os.environ["GDAL_DATA"] = str(GDAL_DATA)
    os.environ["PROJ_LIB"] = str(PROJ_DATA)
    os.environ["PROJ_DATA"] = str(PROJ_DATA)
