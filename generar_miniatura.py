"""
Última Señal — Miniatura (thumbnail)
=======================================
Genera una imagen de portada llamativa en el formato estándar de
YouTube (1280x720), reutilizando el mismo proveedor de imágenes del
canal y quemando el titular en grande encima, en los colores de marca.
"""

import subprocess
import os

from generar_imagen import generar_imagen, ESTILO_BASE

COLOR_TITULO = "0xC1502E"
COLOR_BORDE = "0x1B2A4A"


def generar_miniatura(prompt_visual: str, titulo_corto: str, ruta_salida: str):
    """
    prompt_visual: descripción en inglés de la imagen de fondo (el momento
                   más impactante/representativo del vídeo).
    titulo_corto: texto corto (3-6 palabras) para quemar en grande, en
                  MAYÚSCULAS, sobre la imagen.
    """
    ruta_fondo = ruta_salida + "_fondo_temp.png"
    ok = generar_imagen(prompt_visual, ruta_fondo)
    if not ok:
        raise RuntimeError("No se pudo generar la imagen base de la miniatura")

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
        "ffmpeg", "-y", "-i", ruta_fondo,
        "-vf", filtro, "-frames:v", "1",
        ruta_salida,
    ]
    resultado = subprocess.run(comando, capture_output=True, text=True)
    os.remove(ruta_fondo)
    if resultado.returncode != 0 or not os.path.exists(ruta_salida):
        raise RuntimeError(f"Fallo generando la miniatura:\n{resultado.stderr[-600:]}")
    return ruta_salida
