import subprocess
import os

FPS = 30
ANCHO, ALTO = 1920, 1080


def animar_imagen(
    ruta_imagen: str,
    duracion_segundos: float,
    ruta_salida: str,
    indice_variante: int,
    texto_pantalla: str = None,
    ruta_ass: str = None,
    es_infografia: bool = False,
):
    carpeta_destino = os.path.dirname(os.path.abspath(ruta_salida))
    os.makedirs(carpeta_destino, exist_ok=True)

    if os.path.exists(ruta_salida) and os.path.getsize(ruta_salida) > 10_000:
        return ruta_salida

    num_frames = max(int(duracion_segundos * FPS), FPS)
    filtro_normalizar = f"scale={ANCHO}:{ALTO}:force_original_aspect_ratio=increase,crop={ANCHO}:{ALTO},setsar=1"

    # MEDIDA CRÍTICA: Si es una infografía (mapa, gráfica o diagrama), NO hacer zoom que corte los bordes
    if es_infografia:
        filtros = [filtro_normalizar]
    else:
        variantes = [
            {"z_ini": 1.0, "z_fin": 1.12, "px": "iw/2-(iw/zoom/2)+10*sin(on/22)", "py": "ih/2-(ih/zoom/2)"},
            {"z_ini": 1.12, "z_fin": 1.0, "px": "iw/2-(iw/zoom/2)-10*sin(on/25)", "py": "ih/2-(ih/zoom/2)"},
            {"z_ini": 1.04, "z_fin": 1.14, "px": "0", "py": "ih/2-(ih/zoom/2)"},
            {"z_ini": 1.14, "z_fin": 1.04, "px": "iw-iw/zoom", "py": "ih/2-(ih/zoom/2)"},
        ]
        var = variantes[indice_variante % len(variantes)]
        z_ini, z_fin = var["z_ini"], var["z_fin"]
        incremento = (z_fin - z_ini) / num_frames
        filtro_zoompan = (
            f"{filtro_normalizar},"
            f"zoompan=z='{z_ini}+{incremento}*on':x='{var['px']}':y='{var['py']}':d={num_frames}:s={ANCHO}x{ALTO}:fps={FPS}"
        )
        filtros = [filtro_zoompan, "vignette=angle=PI/4.5"]

    # Rótulos grandes abajo centrados (62px) con caja negra de alto contraste
    if texto_pantalla:
        texto_seguro = (
            texto_pantalla.strip().upper()
            .replace("\\", "")
            .replace(":", "\\:")
            .replace("'", "")
            .replace('"', "")
            .replace("%", "")
        )
        tamano_letra = 62 if len(texto_seguro) <= 22 else max(46, int(1380 / len(texto_seguro)))
        filtros.append(
            f"drawtext=text='{texto_seguro}':fontcolor=white:fontsize={tamano_letra}:"
            f"font='DejaVu Sans Bold':borderw=4:bordercolor=black@1.0:"
            f"box=1:boxcolor=black@0.85:boxborderw=20:"
            f"x=(w-text_w)/2:y=h-text_h-85:"
            f"alpha='if(lt(t,0.3),t/0.3,1)'"
        )

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
            "-vf", filtro_normalizar,
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
        es_info = str(escena.get("prompt_imagen", "")).startswith("INFOGRAFIA:")
        print(f" Animando clip {i+1}/{total} ({'Infografía Fija' if es_info else 'Cine Zoom'})...")
        animar_imagen(
            ruta_imagen,
            escena["duracion_segundos"],
            ruta_clip,
            i,
            texto_pantalla=escena.get("texto_pantalla"),
            ruta_ass=escena.get("ruta_ass"),
            es_infografia=es_info,
        )
        clips.append(ruta_clip)
    return clips
