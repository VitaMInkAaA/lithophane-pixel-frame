# Lithophane Pixel Frame

A 3D-printed picture frame with a **7 × 9 WS2812 pixel matrix**, a capacitive touch
button and a self-hosted web panel — including a full **pixel-art animation editor**
that runs in your phone's browser. No cloud, no app, no external services: the
Raspberry Pi Pico W serves everything itself.

Draw frame by frame on your phone, apply effects, hit play, and the drawing appears
on the lamp in real time.

![MicroPython](https://img.shields.io/badge/MicroPython-1.20%2B-blue)
![Platform](https://img.shields.io/badge/platform-Raspberry%20Pi%20Pico%20W-informational)
![Dependencies](https://img.shields.io/badge/dependencies-none-success)
![License](https://img.shields.io/badge/license-CC%20BY--NC%204.0-lightgrey)

> 🇵🇱 Pełna dokumentacja po polsku: **[DOKUMENTACJA.md](DOKUMENTACJA.md)**

---

## Features

- **17 built-in modes** — fire, candle flame, aurora, plasma, rainbow, rainbow from
  the corner, snow, Matrix rain, sparkles, fireflies, trailing balls, bouncing cube,
  fireworks, beating heart, breathing, solid colour and a calibration pattern —
  all written for a portrait 7 × 9 grid
- **Pixel-art editor in the browser** — draw with your finger, flood fill,
  eyedropper, undo/redo, onion skin of the previous frame
- **Frame-by-frame animation** — per-frame duration, timeline with thumbnails,
  live preview on both the phone and the lamp
- **Effects** — brightness, invert, desaturate, saturate, contrast, tint;
  applied to one frame, a range, or the whole animation
- **Frame generators** — fade in/out, cross-fade, blink, auto-movement,
  ping-pong, reverse, speed up/down
- **Gallery** — save animations on the device, pick which ones the touch button
  cycles through
- **Touch control** — 1/2/3/4 clicks and press-and-hold ramps for brightness and speed
- **Zero-config networking** — connects to your Wi-Fi, falls back to its own
  access point with a captive portal, reachable at `lampka.local`
- **Auto-off timer**, on-device event log, and a self-healing HTTP listener
- **No external libraries.** Everything runs on stock MicroPython.

---

## Bill of materials

| # | Part | Qty | Notes |
|---|---|---|---|
| 1 | **Raspberry Pi Pico W** | 1 | Wi-Fi is required. Pico 2 W works too. Plain Pico won't — no radio. |
| 2 | **WS2812B LED strip** | 63 LEDs | Cut into segments and glued in a serpentine. 60 LEDs/m gives ~16.7 mm pitch → ~117 × 150 mm active area. |
| 3 | **TTP223 capacitive touch module** | 1 | Momentary mode (factory default). Latching mode will **not** work. |
| 4 | **5 V power supply** | 1 | ≥ 3 A for full brightness, 2 A is enough at the default 40 %. |
| 5 | **Schottky diode** | 1 | 1N5817 / SS14 / MBR120, ≥ 1 A. Lets you keep USB plugged in. |
| 6 | **Resistor 330 Ω** | 1 | In series with the data line, at the first LED. |
| 7 | **Capacitor 470–1000 µF** | 1 | ≥ 6.3 V, across 5 V and GND at the matrix input. |
| 8 | **Wire** | — | AWG 20 (0.5 mm²) for power, AWG 24–26 for data. |
| 9 | **3D-printed enclosure** | 3 parts | STL files in [`cad/`](cad/) — main case, back cover, Pico cover. |
| 10 | **Lithophane panel** | 1 | Printed from your own photo, see below. |

Optional: a **74AHCT125** level shifter if the LEDs misbehave on 3.3 V data
(see [Troubleshooting](#troubleshooting)).

---

## 3D-printed parts

Everything for the enclosure lives in **[`cad/`](cad/)**:

| File | What it is |
|---|---|
| `stl/case-main.stl` | Main enclosure — holds the matrix and the electronics |
| `stl/cover.stl` | Back cover |
| `stl/cover-pico.stl` | Cover over the Pico |

Printed flat, the parts need no supports. Material and colour are up to you — light
passes through the lithophane, not through the enclosure.

The **lithophane panel itself is not in the repository** — you generate it from your
own photo, as described below.

---

## The lithophane panel

The frame is built for a **portrait photo in 3:4 proportion** — straight out of an
iPhone, or any image with the same aspect ratio. A landscape or square photo will not
fit the frame; crop it to portrait 3:4 first.

Generate the model with **[itslitho](https://tool.itslitho.com/CreateModel)** using
these settings:

| Section | Setting | Value |
|---|---|---|
| **Shape** | Shape | `Arc` |
| | Height | `150 mm` |
| | Width | *auto* (≈ 109.5 mm — derived from the photo's aspect ratio) |
| | Angle | `50°` |
| | Min thick | `0.8 mm` |
| | Max thick | `3.2 mm` |
| | Crop / Inside | off |
| **Frame** | Frame | `Frame` |
| | Thickness | `3 mm` |
| | Depth | `4 mm` |
| | Angle | `45°` |
| | Advanced | off |
| **Quality** | mm per pixel | `0.1 mm` |
| | Preview model | `Low` |
| **Attributes** | Enable lamp / Close bottom / Nightlight | all off |
| **Model** | Lighting | `Back lighted` |
| | Light intensity | `5 – 95 %` |
| | Auto update / Cura fix | on |
| **Image** | Positive image | on |
| | Flip / Mirror image | off |
| | Placement horizontal / vertical | `50 % / 50 %` |
| | Zoom factor | `100 %` |

Notes:

- **Min 0.8 mm / max 3.2 mm** is what makes the image readable when backlit — thin
  spots let light through, thick ones block it. Thinner than 0.8 mm becomes fragile
  and prints badly.
- `Back lighted` matters: the tool inverts the depth map for a panel lit from behind,
  which is exactly how the LED matrix sits.
- At `0.1 mm per pixel` the exported STL is around **165 MB**. That is normal for a
  lithophane — slicing it takes a while.
- Print in **white or natural PLA**, no supports needed for the arc shape. The curve
  is deliberate: it keeps the panel away from the LEDs so individual pixels blur into
  an even glow instead of showing as dots.

---

## Wiring

| Signal | Pico W pin | Notes |
|---|---|---|
| Matrix `DIN` | **GP0** — pin 1 | Through the 330 Ω resistor |
| TTP223 `OUT` | **GP2** — pin 4 | |
| TTP223 `VCC` | **3V3(OUT)** — pin 36 | **Not 5 V** — Pico GPIO is not 5 V tolerant |
| Common ground | **GND** — pin 38 | Supply, Pico and matrix must share ground |
| Pico power | **VSYS** — pin 39 | Via the Schottky diode |
| Matrix power | Straight from the PSU | Separate pair of wires |

```
                    ┌──────────── (thick pair) ──────► matrix  5V / GND
   5 V PSU ─────────┤
                    └── ►|── VSYS (pin 39)     ┌── 470–1000 µF across 5V/GND
                      Schottky                 │   at the matrix input
                                               │
   Pico GP0 ──[ 330 Ω ]──────────────────────► DIN (first LED)
   Pico GND ─────────────────────────────────► GND  (shared!)
```

### Power notes

- **Never feed 5 V into `VBUS` (pin 40)** — it is wired directly to the USB
  connector and would back-feed your computer's port.
- **Never feed 5 V into `3V3(OUT)` (pin 36)** — that pin is an output and 5 V kills it.
- With the Schottky diode on `VSYS` you can keep USB connected while the external
  supply is on — the two sources can't fight each other.
- Wire the power in a **star** from the PSU. Don't daisy-chain the Pico behind the
  matrix: several amps of pulsing current through a thin wire cause voltage dips
  that reset the Pico mid-animation.
- 63 LEDs at full white draw ≈ **3.8 A**. The web panel shows the estimated draw
  next to the brightness slider.

### Matrix geometry

The firmware ships configured for a strip that **starts in the bottom-right corner**
(viewed from the front), runs **upwards**, turns around and comes back down — i.e.
serpentine columns of 9.

If yours is soldered differently, don't guess: open **Settings → Matrix geometry →
Wizard** in the panel. It lights individual LEDs *by strip index* (bypassing the
mapping entirely), asks two questions about what you see, and derives the correct
settings itself.

---

## Installation

You need MicroPython for **Pico W**. The `neopixel` and `network` modules ship with
the firmware — there is nothing to install.

Everything under [`firmware/`](firmware/) goes onto the device, keeping the same
layout — `.py` files in the device root, the panel in a `www` folder:

```bash
cd firmware
mpremote connect auto fs mkdir :www
mpremote connect auto fs cp *.py :
mpremote connect auto fs cp www/index.html www/style.css www/app.js :www/
mpremote connect auto reset
```

Using Thonny: copy the contents of `firmware/` to the device, preserving the `www`
subfolder.

Nothing outside `firmware/` belongs on the Pico — `cad/` holds the printable models.

---

## First run

With no Wi-Fi credentials stored, the lamp creates its own network:

- **SSID:** `LED-Lampka` · **password:** `ledlampka`
- **Panel:** <http://192.168.4.1/>

Connect your phone — on most devices the panel opens by itself (captive portal).
Go to the **WiFi** tab, pick your network, enter the password. The lamp connects
**immediately, without rebooting**, and shows the result. If it fails, it tells you
*why* (`wrong password`, `network not visible`, …), keeps its own access point alive,
and stays reachable so you can fix the password on the spot.

### Finding the lamp afterwards

| Method | Address |
|---|---|
| Hostname (mDNS) | <http://lampka.local/> |
| Its own access point | <http://192.168.4.1/> |
| The matrix tells you | last two octets of the IP, digit by digit |

The matrix shows **two** octets rather than one on purpose: a router may put the
lamp on a different subnet than your phone, and a lone `144` would send you to the
wrong address.

---

## Touch control

| Gesture | Action |
|---|---|
| **1 click** | On / off |
| **2 clicks** | Next mode |
| **3 clicks** | Previous mode |
| **4 clicks** | Show IP on the matrix |
| **Press and hold** | Brightness ramp — release and hold again to reverse direction |
| **2 clicks + hold** | Animation speed, same alternating ramp |
| **3 clicks + hold 5 s** | Forget Wi-Fi and return to access-point mode |

A single click reacts after ~0.35 s — that is the window for a second click, without
which one and two clicks cannot be told apart. Wiping the Wi-Fi credentials
deliberately requires three clicks *and* a long hold, so a plain long press (which
controls brightness) can never erase your network by accident.

If your TTP223 has inverted logic (jumper), flip it in **Settings → Button** —
no rewiring needed.

---

## Web panel

**Modes** — brightness, speed, colour, mode grid. The colour tile greys out and
locks in modes that paint their own colours.

**Editor** — a full pixel-art tool:

- 7 × 9 grid mapped 1:1 to the frame, brush + palette, flood fill, eyedropper,
  eraser, undo/redo (40 steps), onion skin of the previous frame
- Frame strip with thumbnails; add, duplicate, reorder, delete, wipe all
- Per-frame duration in milliseconds
- **Effects** applied to *this frame / from here on / all frames*: brightness
  0–200 %, invert, desaturate, saturate, contrast, tint with the brush colour
- **Transforms**: shift in four directions (wrapping), mirror, rotate 180°
- **Generators**: fade in/out, cross-fade to the next frame, blink, auto-movement,
  ping-pong, reverse, ×2 faster/slower
- **Preview** plays on the phone grid and on the lamp at once; stop restores both
  the frame you were editing and what the lamp was showing before

**Gallery** — saved animations with thumbnails, plus a checklist deciding which
modes the touch button cycles through.

**Settings** — auto-off timer, hostname, access-point behaviour, matrix geometry
wizard, button logic, diagnostics.

**WiFi** — status, every address the lamp answers on, network scan, country code.

### Why the effects don't slow the lamp down

All image processing happens **in the browser** and is baked into pixels. The Pico
receives finished frames and does exactly what it does for a static image: one
189-byte `blit()` per frame. You can stack as many effects as you like — the cost on
the device never changes.

Limits that protect the device: **40 frames** per animation, **24 animations** in the
gallery, frame duration **40–10000 ms**, and a **64 kB** cap on request bodies.
Only the currently playing animation is held in RAM.

---

## Writing your own animation

Add a class to `animations.py` and register it in `ANIMS` — the panel picks it up
automatically:

```python
class MyAnimation(Anim):
    name = "mine"            # ASCII id used by the API
    label = "My animation"   # shown in the panel
    interval = 60            # ms between steps at 100 % speed
    uses_color = False       # True if it uses the colour picked in the panel

    def step(self):
        m = self.m
        m.clear()
        m.set(3, 4, 255, 0, 0)   # x, y, r, g, b — (0,0) is the top-left corner
```

Do not call `m.show()` or `time.sleep()` — the render loop in `lamp.py` handles both,
which is why brightness and speed work globally for every effect. Available helpers:
`clear()`, `fill()`, `set()`, `setc()`, `get()`, `add()`, `fade()`, `scale()`,
`blit()`, plus `m.w` and `m.h`.

---

## Project structure

```
firmware/            everything that goes onto the Pico
├── main.py          startup: Wi-Fi, boot signals, task launch
├── config.py        pins, matrix size, settings + settings.json
├── led_matrix.py    Matrix class: one NeoPixel object, serpentine mapping, brightness
├── animations.py    all animations (Anim base class + ANIMS registry)
├── lamp.py          lamp state, render loop, auto-off, gesture handling
├── touch.py         TTP223: click counting and press-and-hold
├── netmgr.py        Wi-Fi connect, access point, scan, reconnect watchdog
├── webserver.py     HTTP server + REST API (uasyncio, no external libraries)
├── dns.py           DNS responder for the captive portal
├── frames.py        gallery of saved animations (anims/ directory)
├── glyphs.py        3 × 5 font for showing the IP on the matrix
├── logger.py        event log: serial always, log.txt optionally
└── www/             panel: index.html, style.css, app.js
cad/                 enclosure: STL files, ready to print
```

`settings.json`, `anims/` and `log.txt` are created on the device at runtime, which
is why they are in `.gitignore`.

---

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| Animations look shredded or move the wrong way | Wrong geometry — run **Settings → Geometry → Wizard** |
| Random flicker, wrong colours | Power. Check the capacitor, common ground and wire gauge. If it persists, add a 74AHCT125 level shifter on the data line |
| Pico resets on bright animations | PSU too weak, or the Pico is daisy-chained behind the matrix — wire in a star |
| Lamp has an IP but the panel won't open | See below |
| `lampka.local` doesn't resolve | Your firmware lacks the mDNS responder, or the client doesn't support it. Use the IP or the access point |
| Phone can't reach it while the computer can | Compare subnets, and check for client isolation on the router |

### If the panel stops responding after hours of uptime

Three known causes, all addressed in the firmware:

1. **Wi-Fi power saving.** The CYW43 sleeps the receiver between frames and drops
   inbound packets — the lamp looks connected but is unreachable. Disabled by default.
2. **No reconnect.** After a router restart or lease expiry the lamp used to stay
   offline forever. A watchdog now checks every 20 s and reconnects.
3. **The HTTP listener dying.** In uasyncio the accept loop is an ordinary task; if
   it raises, it dies silently while animations keep running. A supervisor probes
   the port every 2 minutes and restarts the listener — no reboot, no interruption.

Enable **Settings → Diagnostics** to write events to `log.txt` on the device. Read it
with `mpremote connect auto fs cat :log.txt`, in the panel, or over serial. Each entry
is stamped with uptime, because the Pico has no battery-backed clock. The periodic
status line tells the three causes apart:

```
02:35:11  RAM 138912 B | polaczenia otwarte 0 | obsluzonych 214
```

Falling RAM means a leak; a rising open-connection count means sockets aren't being
released; a frozen served counter means requests aren't arriving at all.

More detail — including every failure mode and the reasoning behind each fix — is in
**[DOKUMENTACJA.md](DOKUMENTACJA.md)**.

---

## Development

The firmware is plain Python, so most of it runs on a desktop. The test suites
replace `machine`, `neopixel` and `network` with stubs that **validate** instead of
merely pretending — the NeoPixel stub raises if a channel leaves 0–255 or an index
falls outside the matrix, so running the animations through it catches real bugs.

- `asyncio.start_server` works on CPython, so the HTTP and DNS servers are tested
  over **real sockets** with real requests
- The button tests drive a **controlled clock**, making a 5-second hold deterministic
- The browser tests extract functions **verbatim from `firmware/www/app.js`** and run them in
  Node, so they exercise the shipped code rather than a copy

What the tests cannot prove: LED timing, current draw, real Wi-Fi behaviour, RAM
pressure and speed on a 133 MHz target, or how anything actually looks. Those need
the hardware.

---

## License

**[CC BY-NC 4.0](LICENSE)** — Creative Commons Attribution-NonCommercial 4.0
International.

Build it for yourself, modify it, publish your version with credit, use it in
workshops and education. **Selling assembled lamps, kits or printed panels requires
written permission** from the copyright holder.

Note that CC BY-NC is deliberately *not* an OSI-approved open-source license — the
non-commercial restriction is the point. Third-party components (MicroPython, the
Pico W SDK, external tools referenced here) keep their own licenses.
