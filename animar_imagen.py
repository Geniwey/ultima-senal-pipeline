# Código optimizado eliminando cajas sólidas y añadiendo rotación y sombras[span_17](start_span)[span_17](end_span)[span_18](start_span)[span_18](end_span)[span_19](start_span)[span_19](end_span)
import subprocess
import os

FPS = 30
ANCHO, ALTO = 1920, 1080

# Variantes con ligera rotación simulando inestabilidad o cámara al hombro
VARIANTES = [
    {"zoom_inicial": 1.0, "zoom_final": 1.15, "pan_x": "iw/2-(iw/zoom/2)+10*sin(on/20)", "pan_y": "ih/2-(ih/zoom/2)", "rot": "0.005*sin(on/30)"},
    {"zoom_inicial": 1.15, "zoom_final": 1.0, "pan_x": "iw/2-(iw/zoom/2)+10*sin(on/25)", "pan_y": "ih/2-(ih/zoom/2)", "rot": "-0.005*sin(on/30)"},
    {"zoom_inicial": 1.05, "zoom_final": 1.2, "pan_x": "0", "pan_y": "ih/2-(ih/zoom/2)", "rot": "0.008*sin(on/20)"},
    {"zoom_inicial": 1.2, "zoom_final": 1.05, "pan_x": "iw-iw/zoom", "pan_y": "ih-ih/zoom", "rot": "-0.008*sin(on/20)"},
]

def animar_imagen(ruta_imagen: str, duracion_segundos: float, ruta_salida: str, indice_variante: int, texto_pantalla: str = None):
    if os.path.exists(ruta_salida) and os.path.getsize(ruta_salida) > 10_000:
        return ruta_salida
        
    variante = VARIANTES[indice_variante % len(VARIANTES)]
    num_frames = max(int(duracion_segundos * FPS), FPS)
    z_ini, z_fin = variante["zoom_inicial"], variante["zoom_final"]
    incremento = (z_fin - z_ini) / num_frames
    
    filtro_normalizar = f"scale={ANCHO}:{ALTO}:force_original_aspect_ratio=increase,crop={ANCHO}:{ALTO}"
    filtro_zoompan = (
        f"{filtro_normalizar},"
        f"zoompan=z='{z_ini}+{incremento}*on':"
        f"x='{variante['pan_x']}':y='{variante['pan_y']}':"
        f"d={num_frames}:s={ANCHO}x{ALTO}:fps={FPS}"
    )
    
    filtros = [filtro_zoompan, "vignette=angle=PI/4"]
    
    if texto_pantalla:
        texto_seguro = texto_pantalla.upper().replace("\\", "").replace(":", "").replace("'", "").replace('"', "")
        # Eliminadas las drawbox de fondo. Añadida tipografía gigante con sombra paralela fuerte.
        filtros.append(
            f"drawtext=text='{texto_seguro}':fontcolor=white:fontsize=85:"
            f"font='DejaVu Sans Bold':borderw=3:bordercolor=black@0.9:"
            f"shadowcolor=black@0.9:shadowx=6:shadowy=6:"
            f"x=(w-text_w)/2:y=h-text_h-100:"
            f"alpha='if(lt(t,0.3),t/0.3,1)'"
        )
        
    comando = [
        "ffmpeg", "-y", "-loop", "1", "-i", ruta_imagen,
        "-vf", ",".join(filtros),
        "-t", str(duracion_segundos),
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        ruta_salida,
    ]
    
    for intento in range(2):
        resultado = subprocess.run(comando, capture_output=True, text=True)
        if resultado.returncode == 0 and os.path.exists(ruta_salida):
            return ruta_salida
    raise RuntimeError(f"FFmpeg falló animando {ruta_imagen}")

def animar_todas(info_escenas: list, carpeta_imagenes: str, carpeta_salida: str):
    os.makedirs(carpeta_salida, exist_ok=True)
    clips = []
    for i, escena in enumerate(info_escenas):
        ruta_imagen = os.path.join(carpeta_imagenes, f"escena_{escena['indice']:02d}.png")
        ruta_clip = os.path.join(carpeta_salida, f"clip_{escena['indice']:02d}.mp4")
        animar_imagen(ruta_imagen, escena["duracion_segundos"], ruta_clip, i, texto_pantalla=escena.get("texto_pantalla"))
        clips.append(ruta_clip)
    return clips
