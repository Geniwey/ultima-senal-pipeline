import subprocess
import os

FPS = 30
ANCHO, ALTO = 1920, 1080
VARIANTES = [
    {"zoom_inicial": 1.0, "zoom_final": 1.15, "pan_x": "iw/2-(iw/zoom/2)+10*sin(on/20)", "pan_y": "ih/2-(ih/zoom/2)"},
    {"zoom_inicial": 1.15, "zoom_final": 1.0, "pan_x": "iw/2-(iw/zoom/2)+10*sin(on/25)", "pan_y": "ih/2-(ih/zoom/2)"},
    {"zoom_inicial": 1.05, "zoom_final": 1.2, "pan_x": "0", "pan_y": "ih/2-(ih/zoom/2)"},
    {"zoom_inicial": 1.2, "zoom_final": 1.05, "pan_x": "iw-iw/zoom", "pan_y": "ih-ih/zoom"},
]

def animar_imagen(ruta_imagen: str, duracion_segundos: float, ruta_salida: str, indice_variante: int, texto_pantalla: str = None):
    if os.path.exists(ruta_salida) and os.path.getsize(ruta_salida) > 10_000: return ruta_salida
        
    variante = VARIANTES[indice_variante % len(VARIANTES)]
    num_frames = max(int(duracion_segundos * FPS), FPS)
    z_ini, z_fin = variante["zoom_inicial"], variante["zoom_final"]
    incremento = (z_fin - z_ini) / num_frames
    
    filtro_normalizar = f"scale={ANCHO}:{ALTO}:force_original_aspect_ratio=increase,crop={ANCHO}:{ALTO}"
    filtro_zoompan = f"{filtro_normalizar},zoompan=z='{z_ini}+{incremento}*on':x='{variante['pan_x']}':y='{variante['pan_y']}':d={num_frames}:s={ANCHO}x{ALTO}:fps={FPS}"
    
    filtros = [filtro_zoompan, "vignette=angle=PI/4"]
    
    if texto_pantalla:
        texto_seguro = texto_pantalla.upper().replace("\\", "").replace(":", "").replace("'", "").replace('"', "")
        filtros.append(
            f"drawtext=text='{texto_seguro}':fontcolor=white:fontsize=80:"
            f"font='DejaVu Sans Bold':borderw=4:bordercolor=black@0.9:"
            f"shadowcolor=black@0.8:shadowx=5:shadowy=5:"
            f"x=(w-text_w)/2:y=h-text_h-120:"
            f"alpha='if(lt(t,0.3),t/0.3,1)'"
        )
        
    comando = ["ffmpeg", "-y", "-loop", "1", "-i", ruta_imagen, "-vf", ",".join(filtros), "-t", str(duracion_segundos), "-c:v", "libx264", "-pix_fmt", "yuv420p", ruta_salida]
    subprocess.run(comando, capture_output=True, text=True)
    return ruta_salida

def animar_todas(info_escenas: list, carpeta_imagenes: str, carpeta_salida: str):
    os.makedirs(carpeta_salida, exist_ok=True)
    clips = []
    for i, escena in enumerate(info_escenas):
        ruta_imagen = os.path.join(carpeta_imagenes, f"escena_{escena['indice']:02d}.png")
        ruta_clip = os.path.join(carpeta_salida, f"clip_{escena['indice']:02d}.mp4")
        animar_imagen(ruta_imagen, escena["duracion_segundos"], ruta_clip, i, texto_pantalla=escena.get("texto_pantalla"))
        clips.append(ruta_clip)
    return clips
