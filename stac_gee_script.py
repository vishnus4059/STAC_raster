import ee
import time

# === Initialize Earth Engine with your project ===
try:
    ee.Initialize(project='ee-corestackdev')
except Exception as e:
    ee.Authenticate()
    ee.Initialize(project='ee-corestackdev')

# === Your private asset ID ===
asset_id = "projects/ee-corestackdev/assets/apps/mws/jharkhand/saraikela-kharsawan/gobindpur/saraikela-kharsawan_gobindpur_2023-07-01_2024-06-30_LULCmap_10m"

# === Load the image ===
lulc_image = ee.Image(asset_id)

# === Define AOI (geometry bounds of the image) ===
aoi = lulc_image.geometry().bounds()

# === Optional: Print metadata ===
info = lulc_image.getInfo()
print("LULC Metadata:")
print(" - Bands:", [band['id'] for band in info['bands']])
print(" - Type:", info['type'])

# === Export the image to Google Drive ===
task = ee.batch.Export.image.toDrive(
    image=lulc_image.clip(aoi),
    description='Gobindpur_LULC_Export',
    folder='GEE_Exports',  # Folder name in your Google Drive
    fileNamePrefix='Gobindpur_LULC_2023_24',
    region=aoi,
    scale=10,
    crs='EPSG:4326',
    maxPixels=1e13
)

# === Start and monitor the export task ===
task.start()
print("🚀 Export started to Google Drive > GEE_Exports")

# Optional: Wait until task completes
while task.active():
    print("⏳ Exporting... Please wait...")
    time.sleep(30)

# === Final status ===
print("✅ Export task finished with state:", task.status()['state'])
