import os
import sys
import json
import shutil
import subprocess

from generar_guion import generar_guion
from generar_imagen import generar_imagen, fue_ultima_generacion_emergencia, obtener_estadisticas_imagenes
from generar_voz import generar_voces
from animar_imagen import animar_todas
from montar_video import montar_video_final
from generar_miniatura import generar_miniatura_desde_imagen

try:
    from generar_short import generar_short_vertical
except ImportError:
    generar_short_vertical = None


def _ejecutar_puerta_final(ruta_video: str, guion: dict) -> dict:
    """Auditoría automática antes de dar el vídeo por bueno."""
    res_dur = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", ruta_video],
        capture_output=True, text=True,
    )
    duracion = float(res_dur.stdout.strip() or 0.0)

    res_vol = subprocess.run(
        ["ffmpeg", "-i", ruta_video, "-af", "volumedetect", "-vn", "-f", "null", "-"],
        capture_output=True, text=True,
    )
    max_db = "N/D"
    mean_db = "N/D"
    for linea in res_vol.stderr.splitlines():
        if "max_volume:" in linea:
            max_db = linea.split("max_volume:")[1].strip()
        if "mean_volume:" in linea:
            mean_db = linea.split("mean_volume:")[1].strip()

    res_black = subprocess.run(
        ["ffmpeg", "-i", ruta_video, "-vf", "blackdetect=d=0.5:pix_th=0.10", "-an", "-f", "null", "-"],
        capture_output=True, text=True,
    )
    tramos_negros = res_black.stderr.count("black_start")

    informe = {
        "duracion_segundos": round(duracion, 1),
        "volumen_medio": mean_db,
        "volumen_pico": max_db,
        "tramos_negros": tramos_negros,
        "estadisticas_imagenes": obtener_estadisticas_imagenes(),
        "total_escenas": len(guion.get("escenas", [])),
    }
    return informe


def ejecutar_pipeline_completo(tema: str, carpeta_proyecto: str = "proyecto"):
    carpeta_audio = os.path.join(carpeta_proyecto, "audio")
    carpeta_imagenes = os.path.join(carpeta_proyecto, "imagenes")
    carpeta_clips = os.path.join(carpeta_proyecto, "clips")

    # Limpiar carpetas de trabajo previas para no arrastrar clips o imágenes viejas
    for carpeta in (carpeta_audio, carpeta_imagenes, carpeta_clips):
        if os.path.exists(carpeta):
            shutil.rmtree(carpeta)
        os.makedirs(carpeta, exist_ok=True)
    os.makedirs(carpeta_proyecto, exist_ok=True)

    print("\n=== 1/6: Guion Forense Verificado + Auditoría Ortográfica ===")
    ruta_guion = os.path.join(carpeta_proyecto, "guion.json")
    guion = generar_guion(tema)
    with open(ruta_guion, "w", encoding="utf-8") as f:
        json.dump(guion, f, ensure_ascii=False, indent=2)

    print("\n=== 2/6: Generación de Voz y Tiempos ===")
    info_escenas = generar_voces(ruta_guion, carpeta_audio)

    print("\n=== 3/6: Generación de Imágenes (Puerta QA) y 6 Infografías ===")
    escenas_guion = guion.get("escenas", [])
    total_escenas = len(info_escenas)
    escenas_sin_imagen = 0

    for idx, escena in enumerate(info_escenas, start=1):
        print(f" Procesando visual escena {idx}/{total_escenas}...")
        ruta_img = os.path.join(carpeta_imagenes, f"escena_{escena['indice']:02d}.png")
        plano_actual = escenas_guion[idx - 1].get("plano", "general") if idx - 1 < len(escenas_guion) else "general"
        ok = generar_imagen(escena["prompt_imagen"], ruta_img, semilla=idx * 103, plano=plano_actual)
        if not ok or not os.path.exists(ruta_img):
            escenas_sin_imagen += 1

    if escenas_sin_imagen > max(2, int(total_escenas * 0.20)):
        raise RuntimeError(f"Abortado por puerta de calidad: {escenas_sin_imagen}/{total_escenas} escenas sin imagen aprobada. Revisa los límites de API en el log.")

    print("\n=== 4/6: Animación y Rótulos ===")
    animar_todas(info_escenas, carpeta_imagenes, carpeta_clips)

    print("\n=== 5/6: Montaje Final y Audio Limitado a -1.5 dB ===")
    ruta_final = os.path.join(carpeta_proyecto, "video_final.mp4")
    info_escenas_path = os.path.join(carpeta_audio, "info_escenas.json")
    montar_video_final(carpeta_clips, carpeta_audio, ruta_final, info_escenas_path)

    if generar_short_vertical is not None:
        try:
            generar_short_vertical(info_escenas_path, carpeta_imagenes, ruta_final, os.path.join(carpeta_proyecto, "short_vertical.mp4"))
        except Exception:
            pass

    print("\n=== 6/6: Miniatura Triple (Cinta + Rayo) y Puerta Final ===")
    ruta_base_miniatura = os.path.join(carpeta_imagenes, "miniatura_base.png")
    miniatura_ok = False
    if guion.get("prompt_miniatura"):
        if generar_imagen(guion["prompt_miniatura"], ruta_base_miniatura, semilla=4207, es_miniatura=True, plano="cinta_puerto"):
            if not fue_ultima_generacion_emergencia():
                miniatura_ok = True

    # Si las 3 candidatas dedicadas de miniatura fallan OCR, usar la mejor escena real de cinta_puerto (NUNCA una infografía)
    if not miniatura_ok:
        for idx, esc_g in enumerate(escenas_guion):
            if esc_g.get("plano") == "cinta_puerto":
                candidata_cinta = os.path.join(carpeta_imagenes, f"escena_{idx + 1:02d}.png")
                if os.path.exists(candidata_cinta):
                    ruta_base_miniatura = candidata_cinta
                    miniatura_ok = True
                    break

    if os.path.exists(ruta_base_miniatura):
        ruta_miniatura = os.path.join(carpeta_proyecto, "miniatura.png")
        generar_miniatura_desde_imagen(ruta_base_miniatura, guion.get("titulo_miniatura", "LA CINTA MORTAL"), ruta_miniatura)

    ruta_metadata = os.path.join(carpeta_proyecto, "metadata_youtube.txt")
    with open(ruta_metadata, "w", encoding="utf-8") as f:
        f.write("=== TÍTULO ===\n" + guion.get("titulo_video", "") + "\n\n")
        f.write("=== DESCRIPCIÓN ===\n" + guion.get("descripcion_youtube", "") + "\n\n")
        f.write("=== TAGS ===\n" + ", ".join(guion.get("tags_youtube", [])) + "\n\n")
        f.write("=== COMENTARIO FIJADO ===\n" + guion.get("comentario_fijado", "") + "\n")

    informe = _ejecutar_puerta_final(ruta_final, guion)
    ruta_informe = os.path.join(carpeta_proyecto, "informe_calidad.json")
    with open(ruta_informe, "w", encoding="utf-8") as f:
        json.dump(informe, f, ensure_ascii=False, indent=2)

    print("\n=== INFORME DE PUERTA FINAL ===")
    print(json.dumps(informe, ensure_ascii=False, indent=2))
    print(f"\n¡LISTO PARA REVISIÓN Y PUBLICACIÓN!: {ruta_final}")
    return ruta_final


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(1)
    ejecutar_pipeline_completo(" ".join(sys.argv[1:]))
