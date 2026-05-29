import tkinter as tk
from tkinter import filedialog
import threading
import sys
import os
import time
from datetime import datetime
import requests
import math

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from voice.pipeline import set_callbacks, wake_listener, conversation_loop, handle_user_input
from voice.tts import speak, get_speaking
from backend.services.stats import get_stats, get_disk_free_text
from backend.services.weather import get_weather_short


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
        self._eq_energy = 0.0

        self._build_topbar()
        self._build_left()
        self._build_center()
        self._build_right()

        self._tick_clock()
        self._tick_stats()
        self._animate_core()
        self._tick_weather_async()

        # initial message
        self.add_message("Jarvis", "Hello, I am Jarvis. Backend is offline.\nSome features may be limited. How can I assist you today sir?")

        # Voice always on by default
        self.root.after(250, self.start_backend)

    def on_toggle_voice_backend(self):
        if self.voice_backend_enabled.get():
            self.start_backend()

    # 🧠 BACKEND VOZ
    def start_backend(self):
        if self._voice_threads_started:
            return

        # import aquí para que la GUI no arranque voz por defecto
        # wire callbacks so voice + typed land in same chat
        set_callbacks(
            on_user=lambda t: self.root.after(0, lambda: self.add_message("You", t)),
            on_jarvis=lambda t: self.root.after(0, lambda: self.add_message("Jarvis", t)),
            on_status=lambda s: self.root.after(0, lambda: self._set_status(s, online=True)),
        )

        threading.Thread(target=wake_listener, daemon=True).start()
        threading.Thread(target=conversation_loop, daemon=True).start()
        self._voice_threads_started = True
        self.voice_backend_enabled.set(True)
        self._set_status("Listening for wake word…", online=True)

    # 🧠 enviar mensaje
    def send_message(self, event=None):
        msg = self.entry.get().strip()
        if not msg:
            return

        self.entry.delete(0, tk.END)

        # Use the same pipeline as voice (and let callbacks populate chat)
        if not self._voice_threads_started:
            set_callbacks(
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
            response = handle_user_input(msg, speak_response=True)
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
            header = f"Jarvis  •  {timestamp}\n"

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

        self.voice_backend_enabled = tk.BooleanVar(value=False)
        self.voice_btn = tk.Button(
            right, text="Enable Voice", command=self._toggle_voice_clicked,
            bg="#0f2432", fg=self.COL_CYAN, activebackground="#132b3d",
            activeforeground=self.COL_CYAN, bd=1, relief="solid", padx=10, pady=4,
            font=self.FT_SMALL
        )
        self.voice_btn.grid(row=0, column=1, padx=(0, 10))

        self.fullscreen_btn = tk.Button(
            right, text="Fullscreen", command=self._toggle_fullscreen,
            bg="#0f2432", fg=self.COL_TEXT, activebackground="#132b3d",
            activeforeground=self.COL_TEXT, bd=1, relief="solid", padx=10, pady=4,
            font=self.FT_SMALL
        )
        self.fullscreen_btn.grid(row=0, column=2)

    def _build_left(self):
        self.left = tk.Frame(self.root, bg=self.COL_BG)
        self.left.grid(row=1, column=0, sticky="nsw", padx=(18, 10), pady=(0, 18))
        self.left.grid_rowconfigure(3, weight=1)

        self.card_stats = self._card(self.left, "System Stats", row=0)
        self._stats_rows(self.card_stats)

        self.card_weather = self._card(self.left, "Weather", row=1)
        self._weather_rows(self.card_weather)


        self.card_uptime = self._card(self.left, "System Uptime", row=2)
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
        try:
            img_path = os.path.join(os.path.dirname(__file__), "..", "web", "static", "reactor.png")
            self.reactor_img = tk.PhotoImage(file=img_path)
        except:
            self.reactor_img = None
            
        self.core_canvas.bind("<Configure>", lambda e: self._draw_core())

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

        # Bottom controls (icons-like)
        self.controls = tk.Frame(self.center, bg=self.COL_BG)
        self.controls.grid(row=1, column=0, sticky="s", pady=(10, 0))

        self._control_button(self.controls, "🎤", self._toggle_voice_clicked).grid(row=0, column=1, padx=10)
        self._control_button(self.controls, "⌨", lambda: self.entry.focus_set()).grid(row=0, column=2, padx=10)

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

        # Conversation panel
        self.conv_panel = tk.Frame(self.right, bg=self.COL_PANEL, bd=1, relief="solid")
        self.conv_panel.grid(row=1, column=0, sticky="nsew")
        self.conv_panel.grid_rowconfigure(0, weight=1)
        self.conv_panel.grid_columnconfigure(0, weight=1)

        self.conv_scroll = tk.Scrollbar(self.conv_panel)
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
    def _card(self, parent, title, row):
        wrap = tk.Frame(parent, bg=self.COL_PANEL, bd=1, relief="solid", highlightthickness=0)
        wrap.grid(row=row, column=0, sticky="ew", pady=10)
        wrap.grid_columnconfigure(0, weight=1)

        head = tk.Frame(wrap, bg=self.COL_PANEL)
        head.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 6))
        head.grid_columnconfigure(0, weight=1)

        tk.Label(head, text=title, bg=self.COL_PANEL, fg=self.COL_TEXT, font=("Segoe UI", 10, "bold")).grid(
            row=0, column=0, sticky="w"
        )
        tk.Label(head, text="⚙", bg=self.COL_PANEL, fg=self.COL_MUTED, font=("Segoe UI", 10)).grid(
            row=0, column=1, sticky="e"
        )

        body = tk.Frame(wrap, bg=self.COL_PANEL)
        body.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 12))
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
        stats = get_stats()
        self.cpu_val.set(f"{stats['cpu']}%")
        self.ram_val.set(f"{stats['ram_used']} GB")
        self.disk_val.set(get_disk_free_text())

        self._draw_progress(self.cpu_bar, stats['cpu'] / 100.0)
        self._draw_progress(self.ram_bar, min(1.0, stats['ram_used'] / max(0.1, stats['ram_total'])))

        # weather
        w = self._get_weather_text()
        if w:
            self.weather_main.set(w)
            self.weather_chip.config(text=w)

        # uptime
        up_s = int(time.time() - self._uptime_start)
        self.uptime_val.set(time.strftime("%H:%M:%S", time.gmtime(up_s)))

        self.root.after(1500, self._tick_stats)

    def _animate_core(self):
        self._anim_phase = (self._anim_phase + 1) % 360
        # Smooth energy envelope: rise quickly while speaking, decay slowly when not
        target = 1.0 if bool(get_speaking()) else 0.0
        if target > self._eq_energy:
            self._eq_energy += (target - self._eq_energy) * 0.28
        else:
            self._eq_energy += (target - self._eq_energy) * 0.10
        self._draw_core()
        self.root.after(33, self._animate_core)  # smoother

    def _draw_core(self):
        c = self.core_canvas
        c.delete("all")
        w = c.winfo_width()
        h = c.winfo_height()
        if w < 10 or h < 10:
            return

        cx, cy = w // 2, int(h * 0.45)
        base = min(w, h) * 0.22
        e = max(0.0, min(1.0, self._eq_energy))
        t = (self._anim_phase * math.pi) / 180.0

        def draw_dashed_ring(r, width, color, dash, offset):
            # Tkinter create_oval doesn't support dash offset animation easily, 
            # so we'll draw simple dashed rings with the dash option
            c.create_oval(cx - r, cy - r, cx + r, cy + r, outline=color, width=width, dash=dash)

        # Outer faint ring
        draw_dashed_ring(base * 1.8, 1, self._blend(self.COL_CYAN, self.COL_BG, 0.2), (4, 8), 0)
        
        # Middle solid ring with gaps
        draw_dashed_ring(base * 1.35, 3, self.COL_CYAN_2, (80, 20, 20, 20), 0)
        draw_dashed_ring(base * 1.25, 1, self._blend(self.COL_CYAN, self.COL_BG, 0.4), (5, 5), 0)

        # Audio visualizer style rings
        num_bars = 60
        for i in range(num_bars):
            ang = (i / num_bars) * math.pi * 2 + t * 0.5
            wave = 0.5 + 0.5 * math.sin(t * 3 + i * 0.2)
            length = base * 0.1 + base * 0.3 * wave * e
            r1 = base * 1.5
            r2 = base * 1.5 + length
            c.create_line(
                cx + math.cos(ang) * r1, cy + math.sin(ang) * r1,
                cx + math.cos(ang) * r2, cy + math.sin(ang) * r2,
                fill=self._blend(self.COL_CYAN_2, self.COL_BG, 0.3 + 0.7 * e * wave),
                width=2
            )

        # Inner visualizer rings
        inner_bars = 40
        for i in range(inner_bars):
            ang = (i / inner_bars) * math.pi * 2 - t
            wave = 0.5 + 0.5 * math.sin(t * 5 + i * 0.5)
            length = base * 0.05 + base * 0.2 * wave * e
            r1 = base * 1.0
            r2 = base * 1.0 + length
            c.create_line(
                cx + math.cos(ang) * r1, cy + math.sin(ang) * r1,
                cx + math.cos(ang) * r2, cy + math.sin(ang) * r2,
                fill=self.COL_CYAN,
                width=2
            )

        # Inner core rings
        draw_dashed_ring(base * 0.8, 2, self._blend(self.COL_CYAN_2, self.COL_BG, 0.8), (10, 5), 0)
        draw_dashed_ring(base * 0.7, 4, self.COL_CYAN_2, (40, 10, 5, 10), 0)

        # Core center
        c.create_oval(cx - base * 0.4, cy - base * 0.4, cx + base * 0.4, cy + base * 0.4, outline=self.COL_CYAN, width=1 + int(e * 2))
        c.create_oval(cx - base * 0.35, cy - base * 0.35, cx + base * 0.35, cy + base * 0.35, fill=self._blend(self.COL_CYAN_2, self.COL_BG, max(0.1, e)), outline="")

    def _set_status(self, text, online):
        self.core_status.config(text=text, fg=self.COL_GREEN if online else self.COL_MUTED)
        if online:
            self.status_pill.config(text=" Online ", fg=self.COL_GREEN, bg="#0f2432")
            self.voice_btn.config(text="Voice On", fg=self.COL_GREEN)
        else:
            self.status_pill.config(text=" Offline ", fg=self.COL_MUTED, bg="#0f2432")
            self.voice_btn.config(text="Enable Voice", fg=self.COL_CYAN)

    def _toggle_voice_clicked(self):
        # Keep voice always on: button becomes a status/bring-to-front helper.
        if not self._voice_threads_started:
            self.start_backend()
        self._set_status("Listening for wake word…", online=True)

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
        top = tk.Frame(parent, bg=self.COL_PANEL)
        top.pack(fill="x")
        tk.Label(top, textvariable=self.weather_main, bg=self.COL_PANEL, fg=self.COL_TEXT, font=("Segoe UI", 16, "bold")).pack(
            anchor="w"
        )
        tk.Label(top, text="Location", bg=self.COL_PANEL, fg=self.COL_MUTED, font=("Segoe UI", 9)).pack(anchor="w")

        grid = tk.Frame(parent, bg=self.COL_PANEL)
        grid.pack(fill="x", pady=(10, 0))
        for i, (k, v) in enumerate([("Humidity", "—"), ("Wind", "—"), ("Feels Like", "—")]):
            col = tk.Frame(grid, bg=self.COL_PANEL)
            col.grid(row=0, column=i, sticky="ew", padx=6)
            grid.grid_columnconfigure(i, weight=1)
            tk.Label(col, text=k, bg=self.COL_PANEL, fg=self.COL_MUTED, font=("Segoe UI", 8)).pack(anchor="w")
            tk.Label(col, text=v, bg=self.COL_PANEL, fg=self.COL_TEXT, font=("Segoe UI", 10, "bold")).pack(anchor="w")

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

    # System stats and disk info now come from backend.services.stats

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
        txt = get_weather_short()
        if txt:
            self._weather_cache = txt

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