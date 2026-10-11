import subprocess
import os

FPS = 30
VARIANTES = [
    {"z_in": 1.0, "z_out": 1.15, "px": "iw/2-(iw/zoom/2)+10*sin(on/20)", "py": "ih/2-(ih/zoom/2)"},
    {"z_in": 1.15, "z_out": 1.0, "px": "iw/2-(iw/zoom/2)+10*sin(on/25)", "py": "ih/2-(ih/zoom/2)"},
    {"z_in": 1.05, "z_out": 1.2, "px": "0", "py": "ih/2-(ih/zoom/2)+5*sin(on/15)"}
]

def animar_imagen(ruta_imagen: str, duracion_segundos: float, ruta_salida: str, indice_variante: int, texto_pantalla: str = None):
    # Forzar sobreescritura, no usamos cache
    if os.path.exists(ruta_salida): os.remove(ruta_salida)
        
    variante = VARIANTES[indice_variante % len(VARIANTES)]
    num_frames = max(int(duracion_segundos * FPS), FPS)
    z_ini, z_fin = variante["z_in"], variante["z_out"]
    incremento = (z_fin - z_ini) / num_frames
    
    # TRUCO ANTI-JITTER: Escalar a 4K, hacer zoom, y bajar a 1080p. Suavidad perfecta.
    filtro_escala = "scale=3840:2160,zoompan=z='{}+{}*on':x='{}':y='{}':d={}:s=1920x1080:fps={}".format(
        z_ini, incremento, variante['px'], variante['py'], num_frames, FPS
    )
    filtros = [filtro_escala, "vignette=angle=PI/4"]
    
    if texto_pantalla:
        texto_seguro = texto_pantalla.upper().replace("\\", "").replace(":", "").replace("'", "").replace('"', "")
        filtros.append(
            f"drawtext=text='{texto_seguro}':fontcolor=white:fontsize=75:"
            f"font='DejaVu Sans Bold':box=1:boxcolor=black@0.5:boxborderw=20:"
            f"borderw=2:bordercolor=black@1.0:"
            f"shadowcolor=black@0.8:shadowx=5:shadowy=5:"
            f"x=(w-text_w)/2:y=h-text_h-100:alpha='if(lt(t,0.3),t/0.3,1)'"
        )
        
    comando = ["ffmpeg", "-y", "-loop", "1", "-i", ruta_imagen, "-vf", ",".join(filtros), "-t", str(duracion_segundos), "-c:v", "libx264", "-pix_fmt", "yuv420p", ruta_salida]
    resultado = subprocess.run(comando, capture_output=True, text=True)
    if resultado.returncode != 0:
        print(f"Error FFmpeg animación:\n{resultado.stderr[-500:]}")
    return ruta_salida

def animar_todas(info_escenas: list, carpeta_imagenes: str, carpeta_salida: str):
    clips = []
    for i, escena in enumerate(info_escenas):
        ruta_imagen = os.path.join(carpeta_imagenes, f"escena_{escena['indice']:02d}.png")
        ruta_clip = os.path.join(carpeta_salida, f"clip_{escena['indice']:02d}.mp4")
        if os.path.exists(ruta_imagen):
            animar_imagen(ruta_imagen, escena["duracion_segundos"], ruta_clip, i, escena.get("texto_pantalla"))
            clips.append(ruta_clip)
    return clips
