import subprocess
import os

def generar_miniatura_desde_imagen(ruta_imagen_base: str, titulo_corto: str, ruta_salida: str):
    if not os.path.exists(ruta_imagen_base): 
        raise RuntimeError(f"No existe imagen base para la miniatura: {ruta_imagen_base}")
        
    texto_seguro = titulo_corto[:35].upper().replace("\\", "").replace(":", "").replace("'", "").replace('"', "").strip()
    
    # Dividir el texto en dos líneas si es muy largo para que no se salga de la pantalla
    palabras = texto_seguro.split()
    if len(palabras) > 2:
        mitad = len(palabras) // 2
        linea1 = " ".join(palabras[:mitad])
        linea2 = " ".join(palabras[mitad:])
    else:
        linea1 = texto_seguro
        linea2 = ""

    filtro = "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,vignette=angle=PI/2.5"
    
    # Línea 1 (Arriba)
    filtro += (
        f",drawtext=text='{linea1}':fontcolor=#FFE800:fontsize=120:"
        f"font='DejaVu Sans Bold':borderw=12:bordercolor=black@1.0:"
        f"shadowcolor=black@1.0:shadowx=15:shadowy=15:"
        f"x=(w-text_w)/2:y=h-text_h-180"
    )
    
    # Línea 2 (Abajo, si existe)
    if linea2:
        filtro += (
            f",drawtext=text='{linea2}':fontcolor=#FFE800:fontsize=120:"
            f"font='DejaVu Sans Bold':borderw=12:bordercolor=black@1.0:"
            f"shadowcolor=black@1.0:shadowx=15:shadowy=15:"
            f"x=(w-text_w)/2:y=h-text_h-40"
        )
    else:
        # Si es una sola línea, la bajamos un poco
        filtro = filtro.replace("y=h-text_h-180", "y=h-text_h-100")
        
    comando = [
        "ffmpeg", "-y", "-i", ruta_imagen_base, 
        "-vf", filtro, "-frames:v", "1", "-q:v", "2", ruta_salida
    ]
    
    resultado = subprocess.run(comando, capture_output=True, text=True)
    if resultado.returncode != 0:
        raise RuntimeError(f"Fallo generando la miniatura:\n{resultado.stderr[-600:]}")
    return ruta_salida
