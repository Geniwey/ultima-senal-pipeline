import os
import json
import sys
import re
from groq import Groq

# Modelos originales intocables
MODELO_PRINCIPAL = "openai/gpt-oss-120b"
MODELO_FALLBACK = "openai/gpt-oss-20b"
MODELO_CEREBRAS = "llama-3.3-70b"

SYSTEM_PROMPT = """Eres guionista de un canal de YouTube de misterios de aviación. El estilo visual es RENDER 3D ABSTRACTO Y MACRO FOTOGRAFÍA SIN TEXTO.

Reglas estrictas:
- Nunca describir restos humanos o cuerpos.
- Español neutro. Tono grave y cinemático de misterio.
- TÍTULO CON BRECHA DE CURIOSIDAD: nunca descriptivo. Usa un título que genere una pregunta inevitable.
- GANCHO INICIAL: Arranca in media res en medio del caos o alerta técnica, antes de dar el contexto.
- PAUSAS: Usa puntos suspensivos (...) y comas estratégicas en "texto_narracion" para obligar al TTS a hacer pausas dramáticas.
- PROHIBICIÓN ABSOLUTA DE DESPEDIDAS: Termina en seco con la moraleja o lección. Cero menciones a likes o suscripciones.
- PROHIBICIÓN VISUAL (ANTI-TEXTO ALIENÍGENA): Los modelos de IA inventan texto falso si les pides pantallas. En "prompt_imagen", NUNCA pidas pantallas, monitores, HUDs, paneles de control, relojes, radares, diagramas, mapas, documentos o instrumentos. Pide SIEMPRE partes externas del avión (turbinas, alas, fuselaje, remaches), luces de emergencia, nubes de tormenta, o geometría abstracta sin etiquetas.
- Devuelve SOLO un JSON válido:
{
  "titulo_video": "titulo con brecha, máximo 60 caracteres",
  "descripcion_youtube": "descripción para YouTube",
  "tags_youtube": ["tags", "cortos"],
  "comentario_fijado": "pregunta polarizante para comentarios",
  "prompt_miniatura": "Hyper-realistic cinematic photography, extreme close-up of a glowing red emergency light in the dark, moody atmosphere, 8k resolution, NO TEXT",
  "titulo_miniatura": "2-4 palabras MAYÚSCULAS",
  "escenas": [
    {
      "texto_narracion": "frase corta, 8-15 palabras, con pausas...",
      "texto_pantalla": "2-5 palabras MAYÚSCULAS",
      "duracion_segundos": 4.5,
      "prompt_imagen": "macro photography of a metallic airplane wing piercing through dark storm clouds, dramatic lighting, NO TEXT"
    }
  ]
}

Genera entre 70 y 90 escenas para un ritmo ágil."""

def _llamar_groq(cliente: Groq, tema: str, modelo: str) -> str:
    respuesta = cliente.chat.completions.create(
        model=modelo,
        messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": f"Tema del video: {tema}"}],
        temperature=0.6, max_tokens=20000,
    )
    return respuesta.choices[0].message.content

def _llamar_cerebras(tema: str) -> str:
    from openai import OpenAI
    api_key = os.environ.get("CEREBRAS_API_KEY")
    if not api_key: raise RuntimeError("Falta CEREBRAS_API_KEY")
    cliente = OpenAI(api_key=api_key, base_url="https://api.cerebras.ai/v1")
    respuesta = cliente.chat.completions.create(
        model=MODELO_CEREBRAS,
        messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": f"Tema del video: {tema}"}],
        temperature=0.6, max_tokens=20000,
    )
    return respuesta.choices[0].message.content

def _limpiar_y_parsear(texto: str) -> dict:
    if not texto or not texto.strip(): raise ValueError("Respuesta vacía")
    match = re.search(r'\{.*\}', texto, re.DOTALL)
    if match:
        return json.loads(match.group(0))
    return json.loads(texto.strip())

def generar_guion(tema: str) -> dict:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key: raise RuntimeError("Falta GROQ_API_KEY")
    cliente = Groq(api_key=api_key)
    
    for modelo in (MODELO_PRINCIPAL, MODELO_FALLBACK):
        try:
            print(f"Generando guion con Groq/{modelo}...")
            texto = _llamar_groq(cliente, tema, modelo)
            datos = _limpiar_y_parsear(texto)
            if "escenas" in datos and len(datos["escenas"]) >= 40: return datos
        except Exception as e: print(f" Fallo con {modelo}: {e}")
            
    try:
        print(f"Groq falló, probando Cerebras...")
        texto = _llamar_cerebras(tema)
        datos = _limpiar_y_parsear(texto)
        if "escenas" in datos and len(datos["escenas"]) >= 40: return datos
    except Exception as e: print(f" Fallo con Cerebras: {e}")
        
    raise RuntimeError("No se pudo generar un guion válido con ningún proveedor")

if __name__ == "__main__":
    if len(sys.argv) < 3: sys.exit(1)
    tema_arg, salida_arg = sys.argv[1], sys.argv[2]
    guion = generar_guion(tema_arg)
    with open(salida_arg, "w", encoding="utf-8") as f:
        json.dump(guion, f, ensure_ascii=False, indent=2)
