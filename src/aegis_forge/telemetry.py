from __future__ import annotations

import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

_provider = TracerProvider(resource=Resource.create({"service.name": "aegis-forge"}))
if not isinstance(trace.get_tracer_provider(), TracerProvider):
    trace.set_tracer_provider(_provider)
if os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"):
    _provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))

tracer = trace.get_tracer("aegis-forge", "0.3.0")
