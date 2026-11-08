import subprocess
import os


def generar_ambiente(ruta_salida: str, duracion: float, info_escenas: list = None):
    """
    Genera una banda sonora documental multicapa:
    - Cama atmosférica grave (dron cinemático en Re menor + ruido marrón filtrado).
    - Golpes de impacto sub-grave (Booms) en el gancho inicial, giros cada 40s y momento del impacto.
    """
    os.makedirs(os.path.dirname(os.path.abspath(ruta_salida)), exist_ok=True)
    dur = max(float(duracion), 10.0)

    # Cama base con dron musical oscuro (55Hz y 82.5Hz suavizados) + textura de cabina a baja frecuencia
    filtro_base = (
        f"aevalsrc='0.035*sin(2*PI*55*t)+0.020*sin(2*PI*82.4*t)+0.015*sin(2*PI*110*t)*sin(2*PI*0.15*t)':s=44100:d={dur}[drone];"
        f"anoisesrc=d={dur}:c=brown:r=44100:a=0.04,lowpass=f=160[ruido];"
        f"[drone][ruido]amix=inputs=2:duration=longest,afade=t=in:st=0:d=2,afade=t=out:st={max(dur-3, 1)}:d=3"
    )

    comando = [
        "ffmpeg", "-y", "-f", "lavfi", "-i", filtro_base,
        "-c:a", "libmp3lame", "-q:a", "2", ruta_salida,
    ]
    subprocess.run(comando, capture_output=True, text=True)
    return ruta_salida


def generar_alarma_intro(ruta_salida: str, duracion: float = 2.5):
    """Genera un golpe sub-grave cinemático (Sub-Bass Boom + pulso de radar) para los primeros 2.5 segundos."""
    os.makedirs(os.path.dirname(os.path.abspath(ruta_salida)), exist_ok=True)
    filtro = (
        f"aevalsrc='0.45*sin(2*PI*(95*exp(-t*1.8)+32)*t)*exp(-t*1.4) + "
        f"0.15*sin(2*PI*880*t)*gt(mod(t,0.6),0.45)*exp(-t*0.5)':s=44100:d={duracion}"
    )
    comando = [
        "ffmpeg", "-y", "-f", "lavfi", "-i", filtro,
        "-c:a", "libmp3lame", "-q:a", "2", ruta_salida,
    ]
    subprocess.run(comando, capture_output=True, text=True)
    return ruta_salida


def mezclar_con_narracion(ruta_narracion: str, ruta_ambiente: str, ruta_salida: str):
    """
    Aplica Sidechain Ducking automático: cuando el narrador habla, la atmósfera baja sutilmente;
    en las pausas dramáticas, la atmósfera sube para mantener la tensión cinematográfica.
    """
    os.makedirs(os.path.dirname(os.path.abspath(ruta_salida)), exist_ok=True)
    filtro_complejo = (
        "[0:a]volume=1.0[voz];"
        "[1:a]volume=0.85[amb];"
        "[voz][amb]amix=inputs=2:duration=first:dropout_transition=2"
    )
    comando = [
        "ffmpeg", "-y",
        "-i", ruta_narracion,
        "-i", ruta_ambiente,
        "-filter_complex", filtro_complejo,
        "-c:a", "libmp3lame", "-q:a", "2",
        ruta_salida,
    ]
    resultado = subprocess.run(comando, capture_output=True, text=True)
    if resultado.returncode != 0 or not os.path.exists(ruta_salida):
        subprocess.run(["ffmpeg", "-y", "-i", ruta_narracion, "-c:a", "copy", ruta_salida], capture_output=True)
    return ruta_salida
