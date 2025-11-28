"""
Extract individual banner and icon assets from the sprite sheet.

The sprite sheet contains 6 theme rows:
1. Default (with glow)
2. Glow-Free
3. High-Contrast
4. Ultra-Dark + Cyan Neon
5. Minimalist Dark
6. Minimalist Dark variant

Each row contains:
- Large banner (left side, ~480x240)
- Icon sizes: 64x64, 48x48, 32x32
- Wide banner format
"""

from PIL import Image
from pathlib import Path

# Paths
SPRITE_SHEET = Path(__file__).parent.parent / "assets" / "temp" / "banner_pack_sheet.png"
OUTPUT_DIR = Path(__file__).parent.parent / "assets" / "banners"

# Theme definitions - map row index to theme name
THEMES = {
    0: "default",
    1: "glow_free",
    2: "high_contrast",
    3: "ultra_dark_cyan",
    4: "minimalist_dark",
    5: "minimalist_dark_alt",
}

# Row height (approximately)
ROW_HEIGHT = 256

# Asset regions within each row (x, y_offset, width, height)
# These are relative to the row's top-left corner
ASSETS = {
    # Large banner with frame
    "banner_large": (10, 10, 480, 180),
    # Icon sizes (approximate positions from the right side)
    "icon_64": (505, 35, 64, 64),
    "icon_48": (590, 35, 64, 64),  # Actually seems similar size
    "icon_32": (670, 35, 64, 64),
    # Wide banner
    "banner_wide": (755, 35, 240, 64),
    # Second row of small icons
    "icon_small": (505, 125, 64, 64),
}


def extract_assets():
    """Extract all assets from the sprite sheet."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    img = Image.open(SPRITE_SHEET)
    print(f"Loaded sprite sheet: {img.size}")

    for row_idx, theme_name in THEMES.items():
        theme_dir = OUTPUT_DIR / theme_name
        theme_dir.mkdir(exist_ok=True)

        row_y = row_idx * ROW_HEIGHT
        print(f"\nExtracting {theme_name} (row {row_idx}, y={row_y})...")

        for asset_name, (x, y_off, w, h) in ASSETS.items():
            # Calculate absolute position
            abs_x = x
            abs_y = row_y + y_off

            # Crop the asset
            box = (abs_x, abs_y, abs_x + w, abs_y + h)
            asset = img.crop(box)

            # Save as PNG
            output_path = theme_dir / f"{asset_name}.png"
            asset.save(output_path, "PNG")
            print(f"  Saved: {output_path.name} ({w}x{h})")

    # Also extract just the logo/icon (circular part) for use as app icon
    print("\n\nExtracting circular icons for app use...")

    # The main icon is centered in the banner - let's extract it
    for row_idx, theme_name in THEMES.items():
        row_y = row_idx * ROW_HEIGHT

        # The circular logo is approximately at center of the large banner
        # Based on visual inspection: logo centered around x=245, y=row+115
        # The logo itself is about 170x170
        logo_center_x = 245
        logo_center_y = row_y + 115
        logo_size = 170
        logo_x = logo_center_x - logo_size // 2
        logo_y = logo_center_y - logo_size // 2

        box = (logo_x, logo_y, logo_x + logo_size, logo_y + logo_size)
        logo = img.crop(box)

        # Save in theme folder
        output_path = OUTPUT_DIR / theme_name / "logo_170.png"
        logo.save(output_path, "PNG")

        # Also create resized versions for common icon sizes
        for size in [128, 64, 48, 32, 16]:
            resized = logo.resize((size, size), Image.Resampling.LANCZOS)
            output_path = OUTPUT_DIR / theme_name / f"icon_{size}.png"
            resized.save(output_path, "PNG")

        print(f"  {theme_name}: logo + icons (16-170px)")

    print(f"\n\nDone! Assets saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    extract_assets()
