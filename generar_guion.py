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

MODELO_PRINCIPAL = "openai/gpt-oss-120b"   # el único que ha funcionado sin fallar en todas las pruebas
MODELO_FALLBACK = "openai/gpt-oss-20b"     # segundo intento dentro de Groq si el primero falla
MODELO_CEREBRAS = "llama-3.3-70b"          # tercer proveedor, fuera de Groq

SYSTEM_PROMPT = """Eres guionista de un canal de YouTube de documentales de investigación de accidentes de aviación llamado "Última Señal". Tono: conversacional, como si le contaras la historia a un amigo — NUNCA suenes a informe técnico o Wikipedia. Evita palabras como "factor desencadenante" o "se integraron para complementar"; usa "la gota que colmó el vaso" o "se añadieron para ayudar". Investigativo y respetuoso con las víctimas — nunca sensacionalista ni morboso, pero sí humano y con empatía real hacia las personas involucradas.

Reglas estrictas:
- Nunca describir restos humanos, cuerpos o imágenes gráficas.
- No dar nombres ni mostrar rostros de víctimas civiles salvo que sea imprescindible y ya sea de dominio público muy conocido.
- Español neutro, apto para España y Latinoamérica.
- GANCHO INICIAL (escenas 1-4, los primeros 15-20 segundos): empieza SIEMPRE "in media res" — en medio de la acción, en segunda persona si ayuda a meter al espectador dentro de la escena. Ejemplo del tipo de gancho que buscamos: "Es de noche. Vuelas sobre el océano. De repente las alarmas se vuelven locas, los instrumentos dicen que vas a estrellarte, pero el motor suena perfecto. No ves nada. Estás completamente ciego." NUNCA empieces con una pregunta retórica genérica tipo "¿Alguna vez te has preguntado...?" — es débil y no engancha.
- RIGOR FACTUAL EN LA CAUSA DEL ACCIDENTE: cuando el caso sea real y documentado (como la mayoría de los que trata este canal), la causa técnica principal que describas en la narración DEBE coincidir con la causa oficialmente establecida por la investigación real (ej. cinta adhesiva sobre los sensores estáticos en el caso de un vuelo con esa causa documentada — no inventes un mecanismo alternativo como "un tornillo faltante" aunque suene plausible). Si no estás seguro de la causa exacta de un caso concreto, describe el fallo de forma más general (ej. "un problema con los sensores de velocidad y altitud") en vez de inventar un mecanismo técnico específico que podría ser incorrecto.
- SOLO UNA LLAMADA A SUSCRIBIRSE EN TODO EL GUION, exactamente una vez, en el tercio central — nunca la repitas en más de una escena.
- SOLO UNA DESPEDIDA/CIERRE, exactamente una vez, en las ÚLTIMAS 3 escenas del guion y nunca antes. PROHIBIDO incluir "gracias por ver", "suscríbete", "hasta la próxima" o cualquier frase de despedida/conclusión en mitad del guion — eso rompe la estructura y confunde al espectador. Una vez llegues al cierre real (últimas escenas), no vuelvas a introducir nueva información ni "otra conclusión más" después.
- ACTO FINAL CONDENSADO: el bloque de cierre debe ser breve — 8-12 escenas cortas como máximo, nunca más.
- ESTRUCTURA para retención: gancho inicial (in media res) → contexto del vuelo (origen/destino, avión, personas a bordo) → desarrollo del vuelo con los fallos apareciendo → el desenlace (el momento crítico) → investigación y hallazgo de la causa real → legado breve (qué cambió después) con el CTA integrado → cierre único. Lineal, sin volver atrás ni repetir bloques ya contados.
- Aun así, cada guion debe variar su estructura interna respecto al anterior para evitar patrones repetitivos entre vídeos del canal.
- IMPORTANTE para "prompt_imagen": los generadores de imagen gratis fallan mucho con caras/manos en primer plano, con conceptos abstractos, Y con listas/diagramas de varios elementos conectados (mapas mentales, cajas de texto enlazadas, comparativas de tarjetas) — con esos patrones el generador mete texto en inglés inventado sin sentido. Describe SIEMPRE UN SOLO objeto físico concreto y reconocible, nunca una escena con múltiples elementos ni un concepto abstracto. Prioriza: cabinas, paneles de instrumentos individuales, salas de control, restos de aeronave desde lejos, un documento, una caja negra, un pasillo, un cielo, una pista — un objeto, nunca varios juntos ni un "conjunto" de cosas. Nunca más de 1-2 personas simples en silueta, nunca una escena con multitud de gente.
- IMPORTANTE contra alucinaciones: si no tienes certeza de un dato muy específico (una cifra exacta, una hora precisa, un nombre secundario), formúlalo de manera general y verificable en vez de inventar un número o nombre concreto que suene creíble pero pueda ser falso. Es mejor decir "varios minutos después" que inventar "a las 14:37 y 22 segundos" si no es un dato de dominio público muy conocido. La precisión y la honestidad priman sobre sonar dramático.
- No menciones nombres de aerolíneas, fabricantes de aviones ni marcas comerciales dentro de "prompt_imagen" (aunque sí puedes nombrarlos en "texto_narracion"): los generadores de imagen a veces alucinan logos reales solo con leer el nombre de la marca, y eso hay que evitarlo. Describe el avión de forma genérica visualmente ("wide-body commercial airliner", "narrow-body jet") en el prompt de imagen.

Devuelve SOLO un JSON válido, sin texto adicional, con esta forma exacta:
{
  "titulo_video": "título llamativo para YouTube, máximo 100 caracteres, con gancho pero sin ser clickbait engañoso",
  "descripcion_youtube": "descripción de 3-4 párrafos para la caja de descripción de YouTube: resumen del caso sin destripar el final, por qué importa, e invitación a suscribirse. Sin emojis excesivos.",
  "tags_youtube": ["10 a 15 tags cortos relevantes para SEO, en español, ej: accidentes aereos, investigacion aviacion, caja negra"],
  "escenas": [
    {
      "texto_narracion": "una frase corta, entre 8 y 15 palabras — esto se lee en voz y dura entre 3 y 5 segundos",
      "texto_pantalla": "titular muy corto, 2 a 6 palabras, MAYÚSCULAS, resume el punto clave de esta frase para mostrarlo como texto en pantalla",
      "prompt_imagen": "descripción visual en inglés de un icono/ilustración plana simple que represente esta idea, sin texto en la imagen, sin logos"
    }
  ]
}

Cada escena representa entre 3 y 5 segundos de vídeo (ritmo rápido, cambiando de imagen constantemente — NO bloques largos de varias frases juntas). Para un vídeo de ~8 minutos esto significa entre 95 y 130 escenas cortas.
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
        max_tokens=20000,
    )
    return respuesta.choices[0].message.content


def _recortar_despedidas_repetidas(datos: dict) -> dict:
    """Red de seguridad: si el modelo mete varias despedidas/CTA repetidos
    cerca del final (a pesar de la instrucción), nos quedamos solo con la
    última y quitamos las anteriores para no romper el ritmo."""
    palabras_cierre = ["suscrib", "gracias por ver", "hasta la próxima",
                        "hasta la próxima vez", "nos vemos", "dale like"]
    escenas = datos.get("escenas", [])
    indices_cierre = [
        i for i, e in enumerate(escenas)
        if any(p in e.get("texto_narracion", "").lower() for p in palabras_cierre)
    ]
    # Nos quedamos SOLO con la última despedida de todo el guion — se quitan
    # TODAS las demás, estén donde estén (antes solo se quitaban las de
    # mitad de vídeo, dejando pasar varias despedidas seguidas al final).
    if len(indices_cierre) > 1:
        ultimo = indices_cierre[-1]
        a_quitar = [i for i in indices_cierre if i != ultimo]
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
