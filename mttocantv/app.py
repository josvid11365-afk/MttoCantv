#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MttoCantv - Registro de Mantenimiento
Gerencia General de Energía & Climatización Guárico
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import os
import sys
import shutil
import calendar
from datetime import datetime
from pathlib import Path

# ── Dependencias opcionales ───────────────────────────────────────────────────
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import cm
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                    Image as RLImage)
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
    REPORTLAB_OK = True
except ImportError:
    REPORTLAB_OK = False

try:
    from PIL import Image as PILImage, ImageTk
    PIL_OK = True
except ImportError:
    PIL_OK = False

# ── Rutas compatibles Windows / Linux ────────────────────────────────────────
APP_NAME = "mttocantv"
if sys.platform.startswith("win"):
    DATA_DIR = Path(os.environ.get("APPDATA", Path.home())) / APP_NAME
else:
    DATA_DIR = Path.home() / ".local" / "share" / APP_NAME

DB_PATH = DATA_DIR / "registros.db"
DATA_DIR.mkdir(parents=True, exist_ok=True)

def find_asset(filename):
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).parent
    else:
        exe_dir = Path(__file__).parent
    candidates = [
        exe_dir / filename,
        exe_dir / "assets" / filename,
        Path(getattr(sys, "_MEIPASS", "")) / filename,
        Path(getattr(sys, "_MEIPASS", "")) / "assets" / filename,
        Path(__file__).parent / "assets" / filename,
        Path(__file__).parent.parent / "assets" / filename,
        DATA_DIR / filename,
    ]
    if not sys.platform.startswith("win"):
        candidates.append(Path("/usr/share/mttocantv") / filename)
    for p in candidates:
        try:
            if p.exists():
                return str(p)
        except Exception:
            pass
    return None

# ── Paleta ────────────────────────────────────────────────────────────────────
C = {
    "bg":         "#F0F2F5",
    "header":     "#1A237E",
    "header_fg":  "#FFFFFF",
    "card":       "#FFFFFF",
    "accent":     "#1565C0",
    "accent2":    "#0D47A1",
    "btn_green":  "#2E7D32",
    "btn_red":    "#C62828",
    "btn_teal":   "#00695C",
    "text":       "#212121",
    "text_light": "#757575",
    "border":     "#CFD8DC",
    "row_alt":    "#F5F7FA",
    "entry_bg":   "#FAFAFA",
    "sel_bg":     "#1A237E",
    "sel_fg":     "#FFFFFF",
    "ac_bg":      "#FFFFFF",
    "ac_sel":     "#E3F2FD",
    "ac_border":  "#1565C0",
}

TIPOS = ["Preventivo", "Correctivo", "Predictivo", "Fuera de Servicio"]
TIPO_COLOR = {
    "Preventivo":        "#2E7D32",
    "Correctivo":        "#E65100",
    "Predictivo":        "#1565C0",
    "Fuera de Servicio": "#6A1B9A",
}

# ── Base de datos ─────────────────────────────────────────────────────────────
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS registros (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha     TEXT NOT NULL,
                hora      TEXT,
                central   TEXT,
                equipo    TEXT NOT NULL,
                ticket    TEXT,
                orden_srv TEXT,
                tipo      TEXT NOT NULL DEFAULT 'Preventivo',
                tecnicos  TEXT,
                actividad TEXT NOT NULL,
                notas     TEXT,
                creado_en TEXT DEFAULT (datetime('now','localtime'))
            )
        """)
        for col, defn in [("orden_srv","TEXT"),("tecnicos","TEXT"),("central","TEXT")]:
            try:
                c.execute(f"ALTER TABLE registros ADD COLUMN {col} {defn}")
            except Exception:
                pass
        c.commit()

def db_all(search="", tipo="Todos"):
    q = "SELECT * FROM registros WHERE 1=1"
    p = []
    if search:
        s = f"%{search}%"
        q += (" AND (central LIKE ? OR equipo LIKE ? OR ticket LIKE ?"
              " OR orden_srv LIKE ? OR actividad LIKE ? OR tecnicos LIKE ?)")
        p.extend([s,s,s,s,s,s])
    if tipo != "Todos":
        q += " AND tipo=?"
        p.append(tipo)
    q += " ORDER BY fecha DESC, creado_en DESC"
    with get_conn() as c:
        return c.execute(q, p).fetchall()

def db_insert(d):
    with get_conn() as c:
        c.execute("""INSERT INTO registros
            (fecha,hora,central,equipo,ticket,orden_srv,tipo,tecnicos,actividad,notas)
            VALUES(:fecha,:hora,:central,:equipo,:ticket,:orden_srv,
                   :tipo,:tecnicos,:actividad,:notas)""", d)
        c.commit()

def db_update(rid, d):
    with get_conn() as c:
        c.execute("""UPDATE registros SET
            fecha=:fecha,hora=:hora,central=:central,equipo=:equipo,
            ticket=:ticket,orden_srv=:orden_srv,tipo=:tipo,
            tecnicos=:tecnicos,actividad=:actividad,notas=:notas
            WHERE id=:id""", {**d, "id": rid})
        c.commit()

def db_delete(rid):
    with get_conn() as c:
        c.execute("DELETE FROM registros WHERE id=?", (rid,))
        c.commit()

def db_get(rid):
    with get_conn() as c:
        return c.execute("SELECT * FROM registros WHERE id=?", (rid,)).fetchone()

def db_stats():
    with get_conn() as c:
        total = c.execute("SELECT COUNT(*) FROM registros").fetchone()[0]
        prev  = c.execute("SELECT COUNT(*) FROM registros WHERE tipo='Preventivo'").fetchone()[0]
        corr  = c.execute("SELECT COUNT(*) FROM registros WHERE tipo='Correctivo'").fetchone()[0]
        pred  = c.execute("SELECT COUNT(*) FROM registros WHERE tipo='Predictivo'").fetchone()[0]
        fs    = c.execute("SELECT COUNT(*) FROM registros WHERE tipo='Fuera de Servicio'").fetchone()[0]
    return total, prev, corr, pred, fs

def db_distinct(field):
    allowed = {"central", "equipo", "tecnicos"}
    if field not in allowed:
        return []
    with get_conn() as c:
        rows = c.execute(
            f"SELECT DISTINCT {field} FROM registros "
            f"WHERE {field} IS NOT NULL AND {field} != '' "
            f"ORDER BY {field} ASC").fetchall()
    return [r[0] for r in rows]

# ── Widget Autocompletar ──────────────────────────────────────────────────────
class AutoCompleteEntry(tk.Frame):
    def __init__(self, parent, db_field, width=20, **kwargs):
        super().__init__(parent, bg=C["card"])
        self.db_field = db_field
        self._popup   = None
        self._listbox = None
        self._var     = tk.StringVar()
        self._entry   = ttk.Entry(self, textvariable=self._var, width=width)
        self._entry.pack(fill="x", expand=True)
        self._var.trace_add("write", self._on_type)
        self._entry.bind("<Down>",     self._focus_list)
        self._entry.bind("<Escape>",   lambda e: self._close_popup())
        self._entry.bind("<FocusOut>", self._on_focus_out)

    def get(self):              return self._var.get()
    def delete(self, a, b=None): self._entry.delete(a, b)
    def insert(self, idx, val): self._entry.insert(idx, val)
    def focus_set(self):        self._entry.focus_set()

    def _on_type(self, *_):
        text = self._var.get().strip().lower()
        if len(text) < 1:
            self._close_popup()
            return
        suggestions = [v for v in db_distinct(self.db_field) if text in v.lower()]
        if suggestions:
            self._show_popup(suggestions)
        else:
            self._close_popup()

    def _show_popup(self, suggestions):
        self._close_popup()
        self._entry.update_idletasks()
        x = self._entry.winfo_rootx()
        y = self._entry.winfo_rooty() + self._entry.winfo_height()
        w = self._entry.winfo_width()
        self._popup = tk.Toplevel(self._entry)
        self._popup.wm_overrideredirect(True)
        self._popup.wm_geometry(f"{w}x{min(len(suggestions),6)*24+4}+{x}+{y}")
        self._popup.configure(bg=C["ac_border"])
        frame = tk.Frame(self._popup, bg=C["ac_bg"], bd=0)
        frame.pack(fill="both", expand=True, padx=1, pady=1)
        sb = tk.Scrollbar(frame, orient="vertical")
        sb.pack(side="right", fill="y")
        self._listbox = tk.Listbox(frame, yscrollcommand=sb.set,
                                   bg=C["ac_bg"], fg=C["text"],
                                   selectbackground=C["ac_sel"],
                                   selectforeground=C["text"],
                                   font=("Helvetica",9),
                                   relief="flat", bd=0,
                                   activestyle="none",
                                   height=min(len(suggestions),6))
        sb.config(command=self._listbox.yview)
        self._listbox.pack(side="left", fill="both", expand=True)
        for s in suggestions:
            self._listbox.insert("end", s)
        self._listbox.bind("<ButtonRelease-1>", self._pick)
        self._listbox.bind("<Return>",           self._pick)
        self._listbox.bind("<Escape>",           lambda e: self._close_popup())
        self._listbox.bind("<FocusOut>",         self._on_list_focus_out)

    def _focus_list(self, event=None):
        if self._listbox:
            self._listbox.focus_set()
            self._listbox.selection_set(0)

    def _pick(self, event=None):
        if self._listbox:
            sel = self._listbox.curselection()
            if sel:
                self._var.set(self._listbox.get(sel[0]))
                self._entry.icursor("end")
        self._close_popup()
        self._entry.focus_set()

    def _close_popup(self):
        if self._popup:
            try:    self._popup.destroy()
            except Exception: pass
            self._popup   = None
            self._listbox = None

    def _on_focus_out(self, event):
        self.after(150, self._check_close)

    def _on_list_focus_out(self, event):
        self.after(150, self._check_close)

    def _check_close(self):
        try:
            focused = self._entry.focus_get()
            if self._listbox and focused != self._listbox:
                self._close_popup()
        except Exception:
            self._close_popup()

# ── Widget Calendario ─────────────────────────────────────────────────────────
class CalendarPicker(tk.Toplevel):
    def __init__(self, parent, callback, initial=None):
        super().__init__(parent)
        self.callback = callback
        self.title("Seleccionar Fecha")
        self.resizable(False, False)
        self.configure(bg=C["card"])
        self.grab_set()
        self.lift()
        self.focus_force()
        now = initial if initial else datetime.today()
        self._year  = now.year
        self._month = now.month
        self._build()

    def _build(self):
        for w in self.winfo_children():
            w.destroy()

        MESES = ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
                 "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]

        # Navegación
        nav = tk.Frame(self, bg=C["header"])
        nav.pack(fill="x")
        tk.Button(nav, text="◀", bg=C["header"], fg="white", bd=0,
                  font=("Helvetica",11,"bold"), activebackground=C["accent"],
                  command=self._prev).pack(side="left", padx=8, pady=6)
        tk.Label(nav, text=f"{MESES[self._month-1]} {self._year}",
                 bg=C["header"], fg="white",
                 font=("Helvetica",11,"bold")).pack(side="left", expand=True)
        tk.Button(nav, text="▶", bg=C["header"], fg="white", bd=0,
                  font=("Helvetica",11,"bold"), activebackground=C["accent"],
                  command=self._next).pack(side="right", padx=8, pady=6)

        # Días de la semana
        df = tk.Frame(self, bg=C["card"], pady=4)
        df.pack(padx=10)
        for i, d in enumerate(["Lu","Ma","Mi","Ju","Vi","Sa","Do"]):
            tk.Label(df, text=d, width=4, bg=C["card"],
                     fg=C["text_light"],
                     font=("Helvetica",9,"bold")).grid(row=0, column=i, padx=1)

        # Días del mes
        first_wd      = calendar.monthrange(self._year, self._month)[0]
        days_in_month = calendar.monthrange(self._year, self._month)[1]
        today         = datetime.today()

        cf = tk.Frame(self, bg=C["card"])
        cf.pack(padx=10, pady=(0,4))

        day = 1
        for week in range(6):
            for wd in range(7):
                if week * 7 + wd >= first_wd and day <= days_in_month:
                    is_today = (today.day == day and
                                today.month == self._month and
                                today.year  == self._year)
                    bg = C["header"] if is_today else C["card"]
                    fg = "white"     if is_today else C["text"]
                    tk.Button(cf, text=str(day), width=4,
                              bg=bg, fg=fg, relief="flat", bd=0,
                              font=("Helvetica",10),
                              activebackground=C["ac_sel"],
                              command=lambda d=day: self._pick(d)
                              ).grid(row=week, column=wd, padx=1, pady=1, ipady=3)
                    day += 1
                else:
                    tk.Label(cf, text="", width=4,
                             bg=C["card"]).grid(row=week, column=wd)
            if day > days_in_month:
                break

        # Botón Hoy
        tk.Button(self, text="  Hoy  ", bg=C["accent"], fg="white", bd=0,
                  font=("Helvetica",9,"bold"),
                  activebackground=C["accent2"],
                  command=lambda: self._pick_date(datetime.today())
                  ).pack(pady=(0,10))

    def _prev(self):
        if self._month == 1:
            self._month = 12
            self._year -= 1
        else:
            self._month -= 1
        self._build()

    def _next(self):
        if self._month == 12:
            self._month = 1
            self._year += 1
        else:
            self._month += 1
        self._build()

    def _pick(self, day):
        self._pick_date(datetime(self._year, self._month, day))

    def _pick_date(self, d):
        self.callback(d)
        self.destroy()

# ── Aplicación principal ──────────────────────────────────────────────────────
class MttoCantvApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MttoCantv – Registro de Mantenimiento")
        self.geometry("1180x820")
        self.minsize(960, 640)
        self.configure(bg=C["bg"])

        icon_path = find_asset("icon.png")
        if icon_path and PIL_OK:
            try:
                img = PILImage.open(icon_path).resize((32,32), PILImage.LANCZOS)
                self._icon = ImageTk.PhotoImage(img)
                self.iconphoto(True, self._icon)
            except Exception:
                pass

        init_db()
        self._styles()
        self._build_header()
        self._build_search_bar()
        self._build_form()
        self._build_table()
        self._refresh()
        self._hora_var.set(datetime.now().strftime("%I:%M"))
        self._ampm_var.set(datetime.now().strftime("%p"))

    # ── Estilos ───────────────────────────────────────────────────────────────
    def _styles(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure("TFrame",      background=C["bg"])
        s.configure("Card.TFrame", background=C["card"])
        s.configure("TLabel",      background=C["bg"],   foreground=C["text"], font=("Helvetica",10))
        s.configure("Card.TLabel", background=C["card"], foreground=C["text"], font=("Helvetica",10))
        s.configure("TEntry",      fieldbackground=C["entry_bg"])
        s.configure("TCombobox",   fieldbackground=C["entry_bg"])
        s.configure("Treeview",
            background=C["card"], fieldbackground=C["card"],
            foreground=C["text"], rowheight=30,
            font=("Helvetica",9), borderwidth=0)
        s.configure("Treeview.Heading",
            background=C["header"], foreground="white",
            font=("Helvetica",9,"bold"), relief="flat")
        s.map("Treeview",
            background=[("selected", C["sel_bg"])],
            foreground=[("selected", C["sel_fg"])])

    # ── Cabecera: banner centrado + título debajo ─────────────────────────────
    def _build_header(self):
        hdr = tk.Frame(self, bg=C["header"])
        hdr.pack(fill="x")

        # Banner centrado
        banner_path = find_asset("banner.png")
        if banner_path and PIL_OK:
            try:
                img = PILImage.open(banner_path)
                ratio = 80 / img.height
                img = img.resize((int(img.width * ratio), 80), PILImage.LANCZOS)
                self._banner_img = ImageTk.PhotoImage(img)
                tk.Label(hdr, image=self._banner_img,
                         bg=C["header"]).pack(pady=(8,2))
            except Exception:
                tk.Label(hdr, text="⚙", bg=C["header"], fg="white",
                         font=("Helvetica",32)).pack(pady=(8,2))
        else:
            tk.Label(hdr, text="⚙", bg=C["header"], fg="white",
                     font=("Helvetica",32)).pack(pady=(8,2))

        # Título debajo del banner, centrado
        tk.Label(hdr,
                 text="GERENCIA GENERAL DE ENERGÍA & CLIMATIZACIÓN GUÁRICO",
                 bg=C["header"], fg="white",
                 font=("Helvetica",13,"bold")).pack()
        tk.Label(hdr,
                 text="MttoCantv – Sistema de Registro de Mantenimiento",
                 bg=C["header"], fg="#90CAF9",
                 font=("Helvetica",9)).pack(pady=(0,8))

    # ── Barra de búsqueda y filtros ───────────────────────────────────────────
    def _build_search_bar(self):
        bar = tk.Frame(self, bg=C["card"])
        bar.pack(fill="x")
        tk.Frame(bar, bg=C["border"], height=1).pack(fill="x")
        inner = tk.Frame(bar, bg=C["card"])
        inner.pack(fill="x", padx=12, pady=6)

        tk.Label(inner, text="🔍", bg=C["card"],
                 font=("Helvetica",11)).pack(side="left")
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._refresh())
        ttk.Entry(inner, textvariable=self._search_var,
                  width=32).pack(side="left", padx=(2,12), ipady=3)

        tk.Label(inner, text="Tipo:", bg=C["card"], fg=C["text_light"],
                 font=("Helvetica",9)).pack(side="left")
        self._filter_tipo = tk.StringVar(value="Todos")
        cb = ttk.Combobox(inner, textvariable=self._filter_tipo,
                          width=18, values=["Todos"]+TIPOS, state="readonly")
        cb.pack(side="left", padx=(2,0))
        cb.bind("<<ComboboxSelected>>", lambda _: self._refresh())

    # ── Formulario ────────────────────────────────────────────────────────────
    def _build_form(self):
        self._edit_id = None

        outer = tk.Frame(self, bg=C["card"])
        outer.pack(fill="x", padx=10, pady=(8,0))

        # Título sección
        title_bar = tk.Frame(outer, bg=C["accent"])
        title_bar.pack(fill="x")
        tk.Label(title_bar, text="  Registrar Nueva Intervención",
                 bg=C["accent"], fg="white",
                 font=("Helvetica",10,"bold"), pady=5).pack(side="left")
        self._form_lbl = tk.Label(title_bar, text="",
                 bg=C["accent"], fg="#BBDEFB", font=("Helvetica",9))
        self._form_lbl.pack(side="left")

        form = tk.Frame(outer, bg=C["card"], padx=14, pady=10)
        form.pack(fill="x")

        # Anchos uniformes por tipo de campo
        W_HALF  = 28   # campos de media línea
        W_FULL  = 58   # campos de línea completa
        W_SHORT = 14   # campos cortos (fecha, hora)
        W_MED   = 20   # campos medianos

        def lbl(text, row, col, span=1, bg=C["card"]):
            tk.Label(form, text=text, bg=bg, fg=C["text_light"],
                     font=("Helvetica",8,"bold")).grid(
                         row=row, column=col, columnspan=span,
                         sticky="w", padx=(0,4), pady=(8,0))

        def plain_entry(row, col, width=W_HALF, span=1):
            e = ttk.Entry(form, width=width)
            e.grid(row=row, column=col, columnspan=span,
                   sticky="ew", padx=(0,8), pady=(2,0))
            return e

        def ac_entry(row, col, field, width=W_HALF, span=1):
            w = AutoCompleteEntry(form, db_field=field, width=width)
            w.grid(row=row, column=col, columnspan=span,
                   sticky="ew", padx=(0,8), pady=(2,0))
            return w

        def text_area(row, col, span=1, height=5):
            t = tk.Text(form, height=height,
                        bg=C["entry_bg"], fg=C["text"],
                        relief="flat", bd=1,
                        font=("Helvetica",10),
                        highlightbackground=C["border"],
                        highlightthickness=1)
            t.grid(row=row, column=col, columnspan=span,
                   sticky="ew", padx=(0,8), pady=(2,0))
            return t

        form.columnconfigure(0, weight=1)
        form.columnconfigure(1, weight=1)
        form.columnconfigure(2, weight=1)
        form.columnconfigure(3, weight=1)

        # ── Fila 0-1: Central ────────────────────────────────────────────────
        lbl("Central:", 0, 0, span=4)
        self._central_ac = ac_entry(1, 0, "central", width=W_FULL, span=4)

        # ── Fila 2-3: Técnicos ───────────────────────────────────────────────
        lbl("Técnicos Responsables (Nombre P00, ...):", 2, 0, span=4)
        self._tecnicos_ac = ac_entry(3, 0, "tecnicos", width=W_FULL, span=4)

        # ── Separador visual ─────────────────────────────────────────────────
        tk.Frame(form, bg=C["border"], height=1).grid(
            row=4, column=0, columnspan=4, sticky="ew", pady=(10,0))

        # ── Fila 5-6: Tipo | Equipo ──────────────────────────────────────────
        lbl("Tipo de Mantenimiento:", 5, 0, span=2)
        lbl("Equipo Intervenido:",    5, 2, span=2)

        self._tipo_var = tk.StringVar(value="Preventivo")
        ttk.Combobox(form, textvariable=self._tipo_var,
                     values=TIPOS, state="readonly", width=W_HALF
                     ).grid(row=6, column=0, columnspan=2,
                            sticky="ew", padx=(0,8), pady=(2,0))
        self._equipo_ac = ac_entry(6, 2, "equipo", width=W_HALF, span=2)

        # ── Separador visual ─────────────────────────────────────────────────
        tk.Frame(form, bg=C["border"], height=1).grid(
            row=7, column=0, columnspan=4, sticky="ew", pady=(10,0))

        # ── Fila 8-9: Fecha | Hora | Orden de Servicio | N° Ticket ──────────
        lbl("Fecha:",             8, 0)
        lbl("Hora:",              8, 1)
        lbl("Orden de Servicio:", 8, 2)
        lbl("N° Ticket:",         8, 3)

        # Fecha con calendario
        fecha_frame = tk.Frame(form, bg=C["card"])
        fecha_frame.grid(row=9, column=0, sticky="ew", padx=(0,8), pady=(2,0))
        self._fecha_var = tk.StringVar(value=datetime.today().strftime("%d/%m/%Y"))
        ttk.Entry(fecha_frame, textvariable=self._fecha_var,
                  width=W_SHORT).pack(side="left")
        tk.Button(fecha_frame, text="📆", bg=C["card"], bd=0,
                  font=("Helvetica",12), cursor="hand2",
                  activebackground=C["bg"],
                  command=self._open_cal).pack(side="left", padx=(2,0))

        # Hora 12h
        hora_frame = tk.Frame(form, bg=C["card"])
        hora_frame.grid(row=9, column=1, sticky="ew", padx=(0,8), pady=(2,0))
        self._hora_var = tk.StringVar()
        ttk.Entry(hora_frame, textvariable=self._hora_var,
                  width=W_SHORT).pack(side="left")
        self._ampm_var = tk.StringVar(value="AM")
        ttk.Combobox(hora_frame, textvariable=self._ampm_var,
                     values=["AM","PM"], state="readonly",
                     width=5).pack(side="left", padx=(2,0))

        self._orden_e  = plain_entry(9, 2, width=W_MED)
        self._ticket_e = plain_entry(9, 3, width=W_MED)

        # ── Separador visual ─────────────────────────────────────────────────
        tk.Frame(form, bg=C["border"], height=1).grid(
            row=10, column=0, columnspan=4, sticky="ew", pady=(10,0))

        # ── Fila 11-12: Actividad Realizada ──────────────────────────────────
        lbl("Actividad Realizada:", 11, 0, span=4)
        self._actividad_t = text_area(12, 0, span=4, height=5)

        # ── Fila 13-14: Notas Adicionales ────────────────────────────────────
        lbl("Notas Adicionales:", 13, 0, span=4)
        self._notas_t = text_area(14, 0, span=4, height=5)

        # ── Fila 15: TODOS LOS BOTONES AL MISMO NIVEL ────────────────────────
        btn_row = tk.Frame(form, bg=C["card"])
        btn_row.grid(row=15, column=0, columnspan=4,
                     sticky="ew", pady=(12,2))

        def btn(parent, text, color, cmd, side="left", padx=(0,6)):
            tk.Button(parent, text=text, bg=color, fg="white", bd=0,
                      font=("Helvetica",9,"bold"), padx=12, pady=6,
                      cursor="hand2",
                      activebackground=color,
                      command=cmd).pack(side=side, padx=padx)

        # Izquierda: acciones del registro
        self._save_btn = tk.Button(btn_row,
                                   text="💾  GUARDAR REGISTRO",
                                   bg=C["accent"], fg="white", bd=0,
                                   font=("Helvetica",9,"bold"),
                                   padx=12, pady=6, cursor="hand2",
                                   command=self._save)
        self._save_btn.pack(side="left", padx=(0,6))

        tk.Button(btn_row, text="🧹  LIMPIAR",
                  bg=C["text_light"], fg="white", bd=0,
                  font=("Helvetica",9,"bold"), padx=12, pady=6,
                  cursor="hand2", command=self._clear
                  ).pack(side="left", padx=(0,0))

        # Separador visual entre grupos
        tk.Frame(btn_row, bg=C["border"], width=1
                 ).pack(side="left", fill="y", padx=16)

        # Derecha: gestión de datos
        btn(btn_row, "📄  Exportar PDF",  C["btn_red"],   self._export_pdf)
        btn(btn_row, "💾  Guardar BD",    C["btn_green"],  self._save_db)
        btn(btn_row, "📂  Cargar BD",     C["btn_teal"],  self._load_db,
            padx=(0,0))

    def _open_cal(self):
        try:
            d = datetime.strptime(self._fecha_var.get(), "%d/%m/%Y")
        except Exception:
            d = datetime.today()
        CalendarPicker(self,
                       lambda date: self._fecha_var.set(date.strftime("%d/%m/%Y")),
                       d)

    def _get_data(self):
        return {
            "fecha":     self._fecha_var.get().strip(),
            "hora":      f"{self._hora_var.get().strip()} {self._ampm_var.get()}",
            "central":   self._central_ac.get().strip(),
            "equipo":    self._equipo_ac.get().strip(),
            "ticket":    self._ticket_e.get().strip(),
            "orden_srv": self._orden_e.get().strip(),
            "tipo":      self._tipo_var.get(),
            "tecnicos":  self._tecnicos_ac.get().strip(),
            "actividad": self._actividad_t.get("1.0","end-1c").strip(),
            "notas":     self._notas_t.get("1.0","end-1c").strip(),
        }

    def _clear(self):
        self._edit_id = None
        self._form_lbl.config(text="")
        self._save_btn.config(text="💾  GUARDAR REGISTRO", bg=C["accent"])
        self._fecha_var.set(datetime.today().strftime("%d/%m/%Y"))
        self._hora_var.set(datetime.now().strftime("%I:%M"))
        self._ampm_var.set(datetime.now().strftime("%p"))
        for w in [self._central_ac, self._equipo_ac, self._tecnicos_ac]:
            w.delete(0, "end")
        for e in [self._ticket_e, self._orden_e]:
            e.delete(0, "end")
        self._tipo_var.set("Preventivo")
        self._actividad_t.delete("1.0","end")
        self._notas_t.delete("1.0","end")

    def _save(self):
        d = self._get_data()
        if not d["fecha"] or not d["equipo"] or not d["actividad"]:
            messagebox.showwarning("Campos requeridos",
                "Fecha, Equipo y Actividad son obligatorios.")
            return
        if self._edit_id:
            db_update(self._edit_id, d)
        else:
            db_insert(d)
        self._clear()
        self._refresh()

    def _load_for_edit(self, rid):
        row = db_get(rid)
        if not row:
            return
        self._edit_id = rid
        self._form_lbl.config(text=f"  ← Editando registro #{rid}")
        self._save_btn.config(text="✏  ACTUALIZAR REGISTRO", bg="#E65100")

        self._fecha_var.set(row["fecha"] or "")
        hp = (row["hora"] or "12:00 AM").rsplit(" ",1)
        self._hora_var.set(hp[0])
        self._ampm_var.set(hp[1] if len(hp)==2 else "AM")

        for w, val in [
            (self._central_ac,  row["central"]   or ""),
            (self._equipo_ac,   row["equipo"]    or ""),
            (self._tecnicos_ac, row["tecnicos"]  or ""),
        ]:
            w.delete(0,"end"); w.insert(0, val)

        for e, val in [
            (self._ticket_e, row["ticket"]    or ""),
            (self._orden_e,  row["orden_srv"] or ""),
        ]:
            e.delete(0,"end"); e.insert(0, val)

        self._tipo_var.set(row["tipo"] or "Preventivo")
        self._actividad_t.delete("1.0","end")
        self._actividad_t.insert("1.0", row["actividad"] or "")
        self._notas_t.delete("1.0","end")
        self._notas_t.insert("1.0", row["notas"] or "")
        self._central_ac.focus_set()

    # ── Tabla ─────────────────────────────────────────────────────────────────
    def _build_table(self):
        outer = tk.Frame(self, bg=C["bg"])
        outer.pack(fill="both", expand=True, padx=10, pady=8)

        th = tk.Frame(outer, bg=C["accent2"])
        th.pack(fill="x")
        tk.Label(th, text="  Registros de Intervención",
                 bg=C["accent2"], fg="white",
                 font=("Helvetica",10,"bold"), pady=4).pack(side="left")
        self._count_lbl = tk.Label(th, text="", bg=C["accent2"],
                                   fg="#BBDEFB", font=("Helvetica",9))
        self._count_lbl.pack(side="right", padx=8)

        cols = ("fecha","hora","central","equipo","tipo",
                "ticket","orden","tecnicos","actividad","notas")
        hdrs = ("Fecha","Hora","Central","Equipo","Tipo",
                "Ticket","O.S.","Técnicos","Actividad","Notas")
        wids = (90,75,120,130,105,80,80,150,230,130)

        ft = tk.Frame(outer, bg=C["card"])
        ft.pack(fill="both", expand=True)

        vsb = ttk.Scrollbar(ft, orient="vertical")
        hsb = ttk.Scrollbar(ft, orient="horizontal")
        vsb.pack(side="right",  fill="y")
        hsb.pack(side="bottom", fill="x")

        self._tree = ttk.Treeview(ft, columns=cols, show="headings",
                                  yscrollcommand=vsb.set,
                                  xscrollcommand=hsb.set,
                                  selectmode="browse")
        vsb.config(command=self._tree.yview)
        hsb.config(command=self._tree.xview)

        for col, hdr, w in zip(cols, hdrs, wids):
            self._tree.heading(col, text=hdr)
            self._tree.column(col, width=w, minwidth=40,
                              stretch=(col in ("actividad","notas")))

        for t, color in TIPO_COLOR.items():
            self._tree.tag_configure(t, foreground=color)
        self._tree.tag_configure("alt", background=C["row_alt"])
        self._tree.pack(fill="both", expand=True)
        self._tree.bind("<Double-1>", lambda e: self._edit_selected())

        act = tk.Frame(outer, bg=C["bg"], pady=4)
        act.pack(fill="x")
        tk.Button(act, text="✏  Editar seleccionado",
                  bg=C["accent"], fg="white", bd=0,
                  font=("Helvetica",9,"bold"), padx=10, pady=4,
                  cursor="hand2",
                  command=self._edit_selected).pack(side="left", padx=(0,6))
        tk.Button(act, text="🗑  Eliminar seleccionado",
                  bg=C["btn_red"], fg="white", bd=0,
                  font=("Helvetica",9,"bold"), padx=10, pady=4,
                  cursor="hand2",
                  command=self._delete_selected).pack(side="left")

    def _refresh(self):
        search = self._search_var.get() if hasattr(self,"_search_var") else ""
        tipo   = self._filter_tipo.get() if hasattr(self,"_filter_tipo") else "Todos"
        rows   = db_all(search, tipo)
        for i in self._tree.get_children():
            self._tree.delete(i)
        for idx, r in enumerate(rows):
            tags = [r["tipo"]]
            if idx % 2: tags.append("alt")
            self._tree.insert("","end", iid=str(r["id"]),
                values=(r["fecha"] or "", r["hora"] or "",
                        r["central"] or "", r["equipo"], r["tipo"],
                        r["ticket"] or "", r["orden_srv"] or "",
                        r["tecnicos"] or "", r["actividad"],
                        r["notas"] or ""),
                tags=tags)
        total = db_stats()[0]
        self._count_lbl.config(text=f"{len(rows)} de {total} registros  ")

    def _sel_id(self):
        s = self._tree.selection()
        return int(s[0]) if s else None

    def _edit_selected(self):
        rid = self._sel_id()
        if rid:
            self._load_for_edit(rid)
        else:
            messagebox.showinfo("MttoCantv","Selecciona un registro para editar.")

    def _delete_selected(self):
        rid = self._sel_id()
        if not rid:
            messagebox.showinfo("MttoCantv","Selecciona un registro para eliminar.")
            return
        if messagebox.askyesno("Confirmar",
                "¿Eliminar este registro?\nEsta acción no se puede deshacer."):
            db_delete(rid)
            self._refresh()

    # ── Backup ────────────────────────────────────────────────────────────────
    def _save_db(self):
        dest = filedialog.asksaveasfilename(
            title="Guardar copia de la base de datos",
            defaultextension=".db",
            filetypes=[("SQLite DB","*.db"),("Todos","*.*")],
            initialfile=f"mttocantv_{datetime.today().strftime('%Y%m%d')}.db")
        if dest:
            shutil.copy2(DB_PATH, dest)
            messagebox.showinfo("MttoCantv", f"Base de datos guardada en:\n{dest}")

    def _load_db(self):
        src = filedialog.askopenfilename(
            title="Cargar base de datos",
            filetypes=[("SQLite DB","*.db"),("Todos","*.*")])
        if src:
            if messagebox.askyesno("Confirmar",
                    "Esto reemplazará todos los registros actuales.\n¿Continuar?"):
                shutil.copy2(src, DB_PATH)
                init_db()
                self._refresh()
                messagebox.showinfo("MttoCantv","Base de datos cargada correctamente.")

    # ── Exportar PDF ──────────────────────────────────────────────────────────
    def _export_pdf(self):
        if not REPORTLAB_OK:
            messagebox.showerror("MttoCantv",
                "Falta la librería 'reportlab'.\n\nInstálala con:\n  pip install reportlab")
            return
        rid = self._sel_id()
        if not rid:
            messagebox.showinfo("MttoCantv",
                "Selecciona un registro en la tabla para exportar su reporte PDF.")
            return
        row = db_get(rid)
        if not row:
            return
        dest = filedialog.asksaveasfilename(
            title="Guardar reporte PDF",
            defaultextension=".pdf",
            filetypes=[("PDF","*.pdf")],
            initialfile=f"Informe_{row['tipo']}_{row['fecha'].replace('/','')}.pdf")
        if not dest:
            return
        self._generate_pdf(row, dest)
        messagebox.showinfo("MttoCantv", f"Reporte exportado:\n{dest}")
        try:
            import subprocess
            if sys.platform.startswith("win"):
                os.startfile(dest)
            else:
                subprocess.Popen(["xdg-open", dest])
        except Exception:
            pass

    def _generate_pdf(self, row, dest):
        doc = SimpleDocTemplate(dest, pagesize=letter,
                                leftMargin=2.5*cm, rightMargin=2.5*cm,
                                topMargin=2*cm, bottomMargin=2*cm)
        styles = getSampleStyleSheet()
        story  = []

        def sty(name, **kw):
            return ParagraphStyle(name, parent=styles["Normal"], **kw)

        title_sty   = sty("T",  fontSize=12, alignment=TA_CENTER,
                          spaceAfter=2, leading=16, fontName="Helvetica-Bold")
        section_sty = sty("S",  fontSize=11, spaceBefore=12, spaceAfter=4,
                          fontName="Helvetica-Bold")
        body_sty    = sty("B",  fontSize=10, leading=14, alignment=TA_JUSTIFY)
        bullet_sty  = sty("BU", fontSize=10, leading=14, leftIndent=20)

        banner_path = find_asset("banner.png")
        if banner_path and PIL_OK:
            try:
                story.append(RLImage(banner_path, width=16*cm, height=3*cm))
                story.append(Spacer(1, 0.3*cm))
            except Exception:
                pass

        for line in [
            "GERENCIA GENERAL DE ENERGÍA Y CLIMATIZACIÓN",
            "GERENCIA DE O&M",
            "COORDINACIÓN EDO.  GUÁRICO.",
            "ALTAGRACIA DE ORITICO.",
        ]:
            story.append(Paragraph(line, title_sty))

        story.append(Spacer(1, 0.5*cm))
        story.append(Paragraph(
            f"INFORME DE MANTENIMIENTO: {row['tipo'].upper()}",
            sty("IT", fontSize=11, fontName="Helvetica-Bold",
                spaceBefore=6, spaceAfter=8)))

        story.append(Paragraph("1. DATOS GENERALES", section_sty))
        story.append(Paragraph(f"• Ubicación: {row['central'] or '—'}", bullet_sty))
        story.append(Paragraph(f"• Fecha de Ejecución: {row['fecha']}", bullet_sty))
        story.append(Paragraph(f"• Hora: {row['hora'] or '—'}", bullet_sty))
        story.append(Paragraph(f"• Personal Técnico: {row['tecnicos'] or '—'}", bullet_sty))

        story.append(Paragraph("2. EQUIPO INTERVENIDO", section_sty))
        story.append(Paragraph(f"• Equipo: {row['equipo']}", bullet_sty))

        story.append(Paragraph("3. ACTIVIDADES REALIZADAS", section_sty))
        story.append(Paragraph(
            (row["actividad"] or "").replace("\n","<br/>"), body_sty))

        story.append(Spacer(1, 0.5*cm))
        story.append(Paragraph(f"• Ticket #: {row['ticket'] or '—'}", bullet_sty))
        story.append(Paragraph(
            f"• Orden de Servicio: {row['orden_srv'] or '—'}", bullet_sty))

        if row["notas"]:
            story.append(Spacer(1, 0.4*cm))
            story.append(Paragraph("4. NOTAS ADICIONALES", section_sty))
            story.append(Paragraph(
                row["notas"].replace("\n","<br/>"), body_sty))

        doc.build(story)


def main():
    app = MttoCantvApp()
    app.mainloop()

if __name__ == "__main__":
    main()
