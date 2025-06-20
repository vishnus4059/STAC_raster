import os
from datetime import datetime
import pystac
from shapely.geometry import shape, mapping
import fiona

# === Paths ===
geojson_path = "/home/vishnu/corestack_STAC/data/gobindpur_swb3.geojson"
thumbnail_path = "/home/vishnu/corestack_STAC/data/gobindpur_swb3_preview.png"  # optional
style_file_path = "/home/vishnu/corestack_STAC/data/style_file.qml"  # optional QGIS style
output_dir = "/home/vishnu/corestack_STAC/output_catalog_vector"

# === Read geometry ===
os.makedirs(output_dir, exist_ok=True)
with fiona.open(geojson_path, "r") as src:
    geom = shape(src[0]['geometry'])
    bbox = list(geom.bounds)
    geometry = mapping(geom)

# === Create Catalog ===
catalog = pystac.Catalog(
    id="gobindpur-vector-catalog",
    title="Gobindpur SWB3 Vector Dataset",
    description="STAC Catalog for Gobindpur SWB3 vector layer (GeoJSON format)",
    href=output_dir
)

# === Create Item ===
item = pystac.Item(
    id="gobindpur-swb3-vector",
    geometry=geometry,
    bbox=bbox,
    datetime=datetime.utcnow(),
    properties={
        "title": "Gobindpur SWB3 GeoJSON Vector Layer",
        "created": datetime.utcnow().isoformat() + "Z",
        "updated": datetime.utcnow().isoformat() + "Z",
        "license": "CC-BY-4.0",
        "platform": "Sentinel-2 (source derived)",
        "region": "Gobindpur, India",
        "vector_type": "SWB3 - Seasonal Water Body Boundaries",
        "format": "GeoJSON"
    }
)

# === Add Primary Asset (GeoJSON) ===
item.add_asset(
    key="data",
    asset=pystac.Asset(
        href=geojson_path,
        media_type=pystac.MediaType.GEOJSON,
        roles=["data"],
        title="SWB3 Vector GeoJSON"
    )
)

# === Optional: Add Thumbnail ===
if os.path.exists(thumbnail_path):
    item.add_asset(
        "thumbnail",
        pystac.Asset(
            href=thumbnail_path,
            media_type=pystac.MediaType.PNG,
            roles=["thumbnail"],
            title="Preview Thumbnail"
        )
    )

# === Optional: Add QGIS Style File ===
if os.path.exists(style_file_path):
    item.add_asset(
        "style",
        pystac.Asset(
            href=style_file_path,
            media_type="application/x-qgis",  # custom or undefined mimetype
            roles=["style"],
            title="QGIS Layer Style"
        )
    )

# === Add item to catalog ===
catalog.add_item(item)

# === Save catalog ===
catalog.normalize_hrefs(output_dir)
catalog.make_all_asset_hrefs_relative()
catalog.save(catalog_type=pystac.CatalogType.SELF_CONTAINED)

# === Validation and Print ===
item.validate()

print(f"\n✅ STAC catalog and item with vector assets saved in: {output_dir}")

