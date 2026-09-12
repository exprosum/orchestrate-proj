import zipfile
from pathlib import Path

root = Path(__file__).parent
zip_path = root / "code.zip"

files_to_zip = [
    ("code/__init__.py", "code/__init__.py"),
    ("code/data_loader.py", "code/data_loader.py"),
    ("code/financial_engine.py", "code/financial_engine.py"),
    ("code/image_cache.json", "code/image_cache.json"),
    ("code/image_extractor.py", "code/image_extractor.py"),
    ("code/main.py", "code/main.py"),
    ("code/message_parser.py", "code/message_parser.py"),
    ("code/requirements.txt", "code/requirements.txt"),
    ("code/evaluation/usage_report.md", "evaluation/usage_report.md"),
    ("README.md", "README.md"),
]

with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
    for src, dst in files_to_zip:
        p = root / src
        if p.exists():
            zf.write(p, dst)
            print(f"Added {src} -> {dst}")
            
        else:
            print(f"Warning: {src} not found!")

print(f"\nCreated {zip_path} (size: {zip_path.stat().st_size / 1024:.1f} KB)")
