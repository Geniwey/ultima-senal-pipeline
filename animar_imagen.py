"""
Última Señal — Animación Ken Burns (FFmpeg zoompan)
======================================================
Convierte cada imagen fija en un clip con zoom/paneo lento, con duración
exacta igual al audio de esa escena (para que casen perfecto en el montaje).

4 variantes de movimiento que van rotando, para que no se note repetitivo
escena tras escena (mismo principio que ya usas en Box to Box FC).
"""

import subprocess
import os

FPS = 30
ANCHO, ALTO = 1920, 1080

# Variantes de movimiento: (dirección zoom, dirección paneo)
VARIANTES = [
    {"zoom_inicial": 1.0, "zoom_final": 1.15, "pan_x": "iw/2-(iw/zoom/2)", "pan_y": "ih/2-(ih/zoom/2)"},        # zoom-in centrado
    {"zoom_inicial": 1.15, "zoom_final": 1.0, "pan_x": "iw/2-(iw/zoom/2)", "pan_y": "ih/2-(ih/zoom/2)"},        # zoom-out centrado
    {"zoom_inicial": 1.05, "zoom_final": 1.2, "pan_x": "0", "pan_y": "ih/2-(ih/zoom/2)"},                        # zoom-in + pan derecha
    {"zoom_inicial": 1.2, "zoom_final": 1.05, "pan_x": "iw-iw/zoom", "pan_y": "ih/2-(ih/zoom/2)"},               # zoom-out + pan izquierda
]


def animar_imagen(ruta_imagen: str, duracion_segundos: float, ruta_salida: str, indice_variante: int):
    variante = VARIANTES[indice_variante % len(VARIANTES)]
    num_frames = max(int(duracion_segundos * FPS), FPS)

    z_ini, z_fin = variante["zoom_inicial"], variante["zoom_final"]
    incremento = (z_fin - z_ini) / num_frames

    filtro_zoompan = (
        f"zoompan=z='{z_ini}+{incremento}*on':"
        f"x='{variante['pan_x']}':y='{variante['pan_y']}':"
        f"d={num_frames}:s={ANCHO}x{ALTO}:fps={FPS}"
    )

    comando = [
        "ffmpeg", "-y", "-loop", "1", "-i", ruta_imagen,
        "-vf", filtro_zoompan,
        "-t", str(duracion_segundos),
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        ruta_salida,
    ]

    resultado = subprocess.run(comando, capture_output=True, text=True)
    if resultado.returncode != 0 or not os.path.exists(ruta_salida):
        raise RuntimeError(f"FFmpeg falló animando {ruta_imagen}:\n{resultado.stderr[-800:]}")

    return ruta_salida


def animar_todas(info_escenas: list, carpeta_imagenes: str, carpeta_salida: str) -> list:
    os.makedirs(carpeta_salida, exist_ok=True)
    clips = []
    for i, escena in enumerate(info_escenas):
        ruta_imagen = os.path.join(carpeta_imagenes, f"escena_{escena['indice']:02d}.png")
        ruta_clip = os.path.join(carpeta_salida, f"clip_{escena['indice']:02d}.mp4")
        print(f"  Animando escena {escena['indice']} (duración {escena['duracion_segundos']:.1f}s)...")
        animar_imagen(ruta_imagen, escena["duracion_segundos"], ruta_clip, i)
        clips.append(ruta_clip)
    return clips
