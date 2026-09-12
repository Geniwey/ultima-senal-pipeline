"""
Última Señal — Subtítulos (Whisper local, gratis)
====================================================
Genera subtítulos .srt a partir del audio completo ya montado.
Usa faster-whisper (más rápido y ligero que el whisper original).

Requiere:
    pip install faster-whisper
"""

import sys
from faster_whisper import WhisperModel

MODELO = "medium"  # "small" si la máquina va justa de recursos, "medium" da mejor precisión en español


def generar_srt(ruta_audio: str, ruta_salida_srt: str):
    print(f"Cargando modelo Whisper ({MODELO})...")
    modelo = WhisperModel(MODELO, device="cpu", compute_type="int8")

    print("Transcribiendo...")
    segmentos, _ = modelo.transcribe(ruta_audio, language="es", vad_filter=True)

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
