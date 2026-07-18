from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class FigurePanel(BaseModel):
    model_config = ConfigDict(extra='ignore')

    label: str = ''
    description: str = ''
    location: str = ''


class FigureAxes(BaseModel):
    model_config = ConfigDict(extra='ignore')

    x: str = ''
    y: str = ''
    units: list[str] = Field(default_factory=list)


class BlotLane(BaseModel):
    model_config = ConfigDict(extra='ignore')

    panel: str = ''
    lane: str = ''
    label: str = ''
    observation: str = ''


class VisionAnalysis(BaseModel):
    """Validated, storage-safe form of a model-generated figure analysis."""

    model_config = ConfigDict(extra='ignore')

    ocr: list[str] = Field(default_factory=list)
    caption: str = ''
    figure_type: Literal[
        'western_blot',
        'gel',
        'plot',
        'microscopy',
        'diagram',
        'table',
        'photo',
        'other',
    ] = 'other'
    panels: list[FigurePanel] = Field(default_factory=list)
    axes: FigureAxes = Field(default_factory=FigureAxes)
    trends: list[str] = Field(default_factory=list)
    blot_lanes: list[BlotLane] = Field(default_factory=list)
    labels: list[str] = Field(default_factory=list)
    scientific_interpretation: str = ''
    uncertainties: list[str] = Field(default_factory=list)

    @field_validator('ocr', 'trends', 'labels', 'uncertainties', mode='before')
    @classmethod
    def normalize_text_lists(cls, value: Any) -> Any:
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        return value

    @field_validator('panels', 'blot_lanes', mode='before')
    @classmethod
    def normalize_object_lists(cls, value: Any) -> Any:
        if value is None:
            return []
        if isinstance(value, dict):
            return [value]
        return value
