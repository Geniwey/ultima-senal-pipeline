"""
Última Señal — Montaje final
===============================
Une los clips animados en orden, concatena todos los audios de voz,
sincroniza, quema los subtítulos y exporta el vídeo final listo para subir.
"""

import subprocess
import os
import json


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


def montar_video_final(carpeta_clips: str, carpeta_audios: str, ruta_srt: str,
                        ruta_salida: str, info_escenas_path: str):
    with open(info_escenas_path, "r", encoding="utf-8") as f:
        info_escenas = json.load(f)

    rutas_clips = [os.path.join(carpeta_clips, f"clip_{e['indice']:02d}.mp4") for e in info_escenas]
    rutas_audios = [e["ruta_audio"] for e in info_escenas]

    print("Concatenando vídeo (sin audio)...")
    video_temp = ruta_salida + "_video_temp.mp4"
    _concatenar_video(rutas_clips, video_temp)

    print("Concatenando audio...")
    audio_temp = ruta_salida + "_audio_temp.mp3"
    _concatenar_audios(rutas_audios, audio_temp)

    print("Uniendo audio + vídeo y quemando subtítulos...")
    filtro_subs = f"subtitles={ruta_srt}:force_style='FontName=Arial,FontSize=20,PrimaryColour=&HFFFFFF&,OutlineColour=&H000000&,BorderStyle=1,Outline=2,Alignment=2,MarginV=60'"

    comando = [
        "ffmpeg", "-y", "-i", video_temp, "-i", audio_temp,
        "-vf", filtro_subs,
        "-c:v", "libx264", "-crf", "18", "-preset", "medium",
        "-c:a", "aac", "-b:a", "192k",
        "-map", "0:v:0", "-map", "1:a:0",
        "-shortest",
        ruta_salida,
    ]
    resultado = subprocess.run(comando, capture_output=True, text=True)

    os.remove(video_temp)
    os.remove(audio_temp)

    if resultado.returncode != 0 or not os.path.exists(ruta_salida):
        raise RuntimeError(f"Fallo en el montaje final:\n{resultado.stderr[-1000:]}")

    print(f"✓ Vídeo final listo: {ruta_salida}")
    return ruta_salida
