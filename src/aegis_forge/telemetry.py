from __future__ import annotations

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider

_provider = TracerProvider(resource=Resource.create({"service.name": "aegis-forge"}))
if not isinstance(trace.get_tracer_provider(), TracerProvider):
    trace.set_tracer_provider(_provider)

tracer = trace.get_tracer("aegis-forge", "0.3.0")
