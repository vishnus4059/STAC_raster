import os
import json
from datetime import datetime
import rasterio
import matplotlib.pyplot as plt
import numpy as np
from shapely.geometry import box, mapping
import pystac
from matplotlib.colors import ListedColormap

# === Input Paths ===
filename_base = "saraikela-kharsawan_gobindpur_2023-07-01_2024-06-30_LULCmap_10m"
input_tif = f"/home/vishnu/corestack_STAC/data/{filename_base}.tif"
data_dir = os.path.dirname(input_tif)

# === Output Paths ===
output_dir = "/home/vishnu/corestack_STAC/output_catalog_lulc"
item_id = "gobindpur-lulc"
item_dir = os.path.join(output_dir, item_id)
os.makedirs(item_dir, exist_ok=True)

# === vis_params color palette
vis_params = {
    'min': 0,
    'max': 12,
    'palette': [
        '#000000', '#ff0000', '#74ccf4', '#1ca3ec', '#0f5e9c',
        '#f1c232', '#38761d', '#A9A9A9', '#f1c232', '#f59d22',
        '#e68600', '#b3561d', '#c39797'
    ]
}

# === classification:classes for STAC
classification_classes = [
    {"value": i, "name": f"Class {i}", "color": hex_code}
    for i, hex_code in enumerate(vis_params["palette"])
]

# === Read raster metadata
with rasterio.open(input_tif) as src:
    bounds = src.bounds
    bbox = [bounds.left, bounds.bottom, bounds.right, bounds.top]
    geometry = mapping(box(*bbox))
    epsg = src.crs.to_epsg()

# === Extract dates from filename
parts = filename_base.split('_')
try:
    start_dt = datetime.strptime(parts[2], "%Y-%m-%d")
    end_dt = datetime.strptime(parts[3], "%Y-%m-%d")
except:
    start_dt = datetime(2023, 1, 1)
    end_dt = datetime(2023, 12, 31)

# === Create STAC catalog and item
catalog = pystac.Catalog(
    id="gobindpur-lulc-catalog",
    description="STAC Catalog for Gobindpur LULC 2023-24 with vis_params and thumbnail"
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
        "proj:bbox": bbox,
        "classification:classes": classification_classes
    },
    stac_extensions=["https://stac-extensions.github.io/projection/v1.0.0/schema.json"]
)

# === Add GeoTIFF as asset
item.add_asset(
    key="raster-data",
    asset=pystac.Asset(
        href=f"../../data/{filename_base}.tif",
        media_type=pystac.MediaType.GEOTIFF,
        roles=["data"],
        title="Gobindpur LULC Raster (GeoTIFF)"
    )
)

# === Save classification legend as JSON
legend_path = os.path.join(data_dir, "legend.json")
with open(legend_path, "w") as f:
    json.dump(classification_classes, f, indent=2)

item.add_asset(
    key="legend",
    asset=pystac.Asset(
        href="../../data/legend.json",
        media_type="application/json",
        roles=["legend"],
        title="LULC Legend (vis_params)"
    )
)

# === Generate thumbnail using vis_params colors
thumb_path = os.path.join(data_dir, "thumbnail.png")
cmap = ListedColormap(vis_params["palette"])

with rasterio.open(input_tif) as src:
    array = src.read(1)
    masked_array = np.where((array >= vis_params["min"]) & (array <= vis_params["max"]), array, 0)

plt.figure(figsize=(3, 3))
plt.axis('off')
plt.imshow(masked_array, cmap=cmap, vmin=vis_params["min"], vmax=vis_params["max"])
plt.savefig(thumb_path, bbox_inches='tight', pad_inches=0)
plt.close()

item.add_asset(
    key="thumbnail",
    asset=pystac.Asset(
        href="../../data/thumbnail.png",
        media_type="image/png",
        roles=["thumbnail"],
        title="LULC Thumbnail"
    )
)

# === Finalize and Save Catalog
catalog.add_item(item)
catalog.normalize_hrefs(output_dir)
catalog.make_all_asset_hrefs_relative()
catalog.save(catalog_type=pystac.CatalogType.SELF_CONTAINED)

# === Rename item.json for clarity
default_item_path = os.path.join(item_dir, "item.json")
custom_item_path = os.path.join(item_dir, f"{item_id}.json")
if os.path.exists(default_item_path):
    os.rename(default_item_path, custom_item_path)

# === Done
print("\n✅ STAC catalog created with:")
print(f"  📄 catalog.json: {os.path.join(output_dir, 'catalog.json')}")
print(f"  📄 item: {custom_item_path}")
print(f"  🖼 thumbnail: {thumb_path}")
print(f"  📜 legend: {legend_path}")
