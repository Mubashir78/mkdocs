#!/usr/bin/env python
"""Tests for SIGTERM handling in the serve command.

https://github.com/mkdocs/mkdocs/pull/4162
"""

import signal
import threading
import unittest
from unittest import mock

from mkdocs.commands import serve as serve_module


class SigtermHandlerTests(unittest.TestCase):
    def setUp(self):
        self._saved = signal.getsignal(signal.SIGTERM)
        self.addCleanup(signal.signal, signal.SIGTERM, self._saved)

    def test_registering_from_a_worker_thread_does_not_raise(self):
        """signal.signal() only works on the main thread, so serve() must
        not attempt to register a handler from another thread."""

        def worker():
            serve_module._register_sigterm_handler()

        thread = threading.Thread(target=worker)
        raised = []
        original = threading.excepthook

        def hook(args):
            raised.append(args.exc_value)

        threading.excepthook = hook
        try:
            thread.start()
            thread.join()
        finally:
            threading.excepthook = original

        self.assertEqual(
            raised, [],
            "registration from a worker thread must not raise",
        )
        self.assertEqual(
            signal.getsignal(signal.SIGTERM), self._saved,
            "the existing handler must be left untouched from a worker thread",
        )

    def test_previous_handler_is_restored(self):
        """A handler installed by serve() must be replaced by whatever was
        there before, not by SIG_DFL."""
        sentinel = mock.Mock()
        signal.signal(signal.SIGTERM, sentinel)

        previous = serve_module._register_sigterm_handler()
        serve_module._restore_sigterm_handler(previous)

        self.assertIs(signal.getsignal(signal.SIGTERM), sentinel)
        self.assertIs(signal.getsignal(signal.SIGTERM), previous)


if __name__ == '__main__':
    unittest.main()
