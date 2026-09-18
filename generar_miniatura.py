"""
Última Señal — Miniatura (thumbnail)
=======================================
Genera la imagen de portada en formato estándar de YouTube (1280x720) a
partir de una imagen del vídeo QUE YA SE GENERÓ BIEN — no pide una imagen
nueva a ningún proveedor, así nunca depende de que quede cupo libre justo
al final de la ejecución.
"""

import subprocess
import os

COLOR_BORDE = "0x1B2A4A"


def generar_miniatura_desde_imagen(ruta_imagen_base: str, titulo_corto: str, ruta_salida: str):
    if not os.path.exists(ruta_imagen_base):
        raise RuntimeError(f"No existe la imagen base para la miniatura: {ruta_imagen_base}")

    texto_seguro = (
        titulo_corto.upper()
        .replace("\\", "").replace(":", "").replace("'", "").replace('"', "")
    )
    filtro = (
        "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,"
        f"drawtext=text='{texto_seguro}':fontcolor=white:fontsize=88:"
        f"font='DejaVu Sans Bold':borderw=6:bordercolor={COLOR_BORDE}@1.0:"
        "x=(w-text_w)/2:y=h-220"
    )
    comando = [
        "ffmpeg", "-y", "-i", ruta_imagen_base,
        "-vf", filtro, "-frames:v", "1",
        ruta_salida,
    ]
    resultado = subprocess.run(comando, capture_output=True, text=True)
    if resultado.returncode != 0 or not os.path.exists(ruta_salida):
        raise RuntimeError(f"Fallo generando la miniatura:\n{resultado.stderr[-600:]}")
    return ruta_salida
