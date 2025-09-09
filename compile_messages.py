import os
import polib

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOCALE_DIR = os.path.join(BASE_DIR, "locale")

for root, dirs, files in os.walk(LOCALE_DIR):
    for file in files:
        if file.endswith(".po"):
            po_path = os.path.join(root, file)
            mo_path = po_path.replace(".po", ".mo")

            print(f"Compiling {po_path} -> {mo_path}")
            po = polib.pofile(po_path)
            po.save_as_mofile(mo_path)
