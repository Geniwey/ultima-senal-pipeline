"""
Última Señal — Generador de guion (Groq + fallback Cerebras)
================================================================
"""

import os
import json
import sys
from groq import Groq

MODELO_PRINCIPAL = "openai/gpt-oss-120b"
MODELO_FALLBACK = "openai/gpt-oss-20b"
MODELO_CEREBRAS = "llama-3.3-70b"

SYSTEM_PROMPT = """Eres guionista de un canal de YouTube de documentales de investigación de accidentes de aviación llamado "Última Señal". Tono: conversacional, como si le contaras la historia a un amigo — NUNCA suenes a informe técnico. Investigativo y respetuoso con las víctimas — nunca sensacionalista ni morboso, pero sí humano y con empatía.

Reglas estrictas:
- Nunca describir restos humanos, cuerpos o imágenes gráficas.
- No dar nombres ni mostrar rostros de víctimas civiles salvo que sea imprescindible y de dominio público muy conocido.
- Español neutro, apto para España y Latinoamérica.
- TÍTULO CON BRECHA DE CURIOSIDAD: nunca descriptivo. Usa un título que genere una pregunta sin responderla — ej. "El avión que cayó al mar por un trozo de cinta".
- GANCHO INICIAL (escenas 1-4): empieza SIEMPRE "in media res", en medio de la acción. Nunca preguntas retóricas genéricas.
- RIGOR FACTUAL: en casos reales documentados, la causa técnica debe coincidir con la causa oficialmente establecida. Si no estás seguro de un dato exacto, formúlalo de forma general en vez de inventar un mecanismo o cifra concretos.
- SOLO UNA LLAMADA A SUSCRIBIRSE en todo el guion, una vez, alrededor del 75% del guion, justo después de resolver la causa raíz. Nunca antes.
- CIERRE ÚNICO Y CORTO: las últimas 4-5 escenas del guion, y NADA MÁS, son el cierre. En esas últimas escenas cabe UNA sola combinación de: la moraleja/reflexión final + la CTA de suscripción si no se puso antes + una frase que invite a ver otro vídeo del canal. Todo eso en 4-5 escenas MÁXIMO, nunca más — ni un bloque largo de despedidas, ni frases repetidas del tipo "gracias por ver", "mantente alerta", "a volar juntos", "nuestro próximo vídeo" en escenas separadas. Es UN cierre, no una sucesión de cierres.
- PROHIBIDO TERMINANTE: cualquier frase de despedida, moraleja o CTA en escenas que no sean las últimas 4-5 del guion. Si ya "cerraste" la historia, no vuelvas a añadir contenido informativo ni otra despedida después.
- IMPORTANTE para "prompt_imagen": los generadores de imagen gratis fallan con caras/manos en primer plano y con conceptos abstractos. Describe SIEMPRE un objeto físico concreto y reconocible, un único objeto por imagen. Nunca "close-up of a face" ni multitudes.
- No menciones nombres de aerolíneas ni marcas comerciales en "prompt_imagen" (sí puedes en "texto_narracion"). Describe el avión de forma genérica visualmente.

Devuelve SOLO un JSON válido, sin texto adicional, con esta forma exacta:
{
  "titulo_video": "título con brecha de curiosidad, máximo 60 caracteres",
  "descripcion_youtube": "descripción de 3-4 párrafos para YouTube",
  "tags_youtube": ["10 a 15 tags cortos en español"],
  "comentario_fijado": "una pregunta polarizante/de debate para fijar en comentarios",
  "escenas": [
    {
      "texto_narracion": "frase corta, 8-15 palabras, 3-5 segundos de voz",
      "texto_pantalla": "titular muy corto, 2-6 palabras, MAYÚSCULAS",
      "prompt_imagen": "descripción visual en inglés de UN icono/objeto, sin texto, sin logos"
    }
  ]
}

Cada escena son 3-5 segundos (ritmo rápido). Para ~8 minutos: 95-130 escenas.
"""


def _llamar_groq(cliente: Groq, tema: str, modelo: str) -> str:
    respuesta = cliente.chat.completions.create(
        model=modelo,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Tema del vídeo: {tema}"},
        ],
        temperature=0.6,
        max_tokens=20000,
    )
    return respuesta.choices[0].message.content


def _llamar_cerebras(tema: str) -> str:
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
        max_tokens=20000,
    )
    return respuesta.choices[0].message.content


def _recortar_despedidas_repetidas(datos: dict) -> dict:
    palabras_cierre = [
        "suscrib", "gracias por ver", "hasta la próxima", "nos vemos",
        "dale like", "mantente alerta", "a volar juntos", "próximo vídeo",
        "próximo caso", "próxima investigación", "si esta historia",
        "nuestro próximo",
    ]
    escenas = datos.get("escenas", [])
    total = len(escenas)
    limite_cierre = max(total - 5, 0)
    indices_cierre = [
        i for i, e in enumerate(escenas)
        if any(p in e.get("texto_narracion", "").lower() for p in palabras_cierre)
    ]
    a_quitar = [i for i in indices_cierre if i < limite_cierre]
    if a_quitar:
        datos["escenas"] = [e for i, e in enumerate(escenas) if i not in a_quitar]
    return datos


def _limpiar_y_parsear(texto: str) -> dict:
    if not texto or not texto.strip():
        raise ValueError("Respuesta vacía del modelo")
    texto = texto.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    datos = json.loads(texto)
    return _recortar_despedidas_repetidas(datos)


def generar_guion(tema: str) -> dict:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("Falta la variable de entorno GROQ_API_KEY")

    cliente = Groq(api_key=api_key)

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

    try:
        print(f"Groq falló, probando Cerebras/{MODELO_CEREBRAS}...")
        texto = _llamar_cerebras(tema)
        datos = _limpiar_y_parsear(texto)
        if "escenas" in datos and len(datos["escenas"]) >= 40:
            return datos
        print("  Respuesta incompleta con Cerebras también.")
    except Exception as e:
        print(f"  Fallo con Cerebras: {e}")

    raise RuntimeError("No se pudo generar un guion válido con ningún proveedor")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python generar_guion.py 'tema del accidente' salida.json")
        sys.exit(1)
    tema_arg, salida_arg = sys.argv[1], sys.argv[2]
    guion = generar_guion(tema_arg)
    with open(salida_arg, "w", encoding="utf-8") as f:
        json.dump(guion, f, ensure_ascii=False, indent=2)
    print(f"✓ Guion guardado en {salida_arg} ({len(guion['escenas'])} escenas)")
