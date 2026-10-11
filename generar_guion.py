import os
import json
import sys
import re
from groq import Groq

# RESTAURADOS LOS MODELOS ORIGINALES QUE FUNCIONAN AL 100%
MODELO_PRINCIPAL = "openai/gpt-oss-120b"
MODELO_FALLBACK = "openai/gpt-oss-20b"
MODELO_CEREBRAS = "llama-3.3-70b"

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
  "acto_1_caos": [
    {
      "texto_narracion": "La frase de la voz en off, usando comas para pausas dramáticas.",
      "texto_pantalla": "RÓTULO DINÁMICO CADA VEZ",
      "duracion_segundos": 4.5,
      "prompt_imagen": "cinematic wide shot of an airplane silhouette flying into thick dark storm clouds, pure atmospheric lighting"
    }
  ],
  "acto_2_investigacion": [
    {
      "texto_narracion": "Explica el contexto, qué falló, la caja negra...",
      "texto_pantalla": "LA VERDAD OCULTA",
      "duracion_segundos": 4.5,
      "prompt_imagen": "cinematic macro photography of broken airplane metal parts"
    }
  ],
  "acto_3_resolucion": [
    {
      "texto_narracion": "El impacto final y cómo cambió la aviación...",
      "texto_pantalla": "EL LEGADO",
      "duracion_segundos": 4.5,
      "prompt_imagen": "cinematic view of a dark empty runway at night"
    }
  ]
}

Genera exactamente 15 escenas en el acto 1, 20 escenas en el acto 2, y 15 escenas en el acto 3."""

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

def _limpiar_y_parsear(texto: str) -> dict:
    if not texto or not texto.strip(): raise ValueError("Respuesta vacía")
    match = re.search(r'\{.*\}', texto, re.DOTALL)
    if match:
        datos_brutos = json.loads(match.group(0))
    else:
        datos_brutos = json.loads(texto.strip())
        
    escenas_completas = []
    if "acto_1_caos" in datos_brutos: escenas_completas.extend(datos_brutos["acto_1_caos"])
    if "acto_2_investigacion" in datos_brutos: escenas_completas.extend(datos_brutos["acto_2_investigacion"])
    if "acto_3_resolucion" in datos_brutos: escenas_completas.extend(datos_brutos["acto_3_resolucion"])
    if "escenas" in datos_brutos and not escenas_completas: escenas_completas.extend(datos_brutos["escenas"])
    
    datos_brutos["escenas"] = escenas_completas
    return datos_brutos

def generar_guion(tema: str) -> dict:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key: raise RuntimeError("Falta GROQ_API_KEY")
    cliente = Groq(api_key=api_key)
    
    for modelo in (MODELO_PRINCIPAL, MODELO_FALLBACK):
        try:
            print(f"Llamando a Groq ({modelo})...")
            texto = _llamar_api(cliente, tema, modelo)
            datos = _limpiar_y_parsear(texto)
            if "escenas" in datos and len(datos["escenas"]) >= 30: return datos
        except Exception as e:
            print(f"Error en {modelo}: {e}")
            
    print("Groq falló. Probando Cerebras...")
    try:
        texto = _llamar_cerebras(tema)
        datos = _limpiar_y_parsear(texto)
        if "escenas" in datos and len(datos["escenas"]) >= 30: return datos
    except Exception as e:
        print(f" Fallo con Cerebras: {e}")
        
    raise RuntimeError("No se pudo generar un guion válido")

if __name__ == "__main__":
    if len(sys.argv) < 3: sys.exit(1)
    tema_arg, salida_arg = sys.argv[1], sys.argv[2]
    guion = generar_guion(tema_arg)
    with open(salida_arg, "w", encoding="utf-8") as f:
        json.dump(guion, f, ensure_ascii=False, indent=2)
