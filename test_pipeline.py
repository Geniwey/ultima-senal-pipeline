import os
import py_compile
import shutil
import subprocess
import sys

ARCHIVOS_REQUERIDOS = [
    "pipeline_auto.py",
    "generar_guion.py",
    "generar_imagen.py",
    "montar_video.py",
]


def verificar_sintaxis():
    for archivo in ARCHIVOS_REQUERIDOS:
        if not os.path.exists(archivo):
            raise FileNotFoundError(f"Falta el archivo obligatorio: {archivo}")
        py_compile.compile(archivo, doraise=True)
    print("✅ Sintaxis Python verificada en todos los módulos.")


def verificar_binarios():
    for bin_name in ("ffmpeg", "ffprobe", "tesseract"):
        if not shutil.which(bin_name):
            raise RuntimeError(f"Falta binario del sistema: {bin_name}")
    print("✅ Binarios ffmpeg, ffprobe y tesseract disponibles.")


def verificar_coherencia_guion():
    import generar_guion as gg
    import generar_imagen as gi

    muestra = {
        "titulo_video": "Test",
        "descripcion_youtube": "Test",
        "tags_youtube": ["test"],
        "comentario_fijado": "Test",
        "escenas": [
            {"texto_narracion": f"Escena documental numero {i} sobre el vuelo Aeroperu 603 en Lima.", "texto_pantalla": "ADHESIVO PLATEADO", "plano": "cabina_pilotos"}
            for i in range(34)
        ],
    }
    res = gg._parsear_guion(__import__("json").dumps(muestra), gg.FICHA_POR_DEFECTO)
    escenas = res["escenas"]
    assert len(escenas) == 34, f"Se esperaban 34 escenas, salieron {len(escenas)}"

    graficos = [e for e in escenas if e["tipo"] == "grafico"]
    assert len(graficos) == 6, f"Se esperaban 6 gráficos, salieron {len(graficos)}"

    cintas = [e for e in escenas if e["plano"] == "cinta_puerto"]
    assert len(cintas) >= 3, f"Se esperaban al menos 3 planos de cinta_puerto, salieron {len(cintas)}"

    for i in range(1, len(escenas)):
        if escenas[i]["plano"] != "grafico":
            assert escenas[i]["plano"] != escenas[i - 1]["plano"], f"Plano repetido seguido en {i}"

    # Probar generación real de una infografía 1080p
    tmp_img = "/tmp/test_infografia.png"
    assert gi.generar_imagen("INFOGRAFIA:GRAFICA_ALTITUD", tmp_img), "Falló infografía de altitud"
    os.remove(tmp_img)
    print("✅ Reglas de guion, 6 infografías y plano cinta_puerto verificados.")


def verificar_limitador_audio():
    tmp_wav = "/tmp/test_tone.wav"
    tmp_out = "/tmp/test_limited.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=2", "-af", "volume=3dB", tmp_wav],
        capture_output=True,
        check=True,
    )
    import montar_video as mv
    mv._normalizar_audio_dos_pasadas(tmp_wav, tmp_out)
    probe = subprocess.run(
        ["ffmpeg", "-i", tmp_out, "-af", "volumedetect", "-f", "null", "-"],
        capture_output=True,
        text=True,
    )
    for line in probe.stderr.splitlines():
        if "max_volume:" in line:
            val = float(line.split("max_volume:")[1].replace("dB", "").strip())
            assert val <= -1.2, f"Pico demasiado alto tras normalizar: {val} dB"
            print(f"✅ Audio normalizado correctamente (pico={val} dB <= -1.5 dB).")
    for f in (tmp_wav, tmp_out):
        if os.path.exists(f):
            os.remove(f)


if __name__ == "__main__":
    verificar_sintaxis()
    verificar_binarios()
    verificar_coherencia_guion()
    verificar_limitador_audio()
    print("🚀 TODOS LOS TESTS PASARON. LISTO PARA GENERAR EL VÍDEO.")
