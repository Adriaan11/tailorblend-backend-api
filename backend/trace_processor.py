"""
Custom TracingProcessor for TailorBlend AI Consultant API

Implements in-memory trace collection with live SSE streaming capabilities.
Captures full trace data from OpenAI Agents SDK for comprehensive observability.
"""

import asyncio
import time
import threading
from typing import Any, Dict, List, Optional
from datetime import datetime
from collections import defaultdict

from agents.tracing.processor_interface import TracingProcessor
from agents.tracing.traces import Trace
from agents.tracing.spans import Span


class InMemoryTraceProcessor(TracingProcessor):
    """
    Custom tracing processor that stores traces in memory and broadcasts updates.

    Features:
    - Stores full trace/span data per session
    - Circular buffer (max 10 traces per session)
    - Thread-safe operations
    - Async broadcasting for SSE streaming
    - Auto-cleanup on session reset
    """

    def __init__(self):
        self._lock = threading.Lock()

        # Storage: session_id -> list of completed traces
        self._traces: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

        # Active traces being built: trace_id -> trace data
        self._active_traces: Dict[str, Dict[str, Any]] = {}

        # Active spans being built: span_id -> span data
        self._active_spans: Dict[str, Dict[str, Any]] = {}

        # Broadcast channels for SSE: session_id -> asyncio.Queue
        self._broadcast_queues: Dict[str, List[asyncio.Queue]] = defaultdict(list)

        # Session ID tracking: trace_id -> session_id
        self._trace_sessions: Dict[str, str] = {}

        # Maximum traces per session (circular buffer)
        self._max_traces_per_session = 10

    def set_session_id(self, trace_id: str, session_id: str) -> None:
        """Associate a trace with a session ID."""
        with self._lock:
            self._trace_sessions[trace_id] = session_id

    def on_trace_start(self, trace: Trace) -> None:
        """Called when a trace begins."""
        with self._lock:
            trace_data = {
                "trace_id": trace.trace_id,
                "name": trace.name or "Unknown Workflow",
                "started_at": datetime.utcnow().isoformat() + "Z",
                "ended_at": None,
                "duration_ms": None,
                "spans": [],
                "metadata": trace.metadata or {}
            }
            self._active_traces[trace.trace_id] = trace_data

    def on_trace_end(self, trace: Trace) -> None:
        """Called when a trace completes."""
        with self._lock:
            if trace.trace_id not in self._active_traces:
                return

            trace_data = self._active_traces[trace.trace_id]
            trace_data["ended_at"] = datetime.utcnow().isoformat() + "Z"

            # Calculate duration
            if trace_data["started_at"] and trace_data["ended_at"]:
                start = datetime.fromisoformat(trace_data["started_at"].replace("Z", "+00:00"))
                end = datetime.fromisoformat(trace_data["ended_at"].replace("Z", "+00:00"))
                trace_data["duration_ms"] = int((end - start).total_seconds() * 1000)

            # Get session ID
            session_id = self._trace_sessions.get(trace.trace_id, "unknown")

            # Store in session traces (circular buffer)
            self._traces[session_id].append(trace_data)
            if len(self._traces[session_id]) > self._max_traces_per_session:
                self._traces[session_id].pop(0)  # Remove oldest

            # Broadcast to SSE subscribers (non-blocking)
            self._broadcast_trace_update(session_id, trace_data)

            # Cleanup
            del self._active_traces[trace.trace_id]
            if trace.trace_id in self._trace_sessions:
                del self._trace_sessions[trace.trace_id]

    def on_span_start(self, span: Span[Any]) -> None:
        """Called when a span begins."""
        with self._lock:
            span_data = {
                "span_id": span.span_id,
                "trace_id": span.trace_id,
                "parent_id": getattr(span, "parent_id", None),
                "type": self._get_span_type(span),
                "name": self._get_span_name(span),
                "started_at": datetime.utcnow().isoformat() + "Z",
                "ended_at": None,
                "duration_ms": None,
                "data": {}
            }
            self._active_spans[span.span_id] = span_data

    def on_span_end(self, span: Span[Any]) -> None:
        """Called when a span completes."""
        with self._lock:
            if span.span_id not in self._active_spans:
                return

            span_data = self._active_spans[span.span_id]
            span_data["ended_at"] = datetime.utcnow().isoformat() + "Z"

            # Calculate duration
            if span_data["started_at"] and span_data["ended_at"]:
                start = datetime.fromisoformat(span_data["started_at"].replace("Z", "+00:00"))
                end = datetime.fromisoformat(span_data["ended_at"].replace("Z", "+00:00"))
                span_data["duration_ms"] = int((end - start).total_seconds() * 1000)

            # Extract span-specific data
            span_data["data"] = self._extract_span_data(span)

            # Add to parent trace
            if span.trace_id in self._active_traces:
                self._active_traces[span.trace_id]["spans"].append(span_data)

            # Cleanup
            del self._active_spans[span.span_id]

    def _get_span_type(self, span: Span[Any]) -> str:
        """Extract span type from span data."""
        span_export = span.export()
        if not span_export:
            return "unknown"

        span_data = span_export.get("span_data", {})
        return span_data.get("type", "unknown")

    def _get_span_name(self, span: Span[Any]) -> str:
        """Extract span name from span data."""
        span_export = span.export()
        if not span_export:
            return "Unknown Operation"

        span_data = span_export.get("span_data", {})
        return span_data.get("name", "Unknown Operation")

    def _extract_span_data(self, span: Span[Any]) -> Dict[str, Any]:
        """Extract detailed data from a span."""
        span_export = span.export()
        if not span_export:
            return {}

        span_data = span_export.get("span_data", {})
        span_type = span_data.get("type", "unknown")

        result = {"type": span_type}

        # Extract type-specific data
        if span_type == "generation":
            result.update({
                "model": span_data.get("model"),
                "input": span_data.get("input"),
                "output": span_data.get("output"),
                "usage": span_data.get("usage")
            })
        elif span_type == "function":
            result.update({
                "name": span_data.get("name"),
                "input": span_data.get("input"),
                "output": span_data.get("output"),
                "mcp_data": span_data.get("mcp_data")
            })
        elif span_type == "agent":
            result.update({
                "name": span_data.get("name"),
                "handoffs": span_data.get("handoffs"),
                "tools": span_data.get("tools"),
                "output_type": span_data.get("output_type")
            })

        return result

    def _broadcast_trace_update(self, session_id: str, trace_data: Dict[str, Any]) -> None:
        """Broadcast trace update to all SSE subscribers (non-blocking)."""
        if session_id not in self._broadcast_queues:
            return

        # Put trace in all active queues for this session
        for queue in self._broadcast_queues[session_id]:
            try:
                queue.put_nowait(trace_data)
            except asyncio.QueueFull:
                # Drop if queue full (slow client)
                pass

    def get_traces(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all traces for a session."""
        with self._lock:
            return list(self._traces.get(session_id, []))

    def clear_session(self, session_id: str) -> None:
        """Clear all traces for a session."""
        with self._lock:
            if session_id in self._traces:
                del self._traces[session_id]

    async def subscribe_to_traces(self, session_id: str) -> asyncio.Queue:
        """
        Subscribe to trace updates for a session (for SSE streaming).

        Returns an asyncio.Queue that receives trace updates.
        """
        queue = asyncio.Queue(maxsize=100)

        with self._lock:
            self._broadcast_queues[session_id].append(queue)

        return queue

    def unsubscribe_from_traces(self, session_id: str, queue: asyncio.Queue) -> None:
        """Unsubscribe from trace updates."""
        with self._lock:
            if session_id in self._broadcast_queues:
                try:
                    self._broadcast_queues[session_id].remove(queue)
                except ValueError:
                    pass  # Already removed

    def shutdown(self) -> None:
        """Clean shutdown."""
        with self._lock:
            self._traces.clear()
            self._active_traces.clear()
            self._active_spans.clear()
            self._broadcast_queues.clear()
            self._trace_sessions.clear()

    def force_flush(self) -> None:
        """Force flush (no-op for in-memory storage)."""
        pass


# Global singleton instance
trace_processor = InMemoryTraceProcessor()
