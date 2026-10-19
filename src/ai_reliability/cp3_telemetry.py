"""Local-only genuine OpenTelemetry SDK spans; never configures OTLP/network export."""
from __future__ import annotations
from contextlib import contextmanager
from typing import Any, Iterator
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.sdk.resources import Resource

@contextmanager
def local_tracing() -> Iterator[tuple[Any,InMemorySpanExporter]]:
    exporter=InMemorySpanExporter()
    provider=TracerProvider(resource=Resource.create({'service.name':'project16-cp3-offline-local'}))
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    try:
        yield provider.get_tracer('ai_reliability.cp3', '1.0'),exporter
    finally:
        provider.shutdown()


def sanitized_spans(exporter: InMemorySpanExporter)->list[dict[str,Any]]:
    """Export metadata only; deny any raw payload, prompt, token, or response text."""
    accepted={'case_id','event_type','fault_kind','observed_status','modeled_latency_ms','attempt'}
    rows=[]
    for span in exporter.get_finished_spans():
        attrs={k:v for k,v in span.attributes.items() if k in accepted}
        rows.append({'name':span.name,'trace_id':format(span.context.trace_id,'032x'),
                     'span_id':format(span.context.span_id,'016x'),
                     'parent_span_id':format(span.parent.span_id,'016x') if span.parent else None,
                     'attributes':attrs,'timing_source':'REAL_LOCAL_INSTRUMENTATION',
                     'network_exported':False})
    return rows
