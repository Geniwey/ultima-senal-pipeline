import subprocess
import os
import json
import re
from generar_intro import generar_intro, generar_outro
from generar_ambiente import generar_ambiente, mezclar_con_narracion, generar_alarma_intro


def _duracion_audio(ruta: str) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", ruta],
        capture_output=True,
        text=True,
    )
    return float(r.stdout.strip())


def _concatenar_audios(rutas_audio: list, ruta_salida: str):
    validas = [r for r in rutas_audio if os.path.exists(r) and os.path.getsize(r) > 100]
    lista_txt = ruta_salida + "_lista.txt"
    with open(lista_txt, "w", encoding="utf-8") as f:
        for ruta in validas:
            f.write(f"file '{os.path.abspath(ruta)}'\n")
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lista_txt, "-c:a", "libmp3lame", "-q:a", "2", ruta_salida], capture_output=True)
    if os.path.exists(lista_txt):
        os.remove(lista_txt)


def _concatenar_video(rutas_clips: list, ruta_salida: str):
    validas = [r for r in rutas_clips if os.path.exists(r) and os.path.getsize(r) > 1000]
    lista_txt = ruta_salida + "_lista.txt"
    with open(lista_txt, "w", encoding="utf-8") as f:
        for ruta in validas:
            f.write(f"file '{os.path.abspath(ruta)}'\n")
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lista_txt, "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p", "-r", "30", ruta_salida],
        capture_output=True,
    )
    if os.path.exists(lista_txt):
        os.remove(lista_txt)


def _normalizar_audio_dos_pasadas(audio_entrada: str, salida_m4a: str):
    p1 = subprocess.run(
        ["ffmpeg", "-y", "-i", audio_entrada, "-af", "loudnorm=I=-16:TP=-3.0:LRA=11:print_format=json", "-f", "null", "-"],
        capture_output=True,
        text=True,
    )
    match = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", p1.stderr, re.DOTALL)
    if match:
        stats = json.loads(match.group(0))
        filtro = (
            f"loudnorm=I=-16:TP=-3.0:LRA=11:measured_I={stats['input_i']}:"
            f"measured_LRA={stats['input_lra']}:measured_TP={stats['input_tp']}:"
            f"measured_thresh={stats['input_thresh']}:offset={stats['target_offset']}:linear=true,"
            "alimiter=level_in=1:level_out=1:limit=0.63:attack=5:release=50:level=disabled"
        )
    else:
        filtro = "loudnorm=I=-16:TP=-3.0:LRA=11,alimiter=level_in=1:level_out=1:limit=0.63:attack=5:release=50:level=disabled"

    subprocess.run(["ffmpeg", "-y", "-i", audio_entrada, "-af", filtro, "-c:a", "aac", "-b:a", "192k", salida_m4a], capture_output=True)


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

    audio_master = ruta_salida + "_master_temp.m4a"
    _normalizar_audio_dos_pasadas(audio_con_ambiente, audio_master)

    subprocess.run(
        ["ffmpeg", "-y", "-i", video_temp, "-i", audio_master, "-c:v", "copy", "-c:a", "copy", "-map", "0:v:0", "-map", "1:a:0", "-shortest", ruta_salida],
        capture_output=True,
    )

    for temp in [video_temp, audio_temp, ruta_intro, ruta_outro, ruta_intro_alarma, ruta_ambiente, audio_con_ambiente, audio_master]:
        if os.path.exists(temp):
            os.remove(temp)
    return ruta_salida
