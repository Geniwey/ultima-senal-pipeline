import os
import json
import sys
import re
from groq import Groq

# Modelos actualizados a las versiones válidas
MODELO_PRINCIPAL = "llama-3.3-70b-versatile"
MODELO_FALLBACK = "llama-3.1-8b-instant"
MODELO_CEREBRAS = "llama3.1-70b"

SYSTEM_PROMPT = """Eres el mejor guionista de YouTube de misterios de aviación. Tu narrativa debe ser un documental realista, no un bucle de alarmas.

Estructura OBLIGATORIA:
1. El Gancho (Tensión inicial)
2. El Contexto (Qué avión, de dónde venía, la investigación)
3. El Desenlace (La causa real verificada, el impacto en la aviación)

Reglas visuales (ESTRICTAS):
- VARIEDAD: Alterna planos visuales. Ejemplo: "cinematic wide shot of an airport tower at night", "macro photography of polished airplane wing", "interior of a dark passenger cabin", "abstract volumetric lighting in storm clouds".
- PROHIBICIÓN ABSOLUTA DE NEGACIONES: NUNCA uses palabras como "no text", "no labels", "no diagrams". En su lugar usa descripciones puras: "unmarked surfaces", "clean polished metal", "empty pristine scenery".
- NUNCA pidas pantallas, documentos, manuales, monitores, instrumentos o interfaces. 

Devuelve SOLO un JSON válido:
{
  "titulo_video": "Título que genere mucha curiosidad",
  "descripcion_youtube": "Descripción profunda del caso con la fuente real...",
  "tags_youtube": ["aviacion", "misterio"],
  "comentario_fijado": "¿Crees que este error fue humano o mecánico?",
  "prompt_miniatura": "hyperrealistic cinematic photography of a completely dark passenger cabin illuminated only by a single red emergency flash, pristine unmarked environment",
  "titulo_miniatura": "EL FALLO FATAL",
  "escenas": [
    {
      "texto_narracion": "La frase de la voz en off, usando comas para pausas dramáticas.",
      "texto_pantalla": "ROLO DINÁMICO CADA VEZ",
      "prompt_imagen": "cinematic wide shot of an airplane silhouette flying into thick dark storm clouds, pure atmospheric lighting"
    }
  ]
}

Genera exactamente entre 35 y 45 escenas para evitar límites de tokens, asegurando que cubres toda la historia."""

def _llamar_api(cliente: Groq, tema: str, modelo: str) -> str:
    respuesta = cliente.chat.completions.create(
        model=modelo,
        messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": f"Caso/Tema: {tema}"}],
        temperature=0.7, max_tokens=6000,
    )
    return respuesta.choices[0].message.content

def _llamar_cerebras(tema: str) -> str:
    from openai import OpenAI
    cliente = OpenAI(api_key=os.environ.get("CEREBRAS_API_KEY"), base_url="https://api.cerebras.ai/v1")
    respuesta = cliente.chat.completions.create(
        model=MODELO_CEREBRAS,
        messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": f"Caso/Tema: {tema}"}],
        temperature=0.7, max_tokens=6000,
    )
    return respuesta.choices[0].message.content

def generar_guion(tema: str) -> dict:
    for modelo in (MODELO_PRINCIPAL, MODELO_FALLBACK):
        try:
            print(f"Llamando a Groq ({modelo})...")
            cliente = Groq(api_key=os.environ.get("GROQ_API_KEY"))
            texto = _llamar_api(cliente, tema, modelo)
            match = re.search(r'\{.*\}', texto, re.DOTALL)
            return json.loads(match.group(0)) if match else json.loads(texto.strip())
        except Exception as e:
            print(f"Error en {modelo}: {e}")
            
    print("Groq falló. Probando Cerebras...")
    texto = _llamar_cerebras(tema)
    match = re.search(r'\{.*\}', texto, re.DOTALL)
    return json.loads(match.group(0)) if match else json.loads(texto.strip())

if __name__ == "__main__":
    tema = sys.argv[1] if len(sys.argv) > 1 else "Vuelo 603 Aeroperú"
    salida = sys.argv[2] if len(sys.argv) > 2 else "guion.json"
    with open(salida, "w", encoding="utf-8") as f:
        json.dump(generar_guion(tema), f, ensure_ascii=False, indent=2)
