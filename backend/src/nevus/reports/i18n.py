# SPDX-License-Identifier: AGPL-3.0-only
"""Report wording in English and Spanish, and the number and date formats of each language."""

from __future__ import annotations

import json
from datetime import date, datetime
from functools import cache
from importlib.resources import files

LANGUAGES = ("en", "es")
NBSP = "\u00a0"

TEXT: dict[str, dict[str, str]] = {
    "en": {
        "lesion_title": "Skin mark record",
        "visit_report_title": "Prepared for an appointment",
        "appointment_title": "Appointment on {date}",
        "visit_marks": "The marks prepared for this appointment; their records follow the summary:",
        "visit_no_marks": "No mark needed a new photo for this appointment.",
        "profile_title": "Skin marks: summary",
        "person": "Person",
        "born": "born {year}",
        "generated": "Generated on {date}",
        "page": "Page {page} of {pages}",
        "intended_use_title": "About this document",
        "intended_use": "A personal record of photographs and measurements, made by the person or their "
        "family with neVus. It documents what was photographed and measured, and when. It does not diagnose "
        "or assess any condition, and nothing in it is a recommendation: interpretation is for the clinician.",
        "mark": "Mark",
        "location": "Location",
        "type": "Type",
        "type_mole": "Mole",
        "type_other": "Other mark",
        "status": "Status",
        "status_active": "Active",
        "status_removed": "Removed",
        "status_resolved": "Resolved",
        "first_noticed": "First noticed",
        "interval": "Photographed every",
        "days": "{n} days",
        "front": "front",
        "back": "back",
        "head": "head",
        "unknown": "not recorded",
        "measured_title": "Measured values",
        "measured_intro": "Sizes measured on the photographs, each with its standard uncertainty (±). A difference "
        "is called a measured change only when it is larger than twice the combined uncertainty of the two "
        "measurements; otherwise it is reported as no detectable change.",
        "chart_title": "Longest diameter at each visit",
        "chart_band": "The shaded band is ± one standard uncertainty.",
        "date": "Date",
        "longest": "Longest",
        "across": "Across",
        "area": "Area",
        "scale": "Scale",
        "tilt": "Tilt",
        "change": "Change",
        "measured_change": "measured change",
        "no_detectable_change": "no detectable change",
        "no_measurements": "No measurements were made on these photographs.",
        "scale_card": "reference card",
        "scale_coin": "coin",
        "scale_manual": "known length",
        "flag_tilted": "photo tilted beyond the limit",
        "flag_unverified_card": "card print size not verified",
        "flag_tilt_unknown": "tilt unknown",
        "visits_title": "Visits",
        "no_visits": "No photo of this mark has been taken yet.",
        "visit": "Visit of {date}",
        "photos": "Photographs",
        "role_close_up": "close-up",
        "role_with_reference": "with the reference card",
        "role_overview": "overview",
        "role_other": "other",
        "scale_bar": "{n} mm",
        "measured_outline": "The outline drawn on the photograph is the one measured.",
        "person_notes": "The person's notes",
        "symptoms": "Reported by the person",
        "symptom_itching": "itching",
        "symptom_bleeding": "bleeding",
        "symptom_pain": "pain",
        "symptom_looks_different": "looks different to them",
        "no_notes": "No notes for this visit.",
        "checks_title": "Automatic photo checks",
        "checks_intro": "Checks of the photographs themselves (focus, light, reference card), made by the "
        "software when each photo was saved. They describe the photo, not the skin.",
        "check_blurry": "blurry",
        "check_too_dark": "too dark",
        "check_too_bright": "overexposed",
        "check_glare": "glare",
        "check_low_resolution": "low resolution",
        "check_tilted": "card tilted",
        "check_card_small": "card far away",
        "checks_none": "No photo was flagged.",
        "methods_title": "Methods",
        "methods_scale": "Scale from: {kinds}.",
        "methods_uncertainty": "Each uncertainty combines the error of the scale used (fit to the reference, "
        "print size check, camera tilt) with the uncertainty of the traced border, propagated to the diameters "
        "and the area.",
        "methods_analyzers": "Software: neVus {version}; analyzers {analyzers}.",
        "clinician_title": "For the clinician",
        "clinician_hint": "Space for your notes.",
        "summary_marks": "Marks being followed",
        "summary_number": "No.",
        "summary_last_visit": "Last photo",
        "summary_next": "Next photo",
        "summary_latest": "Latest size",
        "due_now": "due",
        "overdue": "overdue",
        "snoozed": "postponed",
        "not_followed": "not followed",
        "highlights_title": "Measured changes",
        "highlights_intro": "Marks whose latest two measurements differ by more than twice their combined "
        "uncertainty. This is a statement about the measurements only.",
        "highlights_none": "No measured change between the latest two measurements of any mark.",
        "since": "since {date}",
        "map_title": "Body map",
        "no_marks": "No marks have been recorded for this person.",
        "data_attached": "The data behind this report is attached to the PDF as nevus-report-data.json.",
    },
    "es": {
        "lesion_title": "Registro de una marca de la piel",
        "visit_report_title": "Preparado para una cita",
        "appointment_title": "Cita del {date}",
        "visit_marks": "Las marcas preparadas para esta cita; su registro sigue al resumen:",
        "visit_no_marks": "Ninguna marca necesitaba una foto nueva para esta cita.",
        "profile_title": "Marcas de la piel: resumen",
        "person": "Persona",
        "born": "año de nacimiento {year}",
        "generated": "Generado el {date}",
        "page": "Página {page} de {pages}",
        "intended_use_title": "Sobre este documento",
        "intended_use": "Un registro personal de fotografías y medidas, hecho por la persona o su familia con "
        "neVus. Documenta qué se fotografió y midió, y cuándo. No diagnostica ni evalúa ninguna afección, y nada "
        "de lo que contiene es una recomendación: la interpretación corresponde al profesional sanitario.",
        "mark": "Marca",
        "location": "Ubicación",
        "type": "Tipo",
        "type_mole": "Lunar",
        "type_other": "Otra marca",
        "status": "Estado",
        "status_active": "Activa",
        "status_removed": "Extirpada",
        "status_resolved": "Resuelta",
        "first_noticed": "Vista por primera vez",
        "interval": "Se fotografía cada",
        "days": "{n} días",
        "front": "delante",
        "back": "detrás",
        "head": "cabeza",
        "unknown": "sin registrar",
        "measured_title": "Valores medidos",
        "measured_intro": "Tamaños medidos sobre las fotografías, cada uno con su incertidumbre típica (±). Una "
        "diferencia se llama cambio medido solo cuando supera el doble de la incertidumbre combinada de las dos "
        "medidas; si no, se indica como sin cambio detectable.",
        "chart_title": "Diámetro mayor en cada visita",
        "chart_band": "La banda sombreada es ± una incertidumbre típica.",
        "date": "Fecha",
        "longest": "Mayor",
        "across": "Transversal",
        "area": "Área",
        "scale": "Escala",
        "tilt": "Inclinación",
        "change": "Cambio",
        "measured_change": "cambio medido",
        "no_detectable_change": "sin cambio detectable",
        "no_measurements": "No se hicieron medidas sobre estas fotografías.",
        "scale_card": "tarjeta de referencia",
        "scale_coin": "moneda",
        "scale_manual": "longitud conocida",
        "flag_tilted": "foto inclinada más allá del límite",
        "flag_unverified_card": "tamaño de impresión de la tarjeta sin verificar",
        "flag_tilt_unknown": "inclinación desconocida",
        "visits_title": "Visitas",
        "no_visits": "Todavía no hay ninguna foto de esta marca.",
        "visit": "Visita del {date}",
        "photos": "Fotografías",
        "role_close_up": "primer plano",
        "role_with_reference": "con la tarjeta de referencia",
        "role_overview": "vista general",
        "role_other": "otra",
        "scale_bar": "{n} mm",
        "measured_outline": "El contorno dibujado sobre la fotografía es el que se midió.",
        "person_notes": "Notas de la persona",
        "symptoms": "Lo que indica la persona",
        "symptom_itching": "picor",
        "symptom_bleeding": "sangrado",
        "symptom_pain": "dolor",
        "symptom_looks_different": "le parece distinta",
        "no_notes": "Sin notas en esta visita.",
        "checks_title": "Comprobaciones automáticas de las fotos",
        "checks_intro": "Comprobaciones de las propias fotografías (enfoque, luz, tarjeta de referencia), hechas "
        "por el programa al guardar cada foto. Describen la foto, no la piel.",
        "check_blurry": "desenfocada",
        "check_too_dark": "demasiado oscura",
        "check_too_bright": "sobreexpuesta",
        "check_glare": "reflejos",
        "check_low_resolution": "baja resolución",
        "check_tilted": "tarjeta inclinada",
        "check_card_small": "tarjeta lejana",
        "checks_none": "Ninguna foto tiene avisos.",
        "methods_title": "Métodos",
        "methods_scale": "Escala obtenida de: {kinds}.",
        "methods_uncertainty": "Cada incertidumbre combina el error de la escala usada (ajuste a la referencia, "
        "comprobación del tamaño de impresión, inclinación de la cámara) con la del borde trazado, propagadas a "
        "los diámetros y al área.",
        "methods_analyzers": "Programa: neVus {version}; analizadores {analyzers}.",
        "clinician_title": "Para el profesional sanitario",
        "clinician_hint": "Espacio para sus notas.",
        "summary_marks": "Marcas en seguimiento",
        "summary_number": "N.º",
        "summary_last_visit": "Última foto",
        "summary_next": "Próxima foto",
        "summary_latest": "Último tamaño",
        "due_now": "toca",
        "overdue": "con retraso",
        "snoozed": "aplazada",
        "not_followed": "sin seguimiento",
        "highlights_title": "Cambios medidos",
        "highlights_intro": "Marcas cuyas dos últimas medidas difieren en más del doble de su incertidumbre "
        "combinada. Es una afirmación solo sobre las medidas.",
        "highlights_none": "Ninguna marca tiene un cambio medido entre sus dos últimas medidas.",
        "since": "desde el {date}",
        "map_title": "Mapa corporal",
        "no_marks": "No hay marcas registradas para esta persona.",
        "data_attached": "Los datos de este informe van adjuntos al PDF como nevus-report-data.json.",
    },
}

MONTHS = {
    "en": [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ],
    "es": [
        "enero",
        "febrero",
        "marzo",
        "abril",
        "mayo",
        "junio",
        "julio",
        "agosto",
        "septiembre",
        "octubre",
        "noviembre",
        "diciembre",
    ],
}


class Words:
    """The catalogue and formats of one language, as handed to the templates."""

    def __init__(self, language: str) -> None:
        self.language = language if language in LANGUAGES else "en"
        self.text = TEXT[self.language]

    def __call__(self, key: str, **values: object) -> str:
        return self.text[key].format(**values)

    def number(self, value: float, digits: int = 1, sign: bool = False) -> str:
        text = f"{value:+.{digits}f}" if sign else f"{value:.{digits}f}"
        if text.startswith("-"):
            text = "\u2212" + text[1:]  # a real minus sign
        return text.replace(".", ",") if self.language == "es" else text

    def mm(self, value: float, sigma: float | None = None, sign: bool = False) -> str:
        if sigma is None:
            return f"{self.number(value, sign=sign)}{NBSP}mm"
        return f"{self.number(value, sign=sign)}{NBSP}±{NBSP}{self.number(max(sigma, 0.1))}{NBSP}mm"

    def area(self, value: float, sigma: float | None = None) -> str:
        if sigma is None:
            return f"{self.number(value)}{NBSP}mm²"
        return f"{self.number(value)}{NBSP}±{NBSP}{self.number(max(sigma, 0.1))}{NBSP}mm²"

    def percent(self, fraction: float) -> str:
        return f"{self.number(fraction * 100, 1)}{NBSP}%"

    def day(self, value: date | datetime | None) -> str:
        if value is None:
            return self("unknown")
        month = MONTHS[self.language][value.month - 1]
        if self.language == "es":
            return f"{value.day} de {month} de {value.year}"
        return f"{value.day} {month} {value.year}"

    def short_day(self, value: date | datetime) -> str:
        month = MONTHS[self.language][value.month - 1][:3]
        return f"{value.day}{NBSP}{month}{NBSP}{value.year}"

    def zone(self, code: str) -> str:
        return zone_names()[self.language].get(code, code)


@cache
def zone_names() -> dict[str, dict[str, str]]:
    """The interface's zone names, copied here so reports do not depend on the frontend (a test keeps them equal)."""
    raw = files("nevus.reports").joinpath("zone_names.json").read_text(encoding="utf-8")
    data: dict[str, dict[str, str]] = json.loads(raw)
    return data
