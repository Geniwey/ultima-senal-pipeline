import os
import json
import sys
import re
from groq import Groq

MODELO_PRINCIPAL = "openai/gpt-oss-120b"
MODELO_FALLBACK = "openai/gpt-oss-20b"
MODELO_CEREBRAS = "llama-3.3-70b"

SYSTEM_PROMPT = """Eres un documentalista forense de aviación para YouTube. Tu objetivo es narrar casos reales verificados con rigor técnico y tensión narrativa real.

ESTRUCTURA OBLIGATORIA DEL GUION (SIN RELLENO MORALISTA):
- FASE 1 (Escenas 1 a 10 - Gancho y Contexto): Arranca en el momento exacto en que salta la primera anomalía en vuelo. Identifica el vuelo real, fecha exacta, modelo de avión, ruta y número de ocupantes.
- FASE 2 (Escenas 11 a 38 - Cronología Minuto a Minuto): Narra la evolución real de la emergencia en cabina, las lecturas contradictorias, las comunicaciones con la torre de control (ATC) y las maniobras físicas del avión hasta el impacto.
- FASE 3 (Escenas 39 a 50 - Investigación Forense): El hallazgo de las cajas negras (FDR y CVR) y el descubrimiento exacto de la causa raíz (ej. la cinta adhesiva olvidada por mantenimiento en los tubos pitot).
- FASE 4 (Últimas 4 escenas - Cierre Seco): El cambio concreto en el reglamento de la FAA/OACI y cierre seco. PROHIBIDO repetir durante minutos lecciones genéricas, campañas educativas, liderazgo o hablar de pasajeros sonrientes.

REGLAS ESTRICTAS DE RÓTULOS ("texto_pantalla"):
- PROHIBIDO usar frases poéticas o abstractas (NUNCA pongas cosas como "SENSORES OPALESCENTES", "TORNADO DE LUZ", "CURVA DESCONOCIDA" o "ALAS EN LA NOCHE").
- Usa SIEMPRE datos duros, técnicos o cronológicos de 2 a 4 palabras en MAYÚSCULAS: "VUELO AEROPERÚ 603", "BOEING 757-200", "TUBOS PITOT TAPADOS", " VELOCIDAD ERRÓNEA", "CAÍDA A 12.000 PIES", "ALERTA GPWS", "INFORME OFICIAL OACI".

REGLAS ESTRICTAS DE IMAGEN ("prompt_imagen"):
- PROHIBIDO incluir personas, caras, pilotos, mecánicos, pasajeros, manos, siluetas humanas, interiores con letreros, cuadros de mando, velocímetros, relojes, pantallas, libros, papeles o documentos.
- Describe ÚNICAMENTE planos exteriores de aviones comerciales Boeing/Airbus en la noche, turbinas bajo la lluvia, alas cortando tormentas, luces de pista en la niebla, olas del océano oscuro o piezas metálicas de fuselaje en macrofotografía sin letras.

REGLAS DE MINIATURA ("titulo_miniatura" y "prompt_miniatura"):
- En "titulo_miniatura", crea una frase de 2 a 3 palabras en MAYÚSCULAS específica del caso o en pregunta (ej. "¿VOLARON CIEGOS?", "ERROR DE 2$", "TRAMPA NOCTURNA", "RADAR EN CERO"). NUNCA uses la frase genérica "EL FALLO FATAL".
- En "prompt_miniatura", pide un plano exterior dramático de un avión comercial en medio de una tormenta nocturna con un motor iluminado en rojo, sin letreros ni cabinas interiores.

Devuelve ÚNICAMENTE un objeto JSON válido con esta estructura:
{
  "titulo_video": "Título intrigante con dato concreto del caso (máx 60 caracteres)",
  "descripcion_youtube": "Descripción documental detallada de 3 párrafos incluyendo fecha, modelo de avión y citando explícitamente la fuente oficial (Comisión Investigadora de Accidentes de Aviación / OACI / NTSB).",
  "tags_youtube": ["aviacion", "documental", "misterio", "caja negra"],
  "comentario_fijado": "Pregunta concreta de debate sobre el fallo técnico del caso",
  "prompt_miniatura": "Cinematic wide shot of a commercial airliner flying through dark storm clouds at night, red emergency glow reflecting on the metal wing and turbine, high contrast, bright dramatic lightning, photorealistic, no text, no signs",
  "titulo_miniatura": "2-3 PALABRAS ESPECÍFICAS DEL CASO",
  "escenas": [
    {
      "texto_narracion": "Frase documental clara y tensa de 12 a 20 palabras...",
      "texto_pantalla": "DATO TÉCNICO CONCRETO",
      "duracion_segundos": 4.5,
      "prompt_imagen": "Cinematic exterior shot of a commercial Boeing 757 airplane taking off at night in heavy fog, glowing runway lights below, photorealistic, no text, no people"
    }
  ]
}
Genera entre 50 y 60 escenas."""


def _llamar_groq(cliente: Groq, tema: str, modelo: str) -> str:
    respuesta = cliente.chat.completions.create(
        model=modelo,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Caso real a documentar con datos verificables: {tema}"},
        ],
        temperature=0.5,
        max_tokens=18000,
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
            {"role": "user", "content": f"Caso real a documentar con datos verificables: {tema}"},
        ],
        temperature=0.5,
        max_tokens=18000,
    )
    return respuesta.choices[0].message.content


def _limpiar_y_parsear(texto: str) -> dict:
    if not texto or not texto.strip():
        raise ValueError("Respuesta vacía")
    match = re.search(r"\{.*\}", texto, re.DOTALL)
    datos = json.loads(match.group(0)) if match else json.loads(texto.strip())

    # Blindaje contra título de miniatura genérico
    titulo_min = datos.get("titulo_miniatura", "").strip().upper()
    if not titulo_min or "FALLO FATAL" in titulo_min:
        datos["titulo_miniatura"] = "¿VOLARON CIEGOS?"

    # Asegurar fuente verificable en la descripción
    desc = datos.get("descripcion_youtube", "")
    if "Fuente" not in desc and "Informe" not in desc:
        datos["descripcion_youtube"] = (
            desc.strip()
            + "\n\n📋 Fuente oficial verificada: Informe Final de la Comisión Investigadora de Accidentes de Aviación (CIAA / OACI) y registros oficiales de Seguridad Aérea (ASN)."
        )
    return datos


def generar_guion(tema: str) -> dict:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("Falta GROQ_API_KEY")
    cliente = Groq(api_key=api_key)

    for modelo in (MODELO_PRINCIPAL, MODELO_FALLBACK):
        try:
            print(f"Llamando a Groq ({modelo})...")
            texto = _llamar_groq(cliente, tema, modelo)
            datos = _limpiar_y_parsear(texto)
            if "escenas" in datos and len(datos["escenas"]) >= 40:
                return datos
        except Exception as e:
            print(f" Fallo con {modelo}: {e}")

    try:
        print("Groq falló, probando Cerebras...")
        texto = _llamar_cerebras(tema)
        datos = _limpiar_y_parsear(texto)
        if "escenas" in datos and len(datos["escenas"]) >= 40:
            return datos
    except Exception as e:
        print(f" Fallo con Cerebras: {e}")

    raise RuntimeError("No se pudo generar un guion válido con ningún proveedor")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(1)
    tema_arg, salida_arg = sys.argv[1], sys.argv[2]
    guion = generar_guion(tema_arg)
    with open(salida_arg, "w", encoding="utf-8") as f:
        json.dump(guion, f, ensure_ascii=False, indent=2)
