import os
import json
from datetime import datetime
import rasterio
import matplotlib.pyplot as plt
import numpy as np
from shapely.geometry import box, mapping
import pystac
import xml.etree.ElementTree as ET
from matplotlib.colors import ListedColormap

# === Input and Output Paths ===
filename_base = "saraikela-kharsawan_gobindpur_2023-07-01_2024-06-30_LULCmap_10m"
input_tif = f"/home/vishnu/corestack_STAC/data/{filename_base}.tif"
qgis_style_path = "/home/vishnu/corestack_STAC/data/style_file.qml"
data_dir = os.path.dirname(input_tif)

# === STAC Catalog Metadata ===
output_dir = "/home/vishnu/corestack_STAC/output_catalog_lulc"
item_id = "gobindpur-lulc"
item_dir = os.path.join(output_dir, item_id)
os.makedirs(item_dir, exist_ok=True)

# === Parse QML with color hex codes ===
def parse_qml_to_classes(qml_path):
    tree = ET.parse(qml_path)
    root = tree.getroot()
    classes = []
    for entry in root.findall(".//paletteEntry"):
        try:
            value = int(entry.attrib["value"])
            label = entry.attrib.get("label", f"Class {value}")
            color = entry.attrib.get("color")
            classes.append({
                "value": value,
                "name": label,
                "color": color
            })
        except Exception as e:
            print(f"⚠️ Failed to parse class entry: {e}")
    return classes

def get_qml_colormap(qml_path):
    tree = ET.parse(qml_path)
    root = tree.getroot()
    colormap = {}
    for entry in root.findall(".//paletteEntry"):
        try:
            value = int(entry.attrib["value"])
            color = entry.attrib["color"]
            colormap[value] = color
        except:
            continue
    return colormap

# === Read raster metadata
with rasterio.open(input_tif) as src:
    bounds = src.bounds
    bbox = [bounds.left, bounds.bottom, bounds.right, bounds.top]
    geometry = mapping(box(*bbox))
    epsg = src.crs.to_epsg()

filename = os.path.basename(input_tif)
parts = filename.split('_')
try:
    start_dt = datetime.strptime(parts[2], "%Y-%m-%d")
    end_dt = datetime.strptime(parts[3], "%Y-%m-%d")
except:
    start_dt = datetime(2023, 1, 1)
    end_dt = datetime(2023, 12, 31)

# === Create STAC Catalog and Item
catalog = pystac.Catalog(
    id="gobindpur-lulc-catalog",
    description="STAC Catalog for Gobindpur LULC 2023-24 with thumbnail and legend from local GeoTIFF"
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
    stac_extensions=["https://stac-extensions.github.io/projection/v1.0.0/schema.json"]
)

# === Add GeoTIFF asset
item.add_asset(
    key="raster-data",
    asset=pystac.Asset(
        href="../../data/" + os.path.basename(input_tif),
        media_type=pystac.MediaType.GEOTIFF,
        roles=["data"],
        title="Gobindpur LULC Raster (GeoTIFF)"
    )
)

# === Add QML Style + Classification
if os.path.exists(qgis_style_path):
    # QML style asset
    item.add_asset(
        key="qgis-style",
        asset=pystac.Asset(
            href="../../data/style_file.qml",
            media_type="application/xml",
            roles=["style"],
            title="QGIS Style File"
        )
    )

    # classification:classes property
    lulc_classes = parse_qml_to_classes(qgis_style_path)
    item.properties["classification:classes"] = lulc_classes

    # legend.json
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

# === Generate thumbnail with color map
thumb_path = os.path.join(data_dir, "thumbnail.png")
class_color_map = get_qml_colormap(qgis_style_path)
sorted_values = sorted(class_color_map.keys())
hex_colors = [class_color_map[val] for val in sorted_values]
rgb_colors = [tuple(int(h[i:i+2], 16)/255 for i in (1, 3, 5)) for h in hex_colors]
cmap = ListedColormap(rgb_colors)
value_to_index = {val: i for i, val in enumerate(sorted_values)}

with rasterio.open(input_tif) as src:
    array = src.read(1)
indexed_array = np.vectorize(lambda x: value_to_index.get(x, 0))(array)

plt.figure(figsize=(3, 3))
plt.axis('off')
plt.imshow(indexed_array, cmap=cmap)
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

# === Finalize Catalog
catalog.add_item(item)
catalog.normalize_hrefs(output_dir)
catalog.make_all_asset_hrefs_relative()
catalog.save(catalog_type=pystac.CatalogType.SELF_CONTAINED)

# Rename item file
default_item_path = os.path.join(item_dir, "item.json")
custom_item_path = os.path.join(item_dir, f"{item_id}.json")
if os.path.exists(default_item_path):
    os.rename(default_item_path, custom_item_path)

print("\n✅ STAC catalog created with:")
print(f"  📄 catalog.json: {os.path.join(output_dir, 'catalog.json')}")
print(f"  📄 item: {custom_item_path}")
print(f"  🖼 thumbnail: {thumb_path}")
