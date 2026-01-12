import zipfile
import shutil
import os

files_to_bundle = [
    'docs/02_protocols/lifeos_packet_schemas_v1.1.yaml',
    'docs/01_governance/Antigravity_Council_Review_Packet_Spec_v1.1.md',
    'docs/02_protocols/Build_Handoff_Protocol_v1.1.md',
    'docs/02_protocols/Document_Steward_Protocol_v1.1.md',
    'docs/02_protocols/Packet_Schema_Versioning_Policy_v1.0.md',
    'docs/02_protocols/VALIDATION_IMPLEMENTATION_NOTES.md',
    'scripts/validate_packet.py',
    'runtime/tests/test_packet_validation.py',
    'artifacts/review_packets/Review_Packet_AUR_20260105_Agent_Comm_v1.0.md'
]

bundle_path = 'artifacts/bundles/Bundle_AUR_20260105_Agent_Comm_v1.6.zip'
ceo_pickup_dir = 'artifacts/for_ceo/'
review_packet_src = 'artifacts/review_packets/Review_Packet_AUR_20260105_Agent_Comm_v1.0.md'

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
