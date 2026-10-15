import os
import sys
import json
import time

from generar_guion import generar_guion
from generar_imagen import generar_imagen, fue_ultima_generacion_emergencia
from generar_voz import generar_voces
from animar_imagen import animar_todas
from montar_video import montar_video_final
from generar_miniatura import generar_miniatura_desde_imagen

def ejecutar_pipeline_completo(tema: str, carpeta_proyecto: str = "proyecto"):
    carpeta_audio = os.path.join(carpeta_proyecto, "audio")
    carpeta_imagenes = os.path.join(carpeta_proyecto, "imagenes")
    carpeta_clips = os.path.join(carpeta_proyecto, "clips")

    # BLINDAJE: Crear todas las carpetas necesarias desde el segundo cero
    for carpeta in (carpeta_proyecto, carpeta_audio, carpeta_imagenes, carpeta_clips):
        os.makedirs(carpeta, exist_ok=True)
    
    print("\n=== 1/6: Guion ===")
    ruta_guion = os.path.join(carpeta_proyecto, "guion.json")
    guion = generar_guion(tema)
    with open(ruta_guion, "w", encoding="utf-8") as f:
        json.dump(guion, f, ensure_ascii=False, indent=2)
        
    print("\n=== 2/6: Voz ===")
    info_escenas = generar_voces(ruta_guion, carpeta_audio)
    
    print("\n=== 3/6: Imágenes (Con Visión Artificial y Blindaje) ===")
    ruta_base_miniatura = os.path.join(carpeta_imagenes, "miniatura_base.png")
    miniatura_ok = False
    if guion.get("prompt_miniatura"):
        if generar_imagen(guion["prompt_miniatura"], ruta_base_miniatura):
            if not fue_ultima_generacion_emergencia():
                miniatura_ok = True

    total_escenas = len(info_escenas)
    for idx, escena in enumerate(info_escenas, start=1):
        print(f" Generando imagen {idx}/{total_escenas}...")
        ruta_img = os.path.join(carpeta_imagenes, f"escena_{escena['indice']:02d}.png")
        generar_imagen(escena["prompt_imagen"], ruta_img, semilla=idx * 100)
        
    print("\n=== 4/6: Animación ===")
    animar_todas(info_escenas, carpeta_imagenes, carpeta_clips)
    
    print("\n=== 5/6: Montaje final ===")
    ruta_final = os.path.join(carpeta_proyecto, "video_final.mp4")
    info_escenas_path = os.path.join(carpeta_audio, "info_escenas.json")
    montar_video_final(carpeta_clips, carpeta_audio, ruta_final, info_escenas_path)
    
    ruta_metadata = os.path.join(carpeta_proyecto, "metadata_youtube.txt")
    capitulos = []
    tiempo_acumulado = 2.5
    paso = max(len(info_escenas) // 7, 1)
    
    for i, escena in enumerate(info_escenas):
        if i == 0 or i % paso == 0:
            minutos, segundos = int(tiempo_acumulado // 60), int(tiempo_acumulado % 60)
            titulo_cap = escena.get("texto_pantalla") or f"Parte {len(capitulos) + 1}"
            capitulos.append(f"{minutos:02d}:{segundos:02d} {titulo_cap.title()}")
        tiempo_acumulado += escena["duracion_segundos"]
        
    with open(ruta_metadata, "w", encoding="utf-8") as f:
        f.write("=== TÍTULO ===\n" + guion.get("titulo_video", "") + "\n\n")
        f.write("=== DESCRIPCIÓN ===\n" + guion.get("descripcion_youtube", "") + "\n\n")
        f.write("=== CAPÍTULOS ===\n" + "\n".join(capitulos) + "\n\n")
        f.write("=== TAGS ===\n" + ", ".join(guion.get("tags_youtube", [])) + "\n\n")
        f.write("=== COMENTARIO FIJADO ===\n" + guion.get("comentario_fijado", "") + "\n")
        
    print("\n=== 6/6: Miniatura ===")
    ruta_imagen_base = ruta_base_miniatura if miniatura_ok else os.path.join(carpeta_imagenes, "escena_01.png")
    if os.path.exists(ruta_imagen_base):
        ruta_miniatura = os.path.join(carpeta_proyecto, "miniatura.png")
        texto_miniatura = guion.get("titulo_miniatura") or guion.get("titulo_video", "")
        generar_miniatura_desde_imagen(ruta_imagen_base, texto_miniatura, ruta_miniatura)
        
    print(f"\n¡ÉXITO TOTAL! Video guardado en: {ruta_final}")
    return ruta_final

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(1)
    tema_arg = " ".join(sys.argv[1:])
    ejecutar_pipeline_completo(tema_arg)
