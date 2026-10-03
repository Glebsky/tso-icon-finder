import os
import sys
import json
import glob
import re
import struct
import base64
import time
import shutil
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = r'c:\OSPanel\home\tso_client'
MAPPING_FILE = os.path.join(ROOT_DIR, 'mapping', 'mapping.json')
REFERENCES_DIR = r'C:\OSPanel\home\admin\docs\references'
REF_XML_DIR = os.path.join(REFERENCES_DIR, 'xml')
DOCS_DIR = os.path.join(SCRIPT_DIR, 'docs')
XML_DIR = os.path.join(DOCS_DIR, 'xml') if os.path.exists(os.path.join(DOCS_DIR, 'xml')) else REF_XML_DIR
SWF_ASSETS_DIR = r'C:\OSPanel\home\tso-swf\assets'
ICONS_DIR = os.path.join(SCRIPT_DIR, 'icons')
CACHE_DIR = os.path.join(SCRIPT_DIR, '.hash_cache')
OUTPUT_DATA_JS = os.path.join(SCRIPT_DIR, 'icons_data.js')

os.makedirs(ICONS_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

print("=" * 60)
print("TSO FULL ICON CATALOG BUILDER & CDN/SWF SYNC")
print("=" * 60)

# 1. Load Localizations
print("[1/6] Loading localization dictionaries...")
loca_ru = {}
id_to_ru = {}

for ru_path in [
    os.path.join(XML_DIR, 'loca', 'localization_oasis.xml'),
    os.path.join(REF_XML_DIR, 'loca', 'localization_oasis.xml'),
    os.path.join(REF_XML_DIR, 'loca', 'ru_lang.xml')
]:
    if os.path.exists(ru_path):
        try:
            tree_ru = ET.parse(ru_path)
            trans = tree_ru.getroot().find('translations')
            if trans is not None:
                for s in trans.findall('s'):
                    s_name = s.get('name', '')
                    for t in s.findall('t'):
                        tid = t.get('id', '')
                        txt = t.get('text', '')
                        loca_ru[(s_name, tid)] = txt
                        if tid not in id_to_ru or s_name in ['BUI', 'RES', 'SHI', 'ADN', 'ACL', 'LAB']:
                            id_to_ru[tid] = (s_name, txt)
                print(f"  Loaded Russian strings from: {ru_path} ({len(loca_ru)} strings)")
                break
        except Exception as e:
            print(f"  Warning loading {ru_path}: {e}")

loca_en = {}
id_to_en = {}
for en_path in [
    os.path.join(XML_DIR, 'loca', 'localization_oasis_en.xml'),
    os.path.join(REF_XML_DIR, 'loca', 'localization_oasis_en.xml'),
    os.path.join(XML_DIR, 'en_lang.xml'),
    os.path.join(REF_XML_DIR, 'en_lang.xml')
]:
    if os.path.exists(en_path):
        try:
            tree_en = ET.parse(en_path)
            trans = tree_en.getroot().find('translations')
            if trans is not None:
                for s in trans.findall('s'):
                    s_name = s.get('name', '')
                    for t in s.findall('t'):
                        tid = t.get('id', '')
                        txt = t.get('text', '')
                        loca_en[(s_name, tid)] = txt
                        if tid not in id_to_en or s_name in ['BUI', 'RES', 'SHI', 'ADN', 'ACL', 'LAB']:
                            id_to_en[tid] = (s_name, txt)
                print(f"  Loaded English strings from: {en_path} ({len(loca_en)} strings)")
                break
        except Exception as e:
            print(f"  Warning loading {en_path}: {e}")

# Curated UI translations for embedded and interface icons
UI_TRANSLATIONS = {
    'Close': ('Крестик закрытия окна (обычный)', 'Close Window (Normal)'),
    'CloseHighlight': ('Крестик закрытия окна (активный)', 'Close Window (Highlight)'),
    'buttons_x_small_standard': ('Крестик (кнопка закрытия/отмены)', 'Cross / Close Button (Standard)'),
    'buttons_x_small_selected': ('Крестик (нажатый)', 'Cross / Close Button (Pressed)'),
    'buttons_x_inactive': ('Крестик (неактивный)', 'Cross / Close Button (Inactive)'),
    'buttons_icon_abort_highlight': ('Крестик отмены действия (подсветка)', 'Abort Action Cross (Highlight)'),
    'buttons_checkmark_push': ('Галочка подтверждения (нажатая)', 'Checkmark Button (Pressed)'),
    'CheckMarkYellow': ('Жёлтая галочка (выбор/подтверждение)', 'Yellow Checkmark'),
    'OKIcon': ('Иконка подтверждения (ОК)', 'OK Button Icon'),
    'icon_half_selected': ('Флажок / Чекбокс (частично выбран)', 'Checkbox (Half Selected)'),
    'IconCL1': ('Простые здания (CL1)', 'Basic Buildings (CL1)'),
    'IconCL2': ('Улучшенные здания (CL2)', 'Intermediate Buildings (CL2)'),
    'IconCL3': ('Продвинутые здания (CL3)', 'Advanced Buildings (CL3)'),
    'IconCL4': ('Мастерские здания (CL4)', 'Expert Buildings (CL4)'),
    'IconCL5': ('Великолепные здания (CL5)', 'Magnificent Buildings (CL5)'),
    'IconToolbox': ('Панель инструментов строительства', 'Construction Toolbox'),
    'IconToolboxStar': ('Инструменты звёздного меню', 'Star Menu Toolbox'),
    'IconDefCamp1': ('Лагерь обороны (ур. 1)', 'Defense Camp Level 1'),
    'IconDefCamp2': ('Лагерь обороны (ур. 2)', 'Defense Camp Level 2'),
    'IconDefCamp3': ('Лагерь обороны (ур. 3)', 'Defense Camp Level 3'),
    'IconCannotBuild': ('Запрет строительства (перечёркнуто)', 'Cannot Build Icon'),
    'IconDeleteBuilding': ('Снос здания (удаление/крестик)', 'Demolish Building Icon'),
    'IconMoveBuilding': ('Перемещение здания', 'Move Building Icon'),
    'IconBuildStreet': ('Строительство дорог', 'Build Road Icon'),
    'IconEraseStreet': ('Удаление дорог', 'Erase Road Icon'),
    'StarMenuIcon': ('Иконка Звёздного меню', 'Star Menu Icon'),
    'StarMenuTabIconAll': ('Звёздное меню: Все предметы', 'Star Menu Tab: All Items'),
    'StarMenuTabIconBuff': ('Звёздное меню: Усилители', 'Star Menu Tab: Buffs'),
    'StarMenuTabIconBuilding': ('Звёздное меню: Здания', 'Star Menu Tab: Buildings'),
    'StarMenuTabIconMisc': ('Звёздное меню: Разное', 'Star Menu Tab: Misc'),
    'StarMenuTabIconResource': ('Звёздное меню: Ресурсы', 'Star Menu Tab: Resources'),
    'StarMenuTabIconSpecialist': ('Звёздное меню: Специалисты', 'Star Menu Tab: Specialists'),
    'StarmenuFrameEmpty': ('Звёздное меню: Пустой слот', 'Star Menu: Empty Slot'),
    'IconMailInbox': ('Почта: Входящие', 'Mail: Inbox'),
    'IconMailOutbox': ('Почта: Исходящие', 'Mail: Outbox'),
    'IconMailWrite': ('Почта: Написать письмо', 'Mail: Compose'),
    'IconMailReply': ('Почта: Ответить', 'Mail: Reply'),
    'IconMailTypeAdventureLoot': ('Почта: Награда за приключение', 'Mail: Adventure Loot'),
    'IconMailTypeBattleReport': ('Почта: Отчёт о битве', 'Mail: Battle Report'),
    'IconMailTypeBuffed': ('Почта: Друг применил усилитель', 'Mail: Friend Buffed'),
    'IconMailTypeFriend': ('Почта: Запрос в друзья', 'Mail: Friend Request'),
    'IconMailTypeGift': ('Почта: Подарок', 'Mail: Gift'),
    'IconMailTypeGuild': ('Почта: Сообщение гильдии', 'Mail: Guild Message'),
    'IconMailTypeHardCurrency': ('Почта: Самоцветы', 'Mail: Gems Message'),
    'IconMailTypeMail': ('Почта: Обычное письмо', 'Mail: Normal Mail'),
    'IconMailTypeMailRead': ('Почта: Прочитанное письмо', 'Mail: Read Mail'),
    'IconMailTypeNPC': ('Почта: Сообщение NPC', 'Mail: NPC Mail'),
    'IconMailTypeTrade': ('Почта: Торговое сообщение', 'Mail: Trade Mail'),
    'IconMailContextMenuButton': ('Почта: Кнопка контекстного меню', 'Mail Context Menu Button'),
    'IconBlockedContextMenuButton': ('Заблокированная кнопка меню', 'Blocked Context Menu Button'),
    'IconAllExplorers': ('Все разведчики', 'All Explorers'),
    'IconAllGenerals': ('Все генералы', 'All Generals'),
    'IconAllGeologists': ('Все геологи', 'All Geologists'),
    'IconAddSpecialistItem': ('Назначить предмет специалисту', 'Add Specialist Item'),
    'GeneralStateIconAttack': ('Генерал: В атаке', 'General: Attacking'),
    'GeneralStateIconRecovery': ('Генерал: Восстановление сил', 'General: Recovering'),
    'GeneralStateIconRetreat': ('Генерал: Отступление', 'General: Retreating'),
    'ButtonIconFindWildZone': ('Кнопка: Найти неизведанный сектор', 'Button: Find Wild Zone'),
    'ButtonIconFlag': ('Кнопка: Флаг / Экспедиция', 'Button: Expedition Flag'),
    'ButtonIconGift': ('Кнопка: Подарок', 'Button: Gift'),
    'ButtonIconGold': ('Кнопка: Золотые монеты', 'Button: Gold Coins'),
    'ButtonIconGranite': ('Кнопка: Гранит', 'Button: Granite'),
    'ButtonIconHalfTheTime': ('Кнопка: Сократить время вдвое', 'Button: Half The Time'),
    'ButtonIconHardCurrency': ('Кнопка: Самоцветы', 'Button: Gems'),
    'ButtonIconInstant': ('Кнопка: Завершить мгновенно', 'Button: Instant Finish'),
    'ButtonIconIron': ('Кнопка: Железо', 'Button: Iron'),
    'ButtonIconMagnifier': ('Кнопка: Найти / Поиск', 'Button: Search / Magnifier'),
    'ButtonIconMarble': ('Кнопка: Мрамор', 'Button: Marble'),
    'ButtonIconNewMail': ('Кнопка: Новое письмо', 'Button: New Mail'),
    'ButtonIconOK': ('Кнопка: Подтвердить (ОК)', 'Button: OK / Confirm'),
    'ButtonIconPay': ('Кнопка: Оплатить / Внести ресурсы', 'Button: Pay Resources'),
    'ButtonIconSalpeter': ('Кнопка: Селитра', 'Button: Saltpeter'),
    'ButtonIconScroll': ('Кнопка: Свиток заданий', 'Button: Quest Scroll'),
    'ButtonIconSendToOtherZone': ('Кнопка: Отправить на другой остров', 'Button: Send to Other Zone'),
    'ButtonIconStart': ('Кнопка: Начать / Старт', 'Button: Start'),
    'ButtonIconStone': ('Кнопка: Камень', 'Button: Stone'),
    'ButtonIconStop': ('Кнопка: Остановить / Пауза', 'Button: Stop'),
    'ButtonIconSwords': ('Кнопка: Атака / Войска', 'Button: Attack / Swords'),
    'ButtonIconThrowAway': ('Кнопка: Выбросить / Удалить', 'Button: Discard'),
    'ButtonIconTitanium': ('Кнопка: Титан', 'Button: Titanium'),
    'ButtonIconTools': ('Кнопка: Инструменты', 'Button: Tools'),
    'ButtonIconTrade': ('Кнопка: Торговать', 'Button: Trade'),
    'ButtonIconTrumpet': ('Кнопка: Призыв / Горн', 'Button: Trumpet Call'),
    'ButtonIconUpgrade': ('Кнопка: Улучшить здание', 'Button: Upgrade Building'),
    'ButtonIconUpgradeGems': ('Кнопка: Улучшить за самоцветы', 'Button: Upgrade with Gems'),
    'buttons_pin_standard': ('Кнопка: Закрепить окно', 'Pin Window (Standard)'),
    'buttons_pin_highlight': ('Кнопка: Закрепить окно (подсветка)', 'Pin Window (Highlight)'),
    'buttons_pin_inactive': ('Кнопка: Закрепить окно (неактивно)', 'Pin Window (Inactive)'),
    'buttons_unassign_standard': ('Кнопка: Снять назначение', 'Unassign Button (Standard)'),
    'buttons_unassign_selected': ('Кнопка: Снять назначение (выбрано)', 'Unassign Button (Selected)'),
    'buttons_icon_pencil_standard': ('Кнопка: Редактировать (карандаш)', 'Edit Pencil Button'),
    'buttons_icon_questionmark2': ('Кнопка: Справка (знак вопроса)', 'Help Question Mark Button'),
    'buttons_icon_view_vote': ('Кнопка: Просмотр голосования гильдии', 'View Guild Vote Button'),
    'buttons_icon_recast_vote': ('Кнопка: Переголосовать', 'Recast Vote Button'),
    'buttons_icon_next_vote': ('Кнопка: Следующее голосование', 'Next Vote Button'),
    'camera_scale_down_standard': ('Камера: Отдалить вид', 'Camera Zoom Out'),
    'camera_scale_up_standard': ('Камера: Приблизить вид', 'Camera Zoom In'),
    'OptionsButtonPlus': ('Кнопка: Увеличить (+)', 'Options Plus Button'),
    'OptionsButtonMinus': ('Кнопка: Уменьшить (-)', 'Options Minus Button'),
    'OptionsButtonOptions': ('Кнопка: Параметры / Шестерёнка', 'Options Settings Button'),
    'SearchBtnIcon': ('Кнопка: Поиск', 'Search Button Icon'),
    'SkillTreeBtnIcon': ('Кнопка: Дерево навыков', 'Skill Tree Button Icon'),
    'OnlineStatusGreen': ('Индикатор: В сети (зелёный)', 'Online Status Indicator (Green)'),
    'UnloadTroopsIcon': ('Выгрузить войска из гарнизона', 'Unload Troops Icon'),
    'ReturnToStarIcon': ('Вернуть предмет в звезду', 'Return to Star Menu Icon'),
    'RefreshTradeIcon': ('Обновить список торговли', 'Refresh Trade List Icon'),
    'RegularWindowClosed': ('Обычное окно (закрыто)', 'Regular Window (Closed)'),
    'RegularWindowOpened': ('Обычное окно (открыто)', 'Regular Window (Opened)'),
    'SpecialWindowClosed': ('Особое окно (закрыто)', 'Special Window (Closed)'),
    'SpecialWindowOpened': ('Особое окно (открыто)', 'Special Window (Opened)'),
    'SilvesterWindowClosed': ('Новогоднее окно (закрыто)', 'New Year Window (Closed)'),
    'SilvesterWindowOpened': ('Новогоднее окно (открыто)', 'New Year Window (Opened)'),
    'XmasWindowClosed': ('Рождественское окно (закрыто)', 'Christmas Window (Closed)'),
    'XmasWindowOpened': ('Рождественское окно (открыто)', 'Christmas Window (Opened)'),
    'PresentsWindowClosed': ('Окно подарков (закрыто)', 'Presents Window (Closed)'),
    'PresentsWindowOpened': ('Окно подарков (открыто)', 'Presents Window (Opened)'),
    'adventureTypeCoop': ('Тип приключения: Совместное (Кооп)', 'Adventure Type: Co-op'),
    'adventureTypeEpic': ('Тип приключения: Эпическое', 'Adventure Type: Epic'),
    'adventureTypeExperience': ('Тип приключения: На опыт', 'Adventure Type: Experience'),
    'adventureTypeFairytale': ('Тип приключения: Сказочное', 'Adventure Type: Fairytale'),
    'adventureTypeFollowUp': ('Тип приключения: Продолжение', 'Adventure Type: Follow-up'),
    'adventureTypeMini': ('Тип приключения: Мини', 'Adventure Type: Mini'),
    'adventureTypeMission': ('Тип приключения: Миссия', 'Adventure Type: Mission'),
    'adventureTypeResource': ('Тип приключения: На ресурсы', 'Adventure Type: Resource'),
    'adventureTypeScenario': ('Тип приключения: Сценарий', 'Adventure Type: Scenario'),
    'adventureTypeSpecial': ('Тип приключения: Особое', 'Adventure Type: Special'),
    'adventureTypeVenture': ('Тип приключения: Экспедиция', 'Adventure Type: Venture'),
    'adventureChristmasHeader': ('Заголовок: Рождественское приключение', 'Adventure Header: Christmas'),
    'dragonAnniversary': ('Заголовок окна: Юбилей (Дракон)', 'Window Header: Anniversary Dragon'),
    'dragonValentines': ('Заголовок окна: День св. Валентина', 'Window Header: Valentines Dragon'),
    'dragonEaster': ('Заголовок окна: Пасха (Дракон)', 'Window Header: Easter Dragon'),
    'dragonFootball': ('Заголовок окна: Футбол (Дракон)', 'Window Header: Football Dragon'),
    'dragonHalloween': ('Заголовок окна: Хэллоуин (Дракон)', 'Window Header: Halloween Dragon'),
    'FrameEnemy': ('Рамка: Вражеский отряд', 'Frame: Enemy Unit'),
    'FrameSpecialist': ('Рамка: Специалист', 'Frame: Specialist'),
    'FramePerk': ('Рамка: Перк / Навык', 'Frame: Perk'),
    'FramePermanentBuff': ('Рамка: Постоянный усилитель', 'Frame: Permanent Buff'),
    'FrameZoneBuff': ('Рамка: Усилитель зоны', 'Frame: Zone Buff'),
    'FrameDailyLogin': ('Рамка: Ежедневная награда', 'Frame: Daily Login'),
    'FrameTier1': ('Рамка: Тир 1', 'Frame: Tier 1'),
    'FrameTier2': ('Рамка: Тир 2', 'Frame: Tier 2'),
    'FrameTier3': ('Рамка: Тир 3', 'Frame: Tier 3'),
    'FrameTier4': ('Рамка: Тир 4', 'Frame: Tier 4'),
    'icon_exclamationmark': ('Знак восклицания (Внимание)', 'Exclamation Mark (Alert)'),
    'icon_exclamationmark_large': ('Знак восклицания крупный', 'Exclamation Mark Large'),
    'icon_exclamationmark_small': ('Знак восклицания мелкий', 'Exclamation Mark Small'),
    'adventure_difficulty_icon_1': ('Сложность приключения: 1 череп', 'Adventure Difficulty: 1 Skull'),
    'adventure_difficulty_icon_2': ('Сложность приключения: 2 черепа', 'Adventure Difficulty: 2 Skulls'),
    'adventure_difficulty_icon_3': ('Сложность приключения: 3 черепа', 'Adventure Difficulty: 3 Skulls'),
    'adventure_difficulty_icon_4': ('Сложность приключения: 4 черепа', 'Adventure Difficulty: 4 Skulls'),
    'adventure_difficulty_icon_5': ('Сложность приключения: 5 черепов', 'Adventure Difficulty: 5 Skulls'),
}

def humanize_id(identifier):
    s = re.sub(r'^(icon_|buff_|b_|resource_|unit_|buttons_|btn_)', '', identifier, flags=re.IGNORECASE)
    s = re.sub(r'([a-z])([A-Z])', r'\1 \2', s)
    s = re.sub(r'[_\-]+', ' ', s)
    return s.strip().title()

def get_localization(name, sec=None):
    if name in UI_TRANSLATIONS:
        return UI_TRANSLATIONS[name]
    
    clean_key = re.sub(r'\.png$', '', name, flags=re.IGNORECASE)
    if clean_key in UI_TRANSLATIONS:
        return UI_TRANSLATIONS[clean_key]

    for s in [sec, 'BUI', 'RES', 'SHI', 'ADN', 'ACL', 'SKL', 'LAB', 'DES', 'QUL', 'MES']:
        if s and (s, name) in loca_ru:
            return loca_ru[(s, name)], loca_en.get((s, name), '')
    if name in id_to_ru:
        s, r = id_to_ru[name]
        return r, loca_en.get((s, name), '')
    
    clean = re.sub(r'^(icon_|buff_|b_|resource_|unit_|btn_|buttons_)', '', name, flags=re.IGNORECASE)
    if clean in UI_TRANSLATIONS:
        return UI_TRANSLATIONS[clean]

    for s in [sec, 'BUI', 'RES', 'SHI', 'ADN', 'ACL', 'SKL', 'LAB']:
        if s and (s, clean) in loca_ru:
            return loca_ru[(s, clean)], loca_en.get((s, clean), '')
    if clean in id_to_ru:
        s, r = id_to_ru[clean]
        return r, loca_en.get((s, clean), '')

    # Auto humanized name fallback for UI
    en_human = humanize_id(name)
    ru_human = ''
    if sec == 'GUI':
        ru_human = f"Интерфейс: {en_human}"
    elif sec == 'ADN' and 'difficulty' in name.lower():
        ru_human = f"Сложность: {en_human}"

    return ru_human, en_human

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

# 3. Collect Items from XML, Mapping and SWF
print("[3/6] Parsing XML game definitions and indexing icons...")
catalog = {}
used_safe_names = set()

def register_item(name, asset_path, sec, sec_title, source_info, local_file=None):
    if not name or (not asset_path and not local_file):
        return
    clean_name = name.strip()
    if clean_name in catalog:
        return
    
    ru_text, en_text = get_localization(clean_name, sec)
    base_safe = re.sub(r'[^\w\-]', '_', clean_name)
    safe_name = base_safe
    idx = 2
    while safe_name.lower() in used_safe_names:
        safe_name = f"{base_safe}_{idx}"
        idx += 1
    used_safe_names.add(safe_name.lower())

    catalog[clean_name] = {
        'name': clean_name,
        'safeName': safe_name,
        'path': asset_path or f"swf_assets/{os.path.basename(local_file)}",
        'hash': mapping.get(asset_path) if asset_path else None,
        'sec': sec,
        'secTitle': sec_title,
        'ru': ru_text,
        'en': en_text,
        'source': source_info,
        'local_file': local_file
    }

# 3.1 icons.xml
icons_xml_path = os.path.join(XML_DIR, 'icons.xml')
if not os.path.exists(icons_xml_path):
    icons_xml_path = os.path.join(REF_XML_DIR, 'icons.xml')

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
                
                # Check battleicon attribute!
                battle_fn = r.get('battleicon')
                if battle_fn:
                    b_path = resolve_asset(battle_fn, 'icons/resources') or resolve_asset(battle_fn, 'icons/units')
                    if b_path:
                        b_name = f"{name}_battle" if name else os.path.splitext(battle_fn)[0]
                        register_item(b_name, b_path, 'UNI', 'Боевые значки', 'icons.xml/ResourceIcons[battleicon]')

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
                
                # Check difficultyIcon
                diff_icon = a.get('difficultyIcon')
                if diff_icon:
                    d_path = resolve_asset(diff_icon, 'adventures/difficulty_icons')
                    if d_path:
                        register_item(diff_icon, d_path, 'ADN', 'Сложность приключений', 'icons.xml/Adventures[difficultyIcon]')

        elem_s = go.find('Settlers')
        if elem_s is not None:
            for s in elem_s:
                name = s.get('name')
                path = resolve_asset(s.get('filename'), 'icons/units') or resolve_asset(s.get('filename'), 'settler_lib')
                register_item(name, path, 'UNI', 'Поселенцы', 'icons.xml/Settlers')

print(f"  After icons.xml: {len(catalog)} items")

# 3.2 globals.xml
globals_xml_path = os.path.join(XML_DIR, 'globals.xml')
if not os.path.exists(globals_xml_path):
    globals_xml_path = os.path.join(REF_XML_DIR, 'globals.xml')

if os.path.exists(globals_xml_path):
    try:
        tree_glob = ET.parse(globals_xml_path)
        root_glob = tree_glob.getroot()
        
        # AvailableBuffs in globals
        glob_buffs = root_glob.find('AvailableBuffs')
        if glob_buffs is not None:
            for bf in glob_buffs:
                name = bf.get('name')
                if name and name not in catalog:
                    path = resolve_asset(bf.get('iconfilename'), 'icons/buffs') or resolve_asset(bf.get('iconfilename'), 'shop/icons')
                    if path:
                        register_item(name, path, 'BUFF', 'Усилители', 'globals.xml/AvailableBuffs')

        # Specialists in globals
        glob_specs = root_glob.find('Specialists')
        if glob_specs is not None:
            for sp in glob_specs:
                name = sp.get('name')
                if name and name not in catalog:
                    path = resolve_asset(name, 'iconspack/specialists') or resolve_asset('icon_' + name, 'iconspack/specialists')
                    if path:
                        register_item(name, path, 'AVT', 'Специалисты', 'globals.xml/Specialists')

        # ToolBoxPanels sections (CL1-5, Toolbox, DefCamp)
        for panel_name in ['HomeZoneToolBoxPanel', 'DefenseModeToolBoxPanel', 'AttackModeToolBoxPanel']:
            panel = root_glob.find(panel_name)
            if panel is not None:
                sections = panel.find('Sections')
                if sections is not None:
                    for sec_elem in sections.findall('Section'):
                        icon_id = sec_elem.get('icon')
                        tip = sec_elem.get('toolTip')
                        if icon_id:
                            # Map to SWF asset
                            swf_file = os.path.join(SWF_ASSETS_DIR, 'gAssetManager', icon_id + '.png')
                            if os.path.exists(swf_file):
                                register_item(icon_id, f"swf_assets/gAssetManager/{icon_id}.png", 'GUI', 'Панель строительства', f'globals.xml/{panel_name}', local_file=swf_file)
    except Exception as e:
        print(f"  Warning parsing globals.xml: {e}")

print(f"  After globals.xml: {len(catalog)} items")

# 3.3 ShopItems
for s_dir in [os.path.join(XML_DIR, 'shop'), os.path.join(REF_XML_DIR, 'shop')]:
    if os.path.exists(s_dir):
        for sf in glob.glob(os.path.join(s_dir, '**', '*.xml'), recursive=True):
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

# 3.4 Collectibles
for col_file in [
    os.path.join(XML_DIR, 'collections.xml'), 
    os.path.join(REF_XML_DIR, 'collections.xml'),
    os.path.join(XML_DIR, 'collections', 'collectibles_and_loot.xml'),
    os.path.join(REF_XML_DIR, 'collections', 'collectibles_and_loot.xml')
]:
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

# 3.5 Achievements
for ach_file in [
    os.path.join(XML_DIR, 'achievements', 'trigger_ui_details.xml'),
    os.path.join(REF_XML_DIR, 'achievements', 'trigger_ui_details.xml')
]:
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

# 3.6 All remaining icon files from mapping.json (expanded prefixes)
icon_prefixes = [
    ('icons/buildings/', 'BUI', 'Здания'),
    ('icons/resources/', 'RES', 'Ресурсы'),
    ('icons/buffs/', 'BUFF', 'Усилители'),
    ('icons/units/', 'UNI', 'Войска'),
    ('icons/achievements/', 'ACH', 'Достижения'),
    ('icons/achievements/facebook/', 'ACH', 'Достижения Facebook'),
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
    ('iconspack/basic/', 'GUI', 'Интерфейс'),
    ('iconspack/frames/', 'GUI', 'Рамки интерфейса'),
    ('iconspack/combatanttypes/', 'UNI', 'Войска'),
    ('adventures/buffs/', 'ADN', 'Приключения'),
    ('adventures/avatars/', 'AVT', 'Приключения (Аватары)'),
    ('adventures/teasers/', 'ADN', 'Приключения (Тизеры)'),
    ('adventures/difficulty_icons/', 'ADN', 'Сложность приключений'),
    ('guiicon_lib/', 'GUI', 'Интерфейс'),
    ('widget/', 'GUI', 'Виджеты событий'),
    ('eventwindow/', 'GUI', 'Окна событий'),
    ('combat3pvpreport/', 'GUI', 'Отчёты боя'),
    ('settler_lib/', 'UNI', 'Поселенцы'),
    ('event_banners/', 'GUI', 'Баннеры событий'),
    ('help/', 'GUI', 'Справка и обучение'),
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

print(f"  After full mapping.json: {len(catalog)} items")

# 3.7 Embedded UI icons from tso-swf assets (Close buttons, crosses, checkboxes, etc.)
print("  Indexing embedded UI icons from tso-swf assets...")
swf_count = 0
if os.path.exists(SWF_ASSETS_DIR):
    for root, dirs, files in os.walk(SWF_ASSETS_DIR):
        for f in files:
            if not f.lower().endswith('.png'):
                continue
            full_path = os.path.join(root, f)
            rel_path = os.path.relpath(full_path, SWF_ASSETS_DIR).replace('\\', '/')
            base_name = os.path.splitext(f)[0]
            
            # Categorize SWF assets
            sec = 'GUI'
            sec_title = 'Интерфейс'
            rel_lower = rel_path.lower()
            if 'specialist' in rel_lower or 'avatar' in rel_lower:
                sec = 'AVT'
                sec_title = 'Специалисты'
            elif 'unit' in rel_lower:
                sec = 'UNI'
                sec_title = 'Войска'
            elif 'achievement' in rel_lower:
                sec = 'ACH'
                sec_title = 'Достижения'
            elif 'adventure' in rel_lower:
                sec = 'ADN'
                sec_title = 'Приключения'

            name = base_name
            if name in catalog and catalog[name].get('local_file'):
                continue
            idx = 2
            while name in catalog:
                name = f"{base_name}_{idx}"
                idx += 1

            register_item(name, f"swf_assets/{rel_path}", sec, sec_title, f"tso-swf/{rel_path}", local_file=full_path)
            swf_count += 1

print(f"  Added {swf_count} embedded SWF UI assets.")
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

print(f"  Unique CDN content hashes: {len(hash_to_path)}")
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
            if (completed + failed) % 100 == 0 or (completed + failed) == len(hashes_to_download):
                elapsed = time.time() - t_start
                rate = (completed + failed) / (elapsed if elapsed > 0 else 1)
                print(f"  Progress: {completed + failed}/{len(hashes_to_download)} ({completed} ok, {failed} fail) - {rate:.1f} files/sec")

    print(f"  Download finished in {time.time() - t_start:.1f}s. Total: {total_bytes / (1024*1024):.2f} MB")

# 5. Populate icons folder and prepare bundle
print("[5/6] Generating icon files and base64 bundle...")

final_items = []
categories_count = {}

for name, it in catalog.items():
    local_source = it.get('local_file')
    h = it.get('hash')
    cache_file = os.path.join(CACHE_DIR, h) if h else None
    target_png = os.path.join(ICONS_DIR, it['safeName'] + '.png')
    
    img_data = None
    if local_source and os.path.exists(local_source) and os.path.getsize(local_source) > 0:
        with open(local_source, 'rb') as f:
            img_data = f.read()
    elif cache_file and os.path.exists(cache_file) and os.path.getsize(cache_file) > 0:
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
