import os
import rasterio
from shapely.geometry import box, mapping
import pystac
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt
import json


tif_path = "/home/vishnu/corestack_STAC/data/gobindpur_lulc_2023_2024.tif"
qgis_style_path = "/home/vishnu/corestack_STAC/data/style_file.qml"


output_dir = "/home/vishnu/corestack_STAC/output_catalog_lulc"
item_id = "gobindpur-lulc"
item_dir = os.path.join(output_dir, item_id)
data_dir = os.path.dirname(tif_path)
os.makedirs(item_dir, exist_ok=True)


with rasterio.open(tif_path) as src:
    bounds = src.bounds
    bbox = [bounds.left, bounds.bottom, bounds.right, bounds.top]
    geometry = mapping(box(*bbox))


start_dt = None
end_dt = None

with rasterio.open(tif_path) as src:
    tags = src.tags()
    date_str = tags.get("TIFFTAG_DATETIME")
    if date_str:
        try:
            dt = datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
            start_dt = dt
            end_dt = dt
        except Exception as e:
            print(f"⚠️ Failed to parse TIFFTAG_DATETIME: {e}")

# If no date from TIFF, use fallback
if not start_dt:
    start_dt = datetime(2023, 6, 1)
    end_dt = datetime(2024, 3, 31)


catalog = pystac.Catalog(
    id="gobindpur-lulc-catalog",
    description="STAC Catalog for Gobindpur LULC 2023-24 with metadata and thumbnail"
)

item = pystac.Item(
    id=item_id,
    geometry=geometry,
    bbox=bbox,
    datetime=start_dt,
    properties={
        "start_datetime": start_dt.isoformat() + "Z",
        "end_datetime": end_dt.isoformat() + "Z"
    }
)


item.add_asset(
    key="raster-data",
    asset=pystac.Asset(
        href="../../data/gobindpur_lulc_2023_2024.tif",
        media_type=pystac.MediaType.GEOTIFF,
        roles=["data", "download"],
        title="Gobindpur LULC Raster (GeoTIFF)"
    )
)


if os.path.exists(qgis_style_path):
    item.add_asset(
        key="qgis-style",
        asset=pystac.Asset(
            href="../../data/style_file.qml",
            title="QGIS Style File (QML)",
            media_type="application/xml",
            roles=["style", "download"]
        )
    )
else:
    print("QML file not found. Skipping style asset.")


thumb_path = os.path.join(data_dir, "thumbnail.png")
with rasterio.open(tif_path) as src:
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


lulc_classes = [
    {"value": 1, "name": "Water"},
    {"value": 2, "name": "Urban"},
    {"value": 3, "name": "Forest"},
    {"value": 4, "name": "Cropland"},
    {"value": 5, "name": "Barren"}
]
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


catalog.add_item(item)
catalog.normalize_hrefs(output_dir)
catalog.make_all_asset_hrefs_relative()
catalog.save(catalog_type=pystac.CatalogType.SELF_CONTAINED)


default_item_path = os.path.join(item_dir, "item.json")
custom_item_path = os.path.join(item_dir, f"{item_id}.json")
if os.path.exists(default_item_path):
    os.rename(default_item_path, custom_item_path)

print("STAC catalog created with:")
print("start/end datetime")
print("thumbnail preview")
print("LULC legend")
print(f"📄 catalog.json: {os.path.join(output_dir, 'catalog.json')}")
print(f"📄 item: {custom_item_path}")

