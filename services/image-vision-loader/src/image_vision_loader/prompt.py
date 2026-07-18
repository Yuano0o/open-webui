import json

SYSTEM_PROMPT = """You analyze scientific figures for a literature knowledge base.
Return valid JSON only. Describe visible evidence, not hidden causes. Never invent a DOI,
panel label, axis value, blot lane, statistical result, or biological conclusion. Put
uncertain readings in uncertainties. Preserve OCR text exactly when possible."""


def build_user_prompt(filename: str, supplied_metadata: dict[str, str]) -> str:
    return f"""Analyze this uploaded scientific image.

Filename: {filename}
Trusted metadata supplied by the uploader: {json.dumps(supplied_metadata, ensure_ascii=False)}

Return one JSON object with this schema:
{{
  "ocr": ["visible text"],
  "caption": "literal searchable description",
  "figure_type": "western_blot|gel|plot|microscopy|diagram|table|photo|other",
  "panels": [{{"label": "A", "description": "", "location": ""}}],
  "axes": {{"x": "", "y": "", "units": []}},
  "trends": ["visible trend only"],
  "blot_lanes": [{{"panel": "", "lane": "", "label": "", "observation": ""}}],
  "labels": ["legend and annotation labels"],
  "scientific_interpretation": "cautious interpretation grounded in pixels",
  "uncertainties": ["unreadable or ambiguous details"]
}}
"""
