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
from generar_short import generar_short_vertical


def ejecutar_pipeline_completo(tema: str, carpeta_proyecto: str = "proyecto"):
    carpeta_audio = os.path.join(carpeta_proyecto, "audio")
    carpeta_imagenes = os.path.join(carpeta_proyecto, "imagenes")
    carpeta_clips = os.path.join(carpeta_proyecto, "clips")

    for carpeta in (carpeta_proyecto, carpeta_audio, carpeta_imagenes, carpeta_clips):
        os.makedirs(carpeta, exist_ok=True)

    print("\n=== 1/7: Guion Forense y Estrategia ===")
    ruta_guion = os.path.join(carpeta_proyecto, "guion.json")
    guion = generar_guion(tema)
    with open(ruta_guion, "w", encoding="utf-8") as f:
        json.dump(guion, f, ensure_ascii=False, indent=2)

    print("\n=== 2/7: Voz y Subtítulos Dinámicos Palabra por Palabra ===")
    info_escenas = generar_voces(ruta_guion, carpeta_audio)

    print("\n=== 3/7: Renderizado de Imágenes e Infografías Vectoriales ===")
    ruta_base_miniatura = os.path.join(carpeta_imagenes, "miniatura_base.png")
    miniatura_ok = False
    if guion.get("prompt_miniatura"):
        if generar_imagen(guion["prompt_miniatura"], ruta_base_miniatura):
            if not fue_ultima_generacion_emergencia():
                miniatura_ok = True

    total_escenas = len(info_escenas)
    for idx, escena in enumerate(info_escenas, start=1):
        print(f" Procesando visual escena {idx}/{total_escenas}...")
        ruta_img = os.path.join(carpeta_imagenes, f"escena_{escena['indice']:02d}.png")
        generar_imagen(escena["prompt_imagen"], ruta_img, semilla=idx * 100)

    print("\n=== 4/7: Animación Cinematográfica Horizontal ===")
    animar_todas(info_escenas, carpeta_imagenes, carpeta_clips)

    print("\n=== 5/7: Montaje Final y Diseño de Sonido Multicapa ===")
    ruta_final = os.path.join(carpeta_proyecto, "video_final.mp4")
    info_escenas_path = os.path.join(carpeta_audio, "info_escenas.json")
    montar_video_final(carpeta_clips, carpeta_audio, ruta_final, info_escenas_path)

    print("\n=== 6/7: Generación Automática del Short Vertical (9:16) ===")
    ruta_short = os.path.join(carpeta_proyecto, "short_vertical.mp4")
    try:
        generar_short_vertical(info_escenas_path, carpeta_imagenes, ruta_final, ruta_short)
        print(f"  🎬 Short vertical generado con éxito: {ruta_short}")
    except Exception as e:
        print(f"  [Aviso] No se pudo compilar el short: {e}")

    print("\n=== 7/7: Miniatura y Metadata Estratégica ===")
    ruta_imagen_base = ruta_base_miniatura if miniatura_ok else os.path.join(carpeta_imagenes, "escena_01.png")
    if os.path.exists(ruta_imagen_base):
        ruta_miniatura = os.path.join(carpeta_proyecto, "miniatura.png")
        texto_miniatura = guion.get("titulo_miniatura") or "LA CINTA MORTAL"
        generar_miniatura_desde_imagen(ruta_imagen_base, texto_miniatura, ruta_miniatura)

    # Guardar metadata optimizada (Títulos complementarios + Encuestas de Comunidad)
    ruta_metadata = os.path.join(carpeta_proyecto, "metadata_youtube.txt")
    capitulos = []
    tiempo_acumulado = 2.5
    paso = max(len(info_escenas) // 6, 1)

    for i, escena in enumerate(info_escenas):
        if i == 0 or i % paso == 0:
            m, s = int(tiempo_acumulado // 60), int(tiempo_acumulado % 60)
            tit_cap = escena.get("texto_pantalla") or f"Parte {len(capitulos) + 1}"
            capitulos.append(f"{m:02d}:{s:02d} {tit_cap.title()}")
        tiempo_acumulado += escena["duracion_segundos"]

    with open(ruta_metadata, "w", encoding="utf-8") as f:
        f.write("=== TÍTULO PRINCIPAL ===\n" + guion.get("titulo_video", "") + "\n\n")
        f.write("=== MATRIZ DE TEST A/B (TÍTULO VS TEXTO MINIATURA) ===\n")
        f.write("1. Título: El error de 2$ que derribó al Vuelo 603 | Miniatura: LA CINTA MORTAL\n")
        f.write("2. Título: La trampa de 9700 pies que engañó a los pilotos | Miniatura: CIEGOS EN EL MAR\n")
        f.write("3. Título: Lo que hallaron en el fuselaje tras 31 minutos de vuelo | Miniatura: SENSOR TAPADO\n\n")
        f.write("=== DESCRIPCIÓN ===\n" + guion.get("descripcion_youtube", "") + "\n\n")
        f.write("=== CAPÍTULOS ===\n" + "\n".join(capitulos) + "\n\n")
        f.write("=== TAGS ===\n" + ", ".join(guion.get("tags_youtube", [])) + "\n\n")
        f.write("=== COMENTARIO FIJADO ===\n" + guion.get("comentario_fijado", "") + "\n\n")
        f.write("=== 3 ENCUESTAS PARA PESTAÑA COMUNIDAD (DÍAS SIN VÍDEO) ===\n")
        f.write("Encuesta 1: En una emergencia con alarmas contradictorias, ¿en qué instrumento confiarías tú primero?\n")
        f.write("  [ ] Horizonte artificial analógico | [ ] Altímetro barométrico | [ ] Confirmación radar ATC | [ ] GPS satelital\n\n")
        f.write("Encuesta 2: ¿Quién tuvo mayor responsabilidad en el desastre del Aeroperú 603?\n")
        f.write("  [ ] El mecánico que olvidó la cinta | [ ] El piloto en la inspección prevuelo | [ ] La aerolínea por falta de supervisión\n\n")
        f.write("Encuesta 3: ¿Sabías que los sensores tapados pueden hacer que la torre de control vea la misma altitud falsa que el avión?\n")
        f.write("  [ ] Sí, por el transpondedor | [ ] No, pensé que el radar de tierra era independiente | [ ] Lo acabo de aprender\n")

    print(f"\n¡ÉXITO TOTAL!\n- Vídeo horizontal: {ruta_final}\n- Short vertical 9:16: {ruta_short}")
    return ruta_final


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(1)
    tema_arg = " ".join(sys.argv[1:])
    ejecutar_pipeline_completo(tema_arg)
