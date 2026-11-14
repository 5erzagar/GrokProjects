"""TSO simulator export helper (Windows, Python 3.10+).

1. 'Odpri simulator'   - opens a browser window with tsowiki.eu/simulator
2. you set up and run the simulation yourself
3. 'Pridobi rezultate' - reads camps that do not yet have X generals
4. 'Shrani zemljevid'  - saves the adventure map into the same folder as the results
5. 'Izvozi ZIP'        - packs everything into one zip file
"""
from __future__ import annotations

import json
import os
import queue
import threading
import tkinter as tk
import traceback
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from core import (
    EXCLUDE_COMBOS, INCREMENTS, KIND_LABELS, REPETITIONS, SIM_URL, SKIP_MODES, SORTS,
    UNIT_GROUPS, SimBrowser, export_zip, finished_tabs, resolve_folder, safe_name,
    save_results, should_skip_adventure,
)

APP_DIR = Path(__file__).resolve().parent
OUT_DIR = APP_DIR / "rezultati"
PROFILE_DIR = APP_DIR / "browser_profile"
SETTINGS_PATH = APP_DIR / "auto_settings.json"

BG = "#1a1612"
PANEL = "#262019"
INK = "#f4efe6"
MUTED = "#b5aa96"
GOLD = "#c6a15a"
FIELD = "#100e0c"
LINE = "#3a3228"


def default_settings() -> dict:
    units = {}
    for ids in UNIT_GROUPS.values():
        for unit in ids:
            units[unit] = {"min": 0, "max": 0}
    return {
        "unit_kind": "Default",
        "threads": 15,
        "repetitions": 100,
        "increment": 5,
        "step": 5,
        "only_max": False,
        "merge": False,
        "all_camps": True,
        "skip_victory": True,
        "sort": "Efficiency",
        "exclude": [],
        "units": units,
        "generals": "",
        "skip_mode": "none",
        "checked": [],
    }


def load_settings() -> dict:
    data = default_settings()
    try:
        saved = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except Exception:
        saved = {}
    if isinstance(saved, dict):
        data.update({k: v for k, v in saved.items() if k != "units"})
        units = dict(data["units"])
        for key, val in (saved.get("units") or {}).items():
            if isinstance(val, dict):
                units[key] = {"min": int(val.get("min") or 0), "max": int(val.get("max") or 0)}
        data["units"] = units
    return data


def skip_label(mode: str) -> str:
    for key, label in SKIP_MODES:
        if key == mode:
            return label
    return SKIP_MODES[0][1]


def skip_key(label: str) -> str:
    for key, text in SKIP_MODES:
        if text == label:
            return key
    return "none"


STR = {
    "sl": {
        "title": "TSO simulator",
        "subtitle": "Za vsak tabor shrani X generalov z najmanjšo vojsko, ki še zmaga. Zemljevid gre v isto mapo.",
        "sim": "Simulator", "adv": "Avantura", "get_name": "Pridobi ime avanture",
        "per_camp": "Generalov na tabor", "rows": "Preberi vrstic", "more": "(Show more results se odpre sam)",
        "redo": "Znova vse", "open": "1  Odpri simulator", "collect": "2  Pridobi rezultate",
        "map": "3  Shrani zemljevid", "zip": "Izvozi ZIP", "folder": "Odpri mapo", "debug": "Diagnostika",
        "start": "Start", "pause": "Pavza", "resume": "Nadaljuj", "stop": "Stop",
        "settings": "Nastavitve", "load_adv": "Naloži avanture", "checked": "Obkljukane avanture",
        "all": "Vse", "none": "Nobena", "empty": "Najprej odpri simulator, nato klikni «Naloži avanture».",
        "stats": "Vse: {n}    Izbrane: {s}    Rešene: {r}",
        "lang": "English",
        "skip_none": "Ne preskakuj", "skip_folder": "Preskoči, če mapa obstaja",
        "skip_results": "Preskoči, če je results.json", "skip_both": "Preskoči, če sta rezultati in zemljevid",
        "set_title": "Nastavitve simulacije", "units": "Enote igralca", "from": "Od", "to": "Do",
        "enemy": "Sovražnikove enote se ne vpisujejo. Jih napolni izbrana avantura.",
        "search": "Iskanje", "save": "Shrani", "import": "Uvozi generale",
        "gens": "Generali za simulacijo (samo obkljukani se izberejo, spretnosti ostanejo)",
        "no_gen_file": "Najprej izberi datoteko generalov.",
        "only_max": "Samo napad z največjim številom enot",
        "merge": "Združi izgubljene in obnovljene enote",
        "all_camps": "Simuliraj vse tabore avanture",
        "skip100": "Preskoči kombinacije z manj kot 100 % zmage",
        "skip_combo": "Preskoči kombinacije enot",
    },
    "en": {
        "title": "TSO simulator",
        "subtitle": "For each camp, save the X generals with the smallest army that still wins. The map goes in the same folder.",
        "sim": "Simulator", "adv": "Adventure", "get_name": "Get adventure name",
        "per_camp": "Generals per camp", "rows": "Read rows", "more": "(Show more results opens itself)",
        "redo": "Redo all", "open": "1  Open simulator", "collect": "2  Get results",
        "map": "3  Save map", "zip": "Export ZIP", "folder": "Open folder", "debug": "Diagnostics",
        "start": "Start", "pause": "Pause", "resume": "Resume", "stop": "Stop",
        "settings": "Settings", "load_adv": "Load adventures", "checked": "Checked adventures",
        "all": "All", "none": "None", "empty": "Open the simulator first, then click “Load adventures”.",
        "stats": "All: {n}    Selected: {s}    Solved: {r}",
        "lang": "Slovenščina",
        "skip_none": "Do not skip", "skip_folder": "Skip if the folder exists",
        "skip_results": "Skip if results.json exists", "skip_both": "Skip if results and the map exist",
        "set_title": "Simulation settings", "units": "Player units", "from": "From", "to": "To",
        "enemy": "Enemy units are not filled in. The selected adventure does that.",
        "search": "Search", "save": "Save", "import": "Import generals",
        "gens": "Generals for the simulation (only checked ones are selected, skills stay as imported)",
        "no_gen_file": "Choose a generals file first.",
        "only_max": "Only attack with the maximum number of units",
        "merge": "Merge lost and recovered units",
        "all_camps": "Simulate all camps of the adventure",
        "skip100": "Skip combinations with a victory chance < 100%",
        "skip_combo": "Skip unit combinations",
    },
}
SKIP_KEYS = ("skip_none", "skip_folder", "skip_results", "skip_both")
SKIP_TO_MODE = {"skip_none": "none", "skip_folder": "folder", "skip_results": "results", "skip_both": "both"}
MODE_TO_SKIP = {v: k for k, v in SKIP_TO_MODE.items()}


def tr(lang: str, key: str) -> str:
    pack = STR.get(lang) or STR["sl"]
    return pack.get(key) or STR["sl"].get(key) or key


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("TSO simulator — izvoz rezultatov")
        self.geometry("920x760")
        self.minsize(820, 640)
        self.configure(bg=BG)
        self.browser = SimBrowser(PROFILE_DIR)
        self.ui: queue.Queue = queue.Queue()
        self.last_adv = ""
        self.settings = load_settings()
        self.lang = "en" if self.settings.get("lang") == "en" else "sl"
        self.stop_ev = threading.Event()
        self.pause_ev = threading.Event()
        self._batch = False
        self._adv_vars = {}
        self._adv_names = {}
        self._adv_checks = {}
        self._photos = []
        self._style()

        shell = ttk.Frame(self, padding=16, style="App.TFrame")
        shell.pack(fill="both", expand=True)

        head = ttk.Frame(shell, style="App.TFrame")
        head.pack(fill="x")
        self.title_lbl = ttk.Label(head, text=self.T("title"), style="Title.TLabel")
        self.title_lbl.pack(anchor="w")
        self.sub_lbl = ttk.Label(head, text=self.T("subtitle"), style="Muted.TLabel")
        self.sub_lbl.pack(anchor="w", pady=(2, 12))

        form = ttk.Frame(shell, style="Card.TFrame", padding=12)
        form.pack(fill="x")
        form.columnconfigure(1, weight=1)

        self.lbl_sim = ttk.Label(form, text=self.T("sim"), style="Card.TLabel")
        self.lbl_sim.grid(row=0, column=0, sticky="w", pady=3)
        self.url = tk.StringVar(value=SIM_URL)
        ttk.Entry(form, textvariable=self.url, style="App.TEntry").grid(row=0, column=1, columnspan=3, sticky="we", padx=(8, 0), pady=3)

        self.lbl_adv = ttk.Label(form, text=self.T("adv"), style="Card.TLabel")
        self.lbl_adv.grid(row=1, column=0, sticky="w", pady=3)
        self.adv = tk.StringVar()
        ttk.Entry(form, textvariable=self.adv, style="App.TEntry").grid(row=1, column=1, sticky="we", padx=(8, 0), pady=3)
        self.btn_name = ttk.Button(form, text=self.T("get_name"), command=self.on_name)
        self.btn_name.grid(row=1, column=2, columnspan=2, sticky="e", padx=(8, 0))

        self.lbl_top = ttk.Label(form, text=self.T("per_camp"), style="Card.TLabel")
        self.lbl_top.grid(row=2, column=0, sticky="w", pady=3)
        spins = ttk.Frame(form, style="Card.TFrame")
        spins.grid(row=2, column=1, columnspan=3, sticky="w", padx=(8, 0), pady=3)
        self.topn = tk.IntVar(value=3)
        ttk.Spinbox(spins, from_=1, to=12, textvariable=self.topn, width=5).pack(side="left")
        self.lbl_rows = ttk.Label(spins, text=self.T("rows"), style="Card.TLabel")
        self.lbl_rows.pack(side="left")
        self.scan = tk.IntVar(value=120)
        ttk.Spinbox(spins, from_=5, to=400, textvariable=self.scan, width=5).pack(side="left", padx=(6, 0))
        self.lbl_more = ttk.Label(spins, text=self.T("more"), style="Muted.TLabel")
        self.lbl_more.pack(side="left")
        self.redo = tk.BooleanVar(value=False)
        self.chk_redo = ttk.Checkbutton(spins, text=self.T("redo"), variable=self.redo)
        self.chk_redo.pack(side="left", padx=(10, 0))

        self.folder_var = tk.StringVar(value="Mapa še ni izbrana.")
        ttk.Label(form, textvariable=self.folder_var, style="Muted.TLabel").grid(row=3, column=0, columnspan=4, sticky="w", pady=(8, 0))

        bar = ttk.Frame(shell, style="App.TFrame")
        bar.pack(fill="x", pady=(12, 8))
        self.main_btns = {}
        for key, cmd in [
            ("open", self.on_open), ("collect", self.on_collect), ("map", self.on_map),
            ("zip", self.on_zip), ("folder", self.on_folder), ("debug", self.on_debug),
        ]:
            btn = ttk.Button(bar, text=self.T(key), command=cmd)
            btn.pack(side="left", padx=(0, 6))
            self.main_btns[key] = btn

        auto = ttk.Frame(shell, style="App.TFrame")
        auto.pack(fill="x", pady=(0, 8))
        self.btn_start = ttk.Button(auto, text=self.T("start"), command=self.on_start)
        self.btn_start.pack(side="left", padx=(0, 6))
        self.pause_btn = ttk.Button(auto, text=self.T("pause"), command=self.on_pause)
        self.pause_btn.pack(side="left", padx=(0, 6))
        self.btn_stop = ttk.Button(auto, text=self.T("stop"), command=self.on_stop)
        self.btn_stop.pack(side="left", padx=(0, 6))
        self.btn_set = ttk.Button(auto, text=self.T("settings"), command=self.on_settings)
        self.btn_set.pack(side="left", padx=(0, 6))
        self.btn_load = ttk.Button(auto, text=self.T("load_adv"), command=self.on_load_adventures)
        self.btn_load.pack(side="left", padx=(0, 6))
        self.btn_lang = ttk.Button(auto, text=self.T("lang"), command=self.on_lang)
        self.btn_lang.pack(side="left", padx=(0, 6))
        self.skip_mode = tk.StringVar(value=self._skip_label(self.settings.get("skip_mode") or "none"))
        self.skip_box = ttk.Combobox(auto, textvariable=self.skip_mode, values=self._skip_values(),
                                     state="readonly", width=36)
        self.skip_box.pack(side="left", padx=(8, 0))
        self.skip_box.bind("<<ComboboxSelected>>", lambda e: self._refresh_marks())

        picks = ttk.Frame(shell, style="Card.TFrame", padding=8)
        picks.pack(fill="x", pady=(0, 8))
        head_row = ttk.Frame(picks, style="Card.TFrame")
        head_row.pack(fill="x")
        self.lbl_checked = ttk.Label(head_row, text=self.T("checked"), style="Card.TLabel")
        self.lbl_checked.pack(side="left")
        self.btn_all = ttk.Button(head_row, text=self.T("all"), command=lambda: self._check_all(True))
        self.btn_all.pack(side="right")
        self.btn_none = ttk.Button(head_row, text=self.T("none"), command=lambda: self._check_all(False))
        self.btn_none.pack(side="right", padx=(0, 6))
        self.stats_lbl = ttk.Label(picks, text=self.T("stats").format(n=0, s=0, r=0), style="Card.TLabel")
        self.stats_lbl.pack(anchor="w", pady=(4, 0))
        self.adv_canvas = tk.Canvas(picks, height=150, bg=PANEL, highlightthickness=0)
        self.adv_scroll = ttk.Scrollbar(picks, command=self.adv_canvas.yview)
        self.adv_box = ttk.Frame(self.adv_canvas, style="Card.TFrame")
        self.adv_box.bind("<Configure>", lambda e: self.adv_canvas.configure(scrollregion=self.adv_canvas.bbox("all")))
        self.adv_canvas.create_window((0, 0), window=self.adv_box, anchor="nw")
        self.adv_canvas.configure(yscrollcommand=self.adv_scroll.set)
        self.adv_canvas.pack(side="left", fill="both", expand=True, pady=(6, 0))
        self.adv_scroll.pack(side="right", fill="y", pady=(6, 0))
        self.adv_canvas.bind("<MouseWheel>", self._wheel)
        self.adv_canvas.bind("<Button-4>", lambda e: self.adv_canvas.yview_scroll(-3, "units"))
        self.adv_canvas.bind("<Button-5>", lambda e: self.adv_canvas.yview_scroll(3, "units"))
        ttk.Label(self.adv_box, text=self.T("empty"), style="Card.TLabel").pack(anchor="w")

        self.logbox = tk.Text(
            shell, height=18, state="disabled", wrap="word",
            bg=FIELD, fg=INK, insertbackground=INK, relief="flat",
            highlightthickness=1, highlightbackground=LINE, highlightcolor=GOLD,
            font=("Consolas", 10), padx=10, pady=8,
        )
        self.logbox.pack(fill="both", expand=True)
        self.log(f"Rezultati in zemljevid se shranijo skupaj v:  {OUT_DIR}")

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.after(150, self.pump)

    def _style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("App.TFrame", background=BG)
        style.configure("Card.TFrame", background=PANEL)
        style.configure("Title.TLabel", background=BG, foreground=INK, font=("Segoe UI", 18, "bold"))
        style.configure("Muted.TLabel", background=BG, foreground=MUTED, font=("Segoe UI", 9))
        style.configure("Card.TLabel", background=PANEL, foreground=INK, font=("Segoe UI", 10))
        style.configure("TButton", background="#3a3126", foreground=INK, borderwidth=0, padding=(10, 6), font=("Segoe UI", 9))
        style.map("TButton", background=[("active", "#4a3e2e")], foreground=[("disabled", "#87785f")])
        style.configure("App.TEntry", fieldbackground="#fffaf2", foreground="#1a1612")
        style.configure("TSpinbox", fieldbackground="#fffaf2", foreground="#1a1612", arrowsize=12)
        style.configure("TLabel", background=BG, foreground=INK)

    def report_callback_exception(self, exc, val, tb):
        text = "".join(traceback.format_exception(exc, val, tb))
        self.log("NAPAKA v programu:\n" + text)
        try:
            (APP_DIR / "app.log").open("a", encoding="utf-8").write(text + "\n")
        except Exception:
            pass

    def log(self, msg: str):
        self.ui.put(("log", msg))

    def pump(self):
        try:
            while True:
                kind, val = self.ui.get_nowait()
                if kind == "log":
                    self.logbox.configure(state="normal")
                    self.logbox.insert("end", val + "\n")
                    self.logbox.see("end")
                    self.logbox.configure(state="disabled")
                elif kind == "adv":
                    self.adv.set(val)
                    self.last_adv = val
                    folder = resolve_folder(OUT_DIR, val)
                    self.folder_var.set(f"Skupna mapa za rezultate in zemljevid:  {folder}")
        except queue.Empty:
            pass
        self.after(150, self.pump)

    def run(self, fn, *args, ok=None):
        def done(res, exc):
            if exc is not None:
                self.log(f"NAPAKA: {exc}")
            elif ok:
                ok(res)
        self.browser.submit(fn, *args, done=done)

    def _remember(self, adv: str, label: str = ""):
        self.ui.put(("adv", adv))
        if label and label != adv:
            self.log(f"Avantura: {label}  ({adv})")

    # -- buttons
    def on_open(self):
        self.log("Odpiram brskalnik ...")
        self.run(self.browser.open, self.url.get().strip() or SIM_URL, ok=self.log)

    def on_name(self):
        self.log("Berem ime avanture s strani ...")

        def work():
            info = self.browser.read_adventure()
            adv = (info or {}).get("id") or ""
            if not adv:
                raise RuntimeError("Imena ni mogoče prebrati. Odpri simulator in izberi avanturo.")
            self._remember(adv, (info or {}).get("label") or "")
            return f"Ime zapisano: {adv}   (mapa {safe_name(adv)})"

        self.run(work, ok=self.log)

    def on_collect(self):
        n = max(1, int(self.topn.get() or 1))
        scan = max(5, int(self.scan.get() or 60))
        typed = self.adv.get().strip()
        redo = bool(self.redo.get())
        self.log(f"Berem rezultate (do {scan} vrstic, obdržim {n} generalov na tabor) ...")

        def work():
            guess = typed or getattr(self, "last_adv", "") or ""
            if not guess:
                try:
                    guess = (self.browser.read_adventure() or {}).get("id") or ""
                except Exception:
                    guess = ""
            skip = set() if redo else finished_tabs(OUT_DIR, guess, n)
            if skip:
                self.log("Preskočim tabore, ki že imajo rešitev: " + ", ".join(sorted(skip)))
            camps = self.browser.collect(n, self.log, scan, skip)
            if not camps:
                return "Ni novih taborov. Vključi «Znova vse», če hočeš obstoječe prepisati."
            adv = ""
            for c in camps:
                for s in c["solutions"]:
                    if s.get("setup") and s["setup"].get("adventure"):
                        adv = s["setup"]["adventure"]
                        break
                if adv:
                    break
            if not adv:
                adv = self.browser.read_adventure().get("id") or typed
            if not adv:
                raise RuntimeError("Imena avanture ni mogoče prebrati. Klikni 'Pridobi ime avanture' ali ga vpiši.")
            if typed and typed != adv:
                self.log(f"Vpisano ime «{typed}» ni id avanture. Rezultati gredo v «{safe_name(adv)}», da se ujemajo z zemljevidom.")
            self._remember(adv)
            path = save_results(OUT_DIR, adv, camps)
            return f"Shranjeno: {path}  ({len(camps)} taborov, do {n} generalov)"

        self.run(work, ok=self.log)

    def on_map(self):
        typed = self.adv.get().strip()

        def work():
            info = {}
            try:
                info = self.browser.read_adventure()
            except Exception:
                info = {}
            name = (info or {}).get("id") or self.last_adv or typed
            if not name:
                raise RuntimeError("Najprej klikni 'Pridobi ime avanture' ali 'Pridobi rezultate'.")
            if typed and typed != name:
                self.log(f"Zemljevid ne gre v «{typed}». Uporabljam isto mapo kot rezultati: {safe_name(name)}.")
            self._remember(name, (info or {}).get("label") or "")
            path = self.browser.save_map(OUT_DIR, name)
            return f"Zemljevid shranjen poleg rezultatov: {path}"

        self.log("Shranjujem zemljevid ...")
        self.run(work, ok=self.log)

    def on_zip(self):
        if not OUT_DIR.exists():
            messagebox.showinfo("ZIP", "Še ni shranjenih rezultatov.")
            return
        target = filedialog.asksaveasfilename(
            parent=self, defaultextension=".zip",
            initialdir=str(Path.home() / "Desktop"),
            initialfile="tso_rezultati.zip",
            filetypes=[("ZIP", "*.zip")],
        )
        if not target:
            return
        self.log("Pakiram ZIP ...")

        def work():
            try:
                n = export_zip(OUT_DIR, Path(target))
                self.log(f"ZIP shranjen: {target} ({n} datotek)")
            except Exception as e:  # noqa: BLE001
                self.log(f"NAPAKA pri ZIP: {e}")

        threading.Thread(target=work, daemon=True).start()

    def on_folder(self):
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(str(OUT_DIR))  # Windows only
        except Exception as e:  # noqa: BLE001
            self.log(f"Mape ni mogoče odpreti: {e}  ({OUT_DIR})")

    def on_debug(self):
        self.run(self.browser.debug_dump, OUT_DIR,
                 ok=lambda p: self.log(f"Diagnostika shranjena v: {p}"))

    def on_close(self):
        self._store_checks()
        self._write_settings()
        self.browser.submit(self.browser.close)
        self.after(500, self.destroy)

    def _wheel(self, event):
        self.adv_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def T(self, key: str) -> str:
        return tr(self.lang, key)

    def _skip_values(self):
        return [self.T(key) for key in SKIP_KEYS]

    def _skip_label(self, mode: str) -> str:
        return self.T(MODE_TO_SKIP.get(mode, "skip_none"))

    def _current_skip_mode(self) -> str:
        label = self.skip_mode.get()
        for key in SKIP_KEYS:
            if self.T(key) == label:
                return SKIP_TO_MODE[key]
        return skip_key(label)

    def _icon(self, path: Path):
        if not path.exists():
            return None
        try:
            img = tk.PhotoImage(file=str(path))
        except Exception:
            return None
        self._photos.append(img)
        return img

    def on_lang(self):
        mode = self._current_skip_mode()
        self.lang = "en" if self.lang == "sl" else "sl"
        self.settings["lang"] = self.lang
        self.settings["skip_mode"] = mode
        self.title_lbl.configure(text=self.T("title"))
        self.sub_lbl.configure(text=self.T("subtitle"))
        self.lbl_sim.configure(text=self.T("sim"))
        self.lbl_adv.configure(text=self.T("adv"))
        self.btn_name.configure(text=self.T("get_name"))
        self.lbl_top.configure(text=self.T("per_camp"))
        self.lbl_rows.configure(text=self.T("rows"))
        self.lbl_more.configure(text=self.T("more"))
        self.chk_redo.configure(text=self.T("redo"))
        for key, btn in self.main_btns.items():
            btn.configure(text=self.T(key))
        self.btn_start.configure(text=self.T("start"))
        if not self.pause_ev.is_set():
            self.pause_btn.configure(text=self.T("pause"))
        else:
            self.pause_btn.configure(text=self.T("resume"))
        self.btn_stop.configure(text=self.T("stop"))
        self.btn_set.configure(text=self.T("settings"))
        self.btn_load.configure(text=self.T("load_adv"))
        self.btn_lang.configure(text=self.T("lang"))
        self.lbl_checked.configure(text=self.T("checked"))
        self.btn_all.configure(text=self.T("all"))
        self.btn_none.configure(text=self.T("none"))
        self.skip_box.configure(values=self._skip_values())
        self.skip_mode.set(self._skip_label(mode))
        self._write_settings()
        self._refresh_marks()

    def _refresh_marks(self):
        mode = self._current_skip_mode()
        solved = 0
        for adv_id, cb in self._adv_checks.items():
            mark = should_skip_adventure(OUT_DIR, adv_id, mode)
            if mark:
                solved += 1
            name = self._adv_names.get(adv_id, adv_id)
            cb.configure(text=name + (" (R)" if mark else ""))
        selected = sum(1 for var in self._adv_vars.values() if var.get())
        if hasattr(self, "stats_lbl"):
            self.stats_lbl.configure(text=self.T("stats").format(n=len(self._adv_vars), s=selected, r=solved))
        self._store_checks()

    def _write_settings(self):
        self.settings["skip_mode"] = self._current_skip_mode()
        if self._adv_vars:
            self.settings["checked"] = [key for key, var in self._adv_vars.items() if var.get()]
        try:
            SETTINGS_PATH.write_text(json.dumps(self.settings, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _store_checks(self):
        if not self._adv_vars:
            return
        self.settings["checked"] = [key for key, var in self._adv_vars.items() if var.get()]

    def _check_all(self, on: bool):
        for var in self._adv_vars.values():
            var.set(on)

    def on_load_adventures(self):
        self.log("Berem seznam avantur ...")

        def done(rows, exc):
            if exc is not None:
                self.log(f"NAPAKA: {exc}")
                return
            self._fill_adventures(rows or [])
            self.log(f"Avantur v seznamu: {len(rows or [])}. Obkljukaj tiste za Start.")

        self.browser.submit(self.browser.list_adventures, done=done)

    def _fill_adventures(self, rows):
        for child in self.adv_box.winfo_children():
            child.destroy()
        checked = set(self.settings.get("checked") or [])
        self._adv_vars = {}
        self._adv_names = {}
        self._adv_checks = {}
        if not rows:
            ttk.Label(self.adv_box, text=self.T("empty"), style="Card.TLabel").pack(anchor="w")
            self._refresh_marks()
            return
        for row in rows:
            adv_id = row.get("id") or ""
            if not adv_id:
                continue
            var = tk.BooleanVar(value=adv_id in checked)
            self._adv_vars[adv_id] = var
            self._adv_names[adv_id] = row.get("name") or adv_id
            line = ttk.Frame(self.adv_box, style="Card.TFrame")
            line.pack(anchor="w", fill="x")
            photo = self._icon(APP_DIR / "icons" / "adventures" / f"{adv_id}.png")
            if photo is not None:
                ttk.Label(line, image=photo, style="Card.TLabel").pack(side="left")
            cb = ttk.Checkbutton(line, text=row.get("name") or adv_id, variable=var, command=self._refresh_marks)
            cb.pack(side="left")
            self._adv_checks[adv_id] = cb
        self._refresh_marks()

    def on_pause(self):
        if self.pause_ev.is_set():
            self.pause_ev.clear()
            self.pause_btn.configure(text=self.T("pause"))
            self.log("Nadaljujem z naslednjo avanturo.")
        else:
            self.pause_ev.set()
            self.pause_btn.configure(text=self.T("resume"))
            self.log("Pavza po koncu trenutne avanture.")

    def on_stop(self):
        self.stop_ev.set()
        self.pause_ev.clear()
        self.pause_btn.configure(text=self.T("pause"))
        self.log("Stop: simulacija se prekine, v simulatorju grem na Cancel.")

    def on_start(self):
        if self._batch:
            self.log("Samodejni tek že teče.")
            return
        self._store_checks()
        labeled = [
            {"id": key, "name": self._adv_names.get(key, key)}
            for key, var in self._adv_vars.items() if var.get()
        ]
        if not labeled:
            self.log("Najprej naloži avanture in jih obkljukaj.")
            return
        self.stop_ev.clear()
        self.pause_ev.clear()
        self.pause_btn.configure(text=self.T("pause"))
        self._batch = True
        self._write_settings()
        n = max(1, int(self.topn.get() or 1))
        scan = max(5, int(self.scan.get() or 60))
        self.log(f"Start: {len(labeled)} avantur.")
        self.run(
            self.browser.run_batch,
            labeled, dict(self.settings), OUT_DIR, n, scan,
            self.settings.get("generals") or "",
            self._current_skip_mode(),
            self.stop_ev, self.pause_ev, self.log,
            ok=self._batch_done,
        )

    def _batch_done(self, message):
        self._batch = False
        self.pause_ev.clear()
        self.pause_btn.configure(text=self.T("pause"))
        self.log(message or "Končano.")

    def on_settings(self):
        if getattr(self, "_set_win", None) is not None:
            try:
                if self._set_win.winfo_exists():
                    self._set_win.lift()
                    return
            except Exception:
                pass
        win = tk.Toplevel(self)
        self._set_win = win
        win.title(self.T("set_title"))
        win.geometry("980x680")
        win.configure(bg=BG)
        s = self.settings
        kind = tk.StringVar(value=s.get("unit_kind") or "Default")
        threads = tk.IntVar(value=int(s.get("threads") or 15))
        reps = tk.IntVar(value=int(s.get("repetitions") or 100))
        step_n = tk.IntVar(value=int(s.get("increment") or 5))
        click_step = tk.IntVar(value=int(s.get("step") or 5))
        only_max = tk.BooleanVar(value=bool(s.get("only_max")))
        merge = tk.BooleanVar(value=bool(s.get("merge")))
        all_camps = tk.BooleanVar(value=bool(s.get("all_camps", True)))
        skip_victory = tk.BooleanVar(value=bool(s.get("skip_victory", True)))
        sort = tk.StringVar(value=s.get("sort") or "Efficiency")
        generals = tk.StringVar(value=s.get("generals") or "")
        exclude = {key: tk.BooleanVar(value=key in (s.get("exclude") or [])) for key, _ in EXCLUDE_COMBOS}
        unit_vars = {}
        for ids in UNIT_GROUPS.values():
            for unit in ids:
                cur = (s.get("units") or {}).get(unit) or {}
                unit_vars[unit] = (tk.IntVar(value=int(cur.get("min") or 0)), tk.IntVar(value=int(cur.get("max") or 0)))

        body = ttk.Frame(win, padding=12, style="App.TFrame")
        body.pack(fill="both", expand=True)
        left = ttk.Frame(body, style="Card.TFrame", padding=10)
        mid = ttk.Frame(body, style="Card.TFrame", padding=10)
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))
        mid.pack(side="left", fill="both", expand=True)

        ttk.Label(left, text=self.T("units"), style="Card.TLabel").pack(anchor="w")
        kinds = ttk.Frame(left, style="Card.TFrame")
        kinds.pack(anchor="w", pady=4)
        for key, label in KIND_LABELS.items():
            ttk.Radiobutton(kinds, text=label, value=key, variable=kind).pack(side="left", padx=(0, 8))
        unit_host = ttk.Frame(left, style="Card.TFrame")
        unit_host.pack(fill="both", expand=True)
        rows = {}

        def show_kind(*_):
            for frame in rows.values():
                frame.pack_forget()
            chosen = rows.get(kind.get())
            if chosen:
                chosen.pack(fill="both", expand=True)

        for key, ids in UNIT_GROUPS.items():
            frame = ttk.Frame(unit_host, style="Card.TFrame")
            rows[key] = frame
            head = ttk.Frame(frame, style="Card.TFrame")
            head.pack(fill="x")
            ttk.Label(head, text=self.T("units"), style="Card.TLabel", width=28).pack(side="left")
            ttk.Label(head, text=self.T("from"), style="Card.TLabel", width=8).pack(side="left")
            ttk.Label(head, text=self.T("to"), style="Card.TLabel", width=8).pack(side="left")
            for unit in ids:
                line = ttk.Frame(frame, style="Card.TFrame")
                line.pack(fill="x", pady=1)
                photo = self._icon(APP_DIR / "icons" / "units" / f"{unit}.png")
                if photo is not None:
                    ttk.Label(line, image=photo, style="Card.TLabel").pack(side="left")
                ttk.Label(line, text=unit, style="Card.TLabel", width=24).pack(side="left")
                ttk.Spinbox(line, from_=0, to=1000, textvariable=unit_vars[unit][0], width=6).pack(side="left", padx=(0, 8))
                ttk.Spinbox(line, from_=0, to=1000, textvariable=unit_vars[unit][1], width=6).pack(side="left")
        show_kind()
        kind.trace_add("write", show_kind)
        ttk.Label(left, text=self.T("enemy"), style="Card.TLabel").pack(anchor="w", pady=(8, 0))

        ttk.Label(mid, text=self.T("search"), style="Card.TLabel").pack(anchor="w")
        grid = ttk.Frame(mid, style="Card.TFrame")
        grid.pack(fill="x", pady=4)
        ttk.Label(grid, text="Threads", style="Card.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Spinbox(grid, from_=1, to=128, textvariable=threads, width=6).grid(row=0, column=1, sticky="w")
        ttk.Label(grid, text="Repetitions", style="Card.TLabel").grid(row=1, column=0, sticky="w", pady=3)
        ttk.Combobox(grid, textvariable=reps, values=REPETITIONS, width=8, state="readonly").grid(row=1, column=1, sticky="w")
        ttk.Label(grid, text="Increment", style="Card.TLabel").grid(row=2, column=0, sticky="w")
        ttk.Combobox(grid, textvariable=step_n, values=INCREMENTS, width=8, state="readonly").grid(row=2, column=1, sticky="w")
        ttk.Label(grid, text="Change amounts by", style="Card.TLabel").grid(row=3, column=0, sticky="w", pady=3)
        ttk.Combobox(grid, textvariable=click_step, values=INCREMENTS, width=8, state="readonly").grid(row=3, column=1, sticky="w")
        ttk.Label(grid, text="Sort results by", style="Card.TLabel").grid(row=4, column=0, sticky="w")
        sort_box = ttk.Combobox(grid, state="readonly", width=32, values=[label for _, label in SORTS])
        sort_box.grid(row=4, column=1, sticky="w", pady=3)
        label_by_sort = {key: label for key, label in SORTS}
        key_by_sort = {label: key for key, label in SORTS}
        sort_box.set(label_by_sort.get(sort.get(), label_by_sort["Efficiency"]))

        ttk.Checkbutton(mid, text=self.T("only_max"), variable=only_max).pack(anchor="w")
        ttk.Checkbutton(mid, text=self.T("merge"), variable=merge).pack(anchor="w")
        ttk.Checkbutton(mid, text=self.T("all_camps"), variable=all_camps).pack(anchor="w")
        ttk.Checkbutton(mid, text=self.T("skip100"), variable=skip_victory).pack(anchor="w")
        ttk.Label(mid, text=self.T("skip_combo"), style="Card.TLabel").pack(anchor="w", pady=(8, 2))
        for key, label in EXCLUDE_COMBOS:
            ttk.Checkbutton(mid, text=label, variable=exclude[key]).pack(anchor="w")

        gen_row = ttk.Frame(mid, style="Card.TFrame")
        gen_row.pack(fill="x", pady=(10, 0))
        ttk.Button(gen_row, text=self.T("import"), command=lambda: pick_generals()).pack(side="left")
        ttk.Label(gen_row, textvariable=generals, style="Card.TLabel").pack(side="left", padx=8)
        ttk.Label(mid, text=self.T("gens"), style="Card.TLabel").pack(anchor="w", pady=(8, 2))
        gen_box = ttk.Frame(mid, style="Card.TFrame")
        gen_box.pack(fill="x")
        gen_vars = {}

        def fill_gens(path):
            for child in gen_box.winfo_children():
                child.destroy()
            gen_vars.clear()
            if not path or not Path(path).exists():
                ttk.Label(gen_box, text=self.T("no_gen_file"), style="Card.TLabel").pack(anchor="w")
                return
            try:
                data = json.loads(Path(path).read_text(encoding="utf-8"))
            except Exception:
                ttk.Label(gen_box, text=self.T("no_gen_file"), style="Card.TLabel").pack(anchor="w")
                return
            known = s.get("generals_on")
            chosen = set(known or [])
            for spec in data.get("specialists") or []:
                name = str(spec.get("name") or spec.get("base") or "").strip()
                base = str(spec.get("base") or "")
                if not name:
                    continue
                var = tk.BooleanVar(value=known is None or name in chosen)
                gen_vars[name] = var
                line = ttk.Frame(gen_box, style="Card.TFrame")
                line.pack(anchor="w", fill="x")
                photo = self._icon(APP_DIR / "icons" / "generals" / f"{base.lower()}.png")
                if photo is not None:
                    ttk.Label(line, image=photo, style="Card.TLabel").pack(side="left")
                ttk.Checkbutton(line, text=name, variable=var).pack(side="left")

        def pick_generals():
            path = filedialog.askopenfilename(
                parent=win, filetypes=[("JSON", "*.json"), ("Vse", "*.*")],
                title=self.T("import"),
            )
            if path:
                generals.set(path)
                fill_gens(path)

        fill_gens(generals.get())

        def save():
            units = {}
            for unit, (lo, hi) in unit_vars.items():
                units[unit] = {"min": int(lo.get() or 0), "max": int(hi.get() or 0)}
            self.settings.update({
                "unit_kind": kind.get(),
                "threads": int(threads.get() or 15),
                "repetitions": int(reps.get() or 100),
                "increment": int(step_n.get() or 5),
                "step": int(click_step.get() or 5),
                "only_max": bool(only_max.get()),
                "merge": bool(merge.get()),
                "all_camps": bool(all_camps.get()),
                "skip_victory": bool(skip_victory.get()),
                "sort": key_by_sort.get(sort_box.get(), "Efficiency"),
                "exclude": [key for key, var in exclude.items() if var.get()],
                "units": units,
                "generals": generals.get().strip(),
                "generals_on": [name for name, var in gen_vars.items() if var.get()],
            })
            self._write_settings()
            self.log("Nastavitve shranjene. Start jih vpiše v simulator.")
            win.destroy()

        ttk.Button(mid, text=self.T("save"), command=save).pack(anchor="e", pady=(12, 0))


if __name__ == "__main__":
    App().mainloop()
