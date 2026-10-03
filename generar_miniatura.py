import subprocess
import os

def generar_miniatura_desde_imagen(ruta_imagen_base: str, titulo_corto: str, ruta_salida: str):
    if not os.path.exists(ruta_imagen_base):
        raise RuntimeError(f"No existe imagen base para la miniatura: {ruta_imagen_base}")
        
    texto_seguro = titulo_corto[:30].upper().replace("\\", "").replace(":", "").replace("'", "").replace('"', "")
    ancho_util = 1200
    fontsize = min(150, max(85, int(ancho_util / (max(len(texto_seguro), 1) * 0.55))))
    
    filtro = (
        "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,"
        # Valores suavizados para no freír los colores neón del fondo
        "eq=contrast=1.1:saturation=1.05:brightness=-0.05,"
        "vignette=angle=PI/2:mode=backward,"
        "drawbox=x=0:y=0:w=1280:h=30:color=black@0.9:t=fill,"
        "drawbox=x=0:y=690:w=1280:h=30:color=black@0.9:t=fill,"
        f"drawtext=text='{texto_seguro}':fontcolor=#FFE800:fontsize={fontsize}:"
        f"font='DejaVu Sans Bold':borderw=12:bordercolor=black@1.0:"
        f"shadowcolor=black@0.8:shadowx=15:shadowy=15:"
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
