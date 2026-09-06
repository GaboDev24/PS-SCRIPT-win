"""
main.py
Interfaz grafica de la herramienta de generacion de tarjetas desde Photoshop.
Usa customtkinter para un aspecto moderno con el sistema de diseno tactico.
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
    "bg":          "#0d0d0d",
    "bg_card":     "#121212",
    "bg_input":    "#1a1a1a",
    "red":         "#A30000",
    "red_hover":   "#c40000",
    "red_dim":     "#6B0000",
    "border":      "#2a0000",
    "text":        "#F5F5F5",
    "text_dim":    "#888888",
    "text_muted":  "#444444",
    "success":     "#22c55e",
    "warning":     "#f59e0b",
    "error":       "#ef4444",
}

FONT_MONO = ("Share Tech Mono", 11)
FONT_MONO_SM = ("Share Tech Mono", 9)
FONT_HEAD = ("Barlow Condensed", 22, "bold")
FONT_LABEL = ("Share Tech Mono", 9)


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
# Ventana principal
# ---------------------------------------------------------------------------

class App(ctk.CTk):

    def __init__(self):
        super().__init__()

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.title("PS Card Generator")
        self.geometry("860x780")
        self.minsize(740, 680)
        self.configure(fg_color=COLORS["bg"])
        self.resizable(True, True)

        # Estado interno
        self._psd_path: Optional[str] = None
        self._output_folder: Optional[str] = None
        self._layer_names: list[str] = []
        self._is_generating: bool = False

        self._build_ui()

    # -----------------------------------------------------------------------
    # Construccion de la interfaz
    # -----------------------------------------------------------------------

    def _build_ui(self):
        # --- Encabezado -------------------------------------------------------
        header = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=0)
        header.pack(fill="x", padx=0, pady=(0, 1))

        ctk.CTkLabel(
            header,
            text="PS CARD GENERATOR",
            font=("Barlow Condensed", 26, "bold"),
            text_color=COLORS["text"],
        ).pack(side="left", padx=24, pady=16)

        ctk.CTkLabel(
            header,
            text="PHOTOSHOP AUTOMATION",
            font=FONT_MONO_SM,
            text_color=COLORS["red"],
        ).pack(side="left", padx=0, pady=16)

        # Separador
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

        # --- Seccion: Plantilla PSD -------------------------------------------
        self._section_psd(content)
        self._section_layer(content)
        self._section_names(content)
        self._section_output(content)
        self._section_format(content)

        # --- Separador + boton Generar ----------------------------------------
        make_separator(self).pack(fill="x")
        self._build_footer()

    def _section_psd(self, parent):
        frame = self._card(parent, "01 // PLANTILLA PSD")

        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill="x")
        row.columnconfigure(0, weight=1)

        self._psd_var = ctk.StringVar(value="Sin seleccionar...")
        entry = make_entry(row, textvariable=self._psd_var, state="readonly")
        entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        make_button(row, "EXAMINAR", self._browse_psd, primary=False).grid(
            row=0, column=1, sticky="e"
        )

    def _section_layer(self, parent):
        frame = self._card(parent, "02 // CAPA DE TEXTO")

        make_label(
            frame, "NOMBRE EXACTO DE LA CAPA A REEMPLAZAR"
        ).pack(anchor="w", pady=(0, 4))

        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill="x")
        row.columnconfigure(0, weight=1)

        self._layer_entry = make_entry(
            row, placeholder_text="ej: nombre_alumno"
        )
        self._layer_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        make_button(row, "CARGAR CAPAS", self._load_layers, primary=False).grid(
            row=0, column=1, sticky="e"
        )

        make_label(
            frame,
            "O carga el PSD y usa 'CARGAR CAPAS' para elegir desde una lista."
        ).pack(anchor="w", pady=(6, 0))

        # Dropdown de capas (oculto hasta que se carguen)
        self._layer_combo: Optional[ctk.CTkOptionMenu] = None
        self._layer_combo_frame = ctk.CTkFrame(frame, fg_color="transparent")
        self._layer_combo_frame.pack(fill="x", pady=(6, 0))

    def _section_names(self, parent):
        frame = self._card(parent, "03 // LISTA DE NOMBRES")

        # Fila de botones de carga
        btn_row = ctk.CTkFrame(frame, fg_color="transparent")
        btn_row.pack(fill="x", pady=(0, 10))

        make_button(
            btn_row, "CARGAR CSV", lambda: self._load_names_file("csv"),
            primary=False, width=140,
        ).pack(side="left", padx=(0, 8))

        make_button(
            btn_row, "CARGAR EXCEL (.xlsx)", lambda: self._load_names_file("excel"),
            primary=False, width=180,
        ).pack(side="left")

        make_label(
            frame, "O pega los nombres directamente (uno por linea):"
        ).pack(anchor="w", pady=(0, 4))

        self._names_text = ctk.CTkTextbox(
            frame,
            height=120,
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            border_width=1,
            text_color=COLORS["text"],
            font=FONT_MONO,
            corner_radius=0,
        )
        self._names_text.pack(fill="x")

        self._names_count_label = make_label(frame, "0 nombres cargados")
        self._names_count_label.pack(anchor="e", pady=(4, 0))

    def _section_output(self, parent):
        frame = self._card(parent, "04 // CARPETA DE DESTINO")

        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill="x")
        row.columnconfigure(0, weight=1)

        self._output_var = ctk.StringVar(value="Sin seleccionar...")
        entry = make_entry(row, textvariable=self._output_var, state="readonly")
        entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        make_button(row, "EXAMINAR", self._browse_output, primary=False).grid(
            row=0, column=1, sticky="e"
        )

    def _section_format(self, parent):
        frame = self._card(parent, "05 // FORMATO DE SALIDA")

        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill="x")

        self._format_var = ctk.StringVar(value="JPG")
        for fmt in ("JPG", "PNG"):
            ctk.CTkRadioButton(
                row, text=fmt, variable=self._format_var, value=fmt,
                fg_color=COLORS["red"],
                hover_color=COLORS["red_hover"],
                text_color=COLORS["text"],
                font=FONT_MONO,
            ).pack(side="left", padx=(0, 24))

    def _build_footer(self):
        footer = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=0)
        footer.pack(fill="x", side="bottom")

        # Barra de progreso
        progress_wrap = ctk.CTkFrame(footer, fg_color="transparent")
        progress_wrap.pack(fill="x", padx=24, pady=(16, 0))

        self._progress_label = make_label(
            progress_wrap, "LISTO PARA GENERAR"
        )
        self._progress_label.pack(anchor="w", pady=(0, 4))

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
            height=90,
            fg_color=COLORS["bg"],
            border_color=COLORS["border"],
            border_width=1,
            text_color=COLORS["text_dim"],
            font=FONT_MONO_SM,
            corner_radius=0,
            state="disabled",
        )
        self._log_box.pack(fill="x", padx=24, pady=(8, 0))

        # Boton principal
        self._generate_btn = make_button(
            footer, "// GENERAR TARJETAS", self._start_generation, primary=True
        )
        self._generate_btn.pack(fill="x", padx=24, pady=16, ipady=10)

    # -----------------------------------------------------------------------
    # Componente: tarjeta de seccion
    # -----------------------------------------------------------------------

    def _card(self, parent, title: str) -> ctk.CTkFrame:
        """Crea un panel de seccion con titulo y borde rojo lateral."""
        outer = ctk.CTkFrame(
            parent,
            fg_color=COLORS["bg_card"],
            border_color=COLORS["border"],
            border_width=1,
            corner_radius=0,
        )
        outer.pack(fill="x", pady=(0, 12))

        # Franja roja lateral
        ctk.CTkFrame(
            outer,
            width=3,
            fg_color=COLORS["red"],
            corner_radius=0,
        ).pack(side="left", fill="y")

        inner = ctk.CTkFrame(outer, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=16, pady=12)

        ctk.CTkLabel(
            inner,
            text=title,
            font=("Share Tech Mono", 10),
            text_color=COLORS["red"],
        ).pack(anchor="w", pady=(0, 8))

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
            self._psd_var.set(path)
            self._log(f"PSD cargado: {Path(path).name}")

    def _browse_output(self):
        folder = filedialog.askdirectory(title="Seleccionar carpeta de destino")
        if folder:
            self._output_folder = folder
            self._output_var.set(folder)
            self._log(f"Carpeta de salida: {folder}")

    def _load_layers(self):
        if not self._psd_path:
            self._show_error("Primero selecciona un archivo PSD.")
            return

        self._log("Cargando capas de texto del PSD...")
        self._set_ui_busy(True)

        def worker():
            try:
                names = ps_mgr.get_text_layers(self._psd_path)
                self.after(0, self._on_layers_loaded, names)
            except Exception as e:
                self.after(0, self._show_error, str(e))
                self.after(0, self._set_ui_busy, False)

        threading.Thread(target=worker, daemon=True).start()

    def _on_layers_loaded(self, names: list[str]):
        self._layer_names = names
        self._set_ui_busy(False)

        if not names:
            self._show_error("No se encontraron capas de texto en el PSD.")
            return

        self._log(f"{len(names)} capas de texto encontradas.")

        # Destruir combo anterior si existe
        for widget in self._layer_combo_frame.winfo_children():
            widget.destroy()

        make_label(
            self._layer_combo_frame, "SELECCIONAR CAPA DESDE LA LISTA:"
        ).pack(anchor="w", pady=(0, 4))

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
            self._update_names_count()
            self._log(f"Cargados {len(names)} nombres desde {Path(path).name}")
        except Exception as e:
            self._show_error(str(e))

    def _update_names_count(self):
        names = self._get_names_from_textbox()
        self._names_count_label.configure(text=f"{len(names)} nombres cargados")

    def _get_names_from_textbox(self) -> list[str]:
        raw = self._names_text.get("1.0", "end")
        return [line.strip() for line in raw.splitlines() if line.strip()]

    # -----------------------------------------------------------------------
    # Generacion
    # -----------------------------------------------------------------------

    def _start_generation(self):
        if self._is_generating:
            return

        # Validaciones
        if not self._psd_path:
            self._show_error("Selecciona un archivo PSD.")
            return

        layer_name = self._layer_entry.get().strip()
        if not layer_name:
            self._show_error("Escribe el nombre de la capa de texto a reemplazar.")
            return

        names = self._get_names_from_textbox()
        if not names:
            self._show_error("Agrega al menos un nombre a la lista.")
            return

        if not self._output_folder:
            self._show_error("Selecciona una carpeta de destino.")
            return

        fmt = self._format_var.get()

        self._is_generating = True
        self._set_ui_busy(True)
        self._progress_bar.set(0)
        self._clear_log()
        self._log(f"Iniciando generacion de {len(names)} tarjetas...")

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
        self.after(0, self._progress_bar.set, fraction)
        self.after(
            0,
            self._progress_label.configure,
            {"text": f"GENERANDO {current}/{total}: {name.upper()}"},
        )
        self.after(0, self._log, f"[{current:>3}/{total}] {name}")

    def _on_generation_done(self, results):
        self._is_generating = False
        self._set_ui_busy(False)
        self._progress_bar.set(1)

        ok = [r for r in results if r.success]
        fail = [r for r in results if not r.success]

        self._progress_label.configure(text=f"COMPLETADO: {len(ok)}/{len(results)} tarjetas generadas")

        for r in fail:
            self._log(f"ERROR [{r.name}]: {r.error}")

        # Dialogo de resumen
        msg = (
            f"Imagenes generadas exitosamente: {len(ok)}\n"
            f"Errores: {len(fail)}\n\n"
            f"Carpeta de salida:\n{self._output_folder}"
        )
        if messagebox.askyesno(
            "Generacion completada",
            msg + "\n\n¿Abrir carpeta de destino?",
        ):
            ps_mgr.open_folder(self._output_folder)

    def _on_generation_error(self, error: str):
        self._is_generating = False
        self._set_ui_busy(False)
        self._progress_label.configure(text="ERROR EN LA GENERACION")
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
