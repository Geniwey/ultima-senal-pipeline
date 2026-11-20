import os
import sys
import base64
import shutil
import requests
import urllib.parse
import re

ESTILO_BASE = (
    "cinematic documentary photography, photorealistic, sharp focus, "
    "smooth unmarked metallic surfaces, dramatic moody lighting, 8k"
)

TIMEOUT = 40
TAMANO_MINIMO_BYTES = 12_000
_cf_flux_agotado = [False]
_cf_sdxl_agotado = [False]
_pol_agotado = [False]
_ultima_fue_emergencia = [False]
_hashes_usados = []
_aprobadas_por_plano = {}
_aprobadas_generales = []
_reutilizaciones_por_ruta = {}
_indice_rotacion_banco = [0]
_urls_wikimedia_usadas = set()
_stats = {
    "generadas_ia": 0,
    "wikimedia_real": 0,
    "rechazadas_qa": 0,
    "reutilizadas_banco": 0,
    "infografias": 0,
}

QUERIES_WIKIMEDIA_POR_PLANO = {
    "cinta_puerto": "Boeing 757 fuselage static port close up",
    "cabina_pilotos": "Boeing 757 cockpit night instruments",
    "ala_nubes": "aircraft wing clouds sunset sky",
    "pista_lluvia": "airport runway night lights rain",
    "turbina": "jet engine turbofan blades close up",
    "mar_tormenta": "stormy ocean waves dark sea",
    "barco_rescate": "coast guard rescue ship ocean",
    "caja_negra": "flight data recorder black box aviation",
    "hangar": "Boeing 757 aircraft maintenance hangar",
    "avion_frontal": "Boeing 757 commercial airliner",
    "torre_noche": "airport air traffic control tower night",
    "general": "commercial airliner clouds sky",
}


def fue_ultima_generacion_emergencia() -> bool:
    return _ultima_fue_emergencia[0]


def obtener_estadisticas_imagenes() -> dict:
    return dict(_stats)


def obtener_mejor_imagen_plano(plano: str) -> str:
    candidatas = _aprobadas_por_plano.get(plano, [])
    if not candidatas:
        return ""
    candidatas_ordenadas = sorted(candidatas, key=lambda item: item[0], reverse=True)
    for _, ruta in candidatas_ordenadas:
        if os.path.exists(ruta):
            return ruta
    return ""


def _generar_infografia_codigo(tipo: str, ruta_salida: str) -> bool:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np

        plt.rcParams["font.sans-serif"] = "DejaVu Sans"
        plt.rcParams["axes.edgecolor"] = "#2A3F5F"
        fig, ax = plt.subplots(figsize=(19.2, 10.8), dpi=100)
        fig.patch.set_facecolor("#070B12")
        ax.set_facecolor("#0B1320")
        fig.subplots_adjust(left=0.11, right=0.92, top=0.84, bottom=0.22)

        if "TARJETA_VUELO" in tipo:
            ax.axis("off")
            ax.set_title(
                "EXPEDIENTE TÉCNICO: VUELO AEROPERÚ 603",
                color="#00E5FF",
                fontsize=28,
                fontweight="bold",
                pad=22,
            )
            tarjetas = [
                (0.18, "AERONAVE\n\nBOEING 757-200\nMatrícula N52AW", "#00E5FF"),
                (0.50, "OCUPANTES\n\n70 PERSONAS\n61 Pasajeros · 9 Tripul.", "#FFAA00"),
                (0.82, "RUTA Y FECHA\n\nLIMA → SANTIAGO\n2 Octubre 1996", "#FF3333"),
            ]
            for x, texto, col in tarjetas:
                bbox = dict(
                    boxstyle="round,pad=0.65",
                    facecolor="#101C2E",
                    edgecolor=col,
                    linewidth=4,
                )
                ax.text(
                    x, 0.56, texto,
                    color="#FFFFFF", fontsize=22, fontweight="bold",
                    ha="center", va="center", bbox=bbox, transform=ax.transAxes,
                )

        elif "ESQUEMA_SENSORES" in tipo:
            ax.axis("off")
            ax.set_title(
                "INFORME FORENSE: CÓMO LA CINTA ENGAÑÓ AL AVIÓN",
                color="#FFFFFF",
                fontsize=28,
                fontweight="bold",
                pad=22,
            )
            bloques = [
                (0.18, "1. SENSOR TAPADO\n\nBloquea presión\natmosférica real", "#FF3333"),
                (0.50, "2. COMPUTADORA\n\nCongela altitud en\n9.700 pies falsos", "#FFAA00"),
                (0.82, "3. RADAR DE LIMA\n\nRecibe lectura falsa\ndel transpondedor", "#00E5FF"),
            ]
            for x, texto, col in bloques:
                bbox = dict(
                    boxstyle="round,pad=0.65",
                    facecolor="#101C2E",
                    edgecolor=col,
                    linewidth=4,
                )
                ax.text(
                    x, 0.56, texto,
                    color="#FFFFFF", fontsize=22, fontweight="bold",
                    ha="center", va="center", bbox=bbox, transform=ax.transAxes,
                )
            ax.annotate(
                "", xy=(0.35, 0.56), xytext=(0.31, 0.56),
                arrowprops=dict(facecolor="#FFFFFF", width=4),
                transform=ax.transAxes,
            )
            ax.annotate(
                "", xy=(0.67, 0.56), xytext=(0.63, 0.56),
                arrowprops=dict(facecolor="#FFFFFF", width=4),
                transform=ax.transAxes,
            )

        elif "MAPA_RUTA" in tipo:
            costa_x = [-77.05, -77.12, -77.16, -77.22, -77.27, -77.32]
            costa_y = [-12.20, -12.05, -11.90, -11.75, -11.60, -11.45]
            ax.plot(costa_x, costa_y, color="#4A7A9C", linewidth=5.0, label="COSTA DEL PERÚ")
            ax.fill_betweenx(costa_y, costa_x, -76.80, color="#142230", alpha=0.85)
            ruta_x = [-77.11, -77.28, -77.42, -77.36, -77.25]
            ruta_y = [-12.02, -12.08, -11.92, -11.76, -11.65]
            ax.plot(ruta_x, ruta_y, color="#00E5FF", linewidth=6.0, label="TRAYECTORIA VUELO 603")
            ax.scatter([-77.11], [-12.02], color="#00FF88", s=280, zorder=5)
            ax.text(-77.08, -12.04, "1. DESPEGUE LIMA (00:40 AM)", color="#00FF88", fontweight="bold", fontsize=22)
            ax.scatter([-77.25], [-11.65], color="#FF2222", s=320, marker="X", zorder=6)
            ax.text(-77.22, -11.66, "2. IMPACTO EN EL MAR (01:11 AM)", color="#FF4444", fontweight="bold", fontsize=22)
            ax.set_title("TRAYECTORIA RADAR: SALIDA DE LIMA Y GIRO AL PACÍFICO", color="#FFFFFF", fontsize=27, fontweight="bold", pad=22)
            ax.set_xlabel("LONGITUD OESTE", color="#B0C4DE", fontsize=20, fontweight="bold")
            ax.set_ylabel("LATITUD SUR", color="#B0C4DE", fontsize=20, fontweight="bold")
            ax.set_xlim(-77.52, -76.88)
            ax.set_ylim(-12.18, -11.48)
            ax.grid(True, color="#1C2D42", linestyle="--", linewidth=1.2)
            ax.tick_params(colors="#FFFFFF", labelsize=18)
            leg = ax.legend(loc="lower left", facecolor="#070B12", edgecolor="#2A3F5F", fontsize=19)
            for t in leg.get_texts():
                t.set_color("#FFFFFF")

        elif "PANEL_ALARMAS" in tipo:
            ax.axis("off")
            ax.set_title(
                "CABINA DE MANDO: CONFLICTO DE ALERTAS SIMULTÁNEAS",
                color="#FFAA00",
                fontsize=28,
                fontweight="bold",
                pad=22,
            )
            paneles = [
                (0.26, "ALARMA DE PÉRDIDA\n(STICK SHAKER)\n\nIndica velocidad\ndemasiado BAJA", "#FF3333"),
                (0.74, "EXCESO VELOCIDAD\n(OVERSPEED)\n\nIndica velocidad\ndemasiado ALTA", "#00E5FF"),
            ]
            for x, texto, col in paneles:
                bbox = dict(
                    boxstyle="round,pad=0.7",
                    facecolor="#101C2E",
                    edgecolor=col,
                    linewidth=4,
                )
                ax.text(
                    x, 0.56, texto,
                    color="#FFFFFF", fontsize=23, fontweight="bold",
                    ha="center", va="center", bbox=bbox, transform=ax.transAxes,
                )
            ax.text(0.50, 0.56, "VS", color="#FFAA00", fontsize=34, fontweight="bold", ha="center", va="center", transform=ax.transAxes)

        elif "GRAFICA_ALTITUD" in tipo:
            minutos = np.linspace(0, 31, 200)
            alt_falsa = np.piecewise(
                minutos,
                [minutos < 6, minutos >= 6],
                [lambda t: (t / 6.0) * 9700, 9700],
            )
            alt_real = np.piecewise(
                minutos,
                [minutos < 6, (minutos >= 6) & (minutos < 18), minutos >= 18],
                [
                    lambda t: (t / 6.0) * 9700,
                    lambda t: 9700 - ((t - 6.0) / 12.0) * 5200,
                    lambda t: 4500 * (1.0 - ((t - 18.0) / 13.0) ** 1.4),
                ],
            )
            ax.plot(minutos, alt_falsa, color="#FFAA00", linewidth=5.5, linestyle="--", label="LECTURA FALSA EN CABINA / RADAR (9700 PIES)")
            ax.plot(minutos, alt_real, color="#FF2A2A", linewidth=6.5, label="ALTITUD REAL DEL AVIÓN (DESCENSO AL MAR)")
            ax.fill_between(minutos, alt_real, 0, color="#FF2A2A", alpha=0.18)
            ax.scatter([31], [0], color="#FFFFFF", s=260, zorder=5)
            ax.annotate(
                "01:11 AM - IMPACTO (0 PIES)",
                xy=(30.8, 200), xytext=(15.5, 2800),
                color="#FFFFFF", fontweight="bold", fontsize=22,
                arrowprops=dict(facecolor="#FF2A2A", shrink=0.08, width=3),
            )
            ax.set_title("DATOS CAJA NEGRA (FDR): ALTITUD FALSA VS REAL", color="#FFFFFF", fontsize=27, fontweight="bold", pad=22)
            ax.set_xlabel("MINUTOS DE VUELO DESDE LIMA", color="#B0C4DE", fontsize=20, fontweight="bold", labelpad=12)
            ax.set_ylabel("ALTITUD (PIES)", color="#B0C4DE", fontsize=20, fontweight="bold", labelpad=12)
            ax.set_ylim(-600, 12500)
            ax.set_xlim(0, 34)
            ax.grid(True, color="#1C2D42", linestyle=":", linewidth=1.5)
            ax.tick_params(colors="#FFFFFF", labelsize=18)
            leg = ax.legend(loc="upper left", facecolor="#070B12", edgecolor="#2A3F5F", fontsize=19)
            for t in leg.get_texts():
                t.set_color("#FFFFFF")

        else:
            ax.axis("off")
            ax.set_title("CRONOLOGÍA OFICIAL (INFORME CIAA - 2 OCT 1996)", color="#FFFFFF", fontsize=27, fontweight="bold", pad=20)
            hitos = [
                ("00:40 AM", "DESPEGUE EN LIMA", "El Boeing 757 despega con los puertos estáticos tapados."),
                ("00:42 AM", "INSTRUMENTOS BLOQUEADOS", "Velocímetro y altímetro dejan de marcar datos reales."),
                ("00:44 AM", "EMERGENCIA DECLARADA", "Los pilotos piden vectores para regresar a Lima."),
                ("00:58 AM", "DATO FALSO (9700 PIES)", "El transpondedor envía altitud congelada al radar."),
                ("01:11 AM", "IMPACTO EN EL OCÉANO", "El ala izquierda golpea el agua tras 31 min de vuelo."),
            ]
            y_positions = [0.85, 0.67, 0.49, 0.31, 0.13]
            ax.plot([0.21, 0.21], [0.13, 0.85], color="#00E5FF", linewidth=5, transform=ax.transAxes)
            for (hora, titulo, detalle), y in zip(hitos, y_positions):
                color_punto = "#FF2A2A" if "IMPACTO" in titulo else "#FFAA00"
                ax.scatter([0.21], [y], color=color_punto, s=280, zorder=5, transform=ax.transAxes)
                ax.text(0.03, y, hora, color="#00E5FF", fontsize=22, fontweight="bold", va="center", transform=ax.transAxes)
                ax.text(0.25, y + 0.025, titulo, color="#FFFFFF", fontsize=22, fontweight="bold", va="center", transform=ax.transAxes)
                ax.text(0.25, y - 0.03
