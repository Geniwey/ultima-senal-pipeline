import subprocess
import os

def generar_miniatura_desde_imagen(ruta_imagen_base: str, titulo_corto: str, ruta_salida: str):
    if not os.path.exists(ruta_imagen_base):
        raise RuntimeError(f"No existe la imagen base para la miniatura: {ruta_imagen_base}")
        
    # Limpiamos el texto y calculamos el tamaño para que sea masivo y no se salga
    texto_seguro = titulo_corto[:35].upper().replace("\\", "").replace(":", "").replace("'", "").replace('"', "")
    ancho_util = 1200
    fontsize = min(140, max(80, int(ancho_util / (max(len(texto_seguro), 1) * 0.60))))
    
    filtro = (
        "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,"
        # Boost brutal de contraste y color para CTR
        "eq=contrast=1.35:saturation=1.45:brightness=-0.05,"
        # Viñeta muy oscura para centrar la atención en el medio
        "vignette=angle=PI/2.2:mode=backward,"
        # Barras cinemáticas arriba y abajo para darle aspecto documental
        "drawbox=x=0:y=0:w=1280:h=45:color=black@0.9:t=fill,"
        "drawbox=x=0:y=675:w=1280:h=45:color=black@0.9:t=fill,"
        # Texto gigantesco, amarillo puro, con borde súper grueso y sombra
        f"drawtext=text='{texto_seguro}':fontcolor=#FFDD00:fontsize={fontsize}:"
        f"font='DejaVu Sans Bold':borderw=10:bordercolor=black@1.0:"
        f"shadowcolor=black@0.9:shadowx=12:shadowy=12:"
        f"x=(w-text_w)/2:y=h-(text_h+70)"
    )
    
    comando = [
        "ffmpeg", "-y", "-i", ruta_imagen_base,
        "-vf", filtro, "-frames:v", "1",
        ruta_salida,
    ]
    
    resultado = subprocess.run(comando, capture_output=True, text=True)
    if resultado.returncode != 0 or not os.path.exists(ruta_salida):
        raise RuntimeError(f"Fallo generando la miniatura:\n{resultado.stderr[-600:]}")
    return ruta_salida
