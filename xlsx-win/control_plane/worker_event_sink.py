"""Sequential WorkerEvent-compatible output for pre-native composite work."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


class WorkerEventSink:
    def __init__(self, events_path: Path, *, run_id: str, report_every: int = 1000) -> None:
        if report_every <= 0:
            raise ValueError("report_every must be positive")
        events_path.parent.mkdir(parents=True, exist_ok=True)
        self._run_id = run_id
        self._report_every = report_every
        self._stream = events_path.open("w", encoding="utf-8", newline="\n")

    def start(self, rows_total: int) -> None:
        self._emit(0, rows_total)

    def row_written(self, rows_done: int, rows_total: int) -> None:
        if rows_done == 1 or rows_done % self._report_every == 0 or rows_done == rows_total:
            self._emit(rows_done, rows_total)

    def _emit(self, rows_done: int, rows_total: int) -> None:
        event = {
            "run_id": self._run_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "phase": "APPLYING_EDITS",
            "message": "Streamed source rows into the intermediate worksheet.",
            "rows_done": rows_done,
            "rows_total": rows_total,
        }
        self._stream.write(json.dumps(event, separators=(",", ":"), ensure_ascii=False) + "\n")
        self._stream.flush()

    def __enter__(self) -> WorkerEventSink:
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self._stream.close()
