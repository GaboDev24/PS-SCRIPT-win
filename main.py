"""
main.py
Interfaz grafica de la herramienta de generacion de tarjetas desde Photoshop.
Usa customtkinter para un aspecto moderno con el sistema de diseno tactico.
Mejorado con flujo paso a paso, indicadores de estado y tooltips.
"""

from __future__ import annotations

import threading
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Optional

import customtkinter as ctk

import photoshop_manager as ps_mgr

# ---------------------------------------------------------------------------
# Datos de nombre / cargado desde Excel o CSV
# ---------------------------------------------------------------------------

def load_names_from_file(path: str) -> list[str]:
    """
    Lee nombres desde un archivo CSV o Excel (.xlsx / .xls).
    Toma la primera columna con datos no vacios.
    """
    p = Path(path)
    ext = p.suffix.lower()

    if ext == ".csv":
        import csv
        names: list[str] = []
        with open(p, newline="", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            for row in reader:
                if row and row[0].strip():
                    names.append(row[0].strip())
        return names

    elif ext in (".xlsx", ".xls"):
        import pandas as pd
        df = pd.read_excel(p, header=None, dtype=str)
        col = df.iloc[:, 0].dropna().str.strip()
        return [v for v in col if v]

    else:
        raise ValueError(f"Formato de archivo no soportado: {ext}. Use .csv, .xlsx o .xls")


# ---------------------------------------------------------------------------
# Paleta de colores (basada en DESIGN.md - sistema tactico)
# ---------------------------------------------------------------------------

COLORS = {
    "bg":            "#0d0d0d",
    "bg_card":       "#121212",
    "bg_input":      "#1a1a1a",
    "red":           "#A30000",
    "red_hover":     "#c40000",
    "red_dim":       "#6B0000",
    "border":        "#2a0000",
    "border_active": "#A30000",
    "border_done":   "#1a3a1a",
    "text":          "#F5F5F5",
    "text_dim":      "#888888",
    "text_muted":    "#444444",
    "success":       "#22c55e",
    "success_dim":   "#143d21",
    "warning":       "#f59e0b",
    "warning_dim":   "#3d2e03",
    "error":         "#ef4444",
    "step_pending":  "#333333",
    "step_active":   "#A30000",
    "step_done":     "#22c55e",
}

FONT_MONO    = ("Share Tech Mono", 11)
FONT_MONO_SM = ("Share Tech Mono", 9)
FONT_MONO_XS = ("Share Tech Mono", 8)
FONT_HEAD    = ("Barlow Condensed", 22, "bold")
FONT_LABEL   = ("Share Tech Mono", 9)
FONT_TITLE   = ("Barlow Condensed", 11, "bold")


# ---------------------------------------------------------------------------
# Componentes de UI reutilizables
# ---------------------------------------------------------------------------

def make_label(parent, text: str, is_header: bool = False, **kwargs) -> ctk.CTkLabel:
    if is_header:
        return ctk.CTkLabel(
            parent, text=text,
            font=FONT_HEAD,
            text_color=COLORS["red"],
            **kwargs,
        )
    return ctk.CTkLabel(
        parent, text=text,
        font=FONT_LABEL,
        text_color=COLORS["text_dim"],
        **kwargs,
    )


def make_button(parent, text: str, command, primary: bool = True, **kwargs) -> ctk.CTkButton:
    if primary:
        return ctk.CTkButton(
            parent, text=text, command=command,
            fg_color=COLORS["red"],
            hover_color=COLORS["red_hover"],
            text_color=COLORS["text"],
            font=FONT_MONO,
            corner_radius=0,
            **kwargs,
        )
    return ctk.CTkButton(
        parent, text=text, command=command,
        fg_color=COLORS["bg_input"],
        hover_color=COLORS["bg_card"],
        text_color=COLORS["text_dim"],
        border_color=COLORS["border"],
        border_width=1,
        font=FONT_MONO,
        corner_radius=0,
        **kwargs,
    )


def make_entry(parent, **kwargs) -> ctk.CTkEntry:
    return ctk.CTkEntry(
        parent,
        fg_color=COLORS["bg_input"],
        border_color=COLORS["border"],
        text_color=COLORS["text"],
        placeholder_text_color=COLORS["text_muted"],
        font=FONT_MONO,
        corner_radius=0,
        **kwargs,
    )


def make_separator(parent):
    return ctk.CTkFrame(
        parent,
        height=1,
        fg_color=COLORS["border"],
        corner_radius=0,
    )


# ---------------------------------------------------------------------------
# Tooltip simple
# ---------------------------------------------------------------------------

class Tooltip:
    """Muestra un tooltip al hacer hover sobre un widget."""

    def __init__(self, widget, text: str):
        self.widget = widget
        self.text = text
        self._tip_window: Optional[object] = None
        widget.bind("<Enter>", self._show)
        widget.bind("<Leave>", self._hide)

    def _show(self, event=None):
        if self._tip_window:
            return
        x = self.widget.winfo_rootx()
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4

        import tkinter as tk
        tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tw.configure(bg=COLORS["bg_card"])

        frame = tk.Frame(tw, bg=COLORS["bg_card"], bd=1, relief="solid",
                         highlightbackground=COLORS["border"], highlightthickness=1)
        frame.pack()

        tk.Label(
            frame,
            text=self.text,
            bg=COLORS["bg_card"],
            fg=COLORS["text_dim"],
            font=("Share Tech Mono", 8),
            padx=8, pady=4,
            wraplength=280,
            justify="left",
        ).pack()

        self._tip_window = tw

    def _hide(self, event=None):
        if self._tip_window:
            self._tip_window.destroy()
            self._tip_window = None


# ---------------------------------------------------------------------------
# Ventana principal
# ---------------------------------------------------------------------------

class App(ctk.CTk):

    # Constantes de estado de cada paso
    STATE_PENDING = "pending"
    STATE_ACTIVE  = "active"
    STATE_DONE    = "done"

    def __init__(self):
        super().__init__()

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.title("PS Card Generator")
        self.geometry("880x820")
        self.minsize(740, 700)
        self.configure(fg_color=COLORS["bg"])
        self.resizable(True, True)

        # Estado interno
        self._psd_path: Optional[str] = None
        self._output_folder: Optional[str] = None
        self._layer_names: list[str] = []
        self._is_generating: bool = False

        # Estados de cada paso para los indicadores
        self._step_states: dict[int, str] = {
            1: self.STATE_ACTIVE,   # PSD - activo desde el inicio
            2: self.STATE_PENDING,
            3: self.STATE_PENDING,
            4: self.STATE_PENDING,
            5: self.STATE_PENDING,
        }

        self._build_ui()

    # -----------------------------------------------------------------------
    # Construccion de la interfaz
    # -----------------------------------------------------------------------

    def _build_ui(self):
        # --- Encabezado -------------------------------------------------------
        header = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=0)
        header.pack(fill="x", padx=0, pady=(0, 1))

        left_bar = ctk.CTkFrame(header, width=4, fg_color=COLORS["red"], corner_radius=0)
        left_bar.pack(side="left", fill="y")

        title_block = ctk.CTkFrame(header, fg_color="transparent")
        title_block.pack(side="left", padx=(16, 0), pady=14)

        ctk.CTkLabel(
            title_block,
            text="PS CARD GENERATOR",
            font=("Barlow Condensed", 28, "bold"),
            text_color=COLORS["text"],
        ).pack(anchor="w")

        ctk.CTkLabel(
            title_block,
            text="PHOTOSHOP AUTOMATION TOOL  //  GENERACION MASIVA DE TARJETAS",
            font=FONT_MONO_SM,
            text_color=COLORS["text_muted"],
        ).pack(anchor="w")

        # Badge version
        ctk.CTkLabel(
            header,
            text="v2.0",
            font=FONT_MONO_XS,
            text_color=COLORS["red"],
            fg_color=COLORS["bg_input"],
            corner_radius=0,
            padx=6, pady=2,
        ).pack(side="right", padx=16, pady=14)

        # Separador
        make_separator(self).pack(fill="x")

        # --- Indicador de pasos (stepper) ------------------------------------
        self._stepper_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=0)
        self._stepper_frame.pack(fill="x", padx=0, pady=(0, 1))
        self._build_stepper()

        make_separator(self).pack(fill="x")

        # --- Cuerpo principal en scroll ---------------------------------------
        scroll = ctk.CTkScrollableFrame(
            self,
            fg_color=COLORS["bg"],
            scrollbar_button_color=COLORS["bg_input"],
            scrollbar_button_hover_color=COLORS["border"],
            corner_radius=0,
        )
        scroll.pack(fill="both", expand=True, padx=0, pady=0)

        content = ctk.CTkFrame(scroll, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=28, pady=20)

        # --- Secciones -------------------------------------------------------
        self._section_psd(content)
        self._section_layer(content)
        self._section_names(content)
        self._section_output(content)
        self._section_format(content)

        # --- Separador + footer ----------------------------------------------
        make_separator(self).pack(fill="x")
        self._build_footer()

        # Actualizar estado inicial
        self._refresh_generate_btn()

    def _build_stepper(self):
        """Construye la barra de progreso de pasos en la parte superior."""
        steps = [
            (1, "PLANTILLA"),
            (2, "CAPA"),
            (3, "NOMBRES"),
            (4, "DESTINO"),
            (5, "FORMATO"),
        ]

        self._step_labels: dict[int, ctk.CTkLabel] = {}
        self._step_dots:   dict[int, ctk.CTkLabel] = {}

        container = ctk.CTkFrame(self._stepper_frame, fg_color="transparent")
        container.pack(pady=10, padx=24)

        for i, (num, label) in enumerate(steps):
            step_col = ctk.CTkFrame(container, fg_color="transparent")
            step_col.pack(side="left")

            # Circulo numerado
            dot = ctk.CTkLabel(
                step_col,
                text=str(num),
                font=("Barlow Condensed", 12, "bold"),
                width=26, height=26,
                corner_radius=13,
                fg_color=COLORS["step_pending"],
                text_color=COLORS["text_muted"],
            )
            dot.pack(side="left")
            self._step_dots[num] = dot

            # Etiqueta de texto
            lbl = ctk.CTkLabel(
                step_col,
                text=label,
                font=FONT_MONO_XS,
                text_color=COLORS["text_muted"],
            )
            lbl.pack(side="left", padx=(4, 0))
            self._step_labels[num] = lbl

            # Linea conectora (excepto despues del ultimo)
            if i < len(steps) - 1:
                ctk.CTkFrame(
                    container,
                    width=40, height=1,
                    fg_color=COLORS["text_muted"],
                    corner_radius=0,
                ).pack(side="left", padx=8)

        self._update_stepper()

    def _update_stepper(self):
        """Actualiza los colores del stepper segun los estados actuales."""
        for num, state in self._step_states.items():
            if state == self.STATE_PENDING:
                dot_bg    = COLORS["step_pending"]
                dot_color = COLORS["text_muted"]
                dot_text  = str(num)
                lbl_color = COLORS["text_muted"]
            elif state == self.STATE_ACTIVE:
                dot_bg    = COLORS["red_dim"]
                dot_color = COLORS["red"]
                dot_text  = str(num)
                lbl_color = COLORS["red"]
            else:  # DONE
                dot_bg    = COLORS["success_dim"]
                dot_color = COLORS["success"]
                dot_text  = "v"
                lbl_color = COLORS["success"]

            if num in self._step_dots:
                self._step_dots[num].configure(
                    text=dot_text,
                    fg_color=dot_bg,
                    text_color=dot_color,
                )
            if num in self._step_labels:
                self._step_labels[num].configure(text_color=lbl_color)

    def _set_step_state(self, step: int, state: str):
        """Cambia el estado de un paso y actualiza el stepper."""
        self._step_states[step] = state
        self._update_stepper()

    # -----------------------------------------------------------------------
    # Secciones del formulario
    # -----------------------------------------------------------------------

    def _section_psd(self, parent):
        frame = self._card(parent, 1, "PLANTILLA PSD", "Archivo .psd con el diseno base")

        # Hint informativo
        hint = ctk.CTkFrame(frame, fg_color=COLORS["warning_dim"], corner_radius=0)
        hint.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(
            hint,
            text="  i  Selecciona el archivo .PSD que usaras como plantilla base para todas las tarjetas.",
            font=FONT_MONO_XS,
            text_color=COLORS["warning"],
            anchor="w",
        ).pack(fill="x", padx=8, pady=6)

        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill="x")
        row.columnconfigure(0, weight=1)

        self._psd_var = ctk.StringVar(value="")
        entry = make_entry(row, textvariable=self._psd_var, state="readonly",
                           placeholder_text="Ningun archivo seleccionado...")
        entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        btn = make_button(row, "EXAMINAR", self._browse_psd, primary=False, width=140)
        btn.grid(row=0, column=1, sticky="e")
        Tooltip(btn, "Abre el explorador para seleccionar tu archivo .PSD")

        # Estado del archivo seleccionado
        self._psd_status_label = ctk.CTkLabel(
            frame, text="", font=FONT_MONO_XS, text_color=COLORS["text_muted"], anchor="w"
        )
        self._psd_status_label.pack(fill="x", pady=(6, 0))

    def _section_layer(self, parent):
        frame = self._card(parent, 2, "CAPA DE TEXTO", "Indica que capa de texto se reemplazara")

        hint = ctk.CTkFrame(frame, fg_color="#1a1500", corner_radius=0)
        hint.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(
            hint,
            text="  i  Primero carga el PSD (paso 1), luego usa 'CARGAR CAPAS' para ver la lista disponible.",
            font=FONT_MONO_XS,
            text_color=COLORS["warning"],
            anchor="w",
        ).pack(fill="x", padx=8, pady=6)

        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill="x")
        row.columnconfigure(0, weight=1)

        self._layer_entry = make_entry(
            row, placeholder_text="ej: nombre_alumno  (escribe o elige de la lista)"
        )
        self._layer_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self._layer_entry.bind("<KeyRelease>", lambda e: self._on_layer_typed())
        Tooltip(self._layer_entry, "Nombre exacto de la capa de texto en Photoshop (distingue mayusculas)")

        load_btn = make_button(row, "CARGAR CAPAS", self._load_layers, primary=False, width=150)
        load_btn.grid(row=0, column=1, sticky="e")
        Tooltip(load_btn, "Conecta con el PSD y lista todas sus capas de texto automaticamente")

        # Dropdown de capas (oculto hasta que se carguen)
        self._layer_combo: Optional[ctk.CTkOptionMenu] = None
        self._layer_combo_frame = ctk.CTkFrame(frame, fg_color="transparent")
        self._layer_combo_frame.pack(fill="x", pady=(8, 0))

        # Estado
        self._layer_status_label = ctk.CTkLabel(
            frame, text="", font=FONT_MONO_XS, text_color=COLORS["text_muted"], anchor="w"
        )
        self._layer_status_label.pack(fill="x", pady=(4, 0))

    def _section_names(self, parent):
        frame = self._card(parent, 3, "LISTA DE NOMBRES", "Los nombres que se imprimiran en cada tarjeta")

        # Fila de botones de carga
        btn_row = ctk.CTkFrame(frame, fg_color="transparent")
        btn_row.pack(fill="x", pady=(0, 10))

        csv_btn = make_button(
            btn_row, "CARGAR CSV", lambda: self._load_names_file("csv"),
            primary=False, width=140,
        )
        csv_btn.pack(side="left", padx=(0, 8))
        Tooltip(csv_btn, "Importa nombres desde un archivo CSV (una columna, un nombre por fila)")

        xlsx_btn = make_button(
            btn_row, "CARGAR EXCEL", lambda: self._load_names_file("excel"),
            primary=False, width=140,
        )
        xlsx_btn.pack(side="left", padx=(0, 8))
        Tooltip(xlsx_btn, "Importa nombres desde un archivo Excel .xlsx o .xls (primera columna)")

        clear_btn = make_button(
            btn_row, "LIMPIAR", self._clear_names,
            primary=False, width=100,
        )
        clear_btn.pack(side="right")
        Tooltip(clear_btn, "Borra todos los nombres del area de texto")

        # Label
        make_label(
            frame, "O ESCRIBE / PEGA LOS NOMBRES DIRECTAMENTE (uno por linea):"
        ).pack(anchor="w", pady=(0, 4))

        self._names_text = ctk.CTkTextbox(
            frame,
            height=130,
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            border_width=1,
            text_color=COLORS["text"],
            font=FONT_MONO,
            corner_radius=0,
        )
        self._names_text.pack(fill="x")
        self._names_text.bind("<KeyRelease>", lambda e: self._on_names_changed())

        # Footer del area de nombres
        names_footer = ctk.CTkFrame(frame, fg_color="transparent")
        names_footer.pack(fill="x", pady=(6, 0))

        self._names_hint_label = ctk.CTkLabel(
            names_footer,
            text="",
            font=FONT_MONO_XS,
            text_color=COLORS["text_muted"],
            anchor="w",
        )
        self._names_hint_label.pack(side="left")

        self._names_count_label = ctk.CTkLabel(
            names_footer,
            text="0 nombres",
            font=("Barlow Condensed", 13, "bold"),
            text_color=COLORS["text_muted"],
        )
        self._names_count_label.pack(side="right")

    def _section_output(self, parent):
        frame = self._card(parent, 4, "CARPETA DE DESTINO", "Donde se guardaran las imagenes generadas")

        hint = ctk.CTkFrame(frame, fg_color=COLORS["bg_input"], corner_radius=0)
        hint.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(
            hint,
            text="  i  Las imagenes se guardaran con el nombre de cada persona como nombre de archivo.",
            font=FONT_MONO_XS,
            text_color=COLORS["text_muted"],
            anchor="w",
        ).pack(fill="x", padx=8, pady=6)

        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill="x")
        row.columnconfigure(0, weight=1)

        self._output_var = ctk.StringVar(value="")
        entry = make_entry(row, textvariable=self._output_var, state="readonly",
                           placeholder_text="Ninguna carpeta seleccionada...")
        entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        btn = make_button(row, "EXAMINAR", self._browse_output, primary=False, width=140)
        btn.grid(row=0, column=1, sticky="e")
        Tooltip(btn, "Selecciona la carpeta donde se guardaran las imagenes generadas")

        self._output_status_label = ctk.CTkLabel(
            frame, text="", font=FONT_MONO_XS, text_color=COLORS["text_muted"], anchor="w"
        )
        self._output_status_label.pack(fill="x", pady=(6, 0))

    def _section_format(self, parent):
        frame = self._card(parent, 5, "FORMATO DE SALIDA", "Tipo de imagen que se generara")

        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill="x")

        self._format_var = ctk.StringVar(value="JPG")

        for fmt, desc in (("JPG", "Menor peso, ideal para fotos"), ("PNG", "Transparencia, mayor calidad")):
            opt_frame = ctk.CTkFrame(row, fg_color=COLORS["bg_input"], corner_radius=0)
            opt_frame.pack(side="left", padx=(0, 12), pady=2)

            ctk.CTkRadioButton(
                opt_frame, text=f"  {fmt}", variable=self._format_var, value=fmt,
                fg_color=COLORS["red"],
                hover_color=COLORS["red_hover"],
                text_color=COLORS["text"],
                font=("Barlow Condensed", 13, "bold"),
                command=self._on_format_changed,
            ).pack(side="left", padx=(8, 4), pady=8)

            ctk.CTkLabel(
                opt_frame,
                text=desc,
                font=FONT_MONO_XS,
                text_color=COLORS["text_muted"],
            ).pack(side="left", padx=(0, 12), pady=8)

        self._set_step_state(5, self.STATE_DONE)

    def _build_footer(self):
        footer = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=0)
        footer.pack(fill="x", side="bottom")

        # Barra de progreso
        progress_wrap = ctk.CTkFrame(footer, fg_color="transparent")
        progress_wrap.pack(fill="x", padx=24, pady=(14, 0))

        prog_header = ctk.CTkFrame(progress_wrap, fg_color="transparent")
        prog_header.pack(fill="x", pady=(0, 4))

        self._progress_label = ctk.CTkLabel(
            prog_header,
            text="LISTO PARA CONFIGURAR",
            font=FONT_MONO_SM,
            text_color=COLORS["text_muted"],
            anchor="w",
        )
        self._progress_label.pack(side="left")

        self._progress_pct = ctk.CTkLabel(
            prog_header,
            text="",
            font=("Barlow Condensed", 13, "bold"),
            text_color=COLORS["text_dim"],
            anchor="e",
        )
        self._progress_pct.pack(side="right")

        self._progress_bar = ctk.CTkProgressBar(
            progress_wrap,
            progress_color=COLORS["red"],
            fg_color=COLORS["bg_input"],
            corner_radius=0,
            height=6,
        )
        self._progress_bar.set(0)
        self._progress_bar.pack(fill="x")

        # Log de salida
        self._log_box = ctk.CTkTextbox(
            footer,
            height=80,
            fg_color=COLORS["bg"],
            border_color=COLORS["border"],
            border_width=1,
            text_color=COLORS["text_dim"],
            font=FONT_MONO_SM,
            corner_radius=0,
            state="disabled",
        )
        self._log_box.pack(fill="x", padx=24, pady=(10, 0))

        # Boton principal
        self._generate_btn = make_button(
            footer, "// GENERAR TARJETAS", self._start_generation, primary=True
        )
        self._generate_btn.pack(fill="x", padx=24, pady=14, ipady=10)

    # -----------------------------------------------------------------------
    # Componente: tarjeta de seccion
    # -----------------------------------------------------------------------

    def _card(self, parent, step: int, title: str, subtitle: str = "") -> ctk.CTkFrame:
        """Crea un panel de seccion con titulo, numero de paso e indicador de estado."""
        outer = ctk.CTkFrame(
            parent,
            fg_color=COLORS["bg_card"],
            border_color=COLORS["border"],
            border_width=1,
            corner_radius=0,
        )
        outer.pack(fill="x", pady=(0, 10))

        # Franja roja lateral
        ctk.CTkFrame(
            outer,
            width=3,
            fg_color=COLORS["red"],
            corner_radius=0,
        ).pack(side="left", fill="y")

        inner = ctk.CTkFrame(outer, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=16, pady=12)

        # Encabezado de la tarjeta
        card_header = ctk.CTkFrame(inner, fg_color="transparent")
        card_header.pack(fill="x", pady=(0, 10))

        # Numero de paso
        ctk.CTkLabel(
            card_header,
            text=f"PASO {step:02d}",
            font=FONT_MONO_XS,
            text_color=COLORS["red"],
            fg_color=COLORS["bg_input"],
            corner_radius=0,
            padx=6, pady=2,
        ).pack(side="left", padx=(0, 10))

        # Titulo
        ctk.CTkLabel(
            card_header,
            text=title,
            font=FONT_TITLE,
            text_color=COLORS["text"],
        ).pack(side="left")

        # Subtitulo
        if subtitle:
            ctk.CTkLabel(
                card_header,
                text=f"  //  {subtitle}",
                font=FONT_MONO_XS,
                text_color=COLORS["text_muted"],
            ).pack(side="left")

        make_separator(inner).pack(fill="x", pady=(0, 10))

        return inner

    # -----------------------------------------------------------------------
    # Acciones de UI
    # -----------------------------------------------------------------------

    def _browse_psd(self):
        path = filedialog.askopenfilename(
            title="Seleccionar plantilla PSD",
            filetypes=[("Photoshop", "*.psd"), ("Todos", "*.*")],
        )
        if path:
            self._psd_path = path
            p = Path(path)
            self._psd_var.set(p.name)
            size_mb = p.stat().st_size / (1024 * 1024)
            self._psd_status_label.configure(
                text=f"v  {p.name}  ({size_mb:.1f} MB)  -  {p.parent}",
                text_color=COLORS["success"],
            )
            self._set_step_state(1, self.STATE_DONE)
            self._set_step_state(2, self.STATE_ACTIVE)
            self._log(f"PSD cargado: {p.name}  ({size_mb:.1f} MB)")
            self._refresh_generate_btn()

    def _browse_output(self):
        folder = filedialog.askdirectory(title="Seleccionar carpeta de destino")
        if folder:
            self._output_folder = folder
            self._output_var.set(folder)
            # Contar archivos existentes
            n = len(list(Path(folder).iterdir()))
            self._output_status_label.configure(
                text=f"v  Carpeta seleccionada  ({n} archivo(s) existente(s))",
                text_color=COLORS["success"],
            )
            self._set_step_state(4, self.STATE_DONE)
            self._log(f"Carpeta de salida: {folder}")
            self._refresh_generate_btn()

    def _load_layers(self):
        if not self._psd_path:
            self._layer_status_label.configure(
                text="!  Primero selecciona un archivo PSD (Paso 1)",
                text_color=COLORS["error"],
            )
            return

        self._log("Cargando capas de texto del PSD...")
        self._layer_status_label.configure(
            text="...  Leyendo capas del PSD...",
            text_color=COLORS["warning"],
        )
        self._set_ui_busy(True)

        def worker():
            try:
                names = ps_mgr.get_text_layers(self._psd_path)
                self.after(0, self._on_layers_loaded, names)
            except Exception as e:
                self.after(0, self._on_layers_error, str(e))
                self.after(0, self._set_ui_busy, False)

        threading.Thread(target=worker, daemon=True).start()

    def _on_layers_error(self, error: str):
        self._layer_status_label.configure(
            text=f"x  Error al leer capas: {error}",
            text_color=COLORS["error"],
        )

    def _on_layers_loaded(self, names: list[str]):
        self._layer_names = names
        self._set_ui_busy(False)

        if not names:
            self._layer_status_label.configure(
                text="!  No se encontraron capas de texto en el PSD.",
                text_color=COLORS["error"],
            )
            return

        self._layer_status_label.configure(
            text=f"v  {len(names)} capas de texto encontradas  - selecciona una de la lista:",
            text_color=COLORS["success"],
        )
        self._log(f"{len(names)} capas de texto encontradas.")

        # Destruir combo anterior si existe
        for widget in self._layer_combo_frame.winfo_children():
            widget.destroy()

        self._layer_combo = ctk.CTkOptionMenu(
            self._layer_combo_frame,
            values=names,
            fg_color=COLORS["bg_input"],
            button_color=COLORS["red"],
            button_hover_color=COLORS["red_hover"],
            dropdown_fg_color=COLORS["bg_card"],
            dropdown_hover_color=COLORS["bg_input"],
            text_color=COLORS["text"],
            font=FONT_MONO,
            corner_radius=0,
            command=self._on_layer_selected,
        )
        self._layer_combo.pack(fill="x")

    def _on_layer_selected(self, value: str):
        self._layer_entry.delete(0, "end")
        self._layer_entry.insert(0, value)
        self._set_step_state(2, self.STATE_DONE)
        self._set_step_state(3, self.STATE_ACTIVE)
        self._layer_status_label.configure(
            text=f"v  Capa seleccionada: '{value}'",
            text_color=COLORS["success"],
        )
        self._refresh_generate_btn()

    def _on_layer_typed(self):
        """Actualiza el estado cuando el usuario escribe manualmente el nombre de la capa."""
        text = self._layer_entry.get().strip()
        if text:
            self._set_step_state(2, self.STATE_DONE)
            self._layer_status_label.configure(
                text=f"v  Capa: '{text}'",
                text_color=COLORS["success"],
            )
        else:
            self._set_step_state(2, self.STATE_ACTIVE)
            self._layer_status_label.configure(text="", text_color=COLORS["text_muted"])
        self._refresh_generate_btn()

    def _load_names_file(self, mode: str):
        if mode == "csv":
            filetypes = [("CSV", "*.csv"), ("Todos", "*.*")]
            title = "Cargar lista desde CSV"
        else:
            filetypes = [("Excel", "*.xlsx *.xls"), ("Todos", "*.*")]
            title = "Cargar lista desde Excel"

        path = filedialog.askopenfilename(title=title, filetypes=filetypes)
        if not path:
            return

        try:
            names = load_names_from_file(path)
            self._names_text.delete("1.0", "end")
            self._names_text.insert("1.0", "\n".join(names))
            self._on_names_changed()
            self._log(f"Cargados {len(names)} nombres desde {Path(path).name}")
        except Exception as e:
            self._show_error(str(e))

    def _clear_names(self):
        self._names_text.delete("1.0", "end")
        self._on_names_changed()

    def _on_names_changed(self):
        """Se llama cada vez que cambia el contenido del textbox de nombres."""
        names = self._get_names_from_textbox()
        n = len(names)

        if n == 0:
            self._names_count_label.configure(text="0 nombres", text_color=COLORS["text_muted"])
            self._names_hint_label.configure(text="")
            self._set_step_state(3, self.STATE_ACTIVE)
        else:
            self._names_count_label.configure(
                text=f"{n} nombre{'s' if n != 1 else ''}  v",
                text_color=COLORS["success"],
            )
            plural = "tarjetas" if n != 1 else "tarjeta"
            self._names_hint_label.configure(
                text=f"Se generaran {n} {plural}",
                text_color=COLORS["text_dim"],
            )
            self._set_step_state(3, self.STATE_DONE)
            if self._step_states[4] == self.STATE_PENDING:
                self._set_step_state(4, self.STATE_ACTIVE)

        self._refresh_generate_btn()

    def _on_format_changed(self):
        self._refresh_generate_btn()

    def _update_names_count(self):
        self._on_names_changed()

    def _get_names_from_textbox(self) -> list[str]:
        raw = self._names_text.get("1.0", "end")
        return [line.strip() for line in raw.splitlines() if line.strip()]

    def _refresh_generate_btn(self):
        """Actualiza el texto y estado del boton Generar segun el estado del formulario."""
        names  = self._get_names_from_textbox()
        n      = len(names)
        ok_psd    = bool(self._psd_path)
        ok_layer  = bool(self._layer_entry.get().strip() if hasattr(self, "_layer_entry") else False)
        ok_names  = n > 0
        ok_output = bool(self._output_folder)

        if ok_psd and ok_layer and ok_names and ok_output:
            fmt = self._format_var.get() if hasattr(self, "_format_var") else "IMG"
            plural = "TARJETAS" if n != 1 else "TARJETA"
            self._generate_btn.configure(
                text=f"GENERAR {n} {plural}  ({fmt})",
                state="normal",
                fg_color=COLORS["red"],
            )
            self._progress_label.configure(
                text=f"v Todo listo  -  {n} tarjeta(s) preparada(s)",
                text_color=COLORS["success"],
            )
        else:
            # Identificar que falta
            missing = []
            if not ok_psd:    missing.append("PSD (paso 1)")
            if not ok_layer:  missing.append("Capa (paso 2)")
            if not ok_names:  missing.append("Nombres (paso 3)")
            if not ok_output: missing.append("Destino (paso 4)")

            missing_str = " · ".join(missing)
            self._generate_btn.configure(
                text="// GENERAR TARJETAS",
                state="normal",
                fg_color=COLORS["red_dim"],
            )
            if missing:
                self._progress_label.configure(
                    text=f"!  Faltan: {missing_str}",
                    text_color=COLORS["warning"],
                )
            else:
                self._progress_label.configure(
                    text="LISTO PARA CONFIGURAR",
                    text_color=COLORS["text_muted"],
                )

    # -----------------------------------------------------------------------
    # Generacion
    # -----------------------------------------------------------------------

    def _start_generation(self):
        if self._is_generating:
            return

        # Validaciones con feedback visual claro
        if not self._psd_path:
            self._progress_label.configure(
                text="!  Selecciona un archivo PSD (Paso 1)",
                text_color=COLORS["error"],
            )
            return

        layer_name = self._layer_entry.get().strip()
        if not layer_name:
            self._progress_label.configure(
                text="!  Escribe o selecciona el nombre de la capa (Paso 2)",
                text_color=COLORS["error"],
            )
            return

        names = self._get_names_from_textbox()
        if not names:
            self._progress_label.configure(
                text="!  Agrega al menos un nombre a la lista (Paso 3)",
                text_color=COLORS["error"],
            )
            return

        if not self._output_folder:
            self._progress_label.configure(
                text="!  Selecciona una carpeta de destino (Paso 4)",
                text_color=COLORS["error"],
            )
            return

        fmt = self._format_var.get()

        self._is_generating = True
        self._set_ui_busy(True)
        self._progress_bar.set(0)
        self._clear_log()
        self._progress_pct.configure(text="0%")
        self._progress_label.configure(
            text=f"Iniciando generacion de {len(names)} tarjetas...",
            text_color=COLORS["text_dim"],
        )
        self._log(f"Iniciando generacion de {len(names)} tarjetas en formato {fmt}...")

        def worker():
            try:
                results = ps_mgr.generate_cards(
                    psd_path=self._psd_path,
                    layer_name=layer_name,
                    names=names,
                    output_folder=self._output_folder,
                    output_format=fmt,
                    progress_callback=self._on_progress,
                )
                self.after(0, self._on_generation_done, results)
            except Exception as e:
                self.after(0, self._on_generation_error, str(e))

        threading.Thread(target=worker, daemon=True).start()

    def _on_progress(self, current: int, total: int, name: str):
        fraction = current / total
        pct = int(fraction * 100)
        self.after(0, self._progress_bar.set, fraction)
        self.after(
            0,
            self._progress_label.configure,
            {"text": f"GENERANDO  {current}/{total}:  {name}", "text_color": COLORS["text_dim"]},
        )
        self.after(0, self._progress_pct.configure, {"text": f"{pct}%"})
        self.after(0, self._log, f"[{current:>3}/{total}] {name}")

    def _on_generation_done(self, results):
        self._is_generating = False
        self._set_ui_busy(False)
        self._progress_bar.set(1)

        ok   = [r for r in results if r.success]
        fail = [r for r in results if not r.success]

        self._progress_label.configure(
            text=f"v  COMPLETADO:  {len(ok)}/{len(results)} tarjetas generadas",
            text_color=COLORS["success"],
        )
        self._progress_pct.configure(text="100%")

        for r in fail:
            self._log(f"ERROR [{r.name}]: {r.error}")

        msg = (
            f"Imagenes generadas exitosamente: {len(ok)}\n"
            f"Errores: {len(fail)}\n\n"
            f"Carpeta de salida:\n{self._output_folder}"
        )
        if messagebox.askyesno("Generacion completada", msg + "\n\n?Abrir carpeta de destino?"):
            ps_mgr.open_folder(self._output_folder)

    def _on_generation_error(self, error: str):
        self._is_generating = False
        self._set_ui_busy(False)
        self._progress_label.configure(
            text="x  ERROR EN LA GENERACION",
            text_color=COLORS["error"],
        )
        self._show_error(error)

    # -----------------------------------------------------------------------
    # Helpers de UI
    # -----------------------------------------------------------------------

    def _set_ui_busy(self, busy: bool):
        state = "disabled" if busy else "normal"
        self._generate_btn.configure(state=state)

    def _log(self, message: str):
        self._log_box.configure(state="normal")
        self._log_box.insert("end", f"> {message}\n")
        self._log_box.see("end")
        self._log_box.configure(state="disabled")

    def _clear_log(self):
        self._log_box.configure(state="normal")
        self._log_box.delete("1.0", "end")
        self._log_box.configure(state="disabled")

    def _show_error(self, message: str):
        self._log(f"ERROR: {message}")
        messagebox.showerror("Error", message)


# ---------------------------------------------------------------------------
# Punto de entrada
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app = App()
    app.mainloop()
