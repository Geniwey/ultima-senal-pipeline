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
    # Marco de acento grueso alrededor de toda la miniatura (look "canal
    # serio" tipo documental true-crime), viñeta oscura en los bordes para
    # dar profundidad, degradado inferior más fuerte, y texto más grande
    # con doble contorno — se aleja del aspecto plano de diapositiva.
    # Círculo rojo de "atención" en una esquina — el clásico elemento de
    # alto contraste de miniaturas de true-crime/investigación que dirige
    # el ojo hacia el punto clave de la imagen.
    cx, cy, radio = 1120, 140, 70
    circulo = (
        f"drawbox=x={cx-radio}:y={cy-6}:w={radio*2}:h=12:color=red@0.95:t=fill,"
        f"drawbox=x={cx-6}:y={cy-radio}:w=12:h={radio*2}:color=red@0.95:t=fill"
    )
    filtro = (
        "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,"
        "eq=contrast=1.12:saturation=1.15,"
        "vignette=angle=PI/4:mode=backward,"
        f"{circulo},"
        "drawbox=x=0:y=480:w=1280:h=40:color=black@0.10:t=fill,"
        "drawbox=x=0:y=520:w=1280:h=40:color=black@0.25:t=fill,"
        "drawbox=x=0:y=560:w=1280:h=40:color=black@0.42:t=fill,"
        "drawbox=x=0:y=600:w=1280:h=40:color=black@0.60:t=fill,"
        "drawbox=x=0:y=640:w=1280:h=80:color=black@0.78:t=fill,"
        f"drawbox=x=0:y=690:w=1280:h=10:color={COLOR_ACENTO}@1.0:t=fill,"
        f"drawtext=text='{texto_seguro}':fontcolor=white:fontsize=112:"
        f"font='DejaVu Sans Bold':borderw=10:bordercolor=black@1.0:"
        "x=(w-text_w)/2:y=h-225,"
        f"drawbox=x=0:y=0:w=1280:h=14:color={COLOR_BORDE}@1.0:t=fill,"
        f"drawbox=x=0:y=706:w=1280:h=14:color={COLOR_BORDE}@1.0:t=fill,"
        f"drawbox=x=0:y=0:w=14:h=720:color={COLOR_BORDE}@1.0:t=fill,"
        f"drawbox=x=1266:y=0:w=14:h=720:color={COLOR_BORDE}@1.0:t=fill"
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
