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
    # Dron grave con "beating" + una tercera capa más aguda muy tenue para
    # dar textura (antes era casi inaudible a volumen 0.05 — ahora se nota
    # de verdad como diseño sonoro sin tapar la voz).
    fade_out = max(duracion_segundos - 3, 0)
    filtro = (
        f"sine=frequency=55:duration={duracion_segundos}[a];"
        f"sine=frequency=58:duration={duracion_segundos}[b];"
        f"sine=frequency=110:duration={duracion_segundos}[c];"
        f"[a][b][c]amix=inputs=3:duration=longest:weights=1 1 0.4,"
        f"volume=0.14,"
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
    """Mezcla voz + ambiente con auto-ducking real: el ambiente baja de
    volumen automáticamente cuando hay voz sonando, y sube un poco en los
    huecos — en vez de un volumen fijo bajo todo el rato."""
    filtro = (
        "[1:a][0:a]sidechaincompress=threshold=0.02:ratio=8:attack=50:release=400:makeup=1[amb_duck];"
        "[0:a][amb_duck]amix=inputs=2:duration=first:dropout_transition=0"
    )
    comando = [
        "ffmpeg", "-y", "-i", ruta_narracion, "-i", ruta_ambiente,
        "-filter_complex", filtro,
        "-ac", "2", ruta_salida,
    ]
    resultado = subprocess.run(comando, capture_output=True, text=True)
    if resultado.returncode != 0 or not os.path.exists(ruta_salida):
        raise RuntimeError(f"Fallo mezclando ambiente + narración:\n{resultado.stderr[-600:]}")
    return ruta_salida


def generar_alarma_intro(ruta_salida: str, duracion_segundos: float = 3.0):
    """Pitidos de alarma sintetizados para los primeros segundos del vídeo
    (durante el bumper de intro, antes de que arranque la narración) —
    refuerza el gancho inicial en vez de empezar en silencio."""
    filtro = (
        f"sine=frequency=1000:duration={duracion_segundos},"
        f"apulsator=hz=2.2,"
        f"volume=0.35,"
        f"afade=t=out:st={max(duracion_segundos-0.3,0)}:d=0.3"
    )
    comando = [
        "ffmpeg", "-y", "-f", "lavfi", "-i", filtro,
        "-ac", "2", ruta_salida,
    ]
    resultado = subprocess.run(comando, capture_output=True, text=True)
    if resultado.returncode != 0 or not os.path.exists(ruta_salida):
        raise RuntimeError(f"Fallo generando la alarma del intro:\n{resultado.stderr[-600:]}")
    return ruta_salida
