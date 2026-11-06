import asyncio
import json
import os
import re
import sys
import subprocess
import time
import edge_tts

VOZ = "es-MX-JorgeNeural"


def _normalizar_texto_para_tts(texto: str) -> str:
    """
    Limpia números con puntos (12.000 -> 12000) y siglas en inglés para que Edge-TTS
    pronuncie un español documental impecable.
    """
    t = texto
    # Quitar puntos o comas entre miles: 12.000 -> 12000 (así dice "doce mil" y no "doce punto cero cero cero")
    t = re.sub(r"(\d)[\.,](\d{3})\b", r"\1\2", t)

    reemplazos_foneticos = {
        r"\bLIM\b": "Lima",
        r"\bSCL\b": "Santiago",
        r"\bGPWS\b": "sistema de alerta de proximidad al terreno",
        r"\bCVR\b": "grabadora de voz de cabina",
        r"\bFDR\b": "registrador de datos de vuelo",
        r"\bATC\b": "control de tráfico aéreo",
        r"\bADF\b": "radiogoniómetro",
        r"\bFLIR\b": "cámara infrarroja",
        r"\bNTSB\b": "Junta Nacional de Seguridad en el Transporte",
        r"\bFAA\b": "Administración Federal de Aviación",
        r"\bOACI\b": "Organización de Aviación Civil Internacional",
        r"\bAD\b": "directiva de aeronavegabilidad",
        r"\bAirworthiness Directive\b": "directiva de seguridad aérea",
    }
    for patron, reemplazo in reemplazos_foneticos.items():
        t = re.sub(patron, reemplazo, t)
    return t


async def _generar_audio_escena(texto: str, ruta_salida: str):
    texto_limpio = _normalizar_texto_para_tts(texto)
    comunicador = edge_tts.Communicate(texto_limpio, VOZ, rate="+2%", pitch="-5Hz")
    await comunicador.save(ruta_salida)


def _duracion_audio(ruta: str) -> float:
    resultado = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", ruta],
        capture_output=True,
        text=True,
    )
    return float(resultado.stdout.strip())


def _generar_silencio_por_defecto(ruta_salida: str, texto: str):
    palabras = max(len(texto.split()), 3)
    duracion = round(palabras / 2.3, 1)
    comando = [
        "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
        "-t", str(duracion), "-q:a", "9", "-acodec", "libmp3lame", ruta_salida,
    ]
    subprocess.run(comando, capture_output=True, text=True)


def generar_voces(ruta_guion: str, carpeta_salida: str) -> list:
    os.makedirs(carpeta_salida, exist_ok=True)
    with open(ruta_guion, "r", encoding="utf-8") as f:
        guion = json.load(f)

    info_escenas = []
    total_escenas = len(guion["escenas"])

    for i, escena in enumerate(guion["escenas"], start=1):
        ruta_audio = os.path.join(carpeta_salida, f"escena_{i:02d}.mp3")
        print(f" Generando voz escena {i}/{total_escenas}...")

        intentos = 0
        exito = False
        while intentos < 3 and not exito:
            try:
                asyncio.run(_generar_audio_escena(escena["texto_narracion"], ruta_audio))
                if os.path.exists(ruta_audio) and os.path.getsize(ruta_audio) > 1000:
                    exito = True
            except Exception as e:
                print(f" Fallo intento {intentos+1}: {e}")
                time.sleep(2)
                intentos += 1

        if not exito:
            print(" Falló voz, insertando silencio...")
            _generar_silencio_por_defecto(ruta_audio, escena["texto_narracion"])

        duracion = _duracion_audio(ruta_audio)
        info_escenas.append({
            "indice": i,
            "ruta_audio": ruta_audio,
            "duracion_segundos": duracion,
            "prompt_imagen": escena["prompt_imagen"],
            "texto_pantalla": escena.get("texto_pantalla", ""),
        })

    ruta_info = os.path.join(carpeta_salida, "info_escenas.json")
    with open(ruta_info, "w", encoding="utf-8") as f:
        json.dump(info_escenas, f, ensure_ascii=False, indent=2)
    return info_escenas


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(1)
    generar_voces(sys.argv[1], sys.argv[2])
