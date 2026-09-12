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

from generar_guion import generar_guion
from generar_imagen import generar_imagen
from generar_voz import generar_voces
from animar_imagen import animar_todas
from generar_subtitulos import generar_srt
from montar_video import montar_video_final, _concatenar_audios


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
    fallos = []
    for escena in info_escenas:
        ruta_img = os.path.join(carpeta_imagenes, f"escena_{escena['indice']:02d}.png")
        print(f"  Escena {escena['indice']}/{len(info_escenas)}")
        if not generar_imagen(escena["prompt_imagen"], ruta_img):
            fallos.append(escena["indice"])
    if fallos:
        # Los 3 proveedores fallaron para alguna escena: paramos el workflow
        # entero en vez de entregar un vídeo con huecos. Mejor que falle
        # visible a que llegue un vídeo roto sin que te des cuenta.
        raise RuntimeError(f"Fallaron las imágenes de las escenas {fallos} tras agotar los 3 proveedores")

    # 4. ANIMACIÓN
    print("\n=== 4/6: Animación (Ken Burns) ===")
    carpeta_clips = os.path.join(carpeta_proyecto, "clips")
    animar_todas(info_escenas, carpeta_imagenes, carpeta_clips)

    # 5. SUBTÍTULOS
    print("\n=== 5/6: Subtítulos ===")
    audio_completo = os.path.join(carpeta_proyecto, "audio_completo_temp.mp3")
    _concatenar_audios([e["ruta_audio"] for e in info_escenas], audio_completo)
    ruta_srt = os.path.join(carpeta_proyecto, "subtitulos.srt")
    generar_srt(audio_completo, ruta_srt)
    os.remove(audio_completo)

    # 6. MONTAJE FINAL
    print("\n=== 6/6: Montaje final ===")
    ruta_final = os.path.join(carpeta_proyecto, "video_final.mp4")
    info_escenas_path = os.path.join(carpeta_audio, "info_escenas.json")
    montar_video_final(carpeta_clips, carpeta_audio, ruta_srt, ruta_final, info_escenas_path)

    print(f"\n✓✓✓ COMPLETO: {ruta_final}")
    return ruta_final


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python pipeline_auto.py 'Tema del accidente aéreo'")
        sys.exit(1)
    tema_arg = " ".join(sys.argv[1:])
    ejecutar_pipeline_completo(tema_arg)
