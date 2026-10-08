import subprocess
import os

def generar_miniatura_desde_imagen(ruta_imagen_base: str, titulo_corto: str, ruta_salida: str):
    if not os.path.exists(ruta_imagen_base): raise RuntimeError(f"No existe imagen base: {ruta_imagen_base}")
        
    texto_seguro = titulo_corto[:30].upper().replace("\\", "").replace(":", "").replace("'", "").replace('"', "")
    ancho_util = 1200
    fontsize = min(150, max(85, int(ancho_util / (max(len(texto_seguro), 1) * 0.55))))
    
    # Eliminada la franja superior negra. Añadido más margen inferior (h-text_h-100).
    filtro = (
        "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,"
        "vignette=angle=PI/3:mode=backward,"
        "drawbox=x=0:y=h-250:w=1280:h=250:color=black@0.6:t=fill,"
        f"drawtext=text='{texto_seguro}':fontcolor=#FFE800:fontsize={fontsize}:"
        f"font='DejaVu Sans Bold':borderw=10:bordercolor=black@1.0:"
        f"shadowcolor=black@0.9:shadowx=12:shadowy=12:"
        f"x=(w-text_w)/2:y=h-text_h-100"
    )
    
    comando = ["ffmpeg", "-y", "-i", ruta_imagen_base, "-vf", filtro, "-frames:v", "1", "-q:v", "2", ruta_salida]
    subprocess.run(comando, capture_output=True, text=True)
    return ruta_salida
