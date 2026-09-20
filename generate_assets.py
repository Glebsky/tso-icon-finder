import os
import math
from PIL import Image, ImageDraw, ImageFont, ImageFilter

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ICONS_DIR = os.path.join(BASE_DIR, 'icons')

print("Starting TSO Asset Generation...")

# 1. Base App Icon / Favicon
# Find iconic source images from icons directory
source_candidates = [
    'Mayorhouse.png',
    'BuildingSettlers2HQ.png',
    'Mayor_House.png',
    'icon_mayorhouse.png',
    'Bakery.png'
]

source_icon = None
for candidate in source_candidates:
    p = os.path.join(ICONS_DIR, candidate)
    if os.path.exists(p):
        source_icon = p
        break

if not source_icon:
    # Fallback to any valid png
    for f in os.listdir(ICONS_DIR):
        if f.endswith('.png'):
            source_icon = os.path.join(ICONS_DIR, f)
            break

print(f"Using base icon source: {os.path.basename(source_icon)}")
base_img = Image.open(source_icon).convert("RGBA")

def create_badge_icon(size, maskable=False):
    """Creates a high quality themed square/rounded icon with TSO style"""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Background
    bg_color = (15, 23, 42, 255) # #0f172a
    border_color = (56, 189, 248, 200) # #38bdf8
    gold_color = (245, 158, 11, 255) # #f59e0b
    
    padding = 0 if maskable else int(size * 0.08)
    radius = 0 if maskable else int(size * 0.22)
    
    rect_box = [padding, padding, size - padding, size - padding]
    
    if maskable:
        draw.rectangle([0, 0, size, size], fill=bg_color)
        # Subtle gradient or inner ring
        inner_pad = int(size * 0.08)
        draw.rounded_rectangle([inner_pad, inner_pad, size - inner_pad, size - inner_pad], 
                               radius=int(size * 0.18), fill=(30, 41, 59, 255), outline=border_color, width=max(2, int(size * 0.02)))
    else:
        # Glow shadow behind
        draw.rounded_rectangle(rect_box, radius=radius, fill=bg_color, outline=border_color, width=max(2, int(size * 0.025)))
    
    # Resize base game icon crisp pixelated or bicubic
    # Safe inner size
    inner_factor = 0.65 if maskable else 0.70
    icon_w = int((size - 2 * padding) * inner_factor)
    aspect = base_img.width / base_img.height
    if aspect >= 1:
        target_w = icon_w
        target_h = int(icon_w / aspect)
    else:
        target_h = icon_w
        target_w = int(icon_w * aspect)
    
    # Crisp pixel resize
    resized = base_img.resize((target_w, target_h), Image.Resampling.NEAREST)
    
    pos_x = (size - target_w) // 2
    pos_y = (size - target_h) // 2
    
    # Subtle drop shadow under the building
    shadow = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 160))
    mask = resized.split()[3]
    img.paste((0, 0, 0, 140), (pos_x, pos_y + max(2, int(size * 0.03))), mask)
    img.paste(resized, (pos_x, pos_y), resized)
    
    # Accent mini badge in bottom-right if large enough
    if size >= 128:
        b_size = int(size * 0.22)
        b_x = size - padding - b_size - int(size * 0.04)
        b_y = size - padding - b_size - int(size * 0.04)
        draw.ellipse([b_x, b_y, b_x + b_size, b_y + b_size], fill=gold_color, outline=(255, 255, 255, 220), width=max(1, int(size * 0.015)))
        # Draw a small magnifying glass or star
        star_color = (15, 23, 42, 255)
        sw = max(1, int(size * 0.02))
        cx = b_x + b_size // 2
        cy = b_y + b_size // 2
        r = b_size // 4
        draw.ellipse([cx - r, cy - r - 2, cx + r, cy + r - 2], outline=star_color, width=sw)
        draw.line([cx + int(r * 0.7), cy + int(r * 0.7) - 2, cx + r + int(b_size*0.15), cy + r + int(b_size*0.15) - 2], fill=star_color, width=sw + 1)
        
    return img

# Generate Favicons & App Icons
sizes = {
    'favicon-16x16.png': (16, False),
    'favicon-32x32.png': (32, False),
    'apple-touch-icon.png': (180, False),
    'icon-192.png': (192, False),
    'icon-512.png': (512, False),
    'icon-maskable-192.png': (192, True),
    'icon-maskable-512.png': (512, True),
}

generated_images = {}
for filename, (s, maskable) in sizes.items():
    icon_img = create_badge_icon(s, maskable)
    out_path = os.path.join(BASE_DIR, filename)
    icon_img.save(out_path, "PNG")
    generated_images[s] = icon_img
    print(f"Created {filename} ({s}x{s})")

# Create multi-resolution favicon.ico (16, 32, 48)
ico_16 = create_badge_icon(16, False)
ico_32 = create_badge_icon(32, False)
ico_48 = create_badge_icon(48, False)
ico_path = os.path.join(BASE_DIR, 'favicon.ico')
ico_16.save(ico_path, format='ICO', sizes=[(16, 16), (32, 32), (48, 48)])
print("Created favicon.ico")

# Create favicon.svg
svg_content = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">
  <defs>
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#1e293b"/>
      <stop offset="100%" stop-color="#0f172a"/>
    </linearGradient>
    <linearGradient id="goldGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#fbbf24"/>
      <stop offset="100%" stop-color="#d97706"/>
    </linearGradient>
    <linearGradient id="cyanGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#38bdf8"/>
      <stop offset="100%" stop-color="#0284c7"/>
    </linearGradient>
    <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="2" result="blur"/>
      <feComposite in="SourceGraphic" in2="blur" operator="over"/>
    </filter>
  </defs>
  <rect x="2" y="2" width="60" height="60" rx="14" fill="url(#bgGrad)" stroke="#38bdf8" stroke-width="2.5"/>
  <!-- Castle / Mayorhouse emblem silhouette -->
  <path d="M16 46 L16 30 L22 30 L22 34 L26 34 L26 30 L32 30 L32 24 L30 24 L32 18 L34 24 L32 24 L32 30 L38 30 L38 34 L42 34 L42 30 L48 30 L48 46 Z" fill="url(#goldGrad)" filter="url(#glow)"/>
  <rect x="28" y="36" width="8" height="10" rx="3" fill="#0f172a"/>
  <!-- Magnifying Glass accent -->
  <circle cx="45" cy="45" r="9" fill="url(#cyanGrad)" stroke="#0f172a" stroke-width="2"/>
  <circle cx="45" cy="45" r="6" fill="none" stroke="#ffffff" stroke-width="1.8"/>
  <line x1="51" y1="51" x2="59" y2="59" stroke="url(#cyanGrad)" stroke-width="3" stroke-linecap="round"/>
</svg>"""

with open(os.path.join(BASE_DIR, 'favicon.svg'), 'w', encoding='utf-8') as f:
    f.write(svg_content)
print("Created favicon.svg")

# 2. Generate Open Graph 1200x630 Social Preview Image (og-image.png)
print("Creating 1200x630 og-image.png...")
OG_W, OG_H = 1200, 630
og_img = Image.new("RGBA", (OG_W, OG_H), (15, 23, 42, 255))
og_draw = ImageDraw.Draw(og_img)

# Background subtle grid pattern
grid_color = (30, 41, 59, 100)
for gx in range(0, OG_W, 30):
    og_draw.line([(gx, 0), (gx, OG_H)], fill=grid_color, width=1)
for gy in range(0, OG_H, 30):
    og_draw.line([(0, gy), (OG_W, gy)], fill=grid_color, width=1)

# Subtle radial gradient highlight on left & center
glow_layer = Image.new("RGBA", (OG_W, OG_H), (0, 0, 0, 0))
glow_draw = ImageDraw.Draw(glow_layer)
glow_draw.ellipse([40, -100, 800, 500], fill=(56, 189, 248, 30))
glow_draw.ellipse([700, 100, 1300, 700], fill=(245, 158, 11, 20))
og_img = Image.alpha_composite(og_img, glow_layer)
og_draw = ImageDraw.Draw(og_img)

# Frame border
og_draw.rectangle([12, 12, OG_W - 13, OG_H - 13], outline=(56, 189, 248, 120), width=2)
og_draw.rectangle([16, 16, OG_W - 17, OG_H - 17], outline=(245, 158, 11, 60), width=1)

# Corner accents
acc_len = 30
for cx, cy, dx, dy in [(12, 12, 1, 1), (OG_W - 13, 12, -1, 1), (12, OG_H - 13, 1, -1), (OG_W - 13, OG_H - 13, -1, -1)]:
    og_draw.line([(cx, cy), (cx + dx * acc_len, cy)], fill=(56, 189, 248, 255), width=3)
    og_draw.line([(cx, cy), (cx, cy + dy * acc_len)], fill=(56, 189, 248, 255), width=3)

# Load fonts if available, otherwise default
def get_font(size, bold=False):
    win_fonts = [
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/tahoma.ttf",
    ]
    for fn in win_fonts:
        if os.path.exists(fn):
            try:
                return ImageFont.truetype(fn, size)
            except Exception:
                pass
    return ImageFont.load_default()

title_font = get_font(58, bold=True)
subtitle_font = get_font(23, bold=False)
badge_font = get_font(19, bold=True)
tag_font = get_font(17, bold=True)
icon_label_font = get_font(15, bold=True)

# Top Bar Badge
og_draw.rounded_rectangle([60, 52, 320, 92], radius=8, fill=(56, 189, 248, 35), outline=(56, 189, 248, 180), width=1)
og_draw.text((76, 62), "THE SETTLERS ONLINE", font=badge_font, fill=(56, 189, 248, 255))

og_draw.rounded_rectangle([335, 52, 535, 92], radius=8, fill=(245, 158, 11, 35), outline=(245, 158, 11, 180), width=1)
og_draw.text((352, 62), "7,882+ ICONS", font=badge_font, fill=(245, 158, 11, 255))

# Title
og_draw.text((60, 115), "TSO Icon Finder", font=title_font, fill=(248, 250, 252, 255))

# Subtitle (wrapped to prevent cut-off)
og_draw.text((62, 190), "Instant Search & High-Res Pixel Zoom", font=subtitle_font, fill=(226, 232, 240, 255))
og_draw.text((62, 224), "Direct PNG, Clipboard & Code Export", font=subtitle_font, fill=(203, 213, 225, 255))

# Feature tags without raw emoji
tags = [
    ("4 Languages (EN / RU / UK / DE)", (56, 189, 248)),
    ("Search by XML ID, Tag or Name", (245, 158, 11)),
    ("PWA & Full Offline Worker", (16, 185, 129)),
    ("Fast 1-Click Clipboard Copy", (192, 132, 252))
]

cur_x = 62
cur_y = 280
for text, col in tags:
    bbox = og_draw.textbbox((0, 0), text, font=tag_font)
    tw = bbox[2] - bbox[0] + 32
    th = 38
    og_draw.rounded_rectangle([cur_x, cur_y, cur_x + tw, cur_y + th], radius=19, 
                              fill=(24, 33, 47, 245), 
                              outline=col, width=2)
    og_draw.text((cur_x + 16, cur_y + 8), text, font=tag_font, fill=(248, 250, 252, 255))
    cur_x += tw + 14
    if cur_x > 500:
        cur_x = 62
        cur_y += 50

# Right Showcase Grid of Iconic Settlers Online Assets
showcase_icons = [
    ("Mayorhouse.png", "Mayor House"),
    ("Bakery.png", "Bakery"),
    ("Bookbinder.png", "Bookbinder"),
    ("BuildingSettlers2HQ.png", "Settlers HQ"),
    ("BronzeMine.png", "Copper Mine"),
    ("Brewery.png", "Brewery"),
    ("Bonechurch.png", "Bone Church"),
    ("AirshipExcelsior.png", "Excelsior"),
]

# Right container box
box_x, box_y, box_w, box_h = 670, 52, 470, 526
og_draw.rounded_rectangle([box_x, box_y, box_x + box_w, box_y + box_h], radius=16, 
                          fill=(30, 41, 59, 200), outline=(51, 65, 85, 255), width=2)

og_draw.text((box_x + 24, box_y + 18), "Live Asset Preview & Zoom", font=badge_font, fill=(248, 250, 252, 255))
og_draw.line([(box_x + 24, box_y + 50), (box_x + box_w - 24, box_y + 50)], fill=(51, 65, 85, 255), width=1)

# 2 columns x 4 rows
cols = 2
rows = 4
card_w = (box_w - 60) // cols
card_h = (box_h - 90) // rows

for idx, (icon_file, label) in enumerate(showcase_icons):
    c = idx % cols
    r = idx // cols
    cx = box_x + 20 + c * (card_w + 20)
    cy = box_y + 65 + r * (card_h + 10)
    
    # mini card
    og_draw.rounded_rectangle([cx, cy, cx + card_w, cy + card_h], radius=10, 
                              fill=(15, 23, 42, 220), outline=(56, 189, 248, 90), width=1)
    
    # load icon
    ipath = os.path.join(ICONS_DIR, icon_file)
    if os.path.exists(ipath):
        try:
            item_img = Image.open(ipath).convert("RGBA")
            # scale nicely (pixelated)
            scale = min(54 / item_img.width, 54 / item_img.height)
            iw = max(16, int(item_img.width * scale))
            ih = max(16, int(item_img.height * scale))
            item_scaled = item_img.resize((iw, ih), Image.Resampling.NEAREST)
            ix = cx + 12 + (54 - iw) // 2
            iy = cy + (card_h - ih) // 2
            og_img.paste(item_scaled, (ix, iy), item_scaled)
        except Exception as e:
            pass
            
    # Label
    og_draw.text((cx + 74, cy + card_h // 2 - 10), label, font=icon_label_font, fill=(226, 232, 240, 240))

# Bottom URL bar
og_draw.rounded_rectangle([60, 524, 600, 574], radius=10, fill=(30, 41, 59, 220), outline=(56, 189, 248, 120), width=1)
og_draw.text((80, 537), "https://tso-icon-finder.vercel.app", font=badge_font, fill=(56, 189, 248, 255))

og_out = os.path.join(BASE_DIR, 'og-image.png')
og_img.save(og_out, "PNG", optimize=True)
print(f"Created og-image.png (1200x630) at {og_out}")
print("Asset generation complete!")
