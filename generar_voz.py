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
    t = re.sub(r"(\d)[\.,\s](\d{3})\b", r"\1\2", t)

    reemplazos = {
        r"\bcockpit\b": "cabina de mando",
        r"\bRemove Before Flight\b": "retirar antes del vuelo",
        r"\boverspeed\b": "exceso de velocidad",
        r"\bstick shaker\b": "vibrador de palanca",
        r"\bEric Schreiber\b": "Éric Shráiber",
        r"\bGPWS\b": "alerta de proximidad al terreno",
        r"\bCVR\b": "grabadora de voz de cabina",
        r"\bFDR\b": "registrador de datos de vuelo",
        r"\bATC\b": "control de tráfico aéreo",
        r"\bOACI\b": "Organización de Aviación Civil Internacional",
        r"\bCIAA\b": "Comisión Investigadora de Accidentes de Aviación",
        r"\bNTSB\b": "Junta Nacional de Seguridad en el Transporte",
        r"\bFAA\b": "Administración Federal de Aviación",
    }
    for patron, reemplazo in reemplazos.items():
        t = re.sub(patron, reemplazo, t, flags=re.IGNORECASE)
    return t


def _formatear_tiempo_ass(segundos: float) -> str:
    horas = int(segundos // 3600)
    minutos = int((segundos % 3600) // 60)
    segs = segundos % 60
    centis = int((segs - int(segs)) * 100)
    return f"{horas}:{minutos:02d}:{int(segs):02d}.{centis:02d}"


async def _generar_audio_y_timestamps(texto: str, ruta_audio: str) -> list:
    texto_limpio = _normalizar_texto_para_tts(texto)
    comunicador = edge_tts.Communicate(texto_limpio, VOZ, rate="+4%", pitch="-5Hz")
    palabras_tiempos = []

    with open(ruta_audio, "wb") as f_audio:
        async for chunk in comunicador.stream():
            if chunk["type"] == "audio":
                f_audio.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                inicio_seg = chunk["offset"] / 10_000_000.0
                dur_seg = chunk["duration"] / 10_000_000.0
                palabras_tiempos.append({
                    "texto": chunk["text"],
                    "inicio": inicio_seg,
                    "fin": inicio_seg + dur_seg,
                })

    return palabras_tiempos


def _crear_subtitulos_ass_palabra_por_palabra(palabras_tiempos: list, duracion_total: float, ruta_salida_ass: str, es_vertical: bool = False):
    """
    Construye un subtítulo cinemático en formato ASS donde cada palabra se ilumina en amarillo
    (#00E8FF en BGR = #FFE800) en el momento exacto en que se pronuncia.
    """
    fontsize = 52 if es_vertical else 42
    margin_v = 240 if es_vertical else 95

    encabezado = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {'1080' if es_vertical else '1920'}
PlayResY: {'1920' if es_vertical else '1080'}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,DejaVu Sans Bold,{fontsize},&H00FFFFFF,&H0000FFFF,&H00000000,&H80000000,-1,0,0,0,100,100,1,0,1,4,2,2,40,40,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    if not palabras_tiempos:
        with open(ruta_salida_ass, "w", encoding="utf-8") as f:
            f.write(encabezado)
        return

    # Agrupar en bloques de 4 a 6 palabras para no saturar la pantalla
    tam_grupo = 4 if es_vertical else 5
    grupos = [palabras_tiempos[i:i + tam_grupo] for i in range(0, len(palabras_tiempos), tam_grupo)]
    lineas_eventos = []

    for grupo in grupos:
        t_inicio_grupo = grupo[0]["inicio"]
        t_fin_grupo = grupo[-1]["fin"] + 0.15

        for idx_activa, palabra_activa in enumerate(grupo):
            t_ini_palabra = palabra_activa["inicio"]
            t_fin_palabra = grupo[idx_activa + 1]["inicio"] if idx_activa + 1 < len(grupo) else t_fin_grupo

            fragmentos = []
            for p in grupo:
                txt = p["texto"].upper()
                if p is palabra_activa:
                    fragmentos.append(r"{\c&H00E8FF&\b1}" + txt + r"{\r}")
                else:
                    fragmentos.append(r"{\c&H90FFFFFF&}" + txt + r"{\r}")

            texto_render = " ".join(fragmentos)
            linea = f"Dialogue: 0,{_formatear_tiempo_ass(t_ini_palabra)},{_formatear_tiempo_ass(t_fin_palabra)},Default,,0,0,0,,{texto_render}"
            lineas_eventos.append(linea)

    with open(ruta_salida_ass, "w", encoding="utf-8") as f:
        f.write(encabezado + "\n".join(lineas_eventos) + "\n")


def _duracion_audio(ruta: str) -> float:
    res = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", ruta],
        capture_output=True, text=True
    )
    return float(res.stdout.strip())


def _generar_voz_respaldo_gtts(texto: str, ruta_salida: str) -> bool:
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
    except Exception:
        return False


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
        ruta_ass = os.path.join(carpeta_salida, f"escena_{i:02d}.ass")
        ruta_ass_vertical = os.path.join(carpeta_salida, f"escena_{i:02d}_vertical.ass")
        print(f" Generando voz y subtítulos dinámicos escena {i}/{total_escenas}...")

        exito = False
        palabras_tiempos = []
        for intento in range(4):
            try:
                palabras_tiempos = asyncio.run(_generar_audio_y_timestamps(escena["texto_narracion"], ruta_audio))
                if os.path.exists(ruta_audio) and os.path.getsize(ruta_audio) > 1000:
                    exito = True
                    break
            except Exception as e:
                time.sleep((intento + 1) * 2.0)

        if not exito:
            exito = _generar_voz_respaldo_gtts(escena["texto_narracion"], ruta_audio)

        if not exito:
            _generar_silencio_por_defecto(ruta_audio, escena["texto_narracion"])

        time.sleep(0.3)
        duracion = _duracion_audio(ruta_audio)

        # Generar subtítulos sincronizados palabra por palabra
        _crear_subtitulos_ass_palabra_por_palabra(palabras_tiempos, duracion, ruta_ass, es_vertical=False)
        _crear_subtitulos_ass_palabra_por_palabra(palabras_tiempos, duracion, ruta_ass_vertical, es_vertical=True)

        info_escenas.append({
            "indice": i,
            "ruta_audio": ruta_audio,
            "ruta_ass": ruta_ass,
            "ruta_ass_vertical": ruta_ass_vertical,
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
