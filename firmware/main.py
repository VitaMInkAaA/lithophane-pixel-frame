# LED Lampka - ramka 7 x 9 WS2812 na Raspberry Pi Pico W
#
# Start:
#   1. wczytanie ustawien
#   2. WiFi: zapisana siec, a jak sie nie uda - wlasny AP "LED-Lampka"
#   3. pokazanie ostatniego czlonu IP na matrycy
#   4. rownolegle: animacje + przycisk + serwer panelu
import time

import machine

try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

import config
import dns
import glyphs
import logger
import netmgr
import touch
from lamp import Lamp
from webserver import Server


def forget_wifi():
    """Wywolywane bardzo dlugim przytrzymaniem dotyku - awaryjny powrot do AP."""
    print("czyszcze ustawienia WiFi i restartuje")
    config.settings["wifi_ssid"] = ""
    config.settings["wifi_pass"] = ""
    config.save()
    time.sleep_ms(200)
    machine.reset()


async def start():
    try:
        asyncio.get_event_loop().set_exception_handler(logger.task_error)
    except (AttributeError, TypeError):
        pass          # starsze uasyncio nie ma tego mechanizmu
    config.load()
    lamp = Lamp()
    s = config.settings

    glyphs.flash(lamp.m, (0, 0, 40))              # zyje

    netmgr.set_country(s["country"])
    host = netmgr.clean_hostname(s["hostname"])
    ip = None
    err = ""
    if s["wifi_ssid"]:
        print("lacze z", s["wifi_ssid"])
        glyphs.flash(lamp.m, (60, 30, 0))         # zolty blysk: lacze sie
        ip, err = await netmgr.connect(s["wifi_ssid"], s["wifi_pass"], host)
        if err:
            print("WiFi nie wyszlo:", err)

    ap_ip = None
    if ip:
        glyphs.flash(lamp.m, (0, 60, 0))          # zielony: jest siec
        # Zapasowe wejscie: wlasny AP obok domowego WiFi. Dzieki temu lampka jest
        # osiagalna nawet tam, gdzie nie wiadomo jaki dostala adres.
        if s["ap_always"]:
            ap_ip = netmgr.start_ap(s["ap_pass"])
        lamp.net = {"mode": "sta+ap" if ap_ip else "sta", "ip": ip,
                    "ssid": s["wifi_ssid"], "host": host, "ap_ip": ap_ip,
                    "err": "", "trying": False, "rssi": netmgr.rssi_of(netmgr.network.WLAN(netmgr.network.STA_IF))}
    else:
        ap_ip = netmgr.start_ap(s["ap_pass"])
        lamp.net = {"mode": "ap", "ip": ap_ip or "-", "ssid": config.AP_SSID,
                    "host": host, "ap_ip": ap_ip, "err": err, "trying": False, "rssi": None}
        glyphs.flash(lamp.m, (0, 0, 90), 2)       # niebieski x2: tryb AP

    logger.log("start; siec:", lamp.net["mode"], "adres:", lamp.net["ip"])
    print("panel:")
    if ip:
        print("   http://%s.local/   (nazwa hosta, mDNS)" % host)
        print("   http://%s/" % ip)
    if ap_ip:
        print("   http://%s/   po podlaczeniu do sieci '%s' (haslo: %s)"
              % (ap_ip, config.AP_SSID, s["ap_pass"]))

    if s["show_ip"] and ip:
        glyphs.show_ip(lamp.m, ip)

    btn = touch.Touch(active_high=s["btn_active_high"])
    server = Server(lamp)
    # Captive portal TYLKO w czystym trybie AP. Gdy lampka siedzi w domowym
    # WiFi, serwer DNS odpowiadalby na zapytania z calej sieci lokalnej
    # (kazda nazwa -> 192.168.4.1), a to psuje internet innym urzadzeniom.
    if ap_ip and not ip and s["captive"]:
        server.portal_ip = ap_ip
        asyncio.create_task(dns.serve(ap_ip))
        print("captive portal: panel otworzy sie sam po podlaczeniu do AP")
    await server.start()

    asyncio.create_task(lamp.button_loop(btn, forget_wifi))
    asyncio.create_task(lamp.save_loop())
    asyncio.create_task(netmgr.watchdog(lamp))     # wznawia zerwane WiFi
    asyncio.create_task(server.supervisor())       # pilnuje nasluchu HTTP
    asyncio.create_task(housekeeping(server))      # porzadki + raport stanu
    await lamp.run()


async def housekeeping(server):
    """Co 5 minut sprzata pamiec i zapisuje stan.

    Trzy liczby w jednej linii rozstrzygaja, co sie dzieje przez noc:
    spadajacy RAM = wyciek, rosnaca liczba otwartych polaczen = gniazda nie sa
    zwalniane, zamarznieta liczba obsluzonych = nasluch przestal odbierac."""
    import gc
    while True:
        gc.collect()
        try:
            free = gc.mem_free()
        except AttributeError:
            free = -1
        logger.log("RAM %d B | polaczenia otwarte %d | obsluzonych %d | %s"
                   % (free, server.open_conns, server.served, netmgr.link_info()))
        await asyncio.sleep(300)


try:
    asyncio.run(start())
except KeyboardInterrupt:
    print("zatrzymane z klawiatury")
except Exception as e:
    # Nie zostawiaj lampki swiecacej byle czym, jak cos padnie
    print("KRYTYCZNY BLAD:", e)
    try:
        import neopixel

        np = neopixel.NeoPixel(machine.Pin(config.LED_PIN), config.LED_COUNT)
        for _ in range(3):
            np.fill((60, 0, 0))
            np.write()
            time.sleep_ms(250)
            np.fill((0, 0, 0))
            np.write()
            time.sleep_ms(250)
    except Exception:
        pass
    raise
