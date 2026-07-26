# WiFi: probuje sie polaczyc z zapisana siecia, a jesli nie ma zapisanego
# hasla albo polaczenie nie wyjdzie - stawia wlasny Access Point, przez ktory
# mozna sterowac lampka i skonfigurowac WiFi.
#
# Dostep do panelu bez znajomosci adresu IP dziala na dwa sposoby:
#   1. nazwa hosta (mDNS)  -> http://lampka.local/
#   2. wlasny AP lampki    -> http://192.168.4.1/  (dziala zawsze, bez rutera)
import time

import network

try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

import config
from logger import log


def clean_hostname(name):
    """Tylko male litery, cyfry i myslnik - inaczej mDNS to odrzuci."""
    out = ""
    for ch in str(name).strip().lower():
        if ("a" <= ch <= "z") or ("0" <= ch <= "9") or ch == "-":
            out += ch
    out = out.strip("-")[:24]
    return out or "lampka"


def set_hostname(name):
    """Ustawia nazwe hosta. MUSI byc wywolane przed podniesieniem interfejsu,
    inaczej ani DHCP ani mDNS jej nie zobacza."""
    name = clean_hostname(name)
    try:
        network.hostname(name)          # MicroPython 1.20+
    except (AttributeError, OSError, ValueError):
        pass
    return name


STATUS_MSG = {
    -3: "złe hasło",
    -2: "nie widzę tej sieci — sprawdź nazwę i pamiętaj, że Pico W działa "
        "wyłącznie na paśmie 2,4 GHz",
    -1: "router odrzucił połączenie",
    0: "brak połączenia",
    1: "nie zdążyłem się połączyć w wyznaczonym czasie",
    2: "sieć nie przydzieliła adresu (DHCP)",
}


def set_power_save(wlan, enabled):
    """Tryb oszczedzania energii ukladu CYW43.

    To NAJCZESTSZA przyczyna tego, ze Pico W po kilku godzinach przestaje
    odpowiadac, choc formalnie jest polaczone: uklad usypia radio miedzy
    ramkami i gubi pakiety przychodzace. Wychodzace dzialaja, wiec z zewnatrz
    wyglada to jak "jest w sieci, ale nie da sie wejsc".
    Wylaczenie kosztuje ~30 mA - przy matrycy pobierajacej ampery to nic."""
    try:
        mode = wlan.PM_PERFORMANCE if enabled else wlan.PM_NONE
    except AttributeError:
        mode = 0xa11140 if not enabled else 0xa11142   # starsze buildy
    try:
        wlan.config(pm=mode)
        return True
    except (AttributeError, OSError, ValueError) as e:
        log("nie ustawilem trybu energii:", e)
        return False


def set_country(code):
    """Kod kraju decyduje o dozwolonych kanalach. Bez niego Pico trzyma sie
    kanalow 1-11, a routery w Polsce potrafia stac na 12 albo 13 - takiej sieci
    lampka po prostu NIE ZOBACZY."""
    try:
        import rp2
        rp2.country(str(code).upper()[:2])
        return True
    except (ImportError, AttributeError, ValueError, OSError) as e:
        print("nie ustawilem kodu kraju:", e)
        return False


async def connect(ssid, password, hostname=None, timeout_ms=15000, tries=3):
    """Laczy sie z siecia. Zwraca (adres_ip, None) albo (None, opis_bledu).

    Asynchroniczne, zeby proba polaczenia uruchomiona z panelu nie zamrazala
    serwera na kilkanascie sekund."""
    wlan = network.WLAN(network.STA_IF)
    if hostname:
        set_hostname(hostname)
    wlan.active(True)
    set_power_save(wlan, bool(config.settings.get("wifi_powersave")))
    if hostname:
        try:
            wlan.config(hostname=hostname)   # starsze buildy
        except (AttributeError, OSError, ValueError):
            pass

    status = 0
    for attempt in range(tries):
        if attempt:
            print("proba %d/%d..." % (attempt + 1, tries))
        try:
            wlan.connect(ssid, password)
        except OSError as e:
            status = 0
            print("connect():", e)
            await asyncio.sleep_ms(500)
            continue

        t0 = time.ticks_ms()
        bad = 0
        while time.ticks_diff(time.ticks_ms(), t0) < timeout_ms:
            if wlan.isconnected():
                return wlan.ifconfig()[0], None
            status = wlan.status()
            if status < 0:
                # Pojedynczy ujemny odczyt zdarza sie w trakcie kojarzenia i
                # nic nie znaczy. Dopiero dwa pod rzad to naprawde porazka.
                bad += 1
                if bad >= 2:
                    break
            else:
                bad = 0
            await asyncio.sleep_ms(300)

        if wlan.isconnected():
            return wlan.ifconfig()[0], None
        if status == -3:
            break            # zle haslo - kolejne proby nic nie dadza
        await asyncio.sleep_ms(600)

    wlan.active(False)
    return None, STATUS_MSG.get(status, "nie udało się połączyć (kod %s)" % status)


def start_ap(password):
    """Stawia AP 'LED-Lampka'. Panel bedzie pod http://192.168.4.1/
    Mozna go trzymac rownolegle z polaczeniem do domowego WiFi - wtedy lampka
    jest osiagalna nawet w miejscu, gdzie nie znasz adresow w sieci."""
    ap = network.WLAN(network.AP_IF)
    if not password or len(password) < 8:
        password = "ledlampka"
    try:
        ap.config(essid=config.AP_SSID, password=password)
        ap.active(True)
    except (OSError, ValueError) as e:
        print("nie udalo sie postawic AP:", e)
        return None
    t0 = time.ticks_ms()
    while not ap.active() and time.ticks_diff(time.ticks_ms(), t0) < 5000:
        time.sleep_ms(100)
    if not ap.active():
        print("AP nie wstal")
        return None
    return ap.ifconfig()[0]


def stop_ap():
    ap = network.WLAN(network.AP_IF)
    if ap.active():
        ap.active(False)


def scan():
    """Lista widocznych sieci, najmocniejsze pierwsze."""
    wlan = network.WLAN(network.STA_IF)
    was_active = wlan.active()
    wlan.active(True)
    best = {}
    try:
        for net in wlan.scan():
            ssid = net[0]
            if isinstance(ssid, bytes):
                try:
                    ssid = ssid.decode()
                except UnicodeError:
                    continue
            if not ssid:
                continue
            rssi = net[3]
            if ssid not in best or rssi > best[ssid]:
                best[ssid] = rssi
    except OSError as e:
        print("skan nieudany:", e)
    finally:
        if not was_active:
            # W trybie AP interfejs STA byl wylaczony - nie zostawiamy go wlaczonego
            try:
                wlan.active(False)
            except OSError:
                pass
    out = [{"ssid": s, "rssi": r} for s, r in best.items()]
    out.sort(key=lambda n: n["rssi"], reverse=True)
    return out


async def watchdog(lamp, interval=20):
    """Pilnuje polaczenia i wznawia je po zerwaniu.

    Bez tego lampka po utracie sieci (restart routera, wygasly adres, zmiana
    kanalu) zostawala offline do konca zycia - nic nie probowalo sie polaczyc
    ponownie. To druga typowa przyczyna "rano nie dzialalo"."""
    wlan = network.WLAN(network.STA_IF)
    fails = 0
    while True:
        await asyncio.sleep(interval)
        ssid = config.settings.get("wifi_ssid")
        if not ssid or lamp.net.get("trying"):
            continue

        if wlan.isconnected():
            if fails:
                log("polaczenie wrocilo")
            fails = 0
            ip = wlan.ifconfig()[0]
            if ip and ip != "0.0.0.0" and lamp.net.get("ip") != ip:
                log("router zmienil nam adres na", ip)
                lamp.net["ip"] = ip
                lamp.net["err"] = ""
            continue

        fails += 1
        log("WiFi zerwane (%d. raz), wznawiam" % fails)
        lamp.net["trying"] = True
        ip, err = await connect(ssid, config.settings.get("wifi_pass", ""),
                                config.settings.get("hostname"), tries=1)
        lamp.net["trying"] = False
        if ip:
            lamp.net["ip"] = ip
            lamp.net["ssid"] = ssid
            lamp.net["mode"] = "sta+ap" if lamp.net.get("ap_ip") else "sta"
            lamp.net["err"] = ""
            log("wznowione, adres", ip)
        else:
            lamp.net["err"] = err or "brak polaczenia"
            log("wznowienie nieudane:", lamp.net["err"])
            # przy dluzszej awarii nie dobijamy sie co 20 s
            if fails > 3:
                await asyncio.sleep(interval * 3)
