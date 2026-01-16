import zipfile
import shutil
import os

files_to_bundle = [
    'docs/02_protocols/lifeos_packet_schemas_v1.2.yaml',
    'docs/02_protocols/lifeos_packet_schemas_CURRENT.yaml',
    'scripts/validate_packet.py',
    'runtime/tests/test_packet_validation.py',
    'artifacts/review_packets/Review_Packet_AUR_20260105_Plan_Cycle_v1.4.md'
]

bundle_path = 'artifacts/bundles/Bundle_AUR_20260105_Plan_Cycle_v1.4.zip'
ceo_pickup_dir = 'artifacts/for_ceo/'
review_packet_src = 'artifacts/review_packets/Review_Packet_AUR_20260105_Plan_Cycle_v1.4.md'

# Ensure directories exist
os.makedirs('artifacts/bundles', exist_ok=True)
os.makedirs(ceo_pickup_dir, exist_ok=True)

print(f"Creating bundle: {bundle_path}")
with zipfile.ZipFile(bundle_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
    for file in files_to_bundle:
        if os.path.exists(file):
            print(f"Adding {file}")
            zipf.write(file)
        else:
            print(f"WARNING: File not found: {file}")

# Copy Bundle to CEO Pickup
print(f"Copying bundle to {ceo_pickup_dir}")
shutil.copy(bundle_path, ceo_pickup_dir)

# Copy Review Packet to CEO Pickup
print(f"Copying review packet to {ceo_pickup_dir}")
shutil.copy(review_packet_src, ceo_pickup_dir)

print("Delivery Complete.")
