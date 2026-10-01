# Código orquestador estable[span_27](start_span)[span_27](end_span)[span_28](start_span)[span_28](end_span)[span_29](start_span)[span_29](end_span)[span_30](start_span)[span_30](end_span)
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
    os.makedirs(carpeta_proyecto, exist_ok=True)
    
    print("\n=== 1/6: Guion ===")
    ruta_guion = os.path.join(carpeta_proyecto, "guion.json")
    guion = generar_guion(tema)
    with open(ruta_guion, "w", encoding="utf-8") as f:
        json.dump(guion, f, ensure_ascii=False, indent=2)
        
    print("\n=== 2/6: Voz ===")
    carpeta_audio = os.path.join(carpeta_proyecto, "audio")
    info_escenas = generar_voces(ruta_guion, carpeta_audio)
    
    print("\n=== 3/6: Imágenes ===")
    carpeta_imagenes = os.path.join(carpeta_proyecto, "imagenes")
    os.makedirs(carpeta_imagenes, exist_ok=True)
    
    ruta_base_miniatura = os.path.join(carpeta_imagenes, "miniatura_base.png")
    miniatura_ok = False
    if guion.get("prompt_miniatura"):
        if os.path.exists(ruta_base_miniatura) and not os.path.exists(ruta_base_miniatura + ".emergencia"):
            miniatura_ok = True
        else:
            if generar_imagen(guion["prompt_miniatura"], ruta_base_miniatura):
                if fue_ultima_generacion_emergencia():
                    open(ruta_base_miniatura + ".emergencia", "w").close()
                else:
                    miniatura_ok = True

    def _generar_todas(lista_escenas):
        fallidas = []
        for escena in lista_escenas:
            ruta_img = os.path.join(carpeta_imagenes, f"escena_{escena['indice']:02d}.png")
            ruta_marca = ruta_img + ".emergencia"
            if (os.path.exists(ruta_img) and os.path.getsize(ruta_img) > 10_000 and not os.path.exists(ruta_marca)):
                continue
            ok = generar_imagen(escena["prompt_imagen"], ruta_img)
            if not ok: fallidas.append(escena)
            elif fue_ultima_generacion_emergencia(): open(ruta_marca, "w").close()
            elif os.path.exists(ruta_marca): os.remove(ruta_marca)
        return fallidas

    fallidas = _generar_todas(info_escenas)
    if fallidas:
        time.sleep(90)
        _generar_todas(fallidas)
        
    print("\n=== 4/6: Animación ===")
    carpeta_clips = os.path.join(carpeta_proyecto, "clips")
    animar_todas(info_escenas, carpeta_imagenes, carpeta_clips)
    
    print("\n=== 5/6: Montaje final ===")
    ruta_final = os.path.join(carpeta_proyecto, "video_final.mp4")
    info_escenas_path = os.path.join(carpeta_audio, "info_escenas.json")
    montar_video_final(carpeta_clips, carpeta_audio, ruta_final, info_escenas_path)
    
    ruta_metadata = os.path.join(carpeta_proyecto, "metadata_youtube.txt")
    capitulos = []
    tiempo_acumulado = 3.0
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
    ruta_imagen_base = ruta_base_miniatura
    if not miniatura_ok:
        ruta_imagen_base = None
        for escena in info_escenas:
            candidata = os.path.join(carpeta_imagenes, f"escena_{escena['indice']:02d}.png")
            if os.path.exists(candidata) and not os.path.exists(candidata + ".emergencia"):
                ruta_imagen_base = candidata
                break
                
    if ruta_imagen_base:
        ruta_miniatura = os.path.join(carpeta_proyecto, "miniatura.png")
        texto_miniatura = guion.get("titulo_miniatura") or guion.get("titulo_video", "")
        generar_miniatura_desde_imagen(ruta_imagen_base, texto_miniatura, ruta_miniatura)
        
    return ruta_final

if __name__ == "__main__":
    if len(sys.argv) < 2: sys.exit(1)
    tema_arg = " ".join(sys.argv[1:])
    ejecutar_pipeline_completo(tema_arg)
