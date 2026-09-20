import os
import sys
import json
import glob
import re
import struct
import base64
import time
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

ROOT_DIR = r'c:\OSPanel\home\tso_client'
SCRIPT_DIR = os.path.join(ROOT_DIR, 'tso_icon_finder')
MAPPING_FILE = os.path.join(ROOT_DIR, 'mapping', 'mapping.json')
DOCS_DIR = os.path.join(SCRIPT_DIR, 'docs')
XML_DIR = os.path.join(DOCS_DIR, 'xml')
ICONS_DIR = os.path.join(SCRIPT_DIR, 'icons')
CACHE_DIR = os.path.join(SCRIPT_DIR, '.hash_cache')
OUTPUT_DATA_JS = os.path.join(SCRIPT_DIR, 'icons_data.js')

os.makedirs(ICONS_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

print("=" * 60)
print("TSO FULL ICON CATALOG BUILDER & CDN SYNC")
print("=" * 60)

# 1. Load Localizations
print("[1/6] Loading localization dictionaries...")
loca_ru = {}
id_to_ru = {}
ru_path = os.path.join(XML_DIR, 'loca', 'localization_oasis.xml')
if os.path.exists(ru_path):
    tree_ru = ET.parse(ru_path)
    trans = tree_ru.getroot().find('translations')
    if trans is not None:
        for s in trans.findall('s'):
            s_name = s.get('name', '')
            for t in s.findall('t'):
                tid = t.get('id', '')
                txt = t.get('text', '')
                loca_ru[(s_name, tid)] = txt
                if tid not in id_to_ru or s_name in ['BUI', 'RES', 'SHI', 'ADN', 'ACL']:
                    id_to_ru[tid] = (s_name, txt)
print(f"  Loaded {len(loca_ru)} Russian strings")

loca_en = {}
id_to_en = {}
en_path = os.path.join(XML_DIR, 'loca', 'localization_oasis_en.xml')
if not os.path.exists(en_path):
    en_path = os.path.join(XML_DIR, 'en_lang.xml')
if os.path.exists(en_path):
    tree_en = ET.parse(en_path)
    trans = tree_en.getroot().find('translations')
    if trans is not None:
        for s in trans.findall('s'):
            s_name = s.get('name', '')
            for t in s.findall('t'):
                tid = t.get('id', '')
                txt = t.get('text', '')
                loca_en[(s_name, tid)] = txt
                if tid not in id_to_en or s_name in ['BUI', 'RES', 'SHI', 'ADN', 'ACL']:
                    id_to_en[tid] = (s_name, txt)
print(f"  Loaded {len(loca_en)} English strings")

def get_localization(name, sec=None):
    for s in [sec, 'BUI', 'RES', 'SHI', 'ADN', 'ACL', 'SKL', 'LAB', 'DES', 'QUL', 'MES']:
        if s and (s, name) in loca_ru:
            return loca_ru[(s, name)], loca_en.get((s, name), '')
    if name in id_to_ru:
        s, r = id_to_ru[name]
        return r, loca_en.get((s, name), '')
    
    clean = re.sub(r'^(icon_|buff_|b_|resource_)', '', name, flags=re.IGNORECASE)
    for s in [sec, 'BUI', 'RES', 'SHI', 'ADN', 'ACL', 'SKL', 'LAB']:
        if s and (s, clean) in loca_ru:
            return loca_ru[(s, clean)], loca_en.get((s, clean), '')
    if clean in id_to_ru:
        s, r = id_to_ru[clean]
        return r, loca_en.get((s, clean), '')

    return '', ''

# 2. Load Mapping
print("[2/6] Loading asset mapping...")
with open(MAPPING_FILE, 'r', encoding='utf-8') as f:
    mapping = json.load(f)

mapping_lower = {}
for k, v in mapping.items():
    if k.endswith('.png'):
        base = os.path.basename(k).lower()
        mapping_lower.setdefault(base, []).append(k)

def resolve_asset(fname, preferred_dir=None):
    if not fname:
        return None
    fname_png = fname if fname.endswith('.png') else fname + '.png'
    if fname_png in mapping:
        return fname_png
    base = os.path.basename(fname_png).lower()
    candidates = mapping_lower.get(base, [])
    if not candidates:
        return None
    if preferred_dir:
        for c in candidates:
            if preferred_dir in c:
                return c
    return candidates[0]

# 3. Collect Items from XML and Mapping
print("[3/6] Parsing XML game definitions and indexing icons...")
catalog = {}

def register_item(name, asset_path, sec, sec_title, source_info):
    if not name or not asset_path:
        return
    clean_name = name.strip()
    if clean_name in catalog:
        return
    ru_text, en_text = get_localization(clean_name, sec)
    safe_name = re.sub(r'[^\w\-]', '_', clean_name)
    catalog[clean_name] = {
        'name': clean_name,
        'safeName': safe_name,
        'path': asset_path,
        'hash': mapping.get(asset_path),
        'sec': sec,
        'secTitle': sec_title,
        'ru': ru_text,
        'en': en_text,
        'source': source_info
    }

# 3.1 icons.xml
icons_xml_path = os.path.join(XML_DIR, 'icons.xml')
if os.path.exists(icons_xml_path):
    tree_icons = ET.parse(icons_xml_path)
    go = tree_icons.getroot().find('GameObjects')
    if go is not None:
        elem_b = go.find('Buildings')
        if elem_b is not None:
            for b in elem_b:
                name = b.get('name')
                path = resolve_asset(b.get('iconfilename'), 'icons/buildings')
                register_item(name, path, 'BUI', 'Здания', 'icons.xml/Buildings')

        elem_r = go.find('ResourceIcons')
        if elem_r is not None:
            for r in elem_r:
                name = r.get('name')
                path = resolve_asset(r.get('filename'), 'icons/resources') or resolve_asset(r.get('filename'), 'shop/icons')
                register_item(name, path, 'RES', 'Ресурсы', 'icons.xml/ResourceIcons')

        elem_bf = go.find('AvailableBuffs')
        if elem_bf is not None:
            for bf in elem_bf:
                name = bf.get('name')
                path = resolve_asset(bf.get('iconfilename'), 'icons/buffs') or resolve_asset(bf.get('iconfilename'), 'shop/icons')
                register_item(name, path, 'BUFF', 'Усилители', 'icons.xml/AvailableBuffs')

        elem_g = go.find('GuiIcons')
        if elem_g is not None:
            for g in elem_g:
                name = g.get('name')
                path = resolve_asset(g.get('filename'), 'guiicon_lib') or resolve_asset(g.get('filename'), 'icons')
                register_item(name, path, 'GUI', 'Интерфейс', 'icons.xml/GuiIcons')

        elem_a = go.find('Adventures')
        if elem_a is not None:
            for a in elem_a:
                name = a.get('name')
                path = resolve_asset(a.get('buffIcon') or a.get('avatarImage') or a.get('teaserImage'), 'adventures') or resolve_asset(a.get('buffIcon'), 'shop/icons')
                register_item(name, path, 'ADN', 'Приключения', 'icons.xml/Adventures')

        elem_s = go.find('Settlers')
        if elem_s is not None:
            for s in elem_s:
                name = s.get('name')
                path = resolve_asset(s.get('filename'), 'icons/units') or resolve_asset(s.get('filename'), 'settler_lib')
                register_item(name, path, 'UNI', 'Поселенцы', 'icons.xml/Settlers')

print(f"  After icons.xml: {len(catalog)} items")

# 3.2 ShopItems
for sf in glob.glob(os.path.join(XML_DIR, 'shop', '**', '*.xml'), recursive=True):
    try:
        t = ET.parse(sf)
        for elem in t.iter('ShopItem'):
            name = elem.get('name')
            if not name or name in catalog:
                continue
            icon = elem.get('icon') or elem.get('iconfilename') or elem.get('customiconfilename')
            path = resolve_asset(icon, 'shop/icons') or resolve_asset(icon, 'icons')
            register_item(name, path, 'SHI', 'Магазин', 'shop/*.xml')
    except Exception:
        pass

print(f"  After ShopItems: {len(catalog)} items")

# 3.3 Collectibles
for col_file in [os.path.join(XML_DIR, 'collections.xml'), os.path.join(XML_DIR, 'collections', 'collectibles_and_loot.xml')]:
    if os.path.exists(col_file):
        try:
            t = ET.parse(col_file)
            for elem in t.iter('resource'):
                name = elem.get('name')
                if not name or name in catalog:
                    continue
                path = resolve_asset(name, 'icons/resources') or resolve_asset('icon_' + name, 'icons/resources')
                register_item(name, path, 'COL', 'Коллекции', 'collections.xml')
        except Exception:
            pass

# 3.4 Achievements
ach_file = os.path.join(XML_DIR, 'achievements', 'trigger_ui_details.xml')
if os.path.exists(ach_file):
    try:
        t = ET.parse(ach_file)
        for elem in t.iter('achievement'):
            name = elem.get('name') or elem.get('id')
            if not name or name in catalog:
                continue
            icon = elem.get('icon') or elem.get('smallIcon')
            path = resolve_asset(icon, 'icons/achievements')
            register_item(name, path, 'ACH', 'Достижения', 'achievements.xml')
    except Exception:
        pass

print(f"  After Achievements & Collectibles: {len(catalog)} items")

# 3.5 All remaining icon files from mapping.json
icon_prefixes = [
    ('icons/buildings/', 'BUI', 'Здания'),
    ('icons/resources/', 'RES', 'Ресурсы'),
    ('icons/buffs/', 'BUFF', 'Усилители'),
    ('icons/units/', 'UNI', 'Войска'),
    ('icons/achievements/', 'ACH', 'Достижения'),
    ('icons/avatars/', 'AVT', 'Аватары'),
    ('icons/guildbanner/', 'GUI', 'Интерфейс'),
    ('icons/npc/', 'AVT', 'Аватары'),
    ('shop/icons/', 'SHI', 'Магазин'),
    ('iconspack/skills/', 'SKL', 'Навыки'),
    ('iconspack/specialists/', 'AVT', 'Специалисты'),
    ('iconspack/attributes/', 'GUI', 'Интерфейс'),
    ('iconspack/avatarmessageicons/', 'GUI', 'Интерфейс'),
    ('iconspack/flyouts/', 'GUI', 'Интерфейс'),
    ('iconspack/buttons/', 'GUI', 'Интерфейс'),
    ('iconspack/combatanttypes/', 'UNI', 'Войска'),
    ('adventures/buffs/', 'ADN', 'Приключения'),
    ('adventures/avatars/', 'AVT', 'Приключения (Аватары)'),
    ('adventures/teasers/', 'ADN', 'Приключения (Тизеры)'),
    ('guiicon_lib/', 'GUI', 'Интерфейс')
]

used_paths = set(v['path'] for v in catalog.values())
for k, v in mapping.items():
    if not k.endswith('.png') or k in used_paths:
        continue
    for prefix, sec, secTitle in icon_prefixes:
        if k.startswith(prefix):
            base = os.path.basename(k)[:-4]
            name = base
            idx = 2
            while name in catalog:
                name = f'{base}_{idx}'
                idx += 1
            register_item(name, k, sec, secTitle, 'mapping.json')
            used_paths.add(k)
            break

print(f"  Total catalog items: {len(catalog)}")

# 4. Download missing PNG assets from CDN
print("[4/6] Checking assets and downloading missing icons via CDN...")

hash_to_path = {}
for it in catalog.values():
    h = it.get('hash')
    if h and h not in hash_to_path:
        hash_to_path[h] = it['path']

hashes_to_download = []
for h, p in hash_to_path.items():
    cache_file = os.path.join(CACHE_DIR, h)
    if not os.path.exists(cache_file) or os.path.getsize(cache_file) == 0:
        hashes_to_download.append((h, p))

print(f"  Unique content hashes: {len(hash_to_path)}")
print(f"  Already in cache: {len(hash_to_path) - len(hashes_to_download)}")
print(f"  Need download: {len(hashes_to_download)}")

def download_hash(item):
    h, p = item
    cache_file = os.path.join(CACHE_DIR, h)
    d = os.path.dirname(p).replace('\\', '/')
    url = f"https://www.thesettlersonline.ru/frontend/GFX_HASHED/{d}/{h}"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                if resp.status == 200:
                    data = resp.read()
                    with open(cache_file, 'wb') as out_f:
                        out_f.write(data)
                    return True, h, len(data)
        except Exception:
            time.sleep(0.5 * (attempt + 1))
    return False, h, 0

if hashes_to_download:
    t_start = time.time()
    completed = 0
    failed = 0
    total_bytes = 0
    
    with ThreadPoolExecutor(max_workers=30) as executor:
        futures = {executor.submit(download_hash, it): it for it in hashes_to_download}
        for future in as_completed(futures):
            ok, h, size = future.result()
            if ok:
                completed += 1
                total_bytes += size
            else:
                failed += 1
            if (completed + failed) % 500 == 0 or (completed + failed) == len(hashes_to_download):
                elapsed = time.time() - t_start
                rate = (completed + failed) / (elapsed if elapsed > 0 else 1)
                print(f"  Progress: {completed + failed}/{len(hashes_to_download)} ({completed} ok, {failed} fail) - {rate:.1f} files/sec")

    print(f"  Download finished in {time.time() - t_start:.1f}s. Total: {total_bytes / (1024*1024):.2f} MB")

# 5. Populate icons folder and prepare bundle
print("[5/6] Generating icon files and base64 bundle...")

final_items = []
categories_count = {}

for name, it in catalog.items():
    h = it.get('hash')
    cache_file = os.path.join(CACHE_DIR, h) if h else None
    target_png = os.path.join(ICONS_DIR, it['safeName'] + '.png')
    
    img_data = None
    if cache_file and os.path.exists(cache_file) and os.path.getsize(cache_file) > 0:
        with open(cache_file, 'rb') as f:
            img_data = f.read()
    elif os.path.exists(target_png) and os.path.getsize(target_png) > 0:
        with open(target_png, 'rb') as f:
            img_data = f.read()

    if not img_data or len(img_data) < 24:
        continue

    # Ensure file exists in icons/
    if not os.path.exists(target_png) or os.path.getsize(target_png) == 0:
        try:
            with open(target_png, 'wb') as f:
                f.write(img_data)
        except Exception:
            pass

    try:
        w, h_px = struct.unpack('>II', img_data[16:24])
    except Exception:
        w, h_px = 24, 24

    sec = it['sec']
    categories_count[sec] = categories_count.get(sec, 0) + 1

    final_items.append({
        'name': it['name'],
        'safeName': it['safeName'],
        'ru': it['ru'],
        'en': it['en'],
        'sec': sec,
        'secTitle': it['secTitle'],
        'w': w,
        'h': h_px,
        'size': len(img_data),
        'src': f"icons/{it['safeName']}.png",
        'path': it['path']
    })

sec_priority = {'BUI': 1, 'RES': 2, 'BUFF': 3, 'SHI': 4, 'ADN': 5, 'COL': 6, 'SKL': 7, 'UNI': 8, 'ACH': 9, 'AVT': 10, 'GUI': 11}
final_items.sort(key=lambda x: (sec_priority.get(x['sec'], 99), x['name'].lower()))

# 6. Write icons_data.js
print(f"[6/6] Writing {len(final_items)} icons to icons_data.js...")
with open(OUTPUT_DATA_JS, 'w', encoding='utf-8') as out_f:
    out_f.write("window.TSO_ICONS_DATA = ")
    json.dump(final_items, out_f, ensure_ascii=False)
    out_f.write(";\n")

file_size_mb = os.path.getsize(OUTPUT_DATA_JS) / (1024 * 1024)
print(f"  icons_data.js written successfully! ({file_size_mb:.2f} MB)")
print("  Categories summary:")
for sec, count in sorted(categories_count.items(), key=lambda x: -x[1]):
    print(f"    {sec}: {count}")

print("=" * 60)
print(f"COMPLETE! Total icons available: {len(final_items)}")
print("=" * 60)
