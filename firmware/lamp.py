# Stan lampki: aktualna animacja, wlacznik, jasnosc, auto-wylaczanie.
# To jedyne miejsce, ktore rysuje na matrycy - i przycisk, i panel www
# wolaja te same metody.
import time

try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

import animations
import config
import frames
import glyphs
import touch
from led_matrix import Matrix


class Lamp:
    def __init__(self):
        self.s = config.settings
        self.m = Matrix(self.s)
        self.gallery = frames.load_index()
        self.anim = None
        self.anim_id = ""
        self.busy = False       # ktos inny rysuje na matrycy (np. pokaz IP)
        self.last_act = time.ticks_ms()
        self.net = {"mode": "?", "ip": "-", "ssid": "", "host": "",
                    "ap_ip": None, "err": "", "trying": False}
        if not self.set_anim(self.s.get("anim", "ogien"), save=False):
            self.set_anim(animations.ANIMS[0].name, save=False)

    # ------------------------------------------------------------ lista trybow
    def anim_list(self):
        """Wszystkie tryby: wbudowane + wlasne z galerii. Pole 'seq' mowi, czy
        tryb bierze udzial w przelaczaniu przyciskiem."""
        off = self.s.get("seq_off", [])
        out = []
        for a in animations.ANIMS:
            out.append({"id": a.name, "label": a.label, "own": False,
                        "seq": a.name not in off})
        for e in self.gallery:
            aid = "px:" + e["slug"]
            out.append({"id": aid, "label": e["name"], "own": True,
                        "n": e.get("n", 1), "seq": aid not in off})
        return out

    def seq_ids(self):
        """Tryby wchodzace w kolo przelaczane przyciskiem."""
        ids = [a["id"] for a in self.anim_list() if a["seq"]]
        return ids or [a["id"] for a in self.anim_list()]

    def set_seq(self, aid, on):
        off = list(self.s.get("seq_off", []))
        if on and aid in off:
            off.remove(aid)
        elif not on and aid not in off:
            off.append(aid)
        self.s["seq_off"] = off
        config.mark()

    def set_anim(self, aid, save=True):
        if not aid:
            return False
        if aid.startswith("px:"):
            entry = frames.find(self.gallery, aid[3:])
            if entry is None:
                return False
            self.anim = animations.WlasnaAnimacja(self.m, self.s, frames.load(entry["slug"]))
        else:
            cls = animations.by_name(aid)
            if cls is None:
                return False
            self.anim = cls(self.m, self.s)
        self.anim_id = aid
        self.s["anim"] = aid
        if save:
            config.mark()
        self.activity()
        return True

    def _step_anim(self, delta):
        ids = self.seq_ids()
        try:
            i = ids.index(self.anim_id)
        except ValueError:
            # biezacy tryb jest poza sekwencja (np. wybrany z panelu albo
            # podglad z edytora) - wchodzimy na skraj listy
            i = -1 if delta > 0 else 0
        self.set_anim(ids[(i + delta) % len(ids)])

    def next_anim(self):
        self._step_anim(1)

    def prev_anim(self):
        self._step_anim(-1)

    def show_preview(self, raw_frames):
        """Podglad na zywo z edytora - nigdzie sie nie zapisuje."""
        fr = frames.clean_frames(raw_frames)
        if not fr:
            return False
        self.anim = animations.WlasnaAnimacja(self.m, self.s, fr)
        self.anim_id = "px:*podglad*"
        self.s["on"] = True
        self.activity()
        return True

    # ------------------------------------------------------------------ wlacznik
    def power(self, on):
        on = bool(on)
        if self.s["on"] != on:
            self.s["on"] = on
            config.mark()
        if not on:
            self.m.blackout()
        self.activity()

    def toggle(self):
        self.power(not self.s["on"])

    def activity(self):
        self.last_act = time.ticks_ms()

    def auto_off_left(self):
        """Ile sekund do zgasniecia (None gdy funkcja wylaczona)."""
        if not self.s.get("auto_off") or not self.s.get("on"):
            return None
        total = int(self.s.get("auto_off_min", 60)) * 60000
        left = total - time.ticks_diff(time.ticks_ms(), self.last_act)
        return max(0, left // 1000)

    def _check_auto_off(self):
        if not self.s.get("auto_off") or not self.s.get("on"):
            return
        total = int(self.s.get("auto_off_min", 60)) * 60000
        if time.ticks_diff(time.ticks_ms(), self.last_act) >= total:
            print("auto-wylaczenie po", self.s.get("auto_off_min"), "min bezczynnosci")
            self.power(False)

    # -------------------------------------------------------------------- petle
    async def run(self):
        """Petla rysowania."""
        while True:
            if self.busy:
                await asyncio.sleep_ms(60)
                continue
            if self.s.get("on") and self.anim:
                try:
                    self.anim.step()
                    self.m.show()
                except Exception as e:
                    print("blad animacji", self.anim_id, ":", e)
                    await asyncio.sleep_ms(1000)
                speed = int(self.s.get("speed", 100))
                if speed < 10:
                    speed = 10
                wait = self.anim.interval * 100 // speed
                await asyncio.sleep_ms(wait if wait > 10 else 10)
            else:
                await asyncio.sleep_ms(150)
            self._check_auto_off()

    # -------------------------------------------------------------- suwaki
    def _ramp(self, key, up, step, lo, hi):
        """Jeden krok zmiany jasnosci/szybkosci podczas trzymania przycisku."""
        v = int(self.s.get(key, lo)) + (step if up else -step)
        v = hi if v > hi else lo if v < lo else v
        self.s[key] = v
        return v

    def _flip(self, up, val, lo, hi):
        """Kierunek na nastepne trzymanie: normalnie odwrotny, a po dojsciu
        do konca zakresu zawsze z powrotem."""
        if val >= hi:
            return False
        if val <= lo:
            return True
        return not up

    # -------------------------------------------------------- kreator geometrii
    def raw_test(self, leds):
        """Zapala diody po NUMERACH na tasmie, z pominieciem mapowania.
        Na tym opiera sie kreator geometrii w panelu: pyta, gdzie fizycznie
        zapalila sie dioda numer 0, i sam wylicza ustawienia."""
        self.busy = True
        b = self.s.get("brightness", 40)
        if b < 10:
            b = 10
        npx = self.m.np
        npx.fill((0, 0, 0))
        for item in leds:
            try:
                i = int(item.get("i", -1))
            except (ValueError, TypeError, AttributeError):
                continue
            if 0 <= i < self.m.n:
                r, g, bl = config.hex_to_rgb(item.get("c", "#ffffff"))
                npx[i] = (r * b // 100, g * b // 100, bl * b // 100)
        npx.write()
        self.activity()

    def raw_off(self):
        self.busy = False

    async def show_ip(self):
        """Pokazuje koncowke adresu IP na matrycy - na zadanie, 4 klikniecia.
        Dwa ostatnie czlony, bo sam ostatni nie mowi, w jakiej lampka jest sieci."""
        self.busy = True
        try:
            x0 = (self.m.w - 3) // 2
            y0 = (self.m.h - 5) // 2
            for ch in glyphs.ip_sequence(self.net.get("ip") or "-"):
                if ch == ".":
                    glyphs.draw_sep(self.m)
                    self.m.show()
                    await asyncio.sleep_ms(280)
                else:
                    self.m.clear()
                    glyphs.draw_char(self.m, ch, x0, y0, (0, 90, 255))
                    self.m.show()
                    await asyncio.sleep_ms(600)
                self.m.clear()
                self.m.show()
                await asyncio.sleep_ms(160)
        finally:
            self.busy = False

    async def button_loop(self, btn, on_wifi_reset=None):
        """Gesty:
             1 klik            wlacz / wylacz
             2 kliki           nastepny tryb
             3 kliki           poprzedni tryb
             4 kliki           pokaz koncowke IP na matrycy
             przytrzymanie     jasnosc (kierunek zmienia sie po kazdym puszczeniu)
             2 kliki + trzymanie   szybkosc animacji
             3 kliki + trzymanie 5 s   zapomnij WiFi i wroc do trybu AP
        """
        up_bright = True
        up_speed = True
        held = 0
        while True:
            ev = btn.poll()
            if ev:
                kind, n = ev
                self.activity()

                if kind == "click":
                    if n == 1:
                        self.toggle()
                    elif n == 2:
                        self.power(True)
                        self.next_anim()
                    elif n == 3:
                        self.power(True)
                        self.prev_anim()
                    elif n >= 4:
                        await self.show_ip()

                elif kind == "hold":
                    held += 1
                    if n >= 3:
                        # dopiero po ~5 s trzymania, zeby nie zrobic tego przypadkiem
                        if held * touch.HOLD_TICK_MS >= 5000:
                            held = 0
                            print("kasuje WiFi na zyczenie przycisku")
                            glyphs.flash(self.m, (90, 0, 0), 2)
                            if on_wifi_reset:
                                on_wifi_reset()
                    elif not self.s.get("on"):
                        pass                       # zgaszona lampka nie reaguje
                    elif n == 1:
                        self._ramp("brightness", up_bright, 4, 1, 100)
                        self.m.show()              # natychmiastowy podglad
                    elif n == 2:
                        self._ramp("speed", up_speed, 10, 10, 300)

                elif kind == "hold_end":
                    held = 0
                    if n == 1:
                        up_bright = self._flip(up_bright, self.s["brightness"], 1, 100)
                    elif n == 2:
                        up_speed = self._flip(up_speed, self.s["speed"], 10, 300)
                    config.mark()
            await asyncio.sleep_ms(20)

    async def save_loop(self):
        """Zapis ustawien na flash najwyzej raz na 5 s."""
        while True:
            await asyncio.sleep(5)
            config.flush()
