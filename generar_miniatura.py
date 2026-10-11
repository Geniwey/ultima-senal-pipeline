import subprocess
import os

def generar_miniatura_desde_imagen(ruta_imagen_base: str, titulo_corto: str, ruta_salida: str):
    texto_seguro = titulo_corto[:35].upper().replace("\\", "").replace(":", "").replace("'", "").replace('"', "").strip()
    
    palabras = texto_seguro.split()
    if len(palabras) > 2 and len(texto_seguro) > 15:
        mitad = len(palabras) // 2
        linea1, linea2 = " ".join(palabras[:mitad]), " ".join(palabras[mitad:])
    else:
        linea1, linea2 = texto_seguro, ""

    # Cálculo dinámico estricto: Si la línea es larguísima, la fuente baja drásticamente
    fs1 = min(150, max(70, int(1500 / max(len(linea1), 1))))
    fs2 = min(150, max(70, int(1500 / max(len(linea2), 1)))) if linea2 else 150

    filtro = "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,vignette=angle=PI/2.5"
    
    filtro += (
        f",drawtext=text='{linea1}':fontcolor=#FFE800:fontsize={fs1}:"
        f"font='DejaVu Sans Bold':borderw=12:bordercolor=black@1.0:"
        f"shadowcolor=black@1.0:shadowx=12:shadowy=12:"
        f"x=(w-text_w)/2:y=h-text_h-180"
    )
    if linea2:
        filtro += (
            f",drawtext=text='{linea2}':fontcolor=#FFE800:fontsize={fs2}:"
            f"font='DejaVu Sans Bold':borderw=12:bordercolor=black@1.0:"
            f"shadowcolor=black@1.0:shadowx=12:shadowy=12:"
            f"x=(w-text_w)/2:y=h-text_h-40"
        )
    else:
        filtro = filtro.replace("y=h-text_h-180", "y=h-text_h-100")
        
    subprocess.run(["ffmpeg", "-y", "-i", ruta_imagen_base, "-vf", filtro, "-frames:v", "1", "-q:v", "2", ruta_salida])
    return ruta_salida
