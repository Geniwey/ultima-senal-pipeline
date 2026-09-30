"""Última Señal — Bumper de marca (intro/outro)"""

import subprocess
import os

ANCHO, ALTO = 1920, 1080
DURACION = 3
COLOR_FONDO = "0x1B2A4A"
COLOR_TITULO = "0xC1502E"
COLOR_SUBTITULO = "0xE8E6DE"


def generar_intro(ruta_salida: str):
    filtro = (
        f"color=c={COLOR_FONDO}:s={ANCHO}x{ALTO}:d={DURACION},"
        f"drawtext=text='ÚLTIMA SEÑAL':fontcolor={COLOR_TITULO}:fontsize=120:"
        f"font='DejaVu Sans Bold':x=(w-text_w)/2:y=(h-text_h)/2-40:"
        f"alpha='if(lt(t,0.4),t/0.4,1)',"
        f"drawtext=text='INVESTIGACIÓN AÉREA':fontcolor={COLOR_SUBTITULO}:fontsize=40:"
        f"font='DejaVu Sans':x=(w-text_w)/2:y=(h/2)+90:"
        f"alpha='if(lt(t,0.7),0,if(lt(t,1.1),(t-0.7)/0.4,1))'"
    )
    comando = [
        "ffmpeg", "-y", "-f", "lavfi", "-i", filtro,
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-t", str(DURACION),
        ruta_salida,
    ]
    resultado = subprocess.run(comando, capture_output=True, text=True)
    if resultado.returncode != 0 or not os.path.exists(ruta_salida):
        raise RuntimeError(f"Fallo generando el bumper de marca:\n{resultado.stderr[-800:]}")
    return ruta_salida


def generar_outro(ruta_salida: str):
    filtro = (
        f"color=c={COLOR_FONDO}:s={ANCHO}x{ALTO}:d={DURACION},"
        f"drawtext=text='ÚLTIMA SEÑAL':fontcolor={COLOR_TITULO}:fontsize=90:"
        f"font='DejaVu Sans Bold':x=(w-text_w)/2:y=(h-text_h)/2-80:"
        f"alpha='if(lt(t,0.4),t/0.4,1)',"
        f"drawtext=text='SUSCRÍBETE PARA MÁS INVESTIGACIONES':fontcolor={COLOR_SUBTITULO}:fontsize=42:"
        f"font='DejaVu Sans':x=(w-text_w)/2:y=(h/2)+60:"
        f"alpha='if(lt(t,0.6),0,if(lt(t,1.0),(t-0.6)/0.4,1))'"
    )
    comando = [
        "ffmpeg", "-y", "-f", "lavfi", "-i", filtro,
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-t", str(DURACION),
        ruta_salida,
    ]
    resultado = subprocess.run(comando, capture_output=True, text=True)
    if resultado.returncode != 0 or not os.path.exists(ruta_salida):
        raise RuntimeError(f"Fallo generando el cierre de marca:\n{resultado.stderr[-800:]}")
    return ruta_salida
