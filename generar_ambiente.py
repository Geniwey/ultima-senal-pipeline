"""
Última Señal — Ambiente sonoro de fondo
==========================================
Genera un lecho sonoro tenso y sutil (dron grave) para mezclar debajo de
toda la narración del vídeo. 100% sintetizado con FFmpeg — no depende de
ninguna librería de música externa, así que no hay riesgo de derechos de
autor ni de que falle por una descarga.
"""

import subprocess
import os


def generar_ambiente(ruta_salida: str, duracion_segundos: float):
    # Dron grave con un ligero "beating" (dos senoidales muy cercanas en
    # frecuencia) — da sensación de tensión de fondo sutil, sin sonar a
    # música con derechos de autor.
    fade_out = max(duracion_segundos - 3, 0)
    filtro = (
        f"sine=frequency=55:duration={duracion_segundos}[a];"
        f"sine=frequency=58:duration={duracion_segundos}[b];"
        f"[a][b]amix=inputs=2:duration=longest,"
        f"volume=0.05,"
        f"afade=t=in:st=0:d=3,afade=t=out:st={fade_out}:d=3"
    )
    comando = [
        "ffmpeg", "-y", "-f", "lavfi", "-i", filtro,
        "-ac", "2", ruta_salida,
    ]
    resultado = subprocess.run(comando, capture_output=True, text=True)
    if resultado.returncode != 0 or not os.path.exists(ruta_salida):
        raise RuntimeError(f"Fallo generando el ambiente sonoro:\n{resultado.stderr[-600:]}")
    return ruta_salida


def mezclar_con_narracion(ruta_narracion: str, ruta_ambiente: str, ruta_salida: str):
    """Mezcla la voz (volumen normal) con el ambiente (ya viene muy bajo)."""
    filtro = "[0:a][1:a]amix=inputs=2:duration=first:dropout_transition=0"
    comando = [
        "ffmpeg", "-y", "-i", ruta_narracion, "-i", ruta_ambiente,
        "-filter_complex", filtro,
        "-ac", "2", ruta_salida,
    ]
    resultado = subprocess.run(comando, capture_output=True, text=True)
    if resultado.returncode != 0 or not os.path.exists(ruta_salida):
        raise RuntimeError(f"Fallo mezclando ambiente + narración:\n{resultado.stderr[-600:]}")
    return ruta_salida
