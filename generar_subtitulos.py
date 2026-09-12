"""
Última Señal — Subtítulos (Whisper local, gratis)
====================================================
Genera subtítulos .srt a partir del audio completo ya montado.
Usa faster-whisper (más rápido y ligero que el whisper original).

Requiere:
    pip install faster-whisper
"""

import sys
import time
from faster_whisper import WhisperModel

MODELO = "medium"  # "small" si la máquina va justa de recursos, "medium" da mejor precisión en español
MODELO_RESPALDO = "small"  # si "medium" falla (poca RAM u otro fallo), probamos uno más ligero


def _transcribir_con(ruta_audio: str, modelo_nombre: str):
    modelo = WhisperModel(modelo_nombre, device="cpu", compute_type="int8")
    segmentos, _ = modelo.transcribe(ruta_audio, language="es", vad_filter=True)
    return list(segmentos)  # forzamos a lista ya para detectar errores aquí, no al escribir


def generar_srt(ruta_audio: str, ruta_salida_srt: str):
    segmentos = None
    for modelo_nombre in (MODELO, MODELO_RESPALDO):
        for intento in range(2):
            try:
                print(f"Cargando modelo Whisper ({modelo_nombre}), intento {intento+1}/2...")
                segmentos = _transcribir_con(ruta_audio, modelo_nombre)
                break
            except Exception as e:
                print(f"  ⚠ Fallo con Whisper/{modelo_nombre}: {e}")
                time.sleep(3)
        if segmentos is not None:
            break

    if segmentos is None:
        raise RuntimeError("Whisper falló con ambos modelos (medium y small) tras varios intentos")

    def formatear_tiempo(segundos: float) -> str:
        h = int(segundos // 3600)
        m = int((segundos % 3600) // 60)
        s = int(segundos % 60)
        ms = int((segundos - int(segundos)) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    with open(ruta_salida_srt, "w", encoding="utf-8") as f:
        for i, seg in enumerate(segmentos, start=1):
            f.write(f"{i}\n")
            f.write(f"{formatear_tiempo(seg.start)} --> {formatear_tiempo(seg.end)}\n")
            f.write(f"{seg.text.strip()}\n\n")

    print(f"✓ Subtítulos guardados en {ruta_salida_srt}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python generar_subtitulos.py audio_completo.mp3 salida.srt")
        sys.exit(1)
    generar_srt(sys.argv[1], sys.argv[2])
