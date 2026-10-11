import os
import sys
import json
import shutil
from PIL import Image

from generar_guion import generar_guion
from generar_imagen import generar_imagen
from generar_voz import generar_voces
from animar_imagen import animar_todas
from montar_video import montar_video_final
from generar_miniatura import generar_miniatura_desde_imagen

def ejecutar_pipeline_completo(tema: str, carpeta_proyecto: str = "proyecto"):
    if os.path.exists(carpeta_proyecto):
        shutil.rmtree(carpeta_proyecto)
    os.makedirs(carpeta_proyecto, exist_ok=True)
    
    print("\n=== 1/6: Guion ===")
    ruta_guion = os.path.join(carpeta_proyecto, "guion.json")
    guion = generar_guion(tema)
    with open(ruta_guion, "w", encoding="utf-8") as f:
        json.dump(guion, f, ensure_ascii=False, indent=2)
        
    print("\n=== 2/6: Voz ===")
    carpeta_audio = os.path.join(carpeta_proyecto, "audio")
    info_escenas = generar_voces(ruta_guion, carpeta_audio)
    
    print("\n=== 3/6: Imágenes (Con Visión Artificial y Blindaje) ===")
    carpeta_imagenes = os.path.join(carpeta_proyecto, "imagenes")
    os.makedirs(carpeta_imagenes, exist_ok=True)
    
    ruta_base_miniatura = os.path.join(carpeta_imagenes, "miniatura_base.png")
    if guion.get("prompt_miniatura"):
        generar_imagen(guion["prompt_miniatura"], ruta_base_miniatura)

    for i, escena in enumerate(info_escenas):
        ruta_img = os.path.join(carpeta_imagenes, f"escena_{escena['indice']:02d}.png")
        print(f" Generando imagen {i+1}/{len(info_escenas)}...")
        
        exito = generar_imagen(escena["prompt_imagen"], ruta_img)
        
        # SISTEMA INDESTRUCTIBLE: Si la API o el OCR fallan, GARANTIZAMOS que haya un archivo.
        if not exito or not os.path.exists(ruta_img) or os.path.getsize(ruta_img) < 1000:
            print("  [CLONANDO/RESCATE] Usando imagen vecina o de emergencia...")
            img_anterior = os.path.join(carpeta_imagenes, f"escena_{escena['indice']-1:02d}.png")
            
            if os.path.exists(img_anterior) and os.path.getsize(img_anterior) > 1000:
                shutil.copy(img_anterior, ruta_img)
            elif os.path.exists(ruta_base_miniatura) and os.path.getsize(ruta_base_miniatura) > 1000:
                shutil.copy(ruta_base_miniatura, ruta_img)
            else:
                # EL SALVAVIDAS FINAL: Si no hay NADA de donde copiar, Python dibuja un fondo oscuro.
                # Así el vídeo NUNCA se quedará en negro ni se estrellará.
                Image.new('RGB', (1024, 576), color=(8, 12, 18)).save(ruta_img)
            
    print("\n=== 4/6: Animación ===")
    carpeta_clips = os.path.join(carpeta_proyecto, "clips")
    animar_todas(info_escenas, carpeta_imagenes, carpeta_clips)
    
    print("\n=== 5/6: Montaje final ===")
    ruta_final = os.path.join(carpeta_proyecto, "video_final.mp4")
    info_escenas_path = os.path.join(carpeta_audio, "info_escenas.json")
    montar_video_final(carpeta_clips, carpeta_audio, ruta_final, info_escenas_path)
    
    print("\n=== 6/6: Miniatura ===")
    ruta_miniatura = os.path.join(carpeta_proyecto, "miniatura.png")
    texto_miniatura = guion.get("titulo_miniatura") or guion.get("titulo_video", "¿QUÉ PASÓ?")
    if os.path.exists(ruta_base_miniatura):
        generar_miniatura_desde_imagen(ruta_base_miniatura, texto_miniatura, ruta_miniatura)
        
    print(f"\n¡ÉXITO TOTAL! Video guardado en: {ruta_final}")
    return ruta_final

if __name__ == "__main__":
    if len(sys.argv) < 2: sys.exit(1)
    tema_arg = " ".join(sys.argv[1:])
    ejecutar_pipeline_completo(tema_arg)
