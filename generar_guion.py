import os
import json
import sys
import re
from groq import Groq

MODELO_PRINCIPAL = "openai/gpt-oss-120b"
MODELO_FALLBACK = "openai/gpt-oss-20b"
MODELO_CEREBRAS = "llama-3.3-70b"

SYSTEM_PROMPT = """Eres el mejor guionista de YouTube de misterios de aviación. 

Regla de ORO: Tu narrativa no puede ser un bucle de alarmas. DEBES contar una historia real con contexto.

Devuelve SOLO un JSON válido con esta estructura estricta, separando la historia en 3 actos:
{
  "titulo_video": "titulo con brecha de curiosidad, máximo 60 caracteres",
  "descripcion_youtube": "descripción para YouTube",
  "tags_youtube": ["tags", "cortos"],
  "comentario_fijado": "pregunta polarizante para comentarios",
  "prompt_miniatura": "Hyper-realistic cinematic photography, an airplane cockpit window looking out at a dark storm, a glowing red emergency light reflecting on the glass, 8k resolution, unmarked clean surfaces",
  "titulo_miniatura": "¿QUÉ VIERON LOS PILOTOS?",
  
  "acto_1_caos": [
    {
      "texto_narracion": "frase corta, 8-15 palabras, con pausas...",
      "texto_pantalla": "EL DESASTRE COMIENZA",
      "duracion_segundos": 4.5,
      "prompt_imagen": "cinematic 3D render of a commercial airplane flying through dark storm clouds"
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
        datos_brutos = json.loads(match.group(0))
    else:
        datos_brutos = json.loads(texto.strip())
        
    # Unificar los 3 actos en una sola lista de "escenas" para que el pipeline no se rompa
    escenas_completas = []
    if "acto_1_caos" in datos_brutos: escenas_completas.extend(datos_brutos["acto_1_caos"])
    if "acto_2_investigacion" in datos_brutos: escenas_completas.extend(datos_brutos["acto_2_investigacion"])
    if "acto_3_resolucion" in datos_brutos: escenas_completas.extend(datos_brutos["acto_3_resolucion"])
    if "escenas" in datos_brutos: escenas_completas.extend(datos_brutos["escenas"]) # Por si acaso el modelo desobedece
    
    datos_brutos["escenas"] = escenas_completas
    return datos_brutos

def generar_guion(tema: str) -> dict:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key: raise RuntimeError("Falta GROQ_API_KEY")
    cliente = Groq(api_key=api_key)
    
    for modelo in (MODELO_PRINCIPAL, MODELO_FALLBACK):
        try:
            texto = _llamar_groq(cliente, tema, modelo)
            datos = _limpiar_y_parsear(texto)
            if "escenas" in datos and len(datos["escenas"]) >= 30: return datos
        except Exception as e: print(f" Fallo con {modelo}: {e}")
            
    try:
        texto = _llamar_cerebras(tema)
        datos = _limpiar_y_parsear(texto)
        if "escenas" in datos and len(datos["escenas"]) >= 30: return datos
    except Exception as e: print(f" Fallo con Cerebras: {e}")
        
    raise RuntimeError("No se pudo generar un guion válido")

if __name__ == "__main__":
    if len(sys.argv) < 3: sys.exit(1)
    tema_arg, salida_arg = sys.argv[1], sys.argv[2]
    guion = generar_guion(tema_arg)
    with open(salida_arg, "w", encoding="utf-8") as f:
        json.dump(guion, f, ensure_ascii=False, indent=2)
