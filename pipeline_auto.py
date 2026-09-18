"""
Última Señal — Pipeline automático de principio a fin
=========================================================
Igual que pipeline.py pero sin pausa interactiva (para correr en GitHub
Actions, donde nadie puede teclear una respuesta). La revisión humana se
hace al final, sobre el vídeo terminado, antes de subirlo a YouTube.

Uso:
    python pipeline_auto.py "Tema del accidente aéreo"
"""

import os
import sys
import json
import time

from generar_guion import generar_guion
from generar_imagen import generar_imagen
from generar_voz import generar_voces
from animar_imagen import animar_todas
from montar_video import montar_video_final
from generar_miniatura import generar_miniatura_desde_imagen


def ejecutar_pipeline_completo(tema: str, carpeta_proyecto: str = "proyecto"):
    os.makedirs(carpeta_proyecto, exist_ok=True)

    # 1. GUION
    print("\n=== 1/6: Guion ===")
    ruta_guion = os.path.join(carpeta_proyecto, "guion.json")
    guion = generar_guion(tema)
    with open(ruta_guion, "w", encoding="utf-8") as f:
        json.dump(guion, f, ensure_ascii=False, indent=2)
    print(f"Título: {guion['titulo_video']} | {len(guion['escenas'])} escenas")

    # 2. VOZ (primero, para saber duración exacta de cada escena)
    print("\n=== 2/6: Voz ===")
    carpeta_audio = os.path.join(carpeta_proyecto, "audio")
    info_escenas = generar_voces(ruta_guion, carpeta_audio)

    # 3. IMÁGENES
    print("\n=== 3/6: Imágenes ===")
    carpeta_imagenes = os.path.join(carpeta_proyecto, "imagenes")
    os.makedirs(carpeta_imagenes, exist_ok=True)

    def _generar_todas(lista_escenas):
        fallidas = []
        for escena in lista_escenas:
            ruta_img = os.path.join(carpeta_imagenes, f"escena_{escena['indice']:02d}.png")
            if os.path.exists(ruta_img) and os.path.getsize(ruta_img) > 10_000:
                continue  # ya generada en un intento/ejecución anterior
            print(f"  Escena {escena['indice']}/{len(info_escenas)}")
            if not generar_imagen(escena["prompt_imagen"], ruta_img):
                fallidas.append(escena)
        return fallidas

    fallidas = _generar_todas(info_escenas)

    if fallidas:
        print(f"\n⚠ {len(fallidas)} escenas fallaron en la primera pasada. "
              f"Esperando 90s antes de reintentar (para que se liberen los límites de los proveedores)...")
        time.sleep(90)
        fallidas = _generar_todas(fallidas)

    if fallidas:
        indices = [e["indice"] for e in fallidas]
        raise RuntimeError(f"Fallaron las imágenes de las escenas {indices} tras agotar los 3 proveedores, dos pasadas")

    # 4. ANIMACIÓN
    print("\n=== 4/6: Animación (Ken Burns) ===")
    carpeta_clips = os.path.join(carpeta_proyecto, "clips")
    animar_todas(info_escenas, carpeta_imagenes, carpeta_clips)

    # 5. MONTAJE FINAL
    # (ya no generamos subtítulos completos con Whisper — se quedaba
    # solapado con el titular corto en pantalla, duplicando el texto.
    # El titular ya cumple esa función de forma más limpia)
    print("\n=== 5/5: Montaje final ===")
    ruta_final = os.path.join(carpeta_proyecto, "video_final.mp4")
    info_escenas_path = os.path.join(carpeta_audio, "info_escenas.json")
    montar_video_final(carpeta_clips, carpeta_audio, ruta_final, info_escenas_path)

    # Archivo con todo lo necesario para subir el vídeo a YouTube sin
    # tener que escribir nada a mano: título, descripción, tags y capítulos.
    ruta_metadata = os.path.join(carpeta_proyecto, "metadata_youtube.txt")

    # Capítulos automáticos: repartimos ~7 puntos a lo largo del guion,
    # usando el titular en pantalla de esa escena y su tiempo acumulado
    # (empezando en 0:00 con el intro de 3s ya sumado).
    capitulos = []
    tiempo_acumulado = 3.0  # el bumper de intro dura 3s
    total_escenas = len(info_escenas)
    paso = max(total_escenas // 7, 1)
    for i, escena in enumerate(info_escenas):
        if i == 0 or i % paso == 0:
            minutos = int(tiempo_acumulado // 60)
            segundos = int(tiempo_acumulado % 60)
            titulo_cap = escena.get("texto_pantalla") or f"Parte {len(capitulos)+1}"
            capitulos.append(f"{minutos}:{segundos:02d} {titulo_cap.title()}")
        tiempo_acumulado += escena["duracion_segundos"]

    with open(ruta_metadata, "w", encoding="utf-8") as f:
        f.write("=== TÍTULO ===\n")
        f.write(guion.get("titulo_video", "") + "\n\n")
        f.write("=== DESCRIPCIÓN ===\n")
        f.write(guion.get("descripcion_youtube", "") + "\n\n")
        f.write("=== CAPÍTULOS (pega esto dentro de la descripción) ===\n")
        f.write("\n".join(capitulos) + "\n\n")
        f.write("=== TAGS (separados por coma) ===\n")
        f.write(", ".join(guion.get("tags_youtube", [])) + "\n")
    print(f"✓ Metadata de YouTube guardada en {ruta_metadata}")

    # Miniatura: reutilizamos una imagen que YA generamos bien para el
    # vídeo (aprox. dos tercios del guion) en vez de pedir una nueva — así
    # no depende de que quede cupo libre justo al final, cuando ya hemos
    # gastado el de las 90-100 imágenes del vídeo.
    print("\nGenerando miniatura (a partir de una imagen ya generada)...")
    indice_miniatura = info_escenas[int(len(info_escenas) * 0.65)]["indice"]
    ruta_imagen_base = os.path.join(carpeta_imagenes, f"escena_{indice_miniatura:02d}.png")
    ruta_miniatura = os.path.join(carpeta_proyecto, "miniatura.png")
    try:
        generar_miniatura_desde_imagen(
            ruta_imagen_base,
            guion.get("titulo_video", "")[:40],
            ruta_miniatura,
        )
        print(f"✓ Miniatura guardada en {ruta_miniatura}")
    except Exception as e:
        print(f"  ⚠ No se pudo generar la miniatura: {e}")

    print(f"\n✓✓✓ COMPLETO: {ruta_final}")
    return ruta_final


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python pipeline_auto.py 'Tema del accidente aéreo'")
        sys.exit(1)
    tema_arg = " ".join(sys.argv[1:])
    ejecutar_pipeline_completo(tema_arg)
