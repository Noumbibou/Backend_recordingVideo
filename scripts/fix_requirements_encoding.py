from pathlib import Path

p = Path("requirements.txt")
bak = p.with_suffix(".txt.bak")
# backup
p.replace(bak)

data = bak.read_bytes()
encodings_to_try = ("utf-8", "utf-16", "utf-16-le", "utf-16-be", "latin-1", "cp1252")

for enc in encodings_to_try:
    try:
        text = data.decode(enc)
        # normalize line endings and remove BOM if present
        text = text.replace("\r\n", "\n").lstrip("\ufeff")
        p.write_text(text, encoding="utf-8")
        print(f"Converted requirements.txt from {enc} -> UTF-8 (backup at {bak})")
        break
    except Exception:
        continue
else:
    print("Impossible de décoder requirements.txt avec les encodages courants. Vérifie le fichier manuellement.")