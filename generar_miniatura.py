import subprocess
import os

def generar_miniatura_desde_imagen(ruta_imagen_base: str, titulo_corto: str, ruta_salida: str):
    if not os.path.exists(ruta_imagen_base):
        raise RuntimeError(f"No existe imagen base para la miniatura: {ruta_imagen_base}")
        
    texto_seguro = titulo_corto[:35].upper().replace("\\", "").replace(":", "").replace("'", "").replace('"', "")
    ancho_util = 1200
    fontsize = min(150, max(85, int(ancho_util / (max(len(texto_seguro), 1) * 0.55))))
    
    # ELIMINADO EL FILTRO 'eq' QUE QUEMABA LOS COLORES. 
    # Añadida una capa negra al 30% (black@0.3) para que el texto resalte de forma natural.
    filtro = (
        "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,"
        "drawbox=x=0:y=0:w=1280:h=720:color=black@0.3:t=fill,"
        "vignette=angle=PI/2.5:mode=backward,"
        f"drawtext=text='{texto_seguro}':fontcolor=#FFEA00:fontsize={fontsize}:"
        f"font='DejaVu Sans Bold':borderw=10:bordercolor=black@1.0:"
        f"shadowcolor=black@1.0:shadowx=12:shadowy=12:"
        f"x=(w-text_w)/2:y=h-(text_h+60)"
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
