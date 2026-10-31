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
    t = texto
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
        r"\bCIAA\b": "Comisión Investigadora de Accidentes de Aviación",
        r"\bAD\b": "directiva de aeronavegabilidad",
    }
    for patron, reemplazo in reemplazos_foneticos.items():
        t = re.sub(patron, reemplazo, t)
    return t


async def _generar_audio_escena(texto: str, ruta_salida: str):
    texto_limpio = _normalizar_texto_para_tts(texto)
    comunicador = edge_tts.Communicate(texto_limpio, VOZ, rate="+4%", pitch="-5Hz")
    await comunicador.save(ruta_salida)


def _generar_voz_respaldo_gtts(texto: str, ruta_salida: str) -> bool:
    """Si Edge-TTS sufre rate-limit, genera la voz con gTTS y la oscurece con FFmpeg para que NUNCA quede una escena muda."""
    try:
        from gtts import gTTS
        texto_limpio = _normalizar_texto_para_tts(texto)
        ruta_temp = ruta_salida + "_gtts_temp.mp3"
        tts = gTTS(text=texto_limpio, lang="es", tld="com.mx")
        tts.save(ruta_temp)
        comando = [
            "ffmpeg", "-y", "-i", ruta_temp,
            "-af", "asetrate=24000*0.92,aresample=44100,atempo=1.18",
            "-q:a", "2", ruta_salida,
        ]
        subprocess.run(comando, capture_output=True, text=True)
        if os.path.exists(ruta_temp):
            os.remove(ruta_temp)
        return os.path.exists(ruta_salida) and os.path.getsize(ruta_salida) > 1000
    except Exception as e:
        print(f" [Aviso] Falló también gTTS: {e}")
        return False


def _duracion_audio(ruta: str) -> float:
    resultado = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", ruta],
        capture_output=True,
        text=True,
    )
    return float(resultado.stdout.strip())


def _generar_silencio_por_defecto(ruta_salida: str, texto: str):
    palabras = max(len(texto.split()), 3)
    duracion = round(palabras / 2.5, 1)
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

        exito = False
        for intento in range(5):
            try:
                asyncio.run(_generar_audio_escena(escena["texto_narracion"], ruta_audio))
                if os.path.exists(ruta_audio) and os.path.getsize(ruta_audio) > 1000:
                    exito = True
                    break
            except Exception as e:
                espera = (intento + 1) * 2.0
                print(f"  [Reintento TTS {intento+1}/5] Esperando {espera}s ({e})...")
                time.sleep(espera)

        if not exito:
            print("  🔄 Usando motor de voz de respaldo (gTTS) para evitar escena muda...")
            exito = _generar_voz_respaldo_gtts(escena["texto_narracion"], ruta_audio)

        if not exito:
            _generar_silencio_por_defecto(ruta_audio, escena["texto_narracion"])

        # Pausa breve de cortesía para que Microsoft no bloquee la IP en mitad del guion
        time.sleep(0.4)

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
