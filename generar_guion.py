import os
import json
import sys
import re
from collections import Counter
from groq import Groq

MODELO_PRINCIPAL = "openai/gpt-oss-120b"
MODELO_FALLBACK = "openai/gpt-oss-20b"
MODELO_CEREBRAS = "llama-3.3-70b"

FICHA_POR_DEFECTO = {
    "caso": "Vuelo Aeroperú 603",
    "fecha": "2 de octubre de 1996",
    "avion": "Boeing 757-200 (matrícula N52AW)",
    "ruta": "Lima (Perú) a Santiago (Chile)",
    "ocupantes": "70 personas (61 pasajeros y 9 tripulantes, sin sobrevivientes)",
    "causa_oficial": "Un operario de limpieza cubrió los 3 puertos estáticos del lado izquierdo con cinta adhesiva plateada y nadie la retiró antes del despegue (Informe Final CIAA).",
    "cronologia": [
        {"hora": "00:40 AM", "hecho": "Despegue desde el aeropuerto de Lima bajo niebla densa"},
        {"hora": "00:42 AM", "hecho": "Velocímetro y altímetro muestran lecturas erróneas en ascenso"},
        {"hora": "00:44 AM", "hecho": "La tripulación declara emergencia y pide vectores de regreso"},
        {"hora": "00:58 AM", "hecho": "El radar de Lima lee 9700 pies falsos enviados por el transpondedor"},
        {"hora": "01:11 AM", "hecho": "El ala izquierda golpea el mar frente a Chancay tras 31 minutos de vuelo"},
    ],
    "consecuencias": [
        "Prohibición de cinta camuflada y uso obligatorio de cubiertas de alta visibilidad con banderines",
        "Refuerzo de las listas de verificación prevuelo y doble inspección de sensores",
    ],
    "fuentes": [
        "Informe Final de la Comisión Investigadora de Accidentes de Aviación (CIAA - Perú)",
        "Registros técnicos y recomendaciones de seguridad de la OACI",
    ],
}

BANCO_PLANOS = {
    "cinta_puerto": "Extreme macro close-up of glossy silver-grey metallic duct tape covering a round chrome static port sensor on a smooth unmarked dark blue aircraft fuselage, dramatic hangar spotlight, shallow depth of field",
    "cabina_pilotos": "Dark cinematic view from behind empty cockpit seats looking through windshield into dense night fog and distant lightning over the black ocean, moody blue instrument glow, smooth unmarked surfaces",
    "ala_nubes": "Close-up of a commercial airliner wingtip with red navigation strobe light cutting through dense dark storm clouds and rain at night, dramatic rim lighting, smooth unmarked metal",
    "pista_lluvia": "Low angle shot of wet airport runway centerlines reflecting amber approach lights in dense night fog, cinematic documentary atmosphere, smooth wet asphalt",
    "turbina": "Close-up exterior shot of commercial jet engine fan blades illuminated by amber runway lights in night mist, smooth unmarked metallic cowling",
    "mar_tormenta": "Dramatic low-angle close-up of a commercial airliner wingtip slicing into dark turbulent Pacific ocean waves at night sending white sea spray into the air, storm lighting",
    "barco_rescate": "Night maritime search vessel with a powerful white searchlight beam scanning dark rough ocean waves under rain and fog, cinematic documentary shot",
    "caja_negra": "Underwater spotlight illuminating a plain smooth bright orange rectangular flight data recorder box resting on dark sandy seabed, completely unmarked painted metal surface",
    "hangar": "Wide cinematic shot of a commercial Boeing 757 parked inside a dimly lit maintenance hangar at night under overhead floodlights, smooth unmarked white and blue fuselage",
    "avion_frontal": "Dramatic low-angle three-quarter view of an unmarked commercial airliner climbing into dark stormy night clouds, landing lights glowing, smooth clean fuselage",
    "torre_noche": "Exterior shot of an airport air traffic control tower at night surrounded by dense mist with glowing green radar room windows, moody cinematic lighting",
}

REGLAS_COHERENCIA = {
    "IMPACTO": {"mar_tormenta", "ala_nubes"},
    "OCÉANO": {"mar_tormenta", "barco_rescate"},
    "MAR": {"mar_tormenta", "barco_rescate"},
    "PUERTO": {"cinta_puerto"},
    "SENSOR": {"cinta_puerto"},
    "CINTA": {"cinta_puerto"},
    "CUBIERTA": {"cinta_puerto"},
    "BANDERÍN": {"cinta_puerto"},
    "INSPECCIÓN": {"hangar", "avion_frontal"},
    "VERIFICACIÓN": {"hangar", "cabina_pilotos"},
    "EMERGENCIA": {"cabina_pilotos", "torre_noche"},
    "ALARMA": {"cabina_pilotos"},
    "CABINA": {"cabina_pilotos"},
    "ALTÍMETRO": {"cabina_pilotos"},
    "VELOCÍMETRO": {"cabina_pilotos"},
    "CAJA NEGRA": {"caja_negra"},
    "GRABADORA": {"caja_negra"},
    "TORRE": {"torre_noche"},
    "RADAR": {"torre_noche"},
    "DESPEGUE": {"pista_lluvia", "avion_frontal"},
    "PISTA": {"pista_lluvia"},
    "TURBINA": {"turbina"},
    "MOTOR": {"turbina"},
    "RESCATE": {"barco_rescate"},
}

PALABRAS_VACIAS = {
    "REFLEXIÓN", "MEMORIAL", "ESTADÍSTICAS", "PREGUNTA", "TECNOLOGÍA",
    "LECCIÓN", "CONCLUSIÓN", "LEGADO", "DECISIÓN", "INTERROGANTE", "ESTUDIO",
    "INFORMACIÓN", "ANÁLISIS", "COMPARTE", "SUSCRÍBETE", "TRAGEDIA",
    "RESUMEN FINAL", "CASOS SIMILARES", "HONOR LIMA", "MEDIDA CRÍTICA",
    "INSPECCIÓN AUTOMATIZADA", "LISTA DOBLE INSPECCIÓN", "REDUNDANCIA DE SENSORES",
    "PITOT INFLUENCIADO",
}

ROTULOS_DATOS_VERIFICADOS = [
    "BOEING 757-200 N52AW",
    "RUTA LIMA A SANTIAGO",
    "70 PERSONAS A BORDO",
    "SIN SOBREVIVIENTES",
    "31 MINUTOS DE VUELO",
    "IMPACTO FRENTE A CHANCAY",
    "INFORME OFICIAL CIAA",
    "BANDERINES OBLIGATORIOS OACI",
    "CINTA CAMUFLADA PROHIBIDA",
    "DOBLE VERIFICACIÓN PREVUELO",
]

CORRECCIONES_ORTOGRAFICAS = {
    r"\bOCCUPANTES\b": "OCUPANTES",
    r"\bNIEBLA DENSO\b": "NIEBLA DENSA",
    r"\bIMPÁCTO\b": "IMPACTO",
    r"\bININTERUMPIDA\b": "ININTERRUMPIDA",
    r"\bAEROPERU\b": "AEROPERÚ",
    r"\bADICIONA\b": "ADICIONAL",
    r"\bla ala\b": "el ala",
    r"\b9\.700\b": "9700",
    r"\btubos?\s+pitot\b": "puertos estáticos",
    r"\bdel\s+pitot\b": "de los puertos estáticos",
    r"\bpitot\b": "puerto estático",
}


def _limpiar_narracion_y_datos(texto: str) -> str:
    res = texto.strip()
    for patron, reemplazo in CORRECCIONES_ORTOGRAFICAS.items():
        res = re.sub(patron, reemplazo, res, flags=re.IGNORECASE)
    # Eliminar alucinaciones de años modernos (ej. "en 2023")
    res = re.sub(r",?\s*\ben\s+20\d{2}\b", "", res, flags=re.IGNORECASE)
    res = re.sub(r"\s+([.,;?¿!¡])", r"\1", res)
    return res.strip()


def _recortar_palabras_limpio(texto: str, max_chars: int = 28, max_palabras: int = 4) -> str:
    palabras = [w.strip(".,;:¡!¿?\"'#") for w in texto.split() if w.strip(".,;:¡!¿?\"'#")]
    resultado = []
    for p in palabras[:max_palabras]:
        candidato = " ".join(resultado + [p])
        if len(candidato) <= max_chars:
            resultado.append(p)
        else:
            break
    if len(resultado) < 2 and len(palabras) >= 2:
        resultado = palabras[:2]
    return " ".join(resultado).upper()


def rotulo_coherente(rotulo: str, plano: str) -> bool:
    rot_up = rotulo.upper()
    for clave, permitidos in REGLAS_COHERENCIA.items():
        if clave in rot_up and plano not in permitidos:
            return False
    return True


def _corregir_plano_por_rotulo(rotulo: str, plano_actual: str) -> str:
    rot_up = rotulo.upper()
    for clave, permitidos in REGLAS_COHERENCIA.items():
        if clave in rot_up and plano_actual not in permitidos:
            return sorted(permitidos)[0]
    return plano_actual


def _cargar_ficha(tema: str) -> dict:
    ruta_ficha = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ficha.json")
    if os.path.exists(ruta_ficha):
        try:
            with open(ruta_ficha, "r", encoding="utf-8") as f:
                ficha = json.load(f)
            print("📋 Ficha verificada cargada desde ficha.json")
            return ficha
        except Exception as e:
            print(f"  [Aviso] No se pudo leer ficha.json ({e}), usando ficha integrada.")
    return FICHA_POR_DEFECTO


def _build_system_prompt(ficha: dict) -> str:
    planos_lista = ", ".join(BANCO_PLANOS.keys())
    return f"""Eres el director jefe de un canal documental forense de aviación en YouTube. Escribe un guion de exactamente 34 escenas (duración total 4:20 a 5:00 min) con máximo rigor técnico y tono respetuoso con las víctimas.

FICHA DE HECHOS VERIFICADA (USA SOLO ESTOS DATOS; PROHIBIDO INVENTAR AÑOS COMO 2023 O HABLAR DE TUBOS PITOT):
{json.dumps(ficha, ensure_ascii=False, indent=2)}

DISTRIBUCIÓN OBLIGATORIA POR BLOQUES:
- Escenas 1 a 3: Gancho en frío a las 01:10 AM sobre el Pacífico con las alarmas activas antes de rebobinar al despegue.
- Escenas 4 a 10: Preparación del Boeing 757-200 en Lima, lavado del fuselaje y colocación de cinta plateada sobre los 3 puertos estáticos (NO tubos pitot).
- Escenas 11 a 18: Despegue a las 00:40 AM bajo niebla densa, conflicto entre velocímetro y altímetro y llamada de emergencia.
- Escenas 19 a 26: Lectura falsa de 9700 pies en el radar de Lima, descenso ciego sobre el océano e impacto a las 01:11 AM frente a Chancay.
- Escenas 27 a 31: Operación de búsqueda marítima, recuperación de la caja negra (FDR) y conclusiones técnicas del informe oficial CIAA.
- Escenas 32 a 34: ÚNICAMENTE aquí menciona las medidas de la OACI (cubiertas con banderines de alta visibilidad y doble verificación prevuelo) y cierra con una pregunta técnica reflexiva.

REGLAS ESTRICTAS DE RÓTULOS ("texto_pantalla"):
- MAYÚSCULAS, entre 2 y 4 palabras completas (MÁXIMO 28 caracteres), con un dato concreto verificable que coincida con "plano".
- NUNCA repitas un rótulo, nunca uses signos '#' ni frases vagas ({", ".join(sorted(PALABRAS_VACIAS))}).

REGLAS DE PLANOS ("plano" y "prompt_imagen"):
- El campo "plano" DEBE ser exactamente uno de estos: {planos_lista}.
- Usa cada plano como máximo 2 veces (máximo 3 veces "cinta_puerto") y NUNCA pongas el mismo plano en dos escenas consecutivas.
- Describe siempre en inglés: sujeto físico + plano + luz + ambiente, con superficies lisas ("smooth unmarked metal"). PROHIBIDO pedir personas, caras, pantallas con texto, relojes, papeles o logos.

Devuelve ÚNICAMENTE un JSON válido:
{{
  "titulo_video": "El error de 2$ que derribó al Vuelo 603 (Caso Aeroperú)",
  "descripcion_youtube": "Resumen documental de 3 párrafos citando las fuentes oficiales de la ficha.",
  "tags_youtube": ["aeroperu 603", "misterios de aviacion", "documental aereo", "caja negra", "seguridad aerea"],
  "comentario_fijado": "¿Qué medida de control crees que es más crítica para evitar un fallo así: las cubiertas con banderín o la doble inspección prevuelo?",
  "prompt_miniatura": "{BANCO_PLANOS['cinta_puerto']}, 8k",
  "titulo_miniatura": "LA CINTA MORTAL",
  "escenas": [
    {{
      "texto_narracion": "Frase documental clara de 14 a 22 palabras...",
      "texto_pantalla": "01:10 AM SOBRE EL PACÍFICO",
      "tipo": "imagen",
      "plano": "cabina_pilotos",
      "duracion_segundos": 5.5,
      "prompt_imagen": "Dark cinematic view from behind empty cockpit seats looking into dense night fog and lightning over the ocean, smooth unmarked surfaces"
    }}
  ]
}}"""


def _llamar_groq(cliente: Groq, messages: list, modelo: str, temperatura: float = 0.3) -> str:
    respuesta = cliente.chat.completions.create(
        model=modelo,
        messages=messages,
        temperature=temperatura,
        max_tokens=16000,
    )
    return respuesta.choices[0].message.content


def _llamar_cerebras(messages: list, temperatura: float = 0.3) -> str:
    from openai import OpenAI
    api_key = os.environ.get("CEREBRAS_API_KEY")
    if not api_key:
        raise RuntimeError("Falta CEREBRAS_API_KEY")
    cliente = OpenAI(api_key
