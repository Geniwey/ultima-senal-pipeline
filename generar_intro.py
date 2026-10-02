"""Última Señal - Bumper de alta retención (Radar Alert)"""
import subprocess
import os

ANCHO, ALTO = 1920, 1080
DURACION = 2.5
COLOR_FONDO = "0x050505"
COLOR_ALERTA = "0xFF1111"

def generar_intro(ruta_salida: str):
    # Efecto de radar, línea de escaneo, y parpadeo rápido tipo "CRITICAL ERROR"
    filtro = (
        f"color=c={COLOR_FONDO}:s={ANCHO}x{ALTO}:d={DURACION},"
        f"drawgrid=w=100:h=100:t=2:c={COLOR_ALERTA}@0.3,"
        f"drawtext=text='ÚLTIMA SEÑAL':fontcolor={COLOR_ALERTA}:fontsize=180:"
        f"font='DejaVu Sans Bold':x=(w-text_w)/2:y=(h-text_h)/2:"
        f"alpha='if(lt(mod(t,0.3),0.15),1,0.2)'," # Parpadeo cardíaco
        f"noise=alls=20:allf=t+u" # Ruido de cámara/pantalla rota
    )
    comando = ["ffmpeg", "-y", "-f", "lavfi", "-i", filtro, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-t", str(DURACION), ruta_salida]
    subprocess.run(comando, capture_output=True, text=True)
    return ruta_salida

def generar_outro(ruta_salida: str):
    # Outro de 2 segundos. Negro absoluto. Corte dramático.
    filtro = f"color=c=black:s={ANCHO}x{ALTO}:d=2"
    comando = ["ffmpeg", "-y", "-f", "lavfi", "-i", filtro, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-t", "2", ruta_salida]
    subprocess.run(comando, capture_output=True, text=True)
    return ruta_salida
