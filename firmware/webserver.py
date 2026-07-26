# Prosty serwer HTTP + API dla panelu sterowania.
# Bez zadnych bibliotek zewnetrznych - tylko uasyncio z firmware'u.
import json
import os

import machine

try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

import config
import frames
import logger
import netmgr

WWW = "www"
REQ_TIMEOUT = 8      # sekundy na odebranie calego zapytania
LOG = True           # wypisuj kazde zapytanie na port szeregowy (diagnostyka)
MAX_BODY = 65536     # gorna granica cialka zapytania (RAM Pico)
MAX_CONN = 6         # ile polaczen obslugujemy naraz (lwIP ma ich skonczona pule)
CTYPE = {
    "html": "text/html; charset=utf-8",
    "css": "text/css; charset=utf-8",
    "js": "application/javascript; charset=utf-8",
    "json": "application/json",
    "svg": "image/svg+xml",
}


async def _send(w, body, ctype="text/plain; charset=utf-8", status="200 OK", cache=False):
    if isinstance(body, str):
        body = body.encode()
    head = "HTTP/1.1 %s\r\nContent-Type: %s\r\nContent-Length: %d\r\n" % (status, ctype, len(body))
    head += "Cache-Control: max-age=300\r\n" if cache else "Cache-Control: no-store\r\n"
    head += "Connection: close\r\n\r\n"
    w.write(head.encode())
    await w.drain()
    if body:
        w.write(body)
        await w.drain()


def path_of(target):
    return target.partition("?")[0]


async def _redirect(w, url):
    head = ("HTTP/1.1 302 Found\r\nLocation: %s\r\nContent-Length: 0\r\n"
            "Cache-Control: no-store\r\nConnection: close\r\n\r\n" % url)
    w.write(head.encode())
    await w.drain()


async def _send_json(w, obj, status="200 OK"):
    await _send(w, json.dumps(obj), "application/json", status)


async def _send_file(w, path, ctype):
    try:
        size = os.stat(path)[6]
    except OSError:
        await _send(w, "brak pliku: " + path, status="404 Not Found")
        return
    head = ("HTTP/1.1 200 OK\r\nContent-Type: %s\r\nContent-Length: %d\r\n"
            "Cache-Control: no-cache\r\nConnection: close\r\n\r\n" % (ctype, size))
    w.write(head.encode())
    await w.drain()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(512)
            if not chunk:
                break
            w.write(chunk)
            await w.drain()


class Server:
    def __init__(self, lamp):
        self.lamp = lamp
        self.portal_ip = None   # ustawiane w main.py, gdy dziala AP z captive portalem
        self.port = 80
        self.srv = None
        self.open_conns = 0     # ile polaczen obslugujemy w tej chwili
        self.served = 0         # ile zapytan od startu

    def _is_ours(self, host):
        """Czy klient puka pod adres lampki, czy pod cudzy (probka lacznosci)?

        Zapytania z adresem IP w naglowku przepuszczamy ZAWSZE, nawet jesli to
        nie ten adres, ktory znamy. Skoro pakiet do nas dotarl, to ten adres do
        nas prowadzi - odbicie go na 192.168.4.1 (osiagalne tylko z sieci
        lampki) potrafiloby zamknac dostep do panelu z domowej sieci.
        Odbijamy wylacznie nazwy domenowe, a tych uzywaja wszystkie probki
        lacznosci telefonow."""
        if not host:
            return True
        h = host.split(":")[0].lower()
        parts = h.split(".")
        if len(parts) == 4 and all(p.isdigit() for p in parts):
            return True
        hn = str(config.settings.get("hostname", ""))
        return bool(hn) and h in (hn, hn + ".local")

    async def start(self, port=80):
        self.port = port
        self.srv = await asyncio.start_server(self.handle, "0.0.0.0", port)
        logger.log("serwer www nasluchuje na porcie", port)

    async def restart(self):
        """Zamyka nasluch i otwiera go od nowa - ratunek, gdy zadanie
        przyjmujace polaczenia padlo, a reszta programu dziala dalej."""
        try:
            if self.srv:
                self.srv.close()
                await self.srv.wait_closed()
        except Exception as e:
            logger.log("zamykanie starego nasluchu:", e)
        self.srv = None
        await asyncio.sleep(1)
        await self.start(self.port)

    async def _probe(self):
        """Puka do wlasnego portu. True = nasluch przyjmuje polaczenia."""
        w = None
        try:
            _, w = await asyncio.wait_for(
                asyncio.open_connection("127.0.0.1", self.port), 4)
            return True
        except Exception:
            return False
        finally:
            if w is not None:
                try:
                    w.close()
                    await w.wait_closed()
                except Exception:
                    pass

    async def supervisor(self, interval=120):
        """Dozor nasluchu. Najpierw sprawdza, czy sonda w ogole dziala na tym
        firmware - jesli nie (brak petli zwrotnej w lwIP), wylacza sie, zeby
        nie restartowac serwera bez powodu."""
        await asyncio.sleep(5)
        if not await self._probe():
            logger.log("dozor serwera nieaktywny: sonda nie dziala na tym firmware")
            return
        logger.log("dozor nasluchu HTTP aktywny")
        bad = 0
        while True:
            await asyncio.sleep(interval)
            if await self._probe():
                bad = 0
                continue
            bad += 1
            logger.log("UWAGA: nasluch nie przyjmuje polaczen (%d/2)" % bad)
            if bad >= 2:
                bad = 0
                logger.log("restartuje nasluch HTTP")
                await self.restart()

    # -------------------------------------------------------------------- HTTP
    async def _read(self, r):
        """Zwraca (metoda, sciezka, query, cialo, host, za_duze) albo None."""
        line = await r.readline()
        if not line:
            return None
        parts = line.decode().split()
        if len(parts) < 2:
            return None
        method, target = parts[0], parts[1]
        length = 0
        host = ""
        while True:
            h = await r.readline()
            if not h or h == b"\r\n":
                break
            hl = h.decode().lower()
            if hl.startswith("content-length:"):
                try:
                    length = int(hl.split(":", 1)[1].strip())
                except ValueError:
                    length = 0
            elif hl.startswith("host:"):
                host = hl.split(":", 1)[1].strip()
        if length > MAX_BODY:
            # Pico ma ~200 kB wolnego RAM-u. Nie probujemy wciagac wiekszego
            # cialka, bo proba parsowania takiego JSON-a konczy sie MemoryError
            # i restartem lampki w srodku pracy.
            return method, path_of(target), "", b"", host, True
        body = await r.readexactly(length) if length else b""
        path, _, query = target.partition("?")
        return method, path, query, body, host, False

    async def handle(self, r, w):
        if self.open_conns >= MAX_CONN:
            # lwIP ma skonczona pule gniazd; zamiast doprowadzic do jej
            # wyczerpania (po czym nasluch przestaje przyjmowac cokolwiek)
            # odsylamy z niczym i zapisujemy to w logu
            logger.log("za duzo polaczen naraz (%d), odrzucam" % self.open_conns)
            try:
                w.close()
                await w.wait_closed()
            except Exception:
                pass
            return
        self.open_conns += 1
        self.served += 1
        try:
            # Limit czasu, zeby polaczenie ucieta w polowie zapytania nie trzymalo
            # gniazda na wieki - Pico ma ich tylko kilka.
            req = await asyncio.wait_for(self._read(r), REQ_TIMEOUT)
            if req is None:
                return
            if LOG:
                logger.trace(req[0], req[1])
            if req[5]:
                await _send_json(w, {"ok": False, "err": "animacja za duza"},
                                 "413 Payload Too Large")
                return
            # captive portal: pytanie o cudzy adres (telefon sprawdza lacznosc)
            # odbijamy na panel, wtedy system sam go otwiera
            if self.portal_ip and not self._is_ours(req[4]):
                await _redirect(w, "http://%s/" % self.portal_ip)
                return
            await self.route(w, req[0], req[1], req[2], req[3])
        except asyncio.TimeoutError:
            # przegladarki otwieraja gniazda "na zapas" i nic nimi nie wysylaja
            if LOG:
                logger.trace("http: puste polaczenie, zamykam")
        except OSError as e:
            # ECONNRESET itp. - klient rozmyslil sie w trakcie, nic groznego
            if LOG:
                logger.trace("http: klient zerwal polaczenie -", e)
        except Exception as e:
            logger.log("BLAD http:", e)
        finally:
            self.open_conns -= 1
            try:
                await w.drain()
                w.close()
                await w.wait_closed()
            except Exception:
                pass

    async def route(self, w, method, path, query, body):
        if path.startswith("/api/"):
            data = {}
            if body:
                try:
                    data = json.loads(body)
                except ValueError:
                    await _send_json(w, {"ok": False, "err": "zly json"}, "400 Bad Request")
                    return
            await self.api(w, method, path[5:], data)
            return

        if path == "/favicon.ico":
            await _send(w, b"", "image/x-icon", "204 No Content")
            return
        if path == "/":
            path = "/index.html"
        if ".." in path:
            await _send(w, "nie", status="403 Forbidden")
            return
        ext = path.rsplit(".", 1)[-1]
        await _send_file(w, WWW + path, CTYPE.get(ext, "application/octet-stream"))

    # --------------------------------------------------------------------- API
    async def api(self, w, method, name, d):
        lamp = self.lamp
        s = config.settings

        if name == "state":
            await _send_json(w, self.state())

        elif name == "power":
            lamp.power(d.get("on", True))
            await _send_json(w, self.state())

        elif name == "toggle":
            lamp.toggle()
            await _send_json(w, self.state())

        elif name == "anim":
            ok = lamp.set_anim(d.get("id", ""))
            if ok:
                lamp.power(True)
            await _send_json(w, self.state() if ok else {"ok": False, "err": "nie ma takiego trybu"})

        elif name == "next":
            lamp.next_anim()
            await _send_json(w, self.state())

        elif name == "set":
            if "brightness" in d:
                s["brightness"] = max(1, min(100, int(d["brightness"])))
            if "speed" in d:
                s["speed"] = max(10, min(400, int(d["speed"])))
            if "color" in d:
                s["color"] = str(d["color"])[:9]
            config.mark()
            lamp.activity()
            await _send_json(w, {"ok": True})

        elif name == "settings":
            if "auto_off" in d:
                s["auto_off"] = bool(d["auto_off"])
            if "auto_off_min" in d:
                s["auto_off_min"] = max(1, min(720, int(d["auto_off_min"])))
            if "show_ip" in d:
                s["show_ip"] = bool(d["show_ip"])
            if "btn_active_high" in d:
                s["btn_active_high"] = bool(d["btn_active_high"])
            if "hostname" in d:
                s["hostname"] = netmgr.clean_hostname(d["hostname"])
            if "ap_always" in d:
                s["ap_always"] = bool(d["ap_always"])
            if "captive" in d:
                s["captive"] = bool(d["captive"])
            if "log_file" in d:
                s["log_file"] = bool(d["log_file"])
            if "wifi_powersave" in d:
                s["wifi_powersave"] = bool(d["wifi_powersave"])
            if "country" in d:
                s["country"] = str(d["country"]).upper()[:2] or "PL"
                netmgr.set_country(s["country"])
            geom = False
            for k in ("origin", "rows", "serpentine"):
                if k in d:
                    s[k] = d[k] if k == "origin" else bool(d[k])
                    geom = True
            if geom:
                lamp.m.remap()
            config.save()
            lamp.activity()
            await _send_json(w, self.state())

        elif name == "seq":
            aid = str(d.get("id", ""))
            if not aid:
                await _send_json(w, {"ok": False, "err": "brak id"}, "400 Bad Request")
                return
            lamp.set_seq(aid, bool(d.get("on", True)))
            await _send_json(w, self.state())

        elif name == "preview":
            # z edytora leci albo pojedyncza klatka (malowanie), albo cala animacja
            raw = d.get("frames")
            if raw is None and "px" in d:
                raw = [{"px": d["px"], "ms": 500}]
            if not lamp.show_preview(raw):
                await _send_json(w, {"ok": False, "err": "brak klatek"}, "400 Bad Request")
                return
            await _send_json(w, {"ok": True})

        elif name == "rawtest":
            # kreator geometrii: zapala diody po NUMERACH na tasmie,
            # z pominieciem calego mapowania
            if d.get("off"):
                lamp.raw_off()
                lamp.set_anim(lamp.anim_id, save=False)
            else:
                lamp.raw_test(d.get("leds") or [])
            await _send_json(w, {"ok": True})

        elif name == "gallery":
            await _send_json(w, {"ok": True, "items": lamp.gallery})

        elif name == "gallery/save":
            entry, err = frames.save(lamp.gallery, d.get("name", ""), d.get("frames"))
            if err:
                await _send_json(w, {"ok": False, "err": err}, "400 Bad Request")
                return
            lamp.set_anim("px:" + entry["slug"])
            lamp.power(True)
            st = self.state()
            st["saved"] = entry["slug"]
            await _send_json(w, st)

        elif name == "gallery/get":
            slug = str(d.get("slug", ""))
            entry = frames.find(lamp.gallery, slug)
            if entry is None:
                await _send_json(w, {"ok": False, "err": "nie ma takiej animacji"},
                                 "404 Not Found")
                return
            fr = frames.load(slug)
            await _send_json(w, {"ok": True, "name": entry["name"],
                                 "frames": [{"px": frames.to_hex(f["px"]), "ms": f["ms"]}
                                            for f in fr]})

        elif name == "gallery/del":
            slug = str(d.get("slug", ""))
            frames.remove(lamp.gallery, slug)
            if lamp.anim_id == "px:" + slug:
                lamp.set_anim(lamp.seq_ids()[0])
            await _send_json(w, self.state())

        elif name == "wifi/scan":
            await _send_json(w, {"nets": netmgr.scan()})

        elif name == "wifi":
            ssid = str(d.get("ssid", "")).strip()
            if not ssid:
                await _send_json(w, {"ok": False, "err": "podaj nazwe sieci"}, "400 Bad Request")
                return
            s["wifi_ssid"] = ssid
            s["wifi_pass"] = str(d.get("pass", ""))
            config.save()
            # Probujemy od razu, bez restartu - dzieki temu widzisz w panelu
            # CZY sie udalo, a jak nie, to dlaczego.
            lamp.net["trying"] = True
            lamp.net["err"] = ""
            await _send_json(w, {"ok": True, "msg": "łączę się..."})
            asyncio.create_task(self._try_wifi())

        elif name == "wifi/forget":
            s["wifi_ssid"] = ""
            s["wifi_pass"] = ""
            config.save()
            await _send_json(w, {"ok": True, "msg": "sieć zapomniana, restartuje..."})
            asyncio.create_task(_reboot())

        elif name == "log":
            await _send_json(w, {"ok": True, "on": bool(s["log_file"]),
                                 "text": logger.read()})

        elif name == "log/clear":
            logger.clear()
            await _send_json(w, {"ok": True, "text": logger.read()})

        elif name == "reboot":
            await _send_json(w, {"ok": True, "msg": "restartuje..."})
            asyncio.create_task(_reboot())

        else:
            await _send_json(w, {"ok": False, "err": "nieznane api"}, "404 Not Found")

    async def _try_wifi(self):
        """Proba polaczenia w tle - serwer w tym czasie dziala dalej,
        a panel widzi postep w /api/state."""
        lamp = self.lamp
        s = config.settings
        ip, err = await netmgr.connect(s["wifi_ssid"], s["wifi_pass"], s["hostname"])
        lamp.net["trying"] = False
        if ip:
            lamp.net["ip"] = ip
            lamp.net["ssid"] = s["wifi_ssid"]
            lamp.net["mode"] = "sta+ap" if lamp.net.get("ap_ip") else "sta"
            lamp.net["err"] = ""
            print("polaczono, adres", ip)
        else:
            lamp.net["err"] = err or "nie udało się połączyć"
            print("WiFi nie wyszlo:", lamp.net["err"])

    def state(self):
        lamp = self.lamp
        s = config.settings
        return {
            "ok": True,
            "on": bool(s["on"]),
            "anim": lamp.anim_id,
            "anims": lamp.anim_list(),
            # bez miniatur - te ida osobno przez /api/gallery, zeby stan
            # odpytywany co kilka sekund zostal maly
            "gallery": [{"slug": e["slug"], "name": e["name"], "n": e.get("n", 1)}
                        for e in lamp.gallery],
            "limits": {"frames": frames.MAX_FRAMES, "anims": frames.MAX_ANIMS,
                       "ms_min": frames.MIN_MS, "ms_max": frames.MAX_MS},
            "brightness": s["brightness"],
            "speed": s["speed"],
            "color": s["color"],
            # czy biezacy tryb w ogole uzywa wybranego koloru
            "color_ok": bool(getattr(lamp.anim, "uses_color", False)),
            "auto_off": bool(s["auto_off"]),
            "auto_off_min": s["auto_off_min"],
            "auto_off_left": lamp.auto_off_left(),
            "show_ip": bool(s["show_ip"]),
            "btn_active_high": bool(s["btn_active_high"]),
            "hostname": s["hostname"],
            "ap_always": bool(s["ap_always"]),
            "captive": bool(s["captive"]),
            "country": s["country"],
            "log_file": bool(s["log_file"]),
            "wifi_powersave": bool(s["wifi_powersave"]),
            "ap_ssid": config.AP_SSID,
            "ap_pass": s["ap_pass"],
            "origin": s["origin"],
            "rows": bool(s["rows"]),
            "serpentine": bool(s["serpentine"]),
            "w": config.WIDTH,
            "h": config.HEIGHT,
            "net": lamp.net,
        }


async def _reboot():
    await asyncio.sleep_ms(600)
    machine.reset()
