import subprocess
import os

def generar_miniatura_desde_imagen(ruta_imagen_base: str, titulo_corto: str, ruta_salida: str):
    if not os.path.exists(ruta_imagen_base): 
        raise RuntimeError(f"No existe imagen base: {ruta_imagen_base}")
        
    # Limpiamos el texto para evitar errores en FFmpeg
    texto_seguro = titulo_corto[:30].upper().replace("\\", "").replace(":", "").replace("'", "").replace('"', "")
    ancho_util = 1200
    # Cálculo dinámico para que el texto sea lo más grande posible sin salirse de los márgenes
    fontsize = min(150, max(85, int(ancho_util / (max(len(texto_seguro), 1) * 0.55))))
    
    # ELIMINADO EL FILTRO 'eq' PARA NO FREÍR LOS COLORES.
    # Añadimos un viñeteado suave, barras de cine sutiles y un fondo oscurecido al 60% solo en la parte inferior para resaltar el texto.
    filtro = (
        "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,"
        "vignette=angle=PI/3:mode=backward,"
        "drawbox=x=0:y=0:w=1280:h=30:color=black@0.9:t=fill,"
        "drawbox=x=0:y=690:w=1280:h=30:color=black@0.9:t=fill,"
        "drawbox=x=0:y=h-220:w=1280:h=220:color=black@0.6:t=fill,"
        f"drawtext=text='{texto_seguro}':fontcolor=#FFE800:fontsize={fontsize}:"
        f"font='DejaVu Sans Bold':borderw=10:bordercolor=black@1.0:"
        f"shadowcolor=black@0.9:shadowx=12:shadowy=12:"
        f"x=(w-text_w)/2:y=h-(text_h+50)"
    )
    
    # -q:v 2 fuerza la máxima calidad de compresión JPEG/PNG para la miniatura
    comando = ["ffmpeg", "-y", "-i", ruta_imagen_base, "-vf", filtro, "-frames:v", "1", "-q:v", "2", ruta_salida]
    
    resultado = subprocess.run(comando, capture_output=True, text=True)
    if resultado.returncode != 0 or not os.path.exists(ruta_salida):
        raise RuntimeError(f"Fallo generando la miniatura:\n{resultado.stderr[-600:]}")
    
    return ruta_salida
