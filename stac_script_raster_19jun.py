import os
import json
from datetime import datetime
import rasterio
import matplotlib.pyplot as plt
from shapely.geometry import box, mapping
import pystac
from osgeo import gdal
from constants import FALLBACK_START_DATE, FALLBACK_END_DATE, CLASSIFICATION_JSON

# === Input and Output Paths ===
input_tif = "/home/vishnu/corestack_STAC/data/saraikela-kharsawan_gobindpur_2023-07-01_2024-06-30_LULCmap_10m.tif"
output_cog = "/home/vishnu/corestack_STAC/data/gobindpur_lulc_cog.tif"
qgis_style_path = "/home/vishnu/corestack_STAC/data/style_file.qml"
data_dir = os.path.dirname(input_tif)

# === Public Raw GitHub COG URL
PUBLIC_COG_URL = "https://raw.githubusercontent.com/vishnus4059/STAC_raster/master/data/gobindpur_lulc_cog.tif"

# === Convert GeoTIFF to COG
def convert_geotiff_to_cog(input_path, output_path):
    gdal.Translate(
        output_path,
        input_path,
        format='COG',
        creationOptions=[
            'COMPRESS=DEFLATE',
            'BLOCKSIZE=512',
            'BIGTIFF=YES'
        ]
    )
    print(f"✅ COG saved to: {output_path}")

convert_geotiff_to_cog(input_tif, output_cog)

# === Geometry and projection info ===
with rasterio.open(output_cog) as src:
    bounds = src.bounds
    bbox = [bounds.left, bounds.bottom, bounds.right, bounds.top]
    geometry = mapping(box(*bbox))
    epsg = src.crs.to_epsg()

# === Extract Dates from filename or fallback ===
filename = os.path.basename(input_tif)
parts = filename.split('_')
try:
    start_dt = datetime.strptime(parts[2], "%Y-%m-%d")
    end_dt = datetime.strptime(parts[3], "%Y-%m-%d")
except Exception as e:
    print(f"⚠️ Failed to extract dates from filename: {e}")
    start_dt = datetime.strptime(FALLBACK_START_DATE, "%Y-%m-%d")
    end_dt = datetime.strptime(FALLBACK_END_DATE, "%Y-%m-%d")

# === STAC Catalog Setup ===
output_dir = "/home/vishnu/corestack_STAC/output_catalog_lulc"
item_id = "gobindpur-lulc"
item_dir = os.path.join(output_dir, item_id)
os.makedirs(item_dir, exist_ok=True)

catalog = pystac.Catalog(
    id="gobindpur-lulc-catalog",
    description="STAC Catalog for Gobindpur LULC 2023-24 with metadata, tile preview, and legend"
)

item = pystac.Item(
    id=item_id,
    geometry=geometry,
    bbox=bbox,
    datetime=start_dt,
    properties={
        "start_datetime": start_dt.isoformat() + "Z",
        "end_datetime": end_dt.isoformat() + "Z",
        "proj:epsg": epsg,
        "proj:bbox": bbox
    },
    stac_extensions=[
        "https://stac-extensions.github.io/projection/v1.0.0/schema.json"
    ]
)

# === COG asset (relative path)
item.add_asset(
    key="raster-data",
    asset=pystac.Asset(
        href="../../data/gobindpur_lulc_cog.tif",
        media_type=pystac.MediaType.COG,
        roles=["data"],
        title="Gobindpur LULC Raster (COG)"
    )
)

# === Tile preview via Titiler
item.add_asset(
    key="tile",
    asset=pystac.Asset(
        href=f"https://titiler.xyz/cog/tilejson.json?url={PUBLIC_COG_URL}",
        media_type="application/json",
        roles=["tiles"],
        title="LULC Tile Preview (Titiler)"
    )
)

# === Optional QGIS style
if os.path.exists(qgis_style_path):
    item.add_asset(
        key="qgis-style",
        asset=pystac.Asset(
            href="../../data/style_file.qml",
            media_type="application/xml",
            roles=["style"],
            title="QGIS Style File"
        )
    )
else:
    print("⚠️ QML file not found. Skipping style asset.")

# === Generate thumbnail preview
thumb_path = os.path.join(data_dir, "thumbnail.png")
with rasterio.open(output_cog) as src:
    array = src.read(1)

plt.figure(figsize=(3, 3))
plt.axis('off')
plt.imshow(array, cmap='tab20')
plt.savefig(thumb_path, bbox_inches='tight', pad_inches=0)
plt.close()

item.add_asset(
    key="thumbnail",
    asset=pystac.Asset(
        href="../../data/thumbnail.png",
        media_type="image/png",
        roles=["thumbnail"],
        title="Thumbnail Preview"
    )
)

# === Load classification legend from JSON
with open(CLASSIFICATION_JSON) as f:
    lulc_classes = json.load(f)

item.properties["classification:classes"] = lulc_classes

legend_path = os.path.join(data_dir, "legend.json")
with open(legend_path, "w") as f:
    json.dump(lulc_classes, f, indent=2)

item.add_asset(
    key="legend",
    asset=pystac.Asset(
        href="../../data/legend.json",
        media_type="application/json",
        roles=["legend"],
        title="LULC Legend (JSON)"
    )
)

# === Finalize and save catalog
catalog.add_item(item)
catalog.normalize_hrefs(output_dir)
catalog.make_all_asset_hrefs_relative()
catalog.save(catalog_type=pystac.CatalogType.SELF_CONTAINED)

# Rename item.json
default_item_path = os.path.join(item_dir, "item.json")
custom_item_path = os.path.join(item_dir, f"{item_id}.json")
if os.path.exists(default_item_path):
    os.rename(default_item_path, custom_item_path)

print("\n✅ STAC catalog created with:")
print("  📅 Dates from filename or fallback")
print("  🖼 Thumbnail preview")
print("  🗺 Tile preview via Titiler")
print("  📄 catalog.json:", os.path.join(output_dir, "catalog.json"))
print("  📄 item:", custom_item_path)
