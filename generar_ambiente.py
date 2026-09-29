"""Última Señal — Ambiente sonoro sintetizado"""

import subprocess
import os


def _ffmpeg(comando, error):
    r = subprocess.run(comando, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"{error}:\n{r.stderr[-600:]}")


def generar_ambiente(ruta_salida: str, duracion_segundos: float):
    """Dron grave + capa aguda tenue + pulso lento tipo latido."""
    fade_out = max(duracion_segundos - 3, 0)
    filtro = (
        f"sine=frequency=55:duration={duracion_segundos}[a];"
        f"sine=frequency=58:duration={duracion_segundos}[b];"
        f"sine=frequency=110:duration={duracion_segundos}[c];"
        f"[a][b][c]amix=inputs=3:duration=longest:weights=1 1 0.4,"
        f"apulsator=hz=1.1:amount=0.6,"
        f"volume=0.16,"
        f"afade=t=in:st=0:d=3,afade=t=out:st={fade_out}:d=3"
    )
    _ffmpeg(["ffmpeg", "-y", "-f", "lavfi", "-i", filtro, "-ac", "2", ruta_salida],
            "Fallo generando el ambiente sonoro")
    return ruta_salida


def mezclar_con_narracion(ruta_narracion: str, ruta_ambiente: str, ruta_salida: str):
    """Mezcla voz + ambiente con auto-ducking real (sidechain)."""
    filtro = (
        "[1:a][0:a]sidechaincompress=threshold=0.02:ratio=8:attack=50:release=400:makeup=1[amb_duck];"
        "[0:a][amb_duck]amix=inputs=2:duration=first:dropout_transition=0"
    )
    _ffmpeg(["ffmpeg", "-y", "-i", ruta_narracion, "-i", ruta_ambiente,
             "-filter_complex", filtro, "-ac", "2", ruta_salida],
            "Fallo mezclando ambiente + narración")
    return ruta_salida


def generar_alarma_intro(ruta_salida: str, duracion_segundos: float = 3.0):
    """Pitidos de alarma sintetizados para el intro."""
    filtro = (
        f"sine=frequency=1000:duration={duracion_segundos},"
        f"apulsator=hz=2.2,volume=0.35,"
        f"afade=t=out:st={max(duracion_segundos-0.3,0)}:d=0.3"
    )
    _ffmpeg(["ffmpeg", "-y", "-f", "lavfi", "-i", filtro, "-ac", "2", ruta_salida],
            "Fallo generando la alarma del intro")
    return ruta_salida
