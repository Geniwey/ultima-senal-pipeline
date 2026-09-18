"""
Última Señal — Generación de voz (Edge TTS, gratis)
======================================================
Convierte cada escena del guion en audio, y devuelve también la duración
de cada clip para poder sincronizar las imágenes después.

Requiere:
    pip install edge-tts
"""

import asyncio
import json
import os
import sys
import subprocess

VOZ = "es-ES-AlvaroNeural"


def _perfil_para_posicion(indice: int, total: int) -> tuple:
    """Varía ritmo/tono según la posición en el guion, para que no suene
    monótono todo el vídeo igual — más urgencia en el gancho, más
    gravedad/pausa en el punto álgido."""
    posicion = indice / max(total, 1)
    if posicion <= 0.08:
        return "+2%", "+0Hz"       # gancho inicial: algo más vivo/urgente
    elif 0.70 <= posicion <= 0.88:
        return "-14%", "-4Hz"      # punto álgido: más lento y grave, dramatismo
    else:
        return "-6%", "-1Hz"       # resto: ritmo pausado estándar


async def _generar_audio_escena(texto: str, ruta_salida: str, velocidad: str, tono: str):
    import edge_tts
    comunicador = edge_tts.Communicate(texto, VOZ, rate=velocidad, pitch=tono)
    await comunicador.save(ruta_salida)


def _duracion_audio(ruta: str) -> float:
    resultado = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", ruta],
        capture_output=True, text=True
    )
    return float(resultado.stdout.strip())


def _es_punto_dramatico(indice: int, total: int) -> bool:
    """La última escena del punto álgido (impacto/hallazgo) recibe una
    pausa de silencio detrás — igual que un corte a negro dramático."""
    posicion = indice / max(total, 1)
    return 0.86 <= posicion <= 0.89


def _anadir_pausa(ruta_audio: str, segundos: float = 1.2):
    ruta_temp = ruta_audio + ".pausa.mp3"
    comando = [
        "ffmpeg", "-y", "-i", ruta_audio,
        "-f", "lavfi", "-t", str(segundos), "-i", "anullsrc=r=44100:cl=stereo",
        "-filter_complex", "[0:a][1:a]concat=n=2:v=0:a=1",
        ruta_temp,
    ]
    resultado = subprocess.run(comando, capture_output=True, text=True)
    if resultado.returncode == 0 and os.path.exists(ruta_temp):
        os.replace(ruta_temp, ruta_audio)


def generar_voces(ruta_guion: str, carpeta_salida: str) -> list:
    os.makedirs(carpeta_salida, exist_ok=True)
    with open(ruta_guion, "r", encoding="utf-8") as f:
        guion = json.load(f)

    info_escenas = []
    total_escenas = len(guion["escenas"])
    for i, escena in enumerate(guion["escenas"], start=1):
        ruta_audio = os.path.join(carpeta_salida, f"escena_{i:02d}.mp3")
        print(f"  Generando voz escena {i}/{total_escenas}...")
        velocidad, tono = _perfil_para_posicion(i, total_escenas)

        intentos = 0
        exito = False
        while intentos < 2 and not exito:
            try:
                asyncio.run(_generar_audio_escena(escena["texto_narracion"], ruta_audio, velocidad, tono))
                if os.path.exists(ruta_audio) and os.path.getsize(ruta_audio) > 1000:
                    exito = True
            except Exception as e:
                print(f"    fallo intento {intentos+1}: {e}")
            intentos += 1

        if not exito:
            raise RuntimeError(f"No se pudo generar voz para la escena {i}")

        if _es_punto_dramatico(i, total_escenas):
            _anadir_pausa(ruta_audio, 1.2)

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

    print(f"✓ {len(info_escenas)} audios generados. Info guardada en {ruta_info}")
    return info_escenas


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python generar_voz.py guion.json carpeta_salida/")
        sys.exit(1)
    generar_voces(sys.argv[1], sys.argv[2])
