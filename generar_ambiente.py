# Código optimizado con ruido marrón (motor/viento) para tensión cinematográfica[span_12](start_span)[span_12](end_span)[span_13](start_span)[span_13](end_span)
import subprocess
import os

def _ffmpeg(comando, error):
    r = subprocess.run(comando, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"{error}:\n{r.stderr[-600:]}")

def generar_ambiente(ruta_salida: str, duracion_segundos: float):
    fade_out = max(duracion_segundos - 3, 0)
    filtro = (
        f"anoisesrc=d={duracion_segundos}:c=brown:a=0.35[noise];"
        f"[noise]lowpass=f=200[low];"
        f"sine=f=45:duration={duracion_segundos}[sub];"
        f"[low][sub]amix=inputs=2:duration=longest:weights=1 0.4,"
        f"apulsator=hz=0.8:amount=0.4,volume=0.35,"
        f"afade=t=in:st=0:d=3,afade=t=out:st={fade_out}:d=3"
    )
    _ffmpeg(["ffmpeg", "-y", "-f", "lavfi", "-i", filtro, "-ac", "2", ruta_salida], "Fallo generando el ambiente sonoro")
    return ruta_salida

def mezclar_con_narracion(ruta_narracion: str, ruta_ambiente: str, ruta_salida: str):
    filtro = (
        "[1:a][0:a]sidechaincompress=threshold=0.03:ratio=8:attack=50:release=400[amb_duck];"
        "[0:a][amb_duck]amix=inputs=2:duration=first:dropout_transition=0"
    )
    _ffmpeg(["ffmpeg", "-y", "-i", ruta_narracion, "-i", ruta_ambiente,
             "-filter_complex", filtro, "-ac", "2", ruta_salida],
            "Fallo mezclando ambiente + narración")
    return ruta_salida

def generar_alarma_intro(ruta_salida: str, duracion_segundos: float = 3.0):
    filtro = (
        f"sine=frequency=800:duration={duracion_segundos},"
        f"apulsator=hz=2.5,volume=0.4,"
        f"afade=t=out:st={max(duracion_segundos-0.3, 0)}:d=0.3"
    )
    _ffmpeg(["ffmpeg", "-y", "-f", "lavfi", "-i", filtro, "-ac", "2", ruta_salida], "Fallo generando la alarma del intro")
    return ruta_salida
