# -*- coding: utf-8 -*-
"""
Background task helper for the Tk UI.

Tkinter is single threaded: any DB query or AI call made directly from a button
handler freezes the window until it finishes. This module runs such work on a
worker thread and delivers the outcome back on the Tk thread.

Usage:
    run_bg(self, work, on_success, on_error)
"""

import threading
import customtkinter as ctk
from typing import Any, Callable, Optional


class _Result:
    """Carrier for a worker outcome"""

    __slots__ = ("value", "error")

    def __init__(self, value: Any = None, error: Optional[BaseException] = None):
        self.value = value
        self.error = error


def run_bg(widget: ctk.CTkBaseClass,
           work: Callable[[], Any],
           on_success: Optional[Callable[[Any], None]] = None,
           on_error: Optional[Callable[[BaseException], None]] = None,
           busy_callback: Optional[Callable[[bool], None]] = None) -> threading.Thread:
    """
    Run `work` off the Tk thread and deliver the result on the Tk thread.

    work:            zero-argument callable doing DB/AI work
    on_success:      called with work()'s return value, on the Tk thread
    on_error:        called with the exception, on the Tk thread
    busy_callback:   called with True before starting and False when finished
    """
    if busy_callback:
        busy_callback(True)

    def target():
        result = _Result()
        try:
            result.value = work()
        except BaseException as e:  # noqa: BLE001 - reported to the caller
            result.error = e

        def deliver():
            if busy_callback:
                busy_callback(False)
            if result.error is not None:
                if on_error:
                    on_error(result.error)
                elif on_success:
                    on_success(None)
            elif on_success:
                on_success(result.value)

        # after() is the only safe way to touch widgets from a worker
        try:
            widget.after(0, deliver)
        except Exception:
            # window already destroyed - nothing to update
            pass

    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    return thread