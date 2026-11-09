import subprocess
import os
import json


def generar_short_vertical(info_escenas_path: str, carpeta_imagenes: str, ruta_audio_mezclado: str, ruta_salida_short: str):
    """
    Toma los primeros 45-50 segundos del vídeo largo (el gancho en frío), escala el contenido
    a formato vertical (1080x1920) con fondo borroso cinemático y superpone los subtítulos dinámicos verticales.
    """
    os.makedirs(os.path.dirname(os.path.abspath(ruta_salida_short)), exist_ok=True)
    with open(info_escenas_path, "r", encoding="utf-8") as f:
        escenas = json.load(f)

    # Seleccionar las escenas del gancho inicial que sumen entre 40 y 55 segundos
    escenas_short = []
    duracion_acum = 0.0
    for e in escenas:
        if duracion_acum + e["duracion_segundos"] > 55.0 and len(escenas_short) >= 4:
            break
        escenas_short.append(e)
        duracion_acum += e["duracion_segundos"]

    clips_verticales = []
    carpeta_clips_vert = os.path.join(os.path.dirname(ruta_salida_short), "clips_short_temp")
    os.makedirs(carpeta_clips_vert, exist_ok=True)

    for i, esc in enumerate(escenas_short):
        ruta_img = os.path.join(carpeta_imagenes, f"escena_{esc['indice']:02d}.png")
        ruta_clip_v = os.path.join(carpeta_clips_vert, f"clip_vert_{i:02d}.mp4")

        # Filtro de composición vertical 9:16 (Fondo 1080x1920 desenfocado + Ventana central nítida)
        filtro_vert = (
            "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,gblur=sigma=28[fondo];"
            "[0:v]scale=1080:608:force_original_aspect_ratio=decrease[primer_plano];"
            "[fondo][primer_plano]overlay=x=(W-w)/2:y=(H-h)/2[base]"
        )

        ruta_ass_v = esc.get("ruta_ass_vertical")
        if ruta_ass_v and os.path.exists(ruta_ass_v):
            ruta_ass_escapada = os.path.abspath(ruta_ass_v).replace("\\", "/").replace(":", "\\:")
            filtro_vert += f";[base]subtitles=filename='{ruta_ass_escapada}'[outv]"
        else:
            filtro_vert += ";[base]null[outv]"

        cmd = [
            "ffmpeg", "-y", "-loop", "1", "-i", ruta_img,
            "-filter_complex", filtro_vert,
            "-map", "[outv]",
            "-t", str(esc["duracion_segundos"]),
            "-r", "30",
            "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
            ruta_clip_v,
        ]
        subprocess.run(cmd, capture_output=True)
        clips_verticales.append(ruta_clip_v)

    lista_txt = ruta_salida_short + "_lista.txt"
    with open(lista_txt, "w", encoding="utf-8") as f:
        for c in clips_verticales:
            f.write(f"file '{os.path.abspath(c)}'\n")

    video_vert_temp = ruta_salida_short + "_temp.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lista_txt,
            "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-r", "30",
            video_vert_temp,
        ],
        capture_output=True,
    )

    # Cortar el audio exacto correspondiente a esa duración y unir
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", video_vert_temp, "-i", ruta_audio_mezclado,
            "-t", str(duracion_acum),
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            ruta_salida_short,
        ],
        capture_output=True,
    )

    # Limpieza de temporales
    for c in clips_verticales:
        if os.path.exists(c):
            os.remove(c)
    if os.path.exists(lista_txt):
        os.remove(lista_txt)
    if os.path.exists(video_vert_temp):
        os.remove(video_vert_temp)
    if os.path.exists(carpeta_clips_vert):
        try:
            os.rmdir(carpeta_clips_vert)
        except Exception:
            pass

    return ruta_salida_short
