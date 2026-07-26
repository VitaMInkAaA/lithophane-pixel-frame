# Konfiguracja LED Lampki - ramka 7 x 9 na Raspberry Pi Pico W
#
# SPRZET (zmieniaj tylko jesli przelutujesz):
#   GP0  -> DIN matrycy WS2812 (przez rezystor 330 om)
#   GP2  -> OUT z TTP223 (modul zasilany z 3V3, pin 36)
#   5V   -> zasilacz zewnetrzny (VSYS pin 39 przez diode Schottky)
import json

LED_PIN = 0
BUTTON_PIN = 2

WIDTH = 7
HEIGHT = 9
LED_COUNT = WIDTH * HEIGHT  # 63

SETTINGS_FILE = "settings.json"
# wlasne animacje siedza w katalogu anims/ - patrz frames.py

AP_SSID = "LED-Lampka"

DEFAULTS = {
    "on": True,
    "anim": "ogien",
    "brightness": 40,        # %
    "speed": 100,            # % szybkosci animacji
    "color": "#ff7800",      # kolor dla trybow Kolor / Oddech
    "auto_off": False,
    "auto_off_min": 60,      # minuty bezczynnosci do zgasniecia
    "wifi_ssid": "",
    "wifi_pass": "",
    "ap_pass": "ledlampka",  # min. 8 znakow
    "hostname": "lampka",    # panel pod http://lampka.local/
    # Wlasny AP utrzymywany obok domowego WiFi - drugie, niezalezne wejscie
    # do panelu. Pico W dzieli jedno radio miedzy oba interfejsy, wiec na
    # niektorych routerach potrafi to rozchwiac polaczenie; jesli lampka ma
    # poprawny adres, a panel nie odpowiada, sprobuj to wylaczyc.
    "ap_always": True,
    "captive": True,         # po podlaczeniu do sieci lampki sam otworz panel
    "country": "PL",         # kod kraju = dozwolone kanaly WiFi (12 i 13!)
    # Oszczedzanie energii radia usypia odbiornik i gubi pakiety przychodzace -
    # po godzinach pracy lampka "jest w sieci", ale panel nie odpowiada.
    "wifi_powersave": False,
    # Ponizej tej sily sygnalu polaczenie formalnie trwa, ale ruch przychodzacy
    # ginie. Lampka probuje wtedy przepiac sie na mocniejszy nadajnik.
    "rssi_min": -78,
    "log_file": True,        # zapisuj zdarzenia do log.txt
    "btn_active_high": True, # TTP223 domyslnie daje stan wysoki przy dotyku
    # Geometria tasmy w ramce: pierwsza dioda w prawym DOLNYM rogu, pasek idzie
    # w GORE, zawraca i schodzi w dol - czyli kolumnami, wezykiem.
    "origin": "BR",          # rog z pierwsza dioda: BL BR TL TR (patrzac z przodu)
    "rows": False,           # True = pasek biegnie rzedami, False = kolumnami
    "serpentine": True,      # wezykiem
    "show_ip": True,         # po starcie pokaz ostatni czlon IP na matrycy
    # tryby WYLACZONE z przelaczania przyciskiem (w panelu dalej dostepne)
    "seq_off": ["kalibracja"],
}

settings = dict(DEFAULTS)

_dirty = False


def load():
    """Wczytuje settings.json na wierzch wartosci domyslnych."""
    try:
        with open(SETTINGS_FILE) as f:
            data = json.load(f)
        for k in DEFAULTS:
            if k in data:
                settings[k] = data[k]
    except (OSError, ValueError):
        pass  # pierwszy start albo uszkodzony plik - zostaja domyslne
    return settings


def save():
    global _dirty
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f)
        _dirty = False
        return True
    except OSError as e:
        print("nie zapisano settings.json:", e)
        return False


def mark():
    """Oznacza zmiane do zapisu. Realny zapis robi flush() co kilka sekund,
    zeby klikanie przyciskiem nie zajezdzalo pamieci flash."""
    global _dirty
    _dirty = True


def flush():
    if _dirty:
        save()
        return True
    return False


def hex_to_rgb(h):
    try:
        v = int(str(h).lstrip("#"), 16)
    except ValueError:
        return (255, 255, 255)
    return ((v >> 16) & 255, (v >> 8) & 255, v & 255)


def color_rgb():
    return hex_to_rgb(settings["color"])
