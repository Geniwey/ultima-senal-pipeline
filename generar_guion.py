"""
Última Señal — Generador de guion (Groq + fallback Cerebras)
================================================================
Genera un guion de investigación de accidente aéreo, dividido en escenas
(beats) listas para pasar a imagen + voz.

Requiere:
    pip install groq openai
    export GROQ_API_KEY="tu_key"
    export CEREBRAS_API_KEY="tu_key"   (fallback, 1M tokens/día gratis, sin tarjeta)

Salida: JSON con lista de escenas, cada una con:
    - texto_narracion  (lo que se lee en voz)
    - prompt_imagen    (descripción visual de la escena, en inglés, para el generador de imágenes)
"""

import os
import json
import sys
from groq import Groq

MODELO_PRINCIPAL = "qwen/qwen3.6-27b"      # el de mejor calidad/razonamiento en Groq ahora mismo
MODELO_FALLBACK = "openai/gpt-oss-120b"    # segundo intento dentro de Groq si el primero falla
MODELO_CEREBRAS = "llama-3.3-70b"          # tercer proveedor, fuera de Groq

SYSTEM_PROMPT = """Eres guionista de un canal de YouTube de documentales de investigación de accidentes de aviación llamado "Última Señal". Tono: serio, investigativo, respetuoso con las víctimas — nunca sensacionalista ni morboso. Enfoque: qué falló técnicamente, decisiones humanas en los últimos minutos, qué cambió en la aviación después.

Reglas estrictas:
- Nunca describir restos humanos, cuerpos o imágenes gráficas.
- No dar nombres ni mostrar rostros de víctimas civiles salvo que sea imprescindible y ya sea de dominio público muy conocido.
- Español neutro, apto para España y Latinoamérica.
- Cada guion debe sonar distinto en estructura al anterior (varía el orden: a veces empieza por el aterrizaje, a veces por la investigación, a veces por el fallo técnico) para evitar patrones repetitivos.
- IMPORTANTE para "prompt_imagen": los generadores de imagen gratis que usamos fallan mucho con caras y manos en primer plano. Describe SIEMPRE planos de ambiente, objetos, o personas de espaldas/en silueta/a distancia — nunca "close-up of a face" ni gestos detallados de manos. Prioriza: cabinas, paneles de instrumentos, salas de control, restos de aeronave desde lejos, documentos, cajas negras, pasillos de oficina, cielos, pistas de aterrizaje.
- IMPORTANTE contra alucinaciones: si no tienes certeza de un dato muy específico (una cifra exacta, una hora precisa, un nombre secundario), formúlalo de manera general y verificable en vez de inventar un número o nombre concreto que suene creíble pero pueda ser falso. Es mejor decir "varios minutos después" que inventar "a las 14:37 y 22 segundos" si no es un dato de dominio público muy conocido. La precisión y la honestidad priman sobre sonar dramático.
- No menciones nombres de aerolíneas, fabricantes de aviones ni marcas comerciales dentro de "prompt_imagen" (aunque sí puedes nombrarlos en "texto_narracion"): los generadores de imagen a veces alucinan logos reales solo con leer el nombre de la marca, y eso hay que evitarlo. Describe el avión de forma genérica visualmente ("wide-body commercial airliner", "narrow-body jet") en el prompt de imagen.

Devuelve SOLO un JSON válido, sin texto adicional, con esta forma exacta:
{
  "titulo_video": "...",
  "escenas": [
    {
      "texto_narracion": "una frase corta, entre 8 y 18 palabras — esto se lee en voz y dura entre 4 y 6 segundos",
      "texto_pantalla": "titular muy corto, 2 a 6 palabras, MAYÚSCULAS, resume el punto clave de esta frase para mostrarlo como texto en pantalla",
      "prompt_imagen": "descripción visual en inglés de un icono/ilustración plana simple que represente esta idea, sin texto en la imagen, sin logos"
    }
  ]
}

Cada escena representa entre 4 y 6 segundos de vídeo (una frase corta cada vez, como un explicador de ritmo rápido, cambiando de imagen constantemente — NO bloques largos de varias frases juntas). Para un vídeo de ~8 minutos esto significa entre 80 y 110 escenas cortas, no 12-18 escenas largas.
"""


def _llamar_groq(cliente: Groq, tema: str, modelo: str) -> str:
    respuesta = cliente.chat.completions.create(
        model=modelo,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Tema del vídeo: {tema}"},
        ],
        temperature=0.6,
        max_tokens=16000,
    )
    return respuesta.choices[0].message.content


def _llamar_cerebras(tema: str) -> str:
    # Cerebras usa API compatible con OpenAI
    from openai import OpenAI
    api_key = os.environ.get("CEREBRAS_API_KEY")
    if not api_key:
        raise RuntimeError("Falta CEREBRAS_API_KEY")
    cliente = OpenAI(api_key=api_key, base_url="https://api.cerebras.ai/v1")
    respuesta = cliente.chat.completions.create(
        model=MODELO_CEREBRAS,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Tema del vídeo: {tema}"},
        ],
        temperature=0.6,
        max_tokens=16000,
    )
    return respuesta.choices[0].message.content


def _limpiar_y_parsear(texto: str) -> dict:
    texto = texto.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(texto)


def generar_guion(tema: str) -> dict:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("Falta la variable de entorno GROQ_API_KEY")

    cliente = Groq(api_key=api_key)

    # --- Intentos 1 y 2: Groq (modelo grande, luego pequeño) ---
    for modelo in (MODELO_PRINCIPAL, MODELO_FALLBACK):
        try:
            print(f"Generando guion con Groq/{modelo}...")
            texto = _llamar_groq(cliente, tema, modelo)
            datos = _limpiar_y_parsear(texto)
            if "escenas" in datos and len(datos["escenas"]) >= 40:
                return datos
            print(f"  Respuesta incompleta con {modelo}, probando siguiente...")
        except Exception as e:
            print(f"  Fallo con {modelo}: {e}")

    # --- Intento 3 (fallback): Cerebras ---
    try:
        print(f"Groq falló, probando Cerebras/{MODELO_CEREBRAS}...")
        texto = _llamar_cerebras(tema)
        datos = _limpiar_y_parsear(texto)
        if "escenas" in datos and len(datos["escenas"]) >= 40:
            return datos
        print("  Respuesta incompleta con Cerebras también.")
    except Exception as e:
        print(f"  Fallo con Cerebras: {e}")

    raise RuntimeError("No se pudo generar un guion válido con ningún proveedor (Groq x2 + Cerebras)")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python generar_guion.py 'tema del accidente' salida.json")
        sys.exit(1)

    tema_arg, salida_arg = sys.argv[1], sys.argv[2]
    guion = generar_guion(tema_arg)
    with open(salida_arg, "w", encoding="utf-8") as f:
        json.dump(guion, f, ensure_ascii=False, indent=2)
    print(f"✓ Guion guardado en {salida_arg} ({len(guion['escenas'])} escenas)")
