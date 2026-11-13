import subprocess
import os
import json
from generar_intro import generar_intro, generar_outro
from generar_ambiente import generar_ambiente, mezclar_con_narracion, generar_alarma_intro


def _duracion_audio(ruta: str) -> float:
    resultado = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", ruta],
        capture_output=True,
        text=True,
    )
    return float(resultado.stdout.strip())


def _concatenar_audios(rutas_audio: list, ruta_salida: str):
    rutas_validas = [r for r in rutas_audio if os.path.exists(r) and os.path.getsize(r) > 100]
    lista_txt = ruta_salida + "_lista.txt"
    with open(lista_txt, "w", encoding="utf-8") as f:
        for ruta in rutas_validas:
            f.write(f"file '{os.path.abspath(ruta)}'\n")
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lista_txt, "-c:a", "libmp3lame", "-q:a", "2", ruta_salida],
        capture_output=True,
    )
    if os.path.exists(lista_txt):
        os.remove(lista_txt)


def _concatenar_video(rutas_clips: list, ruta_salida: str):
    rutas_validas = [r for r in rutas_clips if os.path.exists(r) and os.path.getsize(r) > 1000]
    lista_txt = ruta_salida + "_lista.txt"
    with open(lista_txt, "w", encoding="utf-8") as f:
        for ruta in rutas_validas:
            f.write(f"file '{os.path.abspath(ruta)}'\n")
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lista_txt,
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p", "-r", "30",
            ruta_salida,
        ],
        capture_output=True,
    )
    if os.path.exists(lista_txt):
        os.remove(lista_txt)


def montar_video_final(carpeta_clips: str, carpeta_audios: str, ruta_salida: str, info_escenas_path: str):
    os.makedirs(os.path.dirname(os.path.abspath(ruta_salida)), exist_ok=True)
    with open(info_escenas_path, "r", encoding="utf-8") as f:
        info_escenas = json.load(f)

    rutas_clips = [os.path.join(carpeta_clips, f"clip_{e['indice']:02d}.mp4") for e in info_escenas]
    rutas_audios = [e["ruta_audio"] for e in info_escenas]

    ruta_intro = ruta_salida + "_intro_temp.mp4"
    generar_intro(ruta_intro)
    ruta_outro = ruta_salida + "_outro_temp.mp4"
    generar_outro(ruta_outro)

    ruta_intro_alarma = ruta_salida + "_intro_alarma_temp.mp3"
    generar_alarma_intro(ruta_intro_alarma, 2.5)

    video_temp = ruta_salida + "_video_temp.mp4"
    _concatenar_video([ruta_intro] + rutas_clips + [ruta_outro], video_temp)

    audio_temp = ruta_salida + "_audio_temp.mp3"
    _concatenar_audios([ruta_intro_alarma] + rutas_audios, audio_temp)

    duracion_total = _duracion_audio(audio_temp)
    ruta_ambiente = ruta_salida + "_ambiente_temp.mp3"
    generar_ambiente(ruta_ambiente, duracion_total)

    audio_con_ambiente = ruta_salida + "_audio_con_ambiente_temp.mp3"
    mezclar_con_narracion(audio_temp, ruta_ambiente, audio_con_ambiente)

    # Normalización -16 LUFS + limitador físico para que el pico nunca supere -1.5 dB
    comando = [
        "ffmpeg", "-y", "-i", video_temp, "-i", audio_con_ambiente,
        "-af", "loudnorm=I=-16:TP=-1.5:LRA=11,alimiter=limit=0.84:level=disabled:attack=5:release=50",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-map", "0:v:0", "-map", "1:a:0", "-shortest", ruta_salida,
    ]
    subprocess.run(comando, capture_output=True)

    for temp in [video_temp, audio_temp, ruta_intro, ruta_outro, ruta_intro_alarma, ruta_ambiente, audio_con_ambiente]:
        if os.path.exists(temp):
            os.remove(temp)
    return ruta_salida
