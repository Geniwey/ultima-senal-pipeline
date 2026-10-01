# Código optimizado usando voz grave y puntuación para naturalidad[span_14](start_span)[span_14](end_span)[span_15](start_span)[span_15](end_span)[span_16](start_span)[span_16](end_span)
import asyncio
import json
import os
import sys
import subprocess
import time
import edge_tts

VOZ = "es-MX-JorgeNeural" # Voz profunda y sobria, ideal para misterio

async def _generar_audio_escena(texto: str, ruta_salida: str):
    # Se eliminaron las alteraciones matemáticas de pitch/rate.
    # El LLM inserta puntuación que Edge-TTS interpreta como pausas dramáticas reales.
    comunicador = edge_tts.Communicate(texto, VOZ, rate="+0%", pitch="-2Hz")
    await comunicador.save(ruta_salida)

def _duracion_audio(ruta: str) -> float:
    resultado = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", ruta],
        capture_output=True, text=True
    )
    return float(resultado.stdout.strip())

def _generar_silencio_por_defecto(ruta_salida: str, texto: str):
    palabras = max(len(texto.split()), 3)
    duracion = round(palabras / 2.3, 1)
    comando = [
        "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
        "-t", str(duracion), "-q:a", "9", "-acodec", "libmp3lame", ruta_salida
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
        while intentos < 4 and not exito:
            try:
                asyncio.run(_generar_audio_escena(escena["texto_narracion"], ruta_audio))
                if os.path.exists(ruta_audio) and os.path.getsize(ruta_audio) > 1000:
                    exito = True
            except Exception as e:
                print(f" Fallo intento {intentos+1}: {e}")
                time.sleep(2)
                intentos += 1
                
        if not exito:
            print(f" No se pudo generar voz para la escena {i}, usando silencio...")
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
