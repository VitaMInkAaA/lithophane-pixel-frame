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


def best_ap(ssid):
    """Znajduje NAJMOCNIEJSZY nadajnik o tej nazwie.

    W sieci z repeaterem albo mesh ta sama nazwa leci z kilku miejsc. Sterownik
    potrafi przyczepic sie do dalekiego i wtedy lampka jest "polaczona", ale
    ruch przychodzacy ginie. Skanujemy sami i wybieramy konkretny nadajnik.
    Zwraca (bssid, rssi, kanal) albo None."""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    best = None
    try:
        for net in wlan.scan():
            name = net[0]
            if isinstance(name, bytes):
                try:
                    name = name.decode()
                except UnicodeError:
                    continue
            if name != ssid:
                continue
            if best is None or net[3] > best[1]:
                best = (net[1], net[3], net[2])
    except (OSError, IndexError, TypeError) as e:
        log("skan przed polaczeniem nieudany:", e)
    return best


def rssi_of(wlan):
    try:
        return wlan.status("rssi")
    except (OSError, ValueError, TypeError, AttributeError):
        return None


async def connect(ssid, password, hostname=None, timeout_ms=15000, tries=3, pick_best=True):
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

    target = best_ap(ssid) if pick_best else None
    if target:
        log("wybieram nadajnik: RSSI %d dBm, kanal %s" % (target[1], target[2]))

    status = 0
    for attempt in range(tries):
        if attempt:
            print("proba %d/%d..." % (attempt + 1, tries))
        try:
            if target:
                try:
                    wlan.connect(ssid, password, bssid=target[0])
                except TypeError:
                    # starsze buildy nie przyjmuja bssid - trudno, lecimy bez
                    target = None
                    wlan.connect(ssid, password)
            else:
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
                return _connected(wlan)
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
            return _connected(wlan)
        if status == -3:
            break            # zle haslo - kolejne proby nic nie dadza
        await asyncio.sleep_ms(600)

    wlan.active(False)
    return None, STATUS_MSG.get(status, "nie udało się połączyć (kod %s)" % status)


def _connected(wlan):
    """Wspolne zakonczenie udanego polaczenia - z oceną sily sygnalu."""
    ip = wlan.ifconfig()[0]
    r = rssi_of(wlan)
    if r is None:
        log("polaczone, adres", ip)
    else:
        log("polaczone, adres %s, RSSI %d dBm" % (ip, r))
        if r < config.settings.get("rssi_min", -78):
            log("UWAGA: sygnal slaby (%d dBm). Lampka bedzie miala adres, ale "
                "panel moze byc nieosiagalny - przysun ja blizej routera." % r)
    return ip, None


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
    weak = 0
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

            # Sygnal moze byc fatalny mimo utrzymanego polaczenia - wtedy lampka
            # ma adres, a i tak nic do niej nie dochodzi. Po minucie takiego
            # stanu zrywamy i szukamy mocniejszego nadajnika.
            r = rssi_of(wlan)
            lamp.net["rssi"] = r
            if r is not None and r < config.settings.get("rssi_min", -78):
                weak += 1
                if weak >= 3:
                    weak = 0
                    log("sygnal slaby od minuty (%d dBm) - szukam mocniejszego "
                        "nadajnika" % r)
                    lamp.net["trying"] = True
                    try:
                        try:
                            wlan.disconnect()
                        except (OSError, AttributeError):
                            pass
                        await asyncio.sleep(1)
                        ip2, err2 = await connect(
                            ssid, config.settings.get("wifi_pass", ""),
                            config.settings.get("hostname"), tries=1)
                        if ip2:
                            lamp.net["ip"] = ip2
                            lamp.net["rssi"] = rssi_of(wlan)
                            lamp.net["err"] = ""
                        else:
                            lamp.net["err"] = err2 or "brak polaczenia"
                    finally:
                        # flaga MUSI zejsc nawet gdy proba zostanie przerwana -
                        # inaczej watchdog omijalby sie w nieskonczonosc
                        lamp.net["trying"] = False
            else:
                weak = 0
            continue

        fails += 1
        log("WiFi zerwane (%d. raz), wznawiam" % fails)
        lamp.net["trying"] = True
        try:
            ip, err = await connect(ssid, config.settings.get("wifi_pass", ""),
                                    config.settings.get("hostname"), tries=1)
        finally:
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


def link_info():
    """Krotki opis stanu radia - do wpisu w logu. Rozstrzyga sytuacje, w ktorej
    lampka "jest polaczona", a mimo to nic do niej nie dochodzi."""
    out = []
    try:
        sta = network.WLAN(network.STA_IF)
        if sta.active():
            out.append("STA " + ("polaczone" if sta.isconnected() else "ROZLACZONE"))
            try:
                out.append("RSSI %d dBm" % sta.status("rssi"))
            except (OSError, ValueError, TypeError, AttributeError):
                pass
            try:
                out.append("kanal %s" % sta.config("channel"))
            except (OSError, ValueError, TypeError, AttributeError):
                pass
        else:
            out.append("STA wylaczone")
    except Exception as e:
        out.append("STA ? (%s)" % e)
    try:
        ap = network.WLAN(network.AP_IF)
        if ap.active():
            out.append("AP wlaczone")
            try:
                out.append("kanal AP %s" % ap.config("channel"))
            except (OSError, ValueError, TypeError, AttributeError):
                pass
    except Exception:
        pass
    return ", ".join(out)
