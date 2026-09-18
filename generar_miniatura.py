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
COLOR_ACENTO = "0xC1502E"


def generar_miniatura_desde_imagen(ruta_imagen_base: str, titulo_corto: str, ruta_salida: str):
    if not os.path.exists(ruta_imagen_base):
        raise RuntimeError(f"No existe la imagen base para la miniatura: {ruta_imagen_base}")

    texto_seguro = (
        titulo_corto.upper()
        .replace("\\", "").replace(":", "").replace("'", "").replace('"', "")
    )
    # Varias cajas semitransparentes apiladas simulan un degradado hacia
    # abajo (fiable en cualquier FFmpeg, sin filtros complejos que puedan
    # fallar), barra de acento de marca, y texto grande con contorno fuerte.
    filtro = (
        "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,"
        "drawbox=x=0:y=500:w=1280:h=55:color=black@0.15:t=fill,"
        "drawbox=x=0:y=555:w=1280:h=55:color=black@0.30:t=fill,"
        "drawbox=x=0:y=610:w=1280:h=55:color=black@0.50:t=fill,"
        "drawbox=x=0:y=665:w=1280:h=55:color=black@0.68:t=fill,"
        f"drawbox=x=0:y=690:w=1280:h=8:color={COLOR_ACENTO}@1.0:t=fill,"
        f"drawtext=text='{texto_seguro}':fontcolor=white:fontsize=104:"
        f"font='DejaVu Sans Bold':borderw=8:bordercolor=black@1.0:"
        "x=(w-text_w)/2:y=h-235"
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
