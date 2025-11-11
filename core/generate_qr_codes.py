import qrcode
from pathlib import Path

# === Base setup ===
base_dir = Path(__file__).resolve().parent
output_dir = base_dir / "qr_codes"
output_dir.mkdir(exist_ok=True)

# === 3 tracking URLs ===
links = {
    "poster_artists":  "https://artonomy.ir/?utm_source=qr&utm_medium=poster&utm_campaign=artists",
    "poster_audience": "https://artonomy.ir/?utm_source=qr&utm_medium=poster&utm_campaign=audience",
    "visitcard":       "https://artonomy.ir/?utm_source=qr&utm_medium=visitcard&utm_campaign=visitcard",
}

# === QR generation ===
for name, url in links.items():
    qr = qrcode.QRCode(
        version=1,  # automatic sizing if None
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    file_path = output_dir / f"{name}.png"
    img.save(file_path)
    print(f"✅ Saved: {file_path}")

print("\nAll QR codes generated successfully!")
