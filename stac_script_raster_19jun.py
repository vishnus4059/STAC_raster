import os
import json
from datetime import datetime
import rasterio
import matplotlib.pyplot as plt
from shapely.geometry import box, mapping
import pystac
import xml.etree.ElementTree as ET

# === Input and Output Paths ===
input_tif = "/home/vishnu/corestack_STAC/data/saraikela-kharsawan_gobindpur_2023-07-01_2024-06-30_LULCmap_10m.tif"
qgis_style_path = "/home/vishnu/corestack_STAC/data/style_file.qml"
data_dir = os.path.dirname(input_tif)

# === Public GitHub GeoTIFF URL
PUBLIC_TIF_URL = "https://raw.githubusercontent.com/vishnus4059/STAC_raster/master/data/saraikela-kharsawan_gobindpur_2023-07-01_2024-06-30_LULCmap_10m.tif"

# === Parse QML for classification:classes
def parse_qml_to_classes(qml_path):
    tree = ET.parse(qml_path)
    root = tree.getroot()

    classes = []
    for item in root.findall(".//paletteEntry"):
        try:
            value = int(item.attrib.get("value"))
            label = item.attrib.get("label", f"Class {value}")
            color = item.attrib.get("color")  # Format: #RRGGBB
            classes.append({
                "value": value,
                "name": label,
                "color": color
            })
        except Exception as e:
            print(f"⚠️ Failed to parse entry: {e}")
    return classes

# === Geometry and projection info ===
with rasterio.open(input_tif) as src:
    bounds = src.bounds
    bbox = [bounds.left, bounds.bottom, bounds.right, bounds.top]
    geometry = mapping(box(*bbox))
    epsg = src.crs.to_epsg()

# === Extract Dates from filename or fallback
filename = os.path.basename(input_tif)
parts = filename.split('_')
try:
    start_dt = datetime.strptime(parts[2], "%Y-%m-%d")
    end_dt = datetime.strptime(parts[3], "%Y-%m-%d")
except Exception as e:
    print(f"⚠️ Failed to extract dates from filename: {e}")
    start_dt = datetime(2023, 1, 1)
    end_dt = datetime(2023, 12, 31)

# === STAC Catalog Setup
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

# === GeoTIFF asset
item.add_asset(
    key="raster-data",
    asset=pystac.Asset(
        href="../../data/" + os.path.basename(input_tif),
        media_type=pystac.MediaType.GEOTIFF,
        roles=["data"],
        title="Gobindpur LULC Raster (GeoTIFF)"
    )
)

# === Titiler Tile Preview
item.add_asset(
    key="tile",
    asset=pystac.Asset(
        href=f"https://titiler.xyz/cog/tilejson.json?url={PUBLIC_TIF_URL}",
        media_type="application/json",
        roles=["tiles"],
        title="LULC Tile Preview (Titiler)"
    )
)

# === QML Style + Classification Classes
if os.path.exists(qgis_style_path):
    # Add QML file as style asset
    item.add_asset(
        key="qgis-style",
        asset=pystac.Asset(
            href="../../data/style_file.qml",
            media_type="application/xml",
            roles=["style"],
            title="QGIS Style File"
        )
    )

    # Parse and attach classification
    lulc_classes = parse_qml_to_classes(qgis_style_path)
    item.properties["classification:classes"] = lulc_classes

    # Save legend.json
    legend_path = os.path.join(data_dir, "legend.json")
    with open(legend_path, "w") as f:
        json.dump(lulc_classes, f, indent=2)

    item.add_asset(
        key="legend",
        asset=pystac.Asset(
            href="../../data/legend.json",
            media_type="application/json",
            roles=["legend"],
            title="LULC Legend (from QML)"
        )
    )
else:
    print("⚠️ QML file not found. Skipping style and legend.")

# === Generate Basic Thumbnail (optional: we can color it later)
thumb_path = os.path.join(data_dir, "thumbnail.png")
with rasterio.open(input_tif) as src:
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

# === Finalize and Save Catalog
catalog.add_item(item)
catalog.normalize_hrefs(output_dir)
catalog.make_all_asset_hrefs_relative()
catalog.save(catalog_type=pystac.CatalogType.SELF_CONTAINED)

# === Rename item.json to gobindpur-lulc.json
default_item_path = os.path.join(item_dir, "item.json")
custom_item_path = os.path.join(item_dir, f"{item_id}.json")
if os.path.exists(default_item_path):
    os.rename(default_item_path, custom_item_path)

print("\n✅ STAC catalog created with:")
print("  📅 Dates from filename or fallback")
print("  🎨 classification:classes from QML")
print("  🖼 Thumbnail preview")
print("  🗺 Tile preview via Titiler")
print("  📄 catalog.json:", os.path.join(output_dir, "catalog.json"))
print("  📄 item:", custom_item_path)
