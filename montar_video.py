# Código estable[span_24](start_span)[span_24](end_span)[span_25](start_span)[span_25](end_span)[span_26](start_span)[span_26](end_span)
import subprocess
import os
import json
from generar_intro import generar_intro, generar_outro
from generar_ambiente import generar_ambiente, mezclar_con_narracion, generar_alarma_intro

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
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lista_txt, "-c", "copy", ruta_salida], capture_output=True)
    os.remove(lista_txt)

def _concatenar_video(rutas_clips: list, ruta_salida: str):
    lista_txt = ruta_salida + "_lista.txt"
    with open(lista_txt, "w", encoding="utf-8") as f:
        for ruta in rutas_clips:
            f.write(f"file '{os.path.abspath(ruta)}'\n")
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lista_txt, "-c", "copy", ruta_salida], capture_output=True)
    os.remove(lista_txt)

def _generar_silencio(ruta_salida: str, duracion: int):
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-t", str(duracion), "-q:a", "9", "-acodec", "libmp3lame", ruta_salida], capture_output=True)

def montar_video_final(carpeta_clips: str, carpeta_audios: str, ruta_salida: str, info_escenas_path: str):
    with open(info_escenas_path, "r", encoding="utf-8") as f:
        info_escenas = json.load(f)
        
    rutas_clips = [os.path.join(carpeta_clips, f"clip_{e['indice']:02d}.mp4") for e in info_escenas]
    rutas_audios = [e["ruta_audio"] for e in info_escenas]
    
    ruta_intro = ruta_salida + "_intro_temp.mp4"
    generar_intro(ruta_intro)
    ruta_outro = ruta_salida + "_outro_temp.mp4"
    generar_outro(ruta_outro)
    ruta_intro_alarma = ruta_salida + "_intro_alarma_temp.mp3"
    generar_alarma_intro(ruta_intro_alarma, 3)
    ruta_outro_silencio = ruta_salida + "_outro_silencio_temp.mp3"
    _generar_silencio(ruta_outro_silencio, 3)
    
    video_temp = ruta_salida + "_video_temp.mp4"
    _concatenar_video([ruta_intro] + rutas_clips + [ruta_outro], video_temp)
    
    audio_temp = ruta_salida + "_audio_temp.mp3"
    _concatenar_audios([ruta_intro_alarma] + rutas_audios + [ruta_outro_silencio], audio_temp)
    
    duracion_total = _duracion_audio(audio_temp)
    ruta_ambiente = ruta_salida + "_ambiente_temp.mp3"
    generar_ambiente(ruta_ambiente, duracion_total)
    
    audio_con_ambiente = ruta_salida + "_audio_con_ambiente_temp.mp3"
    mezclar_con_narracion(audio_temp, ruta_ambiente, audio_con_ambiente)
    
    comando = [
        "ffmpeg", "-y", "-i", video_temp, "-i", audio_con_ambiente,
        "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
        "-c:v", "libx264", "-crf", "23", "-preset", "medium",
        "-c:a", "aac", "-b:a", "192k",
        "-map", "0:v:0", "-map", "1:a:0", "-shortest", ruta_salida,
    ]
    subprocess.run(comando, capture_output=True)
    
    for temp in [video_temp, audio_temp, ruta_intro, ruta_outro, ruta_intro_alarma, ruta_outro_silencio, ruta_ambiente, audio_con_ambiente]:
        if os.path.exists(temp): os.remove(temp)
    return ruta_salida
