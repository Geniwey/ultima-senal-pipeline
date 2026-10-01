# Código optimizado eliminando cuadros negros y círculos, priorizando texto gigante e impacto[span_20](start_span)[span_20](end_span)[span_21](start_span)[span_21](end_span)
import subprocess
import os

def generar_miniatura_desde_imagen(ruta_imagen_base: str, titulo_corto: str, ruta_salida: str):
    if not os.path.exists(ruta_imagen_base):
        raise RuntimeError(f"No existe la imagen base para la miniatura: {ruta_imagen_base}")
        
    texto_seguro = titulo_corto[:35].upper().replace("\\", "").replace(":", "").replace("'", "").replace('"', "")
    ancho_util = 1160
    fontsize = min(120, max(70, int(ancho_util / (max(len(texto_seguro), 1) * 0.60))))
    
    filtro = (
        "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,"
        "eq=contrast=1.15:saturation=1.2,"
        "vignette=angle=PI/3:mode=backward,"
        f"drawtext=text='{texto_seguro}':fontcolor=yellow:fontsize={fontsize}:"
        f"font='DejaVu Sans Bold':borderw=8:bordercolor=black@1.0:"
        f"shadowcolor=black@0.9:shadowx=8:shadowy=8:"
        f"x=(w-text_w)/2:y=h-(text_h+50)"
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
