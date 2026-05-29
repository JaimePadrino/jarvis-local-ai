import tkinter as tk
from tkinter import filedialog
import threading
import sys
import os
import time
from datetime import datetime
import requests
import math
import json

# 🔧 arreglar imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import main
from voice.speak import speak, get_speaking, set_tts_listeners


class JarvisGUI:

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("J.A.R.V.I.S")
        self.root.geometry("1200x720")
        self.root.minsize(980, 640)
        self._fullscreen = False
        self.root.bind("<F11>", self._toggle_fullscreen)
        self.root.bind("<Escape>", self._exit_fullscreen)

        # Theme (approx from screenshot)
        # Darker blue palette
        self.COL_BG = "#050a12"
        self.COL_PANEL = "#071320"
        self.COL_PANEL_2 = "#06101c"
        self.COL_BORDER = "#15344a"
        self.COL_TEXT = "#d6e6ff"
        self.COL_MUTED = "#7aa4c7"
        self.COL_CYAN = "#35d6ff"
        self.COL_CYAN_2 = "#11b0ff"
        self.COL_GREEN = "#42d392"
        self.COL_DANGER = "#ff5b6b"

        # Typography (bigger by default)
        self.FT_H1 = ("Segoe UI", 17, "bold")
        self.FT_H2 = ("Segoe UI", 13, "bold")
        self.FT_BODY = ("Segoe UI", 13)
        self.FT_BODY_B = ("Segoe UI", 13, "bold")
        self.FT_SMALL = ("Segoe UI", 11)

        self.root.configure(bg=self.COL_BG)

        # Grid layout: top bar + 3 columns
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(0, weight=0, minsize=310)
        self.root.grid_columnconfigure(1, weight=1, minsize=360)
        self.root.grid_columnconfigure(2, weight=1, minsize=360)

        self._voice_threads_started = False
        self._anim_phase = 0
        self._uptime_start = time.time()
        self._weather_cache = ""
        self._weather_last_fetch = 0.0
        self._weather_details = {
            "temp": "—",
            "location": "Madrid",
            "desc": "—",
            "humidity": "—",
            "wind": "—",
            "feelslike": "—",
        }
        self._eq_energy = 0.0
        self._did_greet = False
        # Core rendering cache (avoid full redraw every frame)
        self._core_static_key = None
        self._arc_main = None
        self._arc_soft = None
        self._guide_ring = None
        self._bars = []
        self._caps = []
        self._bar_count = 28
        self._bar_base_r = 0.0
        self._bar_inner = 0.0

        self._build_topbar()
        self._build_left()
        self._build_center()
        self._build_right()

        # Surface TTS errors in the UI (useful when running hidden via .vbs)
        set_tts_listeners(
            on_error=lambda msg: self.root.after(
                0, lambda: self.add_message("Jarvis", f"(Audio) No puedo hablar ahora: {msg}")
            )
        )

        self._tick_clock()
        self._tick_stats()
        self._animate_core()
        self._tick_weather_async()

        # Voice always on by default
        self.root.after(250, self.start_backend)
        self.root.after(500, self._startup_greeting)

    def on_toggle_voice_backend(self):
        if self.voice_backend_enabled.get():
            self.start_backend()

    # 🧠 BACKEND VOZ
    def start_backend(self):
        if self._voice_threads_started:
            return

        # import aquí para que la GUI no arranque voz por defecto
        # wire callbacks so voice + typed land in same chat
        main.set_callbacks(
            on_user=lambda t: self.root.after(0, lambda: self.add_message("You", t)),
            on_jarvis=lambda t: self.root.after(0, lambda: self.add_message("Jarvis", t)),
            on_status=lambda s: self.root.after(0, lambda: self._set_status(s, online=True)),
        )

        threading.Thread(target=main.wake_listener, daemon=True).start()
        threading.Thread(target=main.conversation_loop, daemon=True).start()
        self._voice_threads_started = True
        self._set_status("Listening for wake word…", online=True)

    # 🧠 enviar mensaje
    def send_message(self, event=None):
        msg = self.entry.get().strip()
        if not msg:
            return

        self.entry.delete(0, tk.END)

        # Use the same pipeline as voice (and let callbacks populate chat)
        if not self._voice_threads_started:
            main.set_callbacks(
                on_user=lambda t: self.root.after(0, lambda: self.add_message("You", t)),
                on_jarvis=lambda t: self.root.after(0, lambda: self.add_message("Jarvis", t)),
                on_status=lambda s: self.root.after(
                    0, lambda: self._set_status(s, online=self._voice_threads_started)
                ),
            )

        self._set_status("Processing…", online=self._voice_threads_started)
        threading.Thread(target=self.process_message, args=(msg,), daemon=True).start()

    # 🧠 lógica Jarvis
    def process_message(self, msg):
        try:
            response = main.handle_user_input(msg, speak_response=True)
        except Exception as e:
            response = f"Ha ocurrido un error al consultar la IA: {e}"

        self.root.after(0, lambda: self._set_status("Idle", online=self._voice_threads_started))
        # TTS already handled in pipeline; avoid double-speaking

    def add_message(self, author, content):
        # Use Text widget with tags for simple "bubble" styling
        self.conv_text.config(state=tk.NORMAL)
        timestamp = datetime.now().strftime("%H:%M")

        if author.lower() in ["you", "usuario", "tú", "tu"]:
            tag = "you"
            header = f"You  •  {timestamp}\n"
        else:
            tag = "jarvis"
            header = f"JARVIS  •  {timestamp}\n"

        self.conv_text.insert(tk.END, header, ("hdr", tag))
        self.conv_text.insert(tk.END, f"{content}\n\n", ("msg", tag))
        self.conv_text.see(tk.END)
        self.conv_text.config(state=tk.DISABLED)

    # 🚀 run correcto
    def run(self):
        self.root.mainloop()

    # ---------- UI BUILDERS ----------
    def _build_topbar(self):
        self.top = tk.Frame(self.root, bg=self.COL_BG)
        self.top.grid(row=0, column=0, columnspan=3, sticky="ew", padx=18, pady=(14, 10))
        self.top.grid_columnconfigure(1, weight=1)

        left = tk.Frame(self.top, bg=self.COL_BG)
        left.grid(row=0, column=0, sticky="w")

        tk.Label(
            left, text="J.A.R.V.I.S", bg=self.COL_BG, fg=self.COL_TEXT,
            font=self.FT_H1
        ).grid(row=0, column=0, sticky="w")

        self.status_pill = tk.Label(
            left, text=" Offline ", bg="#0f2432", fg=self.COL_MUTED,
            font=("Segoe UI", 10, "bold"), bd=1, relief="solid"
        )
        self.status_pill.grid(row=0, column=1, padx=(12, 0), sticky="w")

        self.clock_lbl = tk.Label(
            self.top, text="", bg=self.COL_BG, fg=self.COL_TEXT,
            font=self.FT_SMALL
        )
        self.clock_lbl.grid(row=0, column=1, sticky="n")

        right = tk.Frame(self.top, bg=self.COL_BG)
        right.grid(row=0, column=2, sticky="e")

        self.weather_chip = tk.Label(
            right, text="—  •  Weather", bg="#0f2432", fg=self.COL_TEXT,
            font=self.FT_SMALL, bd=1, relief="solid", padx=10, pady=4
        )
        self.weather_chip.grid(row=0, column=0, padx=(0, 10))

        self.fullscreen_btn = tk.Button(
            right, text="Fullscreen", command=self._toggle_fullscreen,
            bg="#0f2432", fg=self.COL_TEXT, activebackground="#132b3d",
            activeforeground=self.COL_TEXT, bd=1, relief="solid", padx=10, pady=4,
            font=self.FT_SMALL
        )
        self.fullscreen_btn.grid(row=0, column=1)

    def _build_left(self):
        self.left = tk.Frame(self.root, bg=self.COL_BG)
        self.left.grid(row=1, column=0, sticky="nsw", padx=(18, 10), pady=(0, 18))
        # Keep uptime pinned to bottom: insert spacer that expands
        self.left.grid_rowconfigure(3, weight=1)

        self.card_stats = self._card(self.left, "System Stats", row=0)
        self._stats_rows(self.card_stats)

        self.card_weather = self._card(self.left, "Weather", row=1)
        self._weather_rows(self.card_weather)

        self.card_camera = self._card(self.left, "Camera", row=2)
        self._camera_rows(self.card_camera)

        # spacer
        tk.Frame(self.left, bg=self.COL_BG).grid(row=3, column=0, sticky="nsew")

        self.card_uptime = self._card(self.left, "System Uptime", row=4)
        self._uptime_rows(self.card_uptime)

    def _build_center(self):
        self.center = tk.Frame(self.root, bg=self.COL_BG)
        self.center.grid(row=1, column=1, sticky="nsew", padx=10, pady=(0, 18))
        self.center.grid_rowconfigure(0, weight=1)
        self.center.grid_columnconfigure(0, weight=1)

        # Core canvas
        self.core_wrap = tk.Frame(self.center, bg=self.COL_BG)
        self.core_wrap.grid(row=0, column=0, sticky="nsew")
        self.core_wrap.grid_rowconfigure(0, weight=1)
        self.core_wrap.grid_columnconfigure(0, weight=1)

        self.core_canvas = tk.Canvas(
            self.core_wrap, bg=self.COL_BG, highlightthickness=0
        )
        self.core_canvas.grid(row=0, column=0, sticky="nsew")
        self.core_canvas.bind("<Configure>", lambda e: self._draw_core_static(force=True))

        # Core labels (under the circle)
        self.core_label = tk.Label(
            self.core_wrap, text="J.A.R.V.I.S", bg=self.COL_BG, fg=self.COL_TEXT,
            font=("Segoe UI", 16, "bold")
        )
        self.core_label.place(relx=0.5, rely=0.72, anchor="center")

        self.core_status = tk.Label(
            self.core_wrap, text="Offline", bg=self.COL_BG, fg=self.COL_MUTED,
            font=self.FT_BODY
        )
        self.core_status.place(relx=0.5, rely=0.78, anchor="center")

        # Removed bottom icon buttons (per request)

    def _build_right(self):
        self.right = tk.Frame(self.root, bg=self.COL_BG)
        self.right.grid(row=1, column=2, sticky="nsew", padx=(10, 18), pady=(0, 18))
        self.right.grid_rowconfigure(1, weight=1)
        self.right.grid_columnconfigure(0, weight=1)

        header = tk.Frame(self.right, bg=self.COL_BG)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        header.grid_columnconfigure(0, weight=1)

        tk.Label(
            header, text="Conversation", bg=self.COL_BG, fg=self.COL_TEXT,
            font=("Segoe UI", 13, "bold")
        ).grid(row=0, column=0, sticky="w")

        btns = tk.Frame(header, bg=self.COL_BG)
        btns.grid(row=0, column=1, sticky="e")
        tk.Button(
            btns, text="Clear", command=self._clear_conversation,
            bg="#0f2432", fg=self.COL_TEXT, bd=1, relief="solid", padx=10, pady=3
        ).grid(row=0, column=0, padx=(0, 8))
        tk.Button(
            btns, text="Extract Conversation", command=self._export_conversation,
            bg="#0f2432", fg=self.COL_TEXT, bd=1, relief="solid", padx=10, pady=3
        ).grid(row=0, column=1)

        # Conversation panel (rounded)
        self.conv_panel_outer, self.conv_panel = self._rounded_panel(
            self.right, radius=18, padding=0, bg=self.COL_PANEL, border=self.COL_BORDER, border_w=1
        )
        self.conv_panel_outer.grid(row=1, column=0, sticky="nsew")
        self.conv_panel_outer.grid_rowconfigure(0, weight=1)
        self.conv_panel_outer.grid_columnconfigure(0, weight=1)

        self.conv_panel.grid_rowconfigure(0, weight=1)
        self.conv_panel.grid_columnconfigure(0, weight=1)

        self.conv_scroll = tk.Scrollbar(self.conv_panel, troughcolor=self.COL_PANEL, bg=self.COL_PANEL_2, bd=0)
        self.conv_scroll.grid(row=0, column=1, sticky="ns")

        self.conv_text = tk.Text(
            self.conv_panel,
            bg=self.COL_PANEL,
            fg=self.COL_TEXT,
            insertbackground=self.COL_CYAN,
            relief="flat",
            wrap="word",
            font=self.FT_BODY,
            padx=16,
            pady=14,
            yscrollcommand=self.conv_scroll.set
        )
        self.conv_text.grid(row=0, column=0, sticky="nsew")
        self.conv_scroll.config(command=self.conv_text.yview)
        self.conv_text.config(state=tk.DISABLED)

        # Tags
        self.conv_text.tag_configure("hdr", foreground=self.COL_MUTED, spacing1=6, spacing3=2)
        self.conv_text.tag_configure("msg", spacing3=10)
        self.conv_text.tag_configure("jarvis", foreground=self.COL_TEXT)
        self.conv_text.tag_configure("you", foreground="#eaf3ff")

        # Input bar
        input_bar = tk.Frame(self.right, bg=self.COL_BG)
        input_bar.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        input_bar.grid_columnconfigure(0, weight=1)

        self.entry = tk.Entry(
            input_bar,
            bg=self.COL_PANEL_2,
            fg=self.COL_TEXT,
            insertbackground=self.COL_CYAN,
            font=self.FT_BODY,
            relief="solid",
            bd=1
        )
        self.entry.grid(row=0, column=0, sticky="ew", padx=(0, 10), ipady=7)
        self.entry.bind("<Return>", self.send_message)

        self.btn_send = tk.Button(
            input_bar,
            text="➤",
            command=self.send_message,
            bg=self.COL_CYAN_2,
            fg="#001018",
            activebackground=self.COL_CYAN,
            activeforeground="#001018",
            bd=0,
            padx=16,
            pady=8
        )
        self.btn_send.grid(row=0, column=1)

    # ---------- UI PIECES ----------
    def _rounded_rect(self, canvas, x1, y1, x2, y2, r, **kwargs):
        # Draw rounded rectangle using polygon smoothing
        points = [
            x1 + r, y1,
            x2 - r, y1,
            x2, y1,
            x2, y1 + r,
            x2, y2 - r,
            x2, y2,
            x2 - r, y2,
            x1 + r, y2,
            x1, y2,
            x1, y2 - r,
            x1, y1 + r,
            x1, y1,
        ]
        return canvas.create_polygon(points, smooth=True, **kwargs)

    def _rounded_panel(self, parent, radius=16, padding=12, bg=None, border=None, border_w=1):
        """
        Canvas-based rounded container + inner Frame.
        Returns (outer_frame, inner_frame)
        """
        bg = bg or self.COL_PANEL
        border = border or self.COL_BORDER

        outer = tk.Frame(parent, bg=self.COL_BG)
        canvas = tk.Canvas(outer, bg=self.COL_BG, highlightthickness=0)
        canvas.pack(fill="both", expand=True)

        inner = tk.Frame(canvas, bg=bg)
        win = canvas.create_window(padding, padding, anchor="nw", window=inner)

        def _redraw(_evt=None):
            w = canvas.winfo_width()
            h = canvas.winfo_height()
            if w < 2 or h < 2:
                return
            canvas.delete("bg")
            # premium-ish border: outer stroke + inner highlight
            self._rounded_rect(canvas, 0, 0, w, h, radius, fill=bg, outline=border, width=border_w, tags="bg")
            hi = self._blend(self.COL_TEXT, bg, 0.08)
            self._rounded_rect(
                canvas, 1, 1, w - 1, h - 1, max(2, radius - 1),
                fill="", outline=hi, width=1, tags="bg"
            )
            canvas.coords(win, padding, padding)
            inner_w = max(0, w - padding * 2)
            inner_h = max(0, h - padding * 2)
            canvas.itemconfigure(win, width=inner_w, height=inner_h)

        canvas.bind("<Configure>", _redraw)
        return outer, inner

    def _card(self, parent, title, row):
        wrap, inner = self._rounded_panel(parent, radius=18, padding=12, bg=self.COL_PANEL, border=self.COL_BORDER, border_w=1)
        wrap.grid(row=row, column=0, sticky="ew", pady=10)
        wrap.grid_columnconfigure(0, weight=1)
        wrap.grid_propagate(False)

        inner.grid_columnconfigure(0, weight=1)

        head = tk.Frame(inner, bg=self.COL_PANEL)
        head.grid(row=0, column=0, sticky="ew", pady=(2, 8))
        head.grid_columnconfigure(0, weight=1)

        tk.Label(head, text=title, bg=self.COL_PANEL, fg=self.COL_TEXT, font=self.FT_H2).grid(
            row=0, column=0, sticky="w"
        )
        tk.Label(head, text="⚙", bg=self.COL_PANEL, fg=self.COL_MUTED, font=self.FT_BODY).grid(
            row=0, column=1, sticky="e"
        )

        body = tk.Frame(inner, bg=self.COL_PANEL)
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)
        return body

    def _progress_row(self, parent, label, value_var):
        row = tk.Frame(parent, bg=self.COL_PANEL)
        row.pack(fill="x", pady=6)

        tk.Label(row, text=label, bg=self.COL_PANEL, fg=self.COL_MUTED, font=("Segoe UI", 9)).pack(side="left")
        tk.Label(row, textvariable=value_var, bg=self.COL_PANEL, fg=self.COL_TEXT, font=("Segoe UI", 9, "bold")).pack(
            side="right"
        )

        bar = tk.Canvas(parent, height=6, bg=self.COL_PANEL, highlightthickness=0)
        bar.pack(fill="x")
        return bar

    def _control_button(self, parent, text, cmd):
        return tk.Button(
            parent,
            text=text,
            command=cmd,
            bg="#0f2432",
            fg=self.COL_TEXT,
            activebackground="#132b3d",
            activeforeground=self.COL_TEXT,
            bd=1,
            relief="solid",
            width=4,
            height=2
        )

    # ---------- CONTENT / TICKS ----------
    def _tick_clock(self):
        now = datetime.now()
        self.clock_lbl.config(text=now.strftime("%I:%M:%S %p   |   %b %d, %Y"))
        self.root.after(500, self._tick_clock)

    def _tick_stats(self):
        cpu, ram_used, ram_total = self._get_system_stats()
        self.cpu_val.set(f"{cpu:.0f}%")
        self.ram_val.set(f"{ram_used:.1f} GB")
        self.disk_val.set(f"{self._get_disk_free_text()}")

        self._draw_progress(self.cpu_bar, cpu / 100.0)
        self._draw_progress(self.ram_bar, min(1.0, ram_used / max(0.1, ram_total)))

        # weather
        w = self._get_weather_text()
        if w:
            self.weather_main.set(w)
            self.weather_chip.config(text=w)

        # uptime
        up_s = int(time.time() - self._uptime_start)
        self.uptime_val.set(time.strftime("%H:%M:%S", time.gmtime(up_s)))

        self.root.after(3000, self._tick_stats)

    def _animate_core(self):
        self._anim_phase = (self._anim_phase + 1) % 360
        # Smooth energy envelope: rise quickly while speaking, decay slowly when not
        target = 1.0 if bool(get_speaking()) else 0.0
        if target > self._eq_energy:
            self._eq_energy += (target - self._eq_energy) * 0.28
        else:
            self._eq_energy += (target - self._eq_energy) * 0.10
        self._draw_core_dynamic()

        # save CPU: animate fast only when speaking/energized
        delay = 33 if self._eq_energy > 0.08 else 90
        self.root.after(delay, self._animate_core)

    def _draw_core_static(self, force=False):
        c = self.core_canvas
        w = c.winfo_width()
        h = c.winfo_height()
        if w < 10 or h < 10:
            return

        key = (w, h, self.COL_BG, self.COL_CYAN, self.COL_CYAN_2)
        if (not force) and self._core_static_key == key:
            return
        self._core_static_key = key

        c.delete("all")
        self._bars = []
        self._caps = []

        cx, cy = w // 2, int(h * 0.45)
        base = min(w, h) * 0.18

        # Outer rings (static)
        ring_layers = [
            (base * 1.75, 2, 0.14),
            (base * 1.55, 2, 0.18),
            (base * 1.35, 2, 0.24),
            (base * 1.15, 2, 0.32),
            (base * 0.98, 2, 0.45),
        ]
        for r, wpx, a in ring_layers:
            col = self._blend(self.COL_CYAN_2, self.COL_BG, a)
            c.create_oval(cx - r, cy - r, cx + r, cy + r, outline=col, width=wpx, tags=("core_static",))

        # Rotating arcs (dynamic objects)
        arc_r = base * 1.35
        self._arc_main = c.create_arc(
            cx - arc_r, cy - arc_r, cx + arc_r, cy + arc_r,
            start=0, extent=55,
            style="arc", outline=self.COL_CYAN_2, width=4, tags=("core_dyn",)
        )
        self._arc_soft = c.create_arc(
            cx - arc_r, cy - arc_r, cx + arc_r, cy + arc_r,
            start=120, extent=40,
            style="arc", outline=self._blend(self.COL_CYAN_2, self.COL_BG, 0.35), width=2, tags=("core_dyn",)
        )

        # Inner core
        inner = base * 0.55
        c.create_oval(
            cx - inner, cy - inner, cx + inner, cy + inner,
            outline=self.COL_CYAN, width=2, tags=("core_static",)
        )
        # Subtle inner ring
        c.create_oval(
            cx - inner * 0.72, cy - inner * 0.72, cx + inner * 0.72, cy + inner * 0.72,
            outline=self._blend(self.COL_CYAN_2, self.COL_BG, 0.5), width=1, tags=("core_static",)
        )

        # Dynamic guide ring + bars (created once)
        self._bar_inner = inner
        self._bar_base_r = inner * 0.78

        guide = self._blend(self.COL_CYAN_2, self.COL_BG, 0.25)
        br = self._bar_base_r
        self._guide_ring = c.create_oval(cx - br, cy - br, cx + br, cy + br, outline=guide, width=1, tags=("core_dyn",))

        for _i in range(self._bar_count):
            line_id = c.create_line(0, 0, 0, 0, fill=self.COL_CYAN, width=2, capstyle="round", tags=("core_dyn",))
            cap_id = c.create_oval(0, 0, 0, 0, fill=self.COL_CYAN, outline="", tags=("core_dyn",))
            self._bars.append(line_id)
            self._caps.append(cap_id)

    def _draw_core_dynamic(self):
        c = self.core_canvas
        w = c.winfo_width()
        h = c.winfo_height()
        if w < 10 or h < 10:
            return

        if self._core_static_key is None:
            self._draw_core_static(force=True)

        cx, cy = w // 2, int(h * 0.45)

        # Update arcs
        start = self._anim_phase
        if self._arc_main is not None:
            c.itemconfigure(self._arc_main, start=start)
        if self._arc_soft is not None:
            c.itemconfigure(self._arc_soft, start=(start + 120) % 360)

        # Update guide ring coords
        br = self._bar_base_r
        if self._guide_ring is not None:
            c.coords(self._guide_ring, cx - br, cy - br, cx + br, cy + br)

        # Update bars only (no delete/create)
        e = max(0.0, min(1.0, self._eq_energy))
        bars = self._bar_count
        inner = self._bar_inner
        base_r = self._bar_base_r
        t = (self._anim_phase * math.pi) / 180.0
        max_len = inner * (0.20 + 0.55 * e)

        for i in range(bars):
            ang = (i / bars) * (2 * math.pi) + t * 0.15
            w1 = 0.5 + 0.5 * math.sin(t * 2.6 + i * 0.55)
            w2 = 0.5 + 0.5 * math.sin(t * 4.2 + i * 0.92 + 1.7)
            amp = (0.10 + 0.90 * e)
            length = (inner * 0.05) + max_len * (0.35 * w1 + 0.65 * w2) * amp

            x1 = cx + math.cos(ang) * base_r
            y1 = cy + math.sin(ang) * base_r
            x2 = cx + math.cos(ang) * (base_r + length)
            y2 = cy + math.sin(ang) * (base_r + length)

            col = self.COL_CYAN_2 if e > 0.25 else self._blend(self.COL_CYAN, self.COL_BG, 0.65)
            width = 2 if e < 0.35 else 3

            c.coords(self._bars[i], x1, y1, x2, y2)
            c.itemconfigure(self._bars[i], fill=col, width=width)

            if e > 0.55 and i % 2 == 0:
                rr = 1.6 + 1.8 * w2
                c.coords(self._caps[i], x2 - rr, y2 - rr, x2 + rr, y2 + rr)
                c.itemconfigure(self._caps[i], state="normal", fill=col)
            else:
                c.itemconfigure(self._caps[i], state="hidden")

    def _set_status(self, text, online):
        self.core_status.config(text=text, fg=self.COL_GREEN if online else self.COL_MUTED)
        if online:
            self.status_pill.config(text=" Online ", fg=self.COL_GREEN, bg="#0f2432")
        else:
            self.status_pill.config(text=" Offline ", fg=self.COL_MUTED, bg="#0f2432")

    def _toggle_fullscreen(self, event=None):
        self._fullscreen = not self._fullscreen
        self.root.attributes("-fullscreen", self._fullscreen)
        self.fullscreen_btn.config(text="Windowed" if self._fullscreen else "Fullscreen")

    def _exit_fullscreen(self, event=None):
        if self._fullscreen:
            self._fullscreen = False
            self.root.attributes("-fullscreen", False)
            self.fullscreen_btn.config(text="Fullscreen")

    def _clear_conversation(self):
        self.conv_text.config(state=tk.NORMAL)
        self.conv_text.delete("1.0", tk.END)
        self.conv_text.config(state=tk.DISABLED)

    def _export_conversation(self):
        self.conv_text.config(state=tk.NORMAL)
        txt = self.conv_text.get("1.0", tk.END).strip()
        self.conv_text.config(state=tk.DISABLED)
        if not txt:
            return

        path = filedialog.asksaveasfilename(
            title="Save conversation",
            defaultextension=".txt",
            filetypes=[("Text file", "*.txt"), ("All files", "*.*")]
        )
        if not path:
            return

        with open(path, "w", encoding="utf-8") as f:
            f.write(txt)

    def _noop(self):
        pass

    # ---------- LEFT CARD CONTENT ----------
    def _stats_rows(self, parent):
        self.cpu_val = tk.StringVar(value="—")
        self.ram_val = tk.StringVar(value="—")
        self.disk_val = tk.StringVar(value="—")

        self.cpu_bar = self._progress_row(parent, "CPU Usage", self.cpu_val)
        self.ram_bar = self._progress_row(parent, "RAM Usage", self.ram_val)

        extra = tk.Frame(parent, bg=self.COL_PANEL)
        extra.pack(fill="x", pady=(10, 0))

        for label, var in [("CPU", self.cpu_val), ("Memory", self.ram_val), ("Disk", self.disk_val)]:
            box = tk.Frame(extra, bg=self.COL_PANEL)
            box.pack(side="left", expand=True, fill="x")
            tk.Label(box, text=label, bg=self.COL_PANEL, fg=self.COL_MUTED, font=("Segoe UI", 8)).pack()
            tk.Label(box, textvariable=var, bg=self.COL_PANEL, fg=self.COL_TEXT, font=("Segoe UI", 10, "bold")).pack()

    def _weather_rows(self, parent):
        self.weather_main = tk.StringVar(value="—")
        self.weather_location = tk.StringVar(value="Madrid")
        self.weather_desc = tk.StringVar(value="—")
        self.weather_humidity = tk.StringVar(value="—")
        self.weather_wind = tk.StringVar(value="—")
        self.weather_feels = tk.StringVar(value="—")

        top = tk.Frame(parent, bg=self.COL_PANEL)
        top.pack(fill="x")
        tk.Label(top, textvariable=self.weather_main, bg=self.COL_PANEL, fg=self.COL_TEXT, font=("Segoe UI", 16, "bold")).pack(
            anchor="w"
        )
        tk.Label(top, textvariable=self.weather_location, bg=self.COL_PANEL, fg=self.COL_MUTED, font=("Segoe UI", 9)).pack(anchor="w")
        tk.Label(top, textvariable=self.weather_desc, bg=self.COL_PANEL, fg=self.COL_MUTED, font=("Segoe UI", 9)).pack(anchor="w", pady=(2, 0))

        grid = tk.Frame(parent, bg=self.COL_PANEL)
        grid.pack(fill="x", pady=(10, 0))
        items = [
            ("Humedad", self.weather_humidity),
            ("Viento", self.weather_wind),
            ("Sensación", self.weather_feels),
        ]
        for i, (k, var) in enumerate(items):
            col = tk.Frame(grid, bg=self.COL_PANEL)
            col.grid(row=0, column=i, sticky="ew", padx=6)
            grid.grid_columnconfigure(i, weight=1)
            tk.Label(col, text=k, bg=self.COL_PANEL, fg=self.COL_MUTED, font=("Segoe UI", 8)).pack(anchor="w")
            tk.Label(col, textvariable=var, bg=self.COL_PANEL, fg=self.COL_TEXT, font=("Segoe UI", 10, "bold")).pack(anchor="w")

    def _camera_rows(self, parent):
        box = tk.Frame(parent, bg=self.COL_PANEL_2, bd=1, relief="solid")
        box.pack(fill="both", expand=True, ipady=40)
        tk.Label(box, text="Camera Off", bg=self.COL_PANEL_2, fg=self.COL_MUTED, font=("Segoe UI", 10, "bold")).pack(
            pady=(20, 4)
        )
        tk.Label(box, text="(placeholder)", bg=self.COL_PANEL_2, fg=self.COL_MUTED, font=("Segoe UI", 9)).pack()

    def _uptime_rows(self, parent):
        self.uptime_val = tk.StringVar(value="00:00:00")
        tk.Label(parent, text="System Running For", bg=self.COL_PANEL, fg=self.COL_MUTED, font=("Segoe UI", 9)).pack(
            anchor="w"
        )
        tk.Label(parent, textvariable=self.uptime_val, bg=self.COL_PANEL, fg=self.COL_TEXT, font=("Segoe UI", 18, "bold")).pack(
            anchor="w", pady=(6, 6)
        )
        grid = tk.Frame(parent, bg=self.COL_PANEL)
        grid.pack(fill="x", pady=(10, 0))
        for i, (k, v) in enumerate([("Sessions", "1"), ("Commands", "0")]):
            col = tk.Frame(grid, bg=self.COL_PANEL)
            col.grid(row=0, column=i, sticky="ew", padx=6)
            grid.grid_columnconfigure(i, weight=1)
            tk.Label(col, text=k, bg=self.COL_PANEL, fg=self.COL_MUTED, font=("Segoe UI", 8)).pack(anchor="w")
            tk.Label(col, text=v, bg=self.COL_PANEL, fg=self.COL_TEXT, font=("Segoe UI", 10, "bold")).pack(anchor="w")

    # ---------- UTIL ----------
    def _draw_progress(self, canvas, frac):
        canvas.delete("all")
        w = max(10, canvas.winfo_width())
        h = max(6, canvas.winfo_height())
        pad = 2
        canvas.create_rectangle(pad, pad, w - pad, h - pad, outline=self.COL_BORDER, width=1)
        fill_w = int((w - 2 * pad) * max(0.0, min(1.0, frac)))
        canvas.create_rectangle(pad + 1, pad + 1, pad + fill_w, h - pad - 1, outline="", fill=self.COL_CYAN_2)

    def _get_system_stats(self):
        try:
            import psutil  # type: ignore

            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory()
            ram_used = mem.used / (1024**3)
            ram_total = mem.total / (1024**3)
            return cpu, ram_used, ram_total
        except Exception:
            # fallback placeholders
            return 8.0, 4.6, 16.0

    def _get_disk_free_text(self):
        try:
            import psutil  # type: ignore

            d = psutil.disk_usage(os.path.abspath(os.sep))
            return f"{d.free/(1024**3):.0f}/{d.total/(1024**3):.0f} GB"
        except Exception:
            return "—"

    def _get_weather_text(self):
        return self._weather_cache.strip()

    def _tick_weather_async(self):
        # fetch in background every 10 minutes
        now = time.time()
        if now - self._weather_last_fetch >= 600:
            self._weather_last_fetch = now
            threading.Thread(target=self._fetch_weather, daemon=True).start()

        self.root.after(2000, self._tick_weather_async)

    def _fetch_weather(self):
        try:
            # Use JSON for full details
            r = requests.get("https://wttr.in/Madrid?format=j1", timeout=8)
            data = r.json()

            current = (data.get("current_condition") or [{}])[0] or {}
            area = (data.get("nearest_area") or [{}])[0] or {}

            location = ((area.get("areaName") or [{}])[0].get("value")) or "Madrid"
            temp_c = current.get("temp_C") or "—"
            feels_c = current.get("FeelsLikeC") or "—"
            humidity = current.get("humidity") or "—"

            wind_kmph = current.get("windspeedKmph") or "—"
            wind_dir = current.get("winddir16Point") or ""

            desc = ""
            wdesc = current.get("weatherDesc") or []
            if wdesc and isinstance(wdesc, list):
                desc = (wdesc[0].get("value") or "").strip()

            # Cache strings
            self._weather_details = {
                "temp": f"{temp_c}°C" if str(temp_c) != "—" else "—",
                "location": location,
                "desc": desc or "—",
                "humidity": f"{humidity}%" if str(humidity) != "—" else "—",
                "wind": f"{wind_kmph} km/h {wind_dir}".strip() if str(wind_kmph) != "—" else "—",
                "feelslike": f"{feels_c}°C" if str(feels_c) != "—" else "—",
            }

            # Chip and main line
            chip = f"{location}: {self._weather_details['temp']}"
            self._weather_cache = chip

            # Push into UI vars on main thread
            self.root.after(0, self._apply_weather_details)
        except Exception:
            pass

    def _apply_weather_details(self):
        d = self._weather_details
        self.weather_main.set(d.get("temp", "—"))
        self.weather_location.set(d.get("location", "—"))
        self.weather_desc.set(d.get("desc", "—"))
        self.weather_humidity.set(d.get("humidity", "—"))
        self.weather_wind.set(d.get("wind", "—"))
        self.weather_feels.set(d.get("feelslike", "—"))
        # also update chip immediately
        if self._weather_cache:
            self.weather_chip.config(text=self._weather_cache)

    # ---------- STARTUP / GREETING ----------
    def _startup_greeting(self):
        if self._did_greet:
            return
        self._did_greet = True

        hour = datetime.now().hour
        if 6 <= hour < 14:
            sal = "Buenos días"
        elif 14 <= hour < 21:
            sal = "Buenas tardes"
        else:
            sal = "Buenas noches"

        msg = f"{sal}, señor. ¿Qué desea hacer hoy?"
        self.add_message("Jarvis", msg)
        speak(msg)

    def _blend(self, fg, bg, t):
        # t in [0..1] amount of fg
        def _hex_to_rgb(x):
            x = x.lstrip("#")
            return int(x[0:2], 16), int(x[2:4], 16), int(x[4:6], 16)

        def _rgb_to_hex(r, g, b):
            return f"#{r:02x}{g:02x}{b:02x}"

        fr, fg2, fb = _hex_to_rgb(fg)
        br, bg2, bb = _hex_to_rgb(bg)
        r = int(br + (fr - br) * t)
        g = int(bg2 + (fg2 - bg2) * t)
        b = int(bb + (fb - bb) * t)
        return _rgb_to_hex(r, g, b)

    def _sin(self, x):
        return math.sin(x)


if __name__ == "__main__":
    app = JarvisGUI()
    app.run()