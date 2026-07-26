# Galeria wlasnych animacji rysowanych w panelu.
#
# Kazda animacja siedzi w osobnym pliku anims/<slug>.json, a anims/index.json
# trzyma tylko spis nazw i miniatury. Dzieki temu do RAM-u ladujemy wylacznie te
# animacje, ktora akurat gra - a nie cala galerie.
#
# Piksele w plikach sa zapisane jako ciag hex ("rrggbb" x 63), bo lista liczb
# w JSON-ie zajmuje trzy razy wiecej miejsca i pamieci.
import json
import os

try:
    from binascii import hexlify, unhexlify
except ImportError:
    from ubinascii import hexlify, unhexlify

import config

DIR = "anims"
INDEX = DIR + "/index.json"

MAX_ANIMS = 24
MAX_FRAMES = 40
MIN_MS = 40
MAX_MS = 10000
DEF_MS = 200

# zeby "Żółta choinka" dala sensowna nazwe pliku
_PL = {"ą": "a", "ć": "c", "ę": "e", "ł": "l", "ń": "n",
       "ó": "o", "ś": "s", "ź": "z", "ż": "z"}


def _ensure_dir():
    try:
        os.mkdir(DIR)
    except OSError:
        pass  # juz istnieje


def slugify(name):
    out = ""
    for ch in str(name).strip().lower():
        ch = _PL.get(ch, ch)
        if ("a" <= ch <= "z") or ("0" <= ch <= "9"):
            out += ch
        elif out and not out.endswith("-"):
            out += "-"
    return out.strip("-")[:16] or "animacja"


def _unique_slug(index, base, keep=None):
    slug = base
    n = 2
    taken = [e["slug"] for e in index if e["slug"] != keep]
    while slug in taken:
        slug = "%s-%d" % (base[:13], n)
        n += 1
    return slug


# ------------------------------------------------------------------- piksele

def to_bytes(px):
    """Przyjmuje ciag hex albo liste liczb 0xRRGGBB, zwraca bufor RGB."""
    n = config.LED_COUNT * 3
    buf = bytearray(n)
    if isinstance(px, str):
        try:
            raw = unhexlify(px[:n * 2])
        except (ValueError, TypeError):
            return buf
        buf[0:len(raw)] = raw
    elif isinstance(px, (list, tuple)):
        for i in range(min(len(px), config.LED_COUNT)):
            try:
                v = int(px[i]) & 0xFFFFFF
            except (ValueError, TypeError):
                v = 0
            j = i * 3
            buf[j] = v >> 16
            buf[j + 1] = (v >> 8) & 255
            buf[j + 2] = v & 255
    return buf


def to_hex(buf):
    return hexlify(bytes(buf)).decode()


def clean_frames(raw):
    """Sprawdza i normalizuje klatki przychodzace z panelu."""
    out = []
    if not isinstance(raw, (list, tuple)):
        return out
    for item in raw[:MAX_FRAMES]:
        if isinstance(item, dict):
            px = item.get("px", "")
            try:
                ms = int(item.get("ms", DEF_MS))
            except (ValueError, TypeError):
                ms = DEF_MS
        else:
            px, ms = item, DEF_MS
        ms = MAX_MS if ms > MAX_MS else MIN_MS if ms < MIN_MS else ms
        out.append({"px": to_bytes(px), "ms": ms})
    return out


# --------------------------------------------------------------------- spis

def load_index():
    try:
        with open(INDEX) as f:
            data = json.load(f)
        if isinstance(data, list):
            return [e for e in data if isinstance(e, dict) and "slug" in e]
    except (OSError, ValueError):
        pass
    return []


def _save_index(index):
    _ensure_dir()
    try:
        with open(INDEX, "w") as f:
            json.dump(index, f)
        return True
    except OSError as e:
        print("nie zapisano spisu galerii:", e)
        return False


def find(index, slug):
    for e in index:
        if e["slug"] == slug:
            return e
    return None


def find_by_name(index, name):
    name = str(name).strip()
    for e in index:
        if e.get("name") == name:
            return e
    return None


# ------------------------------------------------------------------ animacje

def load(slug):
    """Zwraca liste klatek [{'px': bytearray, 'ms': int}] gotowa do wyswietlenia."""
    try:
        with open("%s/%s.json" % (DIR, slug)) as f:
            data = json.load(f)
    except (OSError, ValueError):
        return []
    return clean_frames(data.get("frames", []))


def save(index, name, raw_frames):
    """Zapisuje animacje. Zwraca (wpis_do_spisu, blad)."""
    name = str(name).strip()[:24]
    if not name:
        return None, "podaj nazwe"
    frames = clean_frames(raw_frames)
    if not frames:
        return None, "animacja nie ma zadnej klatki"

    old = find_by_name(index, name)
    if old is None and len(index) >= MAX_ANIMS:
        return None, "galeria pelna (max %d animacji)" % MAX_ANIMS

    slug = old["slug"] if old else _unique_slug(index, slugify(name))
    _ensure_dir()
    body = {"name": name, "frames": [{"px": to_hex(f["px"]), "ms": f["ms"]} for f in frames]}
    try:
        with open("%s/%s.json" % (DIR, slug), "w") as f:
            json.dump(body, f)
    except OSError as e:
        return None, "brak miejsca albo blad zapisu (%s)" % e

    entry = {"slug": slug, "name": name, "n": len(frames), "thumb": to_hex(frames[0]["px"])}
    if old:
        index[index.index(old)] = entry
    else:
        index.append(entry)
    _save_index(index)
    return entry, None


def remove(index, slug):
    entry = find(index, slug)
    if entry is None:
        return False
    try:
        os.remove("%s/%s.json" % (DIR, slug))
    except OSError:
        pass
    index.remove(entry)
    _save_index(index)
    return True
