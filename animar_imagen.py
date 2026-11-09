import subprocess
import os

FPS = 30
ANCHO, ALTO = 1920, 1080


def animar_imagen(ruta_imagen: str, duracion_segundos: float, ruta_salida: str, indice_variante: int, texto_pantalla: str = None, ruta_ass: str = None):
    carpeta_destino = os.path.dirname(os.path.abspath(ruta_salida))
    os.makedirs(carpeta_destino, exist_ok=True)

    if os.path.exists(ruta_salida) and os.path.getsize(ruta_salida) > 10_000:
        return ruta_salida

    num_frames = max(int(duracion_segundos * FPS), FPS)

    # Dinamismo reactivo: si la escena habla de impacto/pánico/alarma hace un zoom violento hacia dentro
    texto_eval = (texto_pantalla or "").lower()
    es_climax = any(k in texto_eval for k in ("impacto", "alarma", "caída", "roce", "marina", "emergencia", "falso"))

    if es_climax:
        z_ini, z_fin = 1.05, 1.25
        pan_x = "iw/2-(iw/zoom/2)"
        pan_y = "ih/2-(ih/zoom/2)"
    else:
        variantes = [
            {"z_ini": 1.0, "z_fin": 1.12, "px": "iw/2-(iw/zoom/2)+12*sin(on/22)", "py": "ih/2-(ih/zoom/2)"},
            {"z_ini": 1.14, "z_fin": 1.02, "px": "iw/2-(iw/zoom/2)-10*sin(on/26)", "py": "ih/2-(ih/zoom/2)"},
            {"z_ini": 1.04, "z_fin": 1.15, "px": "0", "py": "ih/2-(ih/zoom/2)"},
            {"z_ini": 1.15, "z_fin": 1.05, "px": "iw-iw/zoom", "py": "ih/2-(ih/zoom/2)"},
        ]
        var = variantes[indice_variante % len(variantes)]
        z_ini, z_fin = var["z_ini"], var["z_fin"]
        pan_x, pan_y = var["px"], var["py"]

    incremento = (z_fin - z_ini) / num_frames

    filtro_normalizar = f"scale={ANCHO}:{ALTO}:force_original_aspect_ratio=increase,crop={ANCHO}:{ALTO},setsar=1"
    filtro_zoompan = f"{filtro_normalizar},zoompan=z='{z_ini}+{incremento}*on':x='{pan_x}':y='{pan_y}':d={num_frames}:s={ANCHO}x{ALTO}:fps={FPS}"
    filtros = [filtro_zoompan, "vignette=angle=PI/4.5"]

    # Rótulo de datos en la parte superior izquierda (estilo panel documental moderno)
    if texto_pantalla:
        texto_seguro = (
            texto_pantalla.strip().upper()
            .replace("\\", "")
            .replace(":", "\\:")
            .replace("'", "")
            .replace('"', "")
            .replace("%", "")
        )
        tamano_letra = 40 if len(texto_seguro) <= 24 else 34
        filtros.append(
            f"drawtext=text='{texto_seguro}':fontcolor=white:fontsize={tamano_letra}:"
            f"font='DejaVu Sans Bold':borderw=2:bordercolor=black@0.9:"
            f"box=1:boxcolor=black@0.85:boxborderw=14:"
            f"x=60:y=60:"
            f"alpha='if(lt(t,0.3),t/0.3,1)'"
        )

    # Superponer subtítulos dinámicos palabra por palabra si existe el archivo .ass
    if ruta_ass and os.path.exists(ruta_ass):
        ruta_ass_escapada = os.path.abspath(ruta_ass).replace("\\", "/").replace(":", "\\:")
        filtros.append(f"subtitles=filename='{ruta_ass_escapada}'")

    comando = [
        "ffmpeg", "-y", "-loop", "1", "-i", ruta_imagen,
        "-vf", ",".join(filtros),
        "-t", str(duracion_segundos),
        "-r", str(FPS),
        "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
        ruta_salida,
    ]
    resultado = subprocess.run(comando, capture_output=True, text=True)

    if resultado.returncode != 0 or not os.path.exists(ruta_salida) or os.path.getsize(ruta_salida) < 1000:
        comando_simple = [
            "ffmpeg", "-y", "-loop", "1", "-i", ruta_imagen,
            "-vf", f"scale={ANCHO}:{ALTO}:force_original_aspect_ratio=increase,crop={ANCHO}:{ALTO},setsar=1",
            "-t", str(duracion_segundos),
            "-r", str(FPS),
            "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
            ruta_salida,
        ]
        subprocess.run(comando_simple, capture_output=True, text=True)

    return ruta_salida


def animar_todas(info_escenas: list, carpeta_imagenes: str, carpeta_salida: str):
    os.makedirs(carpeta_salida, exist_ok=True)
    clips = []
    total = len(info_escenas)
    for i, escena in enumerate(info_escenas):
        ruta_imagen = os.path.join(carpeta_imagenes, f"escena_{escena['indice']:02d}.png")
        ruta_clip = os.path.join(carpeta_salida, f"clip_{escena['indice']:02d}.mp4")
        print(f" Animando clip horizontal {i+1}/{total}...")
        animar_imagen(
            ruta_imagen,
            escena["duracion_segundos"],
            ruta_clip,
            i,
            texto_pantalla=escena.get("texto_pantalla"),
            ruta_ass=escena.get("ruta_ass")
        )
        clips.append(ruta_clip)
    return clips
