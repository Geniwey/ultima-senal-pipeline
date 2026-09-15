"""
Última Señal — Montaje final
===============================
Une los clips animados en orden, concatena todos los audios de voz,
sincroniza y exporta el vídeo final listo para subir. El texto en pantalla
ya viene quemado en cada clip (paso de animación) como titular corto —
no se añaden subtítulos completos aparte, para no duplicar el texto.
"""

import subprocess
import os
import json

from generar_intro import generar_intro, generar_outro
from generar_ambiente import generar_ambiente, mezclar_con_narracion


def _duracion_audio(ruta: str) -> float:
    resultado = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", ruta],
        capture_output=True, text=True
    )
    return float(resultado.stdout.strip())


def _concatenar_audios(rutas_audio: list, ruta_salida: str):
    lista_txt = ruta_salida + "_lista.txt"
    with open(lista_txt, "w", encoding="utf-8") as f:
        for ruta in rutas_audio:
            f.write(f"file '{os.path.abspath(ruta)}'\n")

    comando = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lista_txt,
               "-c", "copy", ruta_salida]
    resultado = subprocess.run(comando, capture_output=True, text=True)
    os.remove(lista_txt)
    if resultado.returncode != 0:
        raise RuntimeError(f"Fallo concatenando audio:\n{resultado.stderr[-800:]}")


def _concatenar_video(rutas_clips: list, ruta_salida: str):
    lista_txt = ruta_salida + "_lista.txt"
    with open(lista_txt, "w", encoding="utf-8") as f:
        for ruta in rutas_clips:
            f.write(f"file '{os.path.abspath(ruta)}'\n")

    comando = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lista_txt,
               "-c", "copy", ruta_salida]
    resultado = subprocess.run(comando, capture_output=True, text=True)
    os.remove(lista_txt)
    if resultado.returncode != 0:
        raise RuntimeError(f"Fallo concatenando vídeo:\n{resultado.stderr[-800:]}")


def _generar_silencio(ruta_salida: str, duracion: int):
    comando = [
        "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
        "-t", str(duracion), "-q:a", "9", "-acodec", "libmp3lame", ruta_salida,
    ]
    resultado = subprocess.run(comando, capture_output=True, text=True)
    if resultado.returncode != 0:
        raise RuntimeError(f"Fallo generando silencio:\n{resultado.stderr[-500:]}")


def montar_video_final(carpeta_clips: str, carpeta_audios: str,
                        ruta_salida: str, info_escenas_path: str):
    with open(info_escenas_path, "r", encoding="utf-8") as f:
        info_escenas = json.load(f)

    rutas_clips = [os.path.join(carpeta_clips, f"clip_{e['indice']:02d}.mp4") for e in info_escenas]
    rutas_audios = [e["ruta_audio"] for e in info_escenas]

    print("Generando bumper de marca (intro y cierre)...")
    ruta_intro = ruta_salida + "_intro_temp.mp4"
    generar_intro(ruta_intro)
    ruta_outro = ruta_salida + "_outro_temp.mp4"
    generar_outro(ruta_outro)
    ruta_intro_silencio = ruta_salida + "_intro_silencio_temp.mp3"
    _generar_silencio(ruta_intro_silencio, 3)
    ruta_outro_silencio = ruta_salida + "_outro_silencio_temp.mp3"
    _generar_silencio(ruta_outro_silencio, 3)

    print("Concatenando vídeo (intro + escenas + cierre, sin audio)...")
    video_temp = ruta_salida + "_video_temp.mp4"
    _concatenar_video([ruta_intro] + rutas_clips + [ruta_outro], video_temp)

    print("Concatenando audio (silencio + voces + silencio)...")
    audio_temp = ruta_salida + "_audio_temp.mp3"
    _concatenar_audios([ruta_intro_silencio] + rutas_audios + [ruta_outro_silencio], audio_temp)

    print("Añadiendo ambiente sonoro de fondo...")
    duracion_total = _duracion_audio(audio_temp)
    ruta_ambiente = ruta_salida + "_ambiente_temp.mp3"
    generar_ambiente(ruta_ambiente, duracion_total)
    audio_con_ambiente = ruta_salida + "_audio_con_ambiente_temp.mp3"
    mezclar_con_narracion(audio_temp, ruta_ambiente, audio_con_ambiente)

    print("Uniendo audio + vídeo, normalizando volumen al estándar de YouTube...")
    comando = [
        "ffmpeg", "-y", "-i", video_temp, "-i", audio_con_ambiente,
        "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
        "-c:v", "libx264", "-crf", "18", "-preset", "medium",
        "-c:a", "aac", "-b:a", "192k",
        "-map", "0:v:0", "-map", "1:a:0",
        "-shortest",
        ruta_salida,
    ]

    resultado = None
    for intento in range(2):
        resultado = subprocess.run(comando, capture_output=True, text=True)
        if resultado.returncode == 0 and os.path.exists(ruta_salida):
            break
        print(f"  ⚠ Fallo en el montaje final (intento {intento+1}/2), reintentando...")

    os.remove(video_temp)
    os.remove(audio_temp)
    os.remove(ruta_intro)
    os.remove(ruta_outro)
    os.remove(ruta_intro_silencio)
    os.remove(ruta_outro_silencio)
    os.remove(ruta_ambiente)
    os.remove(audio_con_ambiente)

    if resultado.returncode != 0 or not os.path.exists(ruta_salida):
        raise RuntimeError(f"Fallo en el montaje final tras 2 intentos:\n{resultado.stderr[-1000:]}")

    print(f"✓ Vídeo final listo: {ruta_salida}")
    return ruta_salida
