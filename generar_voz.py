"""Última Señal - Voz de Google (gTTS) procesada para Misterio"""
import json
import os
import sys
import subprocess
import time
from gtts import gTTS

def _generar_audio_escena(texto: str, ruta_salida: str):
    ruta_temp = ruta_salida + ".temp.mp3"
    
    # 1. Obtenemos la voz clásica de Google en español
    tts = gTTS(text=texto, lang='es', tld='com.mx')
    tts.save(ruta_temp)
    
    # 2. PROCESAMIENTO FFmpeg: Bajamos el pitch para hacerla sonar como "narrador de documental / misterio"
    # asetrate altera el tono (más bajo = más grave), atempo compensa la velocidad.
    comando = [
        "ffmpeg", "-y", "-i", ruta_temp,
        "-af", "asetrate=24000*0.82,aresample=24000,atempo=1.20",
        ruta_salida
    ]
    resultado = subprocess.run(comando, capture_output=True, text=True)
    
    if os.path.exists(ruta_temp):
        os.remove(ruta_temp)
        
    if resultado.returncode != 0 or not os.path.exists(ruta_salida):
        raise RuntimeError(f"Fallo aplicando filtro de voz oscura: {resultado.stderr[-500:]}")

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
        print(f" Generando Voz de Google (Dark Mode) escena {i}/{total_escenas}...")
        
        intentos = 0
        exito = False
        while intentos < 3 and not exito:
            try:
                _generar_audio_escena(escena["texto_narracion"], ruta_audio)
                if os.path.exists(ruta_audio) and os.path.getsize(ruta_audio) > 1000:
                    exito = True
            except Exception as e:
                print(f" Fallo intento {intentos+1}: {e}")
                time.sleep(2)
                intentos += 1
                
        if not exito:
            print(f" Falló la voz, usando silencio...")
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
