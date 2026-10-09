import subprocess
import os

def generar_miniatura_desde_imagen(ruta_imagen_base: str, titulo_corto: str, ruta_salida: str):
    if not os.path.exists(ruta_imagen_base): 
        raise RuntimeError(f"No existe imagen base para la miniatura: {ruta_imagen_base}")
        
    # Limpieza estricta: máximo 28 caracteres. Si el título es muy largo, se corta. 
    # En YouTube, menos palabras = texto más grande = más clics.
    texto_seguro = titulo_corto[:28].upper().replace("\\", "").replace(":", "").replace("'", "").replace('"', "").strip()
    
    # Filtro radicalmente limpio. 
    # Cero cajas negras, cero franjas de cine, cero distorsión de color.
    # Solo la imagen pura, una viñeta, y texto con un borde negro gigante para que resalte siempre.
    filtro = (
        "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,"
        "vignette=angle=PI/2.5,"
        f"drawtext=text='{texto_seguro}':fontcolor=#FFE800:fontsize=140:"
        f"font='DejaVu Sans Bold':borderw=15:bordercolor=black@1.0:"
        f"shadowcolor=black@1.0:shadowx=18:shadowy=18:"
        f"x=(w-text_w)/2:y=h-text_h-80"
    )
    
    comando = [
        "ffmpeg", "-y", "-i", ruta_imagen_base, 
        "-vf", filtro, 
        "-frames:v", "1", 
        "-q:v", "2", # Fuerza la máxima calidad de renderizado de imagen
        ruta_salida
    ]
    
    resultado = subprocess.run(comando, capture_output=True, text=True)
    if resultado.returncode != 0 or not os.path.exists(ruta_salida):
        raise RuntimeError(f"Fallo generando la miniatura:\n{resultado.stderr[-600:]}")
    
    return ruta_salida
