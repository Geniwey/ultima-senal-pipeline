"""
Última Señal — Generador de guion (Groq)
==========================================
Genera un guion de investigación de accidente aéreo, dividido en escenas
(beats) listas para pasar a imagen + voz.

Requiere:
    pip install groq
    export GROQ_API_KEY="tu_key"

Salida: JSON con lista de escenas, cada una con:
    - texto_narracion  (lo que se lee en voz)
    - prompt_imagen    (descripción visual de la escena, en inglés, para el generador de imágenes)
"""

import os
import json
import sys
from groq import Groq

MODELO_PRINCIPAL = "openai/gpt-oss-120b"
MODELO_FALLBACK = "openai/gpt-oss-20b"

SYSTEM_PROMPT = """Eres guionista de un canal de YouTube de documentales de investigación de accidentes de aviación llamado "Última Señal". Tono: serio, investigativo, respetuoso con las víctimas — nunca sensacionalista ni morboso. Enfoque: qué falló técnicamente, decisiones humanas en los últimos minutos, qué cambió en la aviación después.

Reglas estrictas:
- Nunca describir restos humanos, cuerpos o imágenes gráficas.
- No dar nombres ni mostrar rostros de víctimas civiles salvo que sea imprescindible y ya sea de dominio público muy conocido.
- Español neutro, apto para España y Latinoamérica.
- Cada guion debe sonar distinto en estructura al anterior (varía el orden: a veces empieza por el aterrizaje, a veces por la investigación, a veces por el fallo técnico) para evitar patrones repetitivos.

Devuelve SOLO un JSON válido, sin texto adicional, con esta forma exacta:
{
  "titulo_video": "...",
  "escenas": [
    {"texto_narracion": "...", "prompt_imagen": "descripción visual en inglés, sin texto en pantalla, sin logos"}
  ]
}

El guion completo debe sumar entre 1000 y 1400 palabras de narración (para un vídeo de ~8 minutos), dividido en 12 a 18 escenas.
"""


def _llamar_groq(cliente: Groq, tema: str, modelo: str) -> str:
    respuesta = cliente.chat.completions.create(
        model=modelo,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Tema del vídeo: {tema}"},
        ],
        temperature=0.85,
        max_tokens=6000,
    )
    return respuesta.choices[0].message.content


def generar_guion(tema: str) -> dict:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("Falta la variable de entorno GROQ_API_KEY")

    cliente = Groq(api_key=api_key)

    for modelo in (MODELO_PRINCIPAL, MODELO_FALLBACK):
        try:
            print(f"Generando guion con {modelo}...")
            texto = _llamar_groq(cliente, tema, modelo)
            # limpiar por si el modelo mete ```json ... ```
            texto = texto.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            datos = json.loads(texto)
            if "escenas" in datos and len(datos["escenas"]) >= 8:
                return datos
            print(f"  Respuesta incompleta con {modelo}, probando siguiente modelo...")
        except (json.JSONDecodeError, Exception) as e:
            print(f"  Fallo con {modelo}: {e}")

    raise RuntimeError("No se pudo generar un guion válido con ningún modelo")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python generar_guion.py 'tema del accidente' salida.json")
        sys.exit(1)

    tema_arg, salida_arg = sys.argv[1], sys.argv[2]
    guion = generar_guion(tema_arg)
    with open(salida_arg, "w", encoding="utf-8") as f:
        json.dump(guion, f, ensure_ascii=False, indent=2)
    print(f"✓ Guion guardado en {salida_arg} ({len(guion['escenas'])} escenas)")
