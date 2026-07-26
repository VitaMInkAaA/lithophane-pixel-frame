# Obsluga przycisku dotykowego TTP223 na GP2 (modul zasilany z 3V3 Pico).
#
# Rozpoznaje serie klikniec i przytrzymanie na koncu serii:
#   ("click", n)     - n klikniec, zglaszane po uplywie okna serii
#   ("hold",  n)     - trzymanie po n-tym nacisnieciu, powtarzane co HOLD_TICK_MS
#   ("hold_end", n)  - puszczenie po trzymaniu (raz)
#
# TTP223 w konfiguracji fabrycznej daje stan WYSOKI na czas dotyku. Jesli Twoj
# modul ma zwarta zworke odwracajaca logike, ustaw btn_active_high na false
# w panelu (zakladka Ustawienia) - nie trzeba nic przelutowywac.
from machine import Pin
from time import ticks_ms, ticks_diff

import config

DEBOUNCE_MS = 25       # ignorowanie drgan styku
CLICK_WINDOW_MS = 350  # ile czekamy na kolejne klikniecie w serii
HOLD_MS = 500          # od kiedy uznajemy, ze to przytrzymanie
HOLD_TICK_MS = 110     # co ile powtarzac zdarzenie podczas trzymania
MAX_CLICKS = 6


class Touch:
    def __init__(self, pin=config.BUTTON_PIN, active_high=True):
        self.active_high = active_high
        pull = Pin.PULL_DOWN if active_high else Pin.PULL_UP
        self.pin = Pin(pin, Pin.IN, pull)
        self.clicks = 0
        self.holding = False
        now = ticks_ms()
        # stan poczatkowy czytamy z pinu, zeby dotyk trzymany w chwili startu
        # nie zglosil sie jako klikniecie
        self.down = self.touched()
        self._raw = self.down
        self.t_raw = now
        self.t_press = now
        self.t_release = now
        self.t_hold = now

    def touched(self):
        v = self.pin.value()
        return bool(v) if self.active_high else not v

    def poll(self):
        now = ticks_ms()
        v = self.touched()

        # --- zmiana stanu ----------------------------------------------------
        # Nowy poziom musi utrzymac sie przez DEBOUNCE_MS, zeby zostal uznany.
        # Krotsza szpilka (drgania, zaklocenie na przewodzie do elektrody)
        # tylko przestawia licznik i nic nie zglasza.
        if v != self._raw:
            self._raw = v
            self.t_raw = now
        elif v != self.down and ticks_diff(now, self.t_raw) >= DEBOUNCE_MS:
            self.down = v
            if v:
                self.t_press = now
                if self.clicks < MAX_CLICKS:
                    self.clicks += 1
            else:
                if self.holding:
                    self.holding = False
                    n = self.clicks
                    self.clicks = 0
                    return ("hold_end", n)
                self.t_release = now
            return 0

        # --- trzymanie -------------------------------------------------------
        if self.down:
            if not self.holding:
                if ticks_diff(now, self.t_press) >= HOLD_MS:
                    self.holding = True
                    self.t_hold = now
                    return ("hold", self.clicks)
            elif ticks_diff(now, self.t_hold) >= HOLD_TICK_MS:
                self.t_hold = now
                return ("hold", self.clicks)
            return 0

        # --- koniec serii klikniec -------------------------------------------
        if self.clicks and ticks_diff(now, self.t_release) >= CLICK_WINDOW_MS:
            n = self.clicks
            self.clicks = 0
            return ("click", n)
        return 0
