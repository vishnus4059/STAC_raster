import os
import json
from datetime import datetime
import rasterio
import matplotlib.pyplot as plt
from shapely.geometry import box, mapping
import pystac
import xml.etree.ElementTree as ET


input_tif = "/home/vishnu/corestack_STAC/data/saraikela-kharsawan_gobindpur_2023-07-01_2024-06-30_LULCmap_10m.tif"
qgis_style_path = "/home/vishnu/corestack_STAC/data/style_file.qml"
data_dir = os.path.dirname(input_tif)


def parse_qml_to_classes(qml_path):
    try:
        tree = ET.parse(qml_path)
        root = tree.getroot()
        classes = []
        for entry in root.findall(".//paletteEntry"):
            value = int(entry.attrib.get("value", -1))
            label = entry.attrib.get("label", f"Class {value}")
            color = entry.attrib.get("color", "#000000")
            classes.append({
                "value": value,
                "name": label,
                "color": color
            })
        return sorted(classes, key=lambda x: x["value"])
    except Exception as e:
        print(f"⚠️ Failed to parse QML: {e}")
        return []

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
    description="Land Use Land Cover (LULC) classification is a method used to identify different features on the Earth's surface, such as forests, rivers, croplands, or buildings, and is used for monitoring and planning land use. The LULC data is derived from multiple sources including multi-spectral data from Landsat-7, Landsat-8, Sentinel-2, MODIS, and Sentinel-1 satellite constellations, Dynamic World data, and Open Street Maps. The classification process involves a series of binary classifications, followed by error-correction layers for each LULC class. Dynamic World data is used to identify built-up areas, barren lands, and shrubs, while Sentinel-1 SAR data is used to identify water pixels, particularly in the Kharif season. Non-classified pixels are categorized into croplands and forests/trees, with further classification of cropland pixels into single Kharif, single non-Kharif, double, and triple cropping. The LULC classifier generates annual outputs from 2003 to the present, with a spatial resolution of 10m. The model has an accuracy of 83% in classifying areas by cropping intensity and 94% accuracy on standard LULC labels. LULC data is used for tracking anthropogenic activities, designing sustainable land management policies, understanding changes in crop water usage, and detecting water bodies with seasonal availability."
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

# === QML Style + Classification Classes
if os.path.exists(qgis_style_path):
    print("✅ QML file found. Parsing classification...")
    lulc_classes = parse_qml_to_classes(qgis_style_path)

    item.add_asset(
        key="qgis-style",
        asset=pystac.Asset(
            href="../../data/style_file.qml",
            media_type="application/xml",
            roles=["style"],
            title="QGIS Style File"
        )
    )

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
            title="LULC Legend"
        )
    )
else:
    print("⚠️ QML file not found. Skipping classification section.")

# === Thumbnail generation
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

# === Finalize catalog
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
print("  ✔ Dates from filename")
print("  ✔ classification:classes from QML")
print("  ✔ Thumbnail preview")
print("📄 catalog.json:", os.path.join(output_dir, "catalog.json"))
print("📄 item:", custom_item_path)
