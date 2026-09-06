"""
photoshop_manager.py
Módulo de automatización de Adobe Photoshop via photoshop-python-api (COM/Windows).
No contiene lógica de interfaz gráfica.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from typing import Callable

# photoshop-python-api solo funciona en Windows con Photoshop instalado
try:
    import photoshop.api as ps
except ImportError:
    ps = None  # Se maneja en runtime para mostrar el error en la UI


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

# Caracteres inválidos en nombres de archivo de Windows
_INVALID_CHARS_RE = re.compile(r'[/\\:*?"<>|]')

# Códigos de exportación
_EXPORT_FORMAT = {
    "JPG": "jpeg",
    "PNG": "png",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def sanitize_filename(name: str) -> str:
    """Elimina caracteres inválidos para nombres de archivo de Windows."""
    sanitized = _INVALID_CHARS_RE.sub("_", name).strip()
    if not sanitized:
        raise ValueError(f"El nombre '{name}' no produce un nombre de archivo válido.")
    return sanitized


def get_text_layers(psd_path: str) -> list[str]:
    """
    Abre el PSD en Photoshop y devuelve una lista con los nombres
    de todas las capas de texto del documento.
    Se cierra el documento sin guardar al terminar.
    """
    if ps is None:
        raise RuntimeError(
            "La librería 'photoshop-python-api' no está instalada. "
            "Ejecuta: pip install photoshop-python-api"
        )

    app = ps.Application()
    doc = app.open(str(Path(psd_path).resolve()))
    try:
        names: list[str] = []
        _collect_text_layers(doc.artLayers, names)
        for layer_set in doc.layerSets:
            _collect_text_layers_recursive(layer_set, names)
        return names
    finally:
        doc.close(ps.SaveOptions.DoNotSaveChanges)


def _collect_text_layers(art_layers, names: list[str]) -> None:
    """Recorre art_layers y agrega a names los que son de tipo texto."""
    for layer in art_layers:
        try:
            if layer.kind == ps.LayerKind.TextLayer:
                names.append(layer.name)
        except Exception:
            pass


def _collect_text_layers_recursive(layer_set, names: list[str]) -> None:
    """Recorre un LayerSet y todos sus sub-conjuntos recursivamente."""
    _collect_text_layers(layer_set.artLayers, names)
    for sub_set in layer_set.layerSets:
        _collect_text_layers_recursive(sub_set, names)


# ---------------------------------------------------------------------------
# Generación de tarjetas
# ---------------------------------------------------------------------------

class GenerationResult:
    """Resultado de una generación individual."""

    def __init__(self, name: str, success: bool, error: str = ""):
        self.name = name
        self.success = success
        self.error = error


def generate_cards(
    psd_path: str,
    layer_name: str,
    names: list[str],
    output_folder: str,
    output_format: str,
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> list[GenerationResult]:
    """
    Genera una imagen por cada nombre en `names`.

    Parámetros
    ----------
    psd_path       : Ruta absoluta al archivo .psd plantilla.
    layer_name     : Nombre exacto de la capa de texto a reemplazar.
    names          : Lista de nombres con los que generar las tarjetas.
    output_folder  : Carpeta de destino para las imágenes generadas.
    output_format  : 'JPG' o 'PNG'.
    progress_callback : Función opcional (actual, total, nombre_actual).

    Retorna
    -------
    Lista de GenerationResult con el estado de cada tarjeta.
    """
    if ps is None:
        raise RuntimeError(
            "La librería 'photoshop-python-api' no está instalada. "
            "Ejecuta: pip install photoshop-python-api"
        )

    psd_path = str(Path(psd_path).resolve())
    output_folder = Path(output_folder).resolve()
    output_folder.mkdir(parents=True, exist_ok=True)

    fmt = output_format.upper()
    if fmt not in _EXPORT_FORMAT:
        raise ValueError(f"Formato no soportado: {output_format}. Use JPG o PNG.")

    app = ps.Application()
    doc = app.open(psd_path)

    try:
        text_layer = _find_layer(doc, layer_name)
        if text_layer is None:
            raise LookupError(
                f"No se encontró la capa de texto '{layer_name}' en el documento."
            )

        results: list[GenerationResult] = []
        total = len(names)

        for idx, name in enumerate(names, start=1):
            if progress_callback:
                progress_callback(idx, total, name)

            try:
                safe_name = sanitize_filename(name)
                text_layer.textItem.contents = name

                out_filename = f"tarjeta_{safe_name}.{fmt.lower()}"
                out_path = str(output_folder / out_filename)

                _export_document(app, doc, out_path, fmt)
                results.append(GenerationResult(name, success=True))

            except Exception as exc:
                results.append(GenerationResult(name, success=False, error=str(exc)))

        return results

    finally:
        doc.close(ps.SaveOptions.DoNotSaveChanges)


# ---------------------------------------------------------------------------
# Internos
# ---------------------------------------------------------------------------

def _find_layer(doc, layer_name: str):
    """Busca recursivamente una capa de texto por su nombre."""
    layer = _search_in_art_layers(doc.artLayers, layer_name)
    if layer:
        return layer
    for layer_set in doc.layerSets:
        layer = _search_recursive(layer_set, layer_name)
        if layer:
            return layer
    return None


def _search_in_art_layers(art_layers, layer_name: str):
    for layer in art_layers:
        try:
            if layer.name == layer_name and layer.kind == ps.LayerKind.TextLayer:
                return layer
        except Exception:
            pass
    return None


def _search_recursive(layer_set, layer_name: str):
    found = _search_in_art_layers(layer_set.artLayers, layer_name)
    if found:
        return found
    for sub_set in layer_set.layerSets:
        found = _search_recursive(sub_set, layer_name)
        if found:
            return found
    return None


def _export_document(app, doc, out_path: str, fmt: str) -> None:
    """Exporta el documento activo a la ruta indicada."""
    if fmt == "JPG":
        options = ps.JPEGSaveOptions(quality=12)
        doc.saveAs(out_path, options, asCopy=True)
    elif fmt == "PNG":
        options = ps.PNGSaveOptions()
        options.compression = 0
        doc.saveAs(out_path, options, asCopy=True)


def open_folder(folder_path: str) -> None:
    """Abre la carpeta en el explorador de Windows."""
    if sys.platform == "win32":
        subprocess.Popen(["explorer", str(Path(folder_path).resolve())])
    else:
        # Fallback para desarrollo en Linux/macOS
        subprocess.Popen(["xdg-open", str(Path(folder_path).resolve())])
