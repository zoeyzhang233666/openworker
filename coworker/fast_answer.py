"""Small fast-answer safeguards; no extra model or network calls."""
from threading import Lock


class AnswerTextFilter:
    """Hide protocol markup even when a no-tool provider emits split markers."""
    markers = ("<｜｜DSML｜｜", "<tool_call>", "<function=", "<invoke ")

    def __init__(self):
        self.pending = ""
        self.blocked = False

    def feed(self, text):
        if self.blocked:
            return ""
        self.pending += text
        starts = [self.pending.find(m) for m in self.markers if m in self.pending]
        if starts:
            visible = self.pending[:min(starts)]
            self.pending = ""
            self.blocked = True
            return visible
        hold = max((n for m in self.markers for n in range(1, len(m))
                    if self.pending.endswith(m[:n])), default=0)
        text, self.pending = (self.pending[:-hold], self.pending[-hold:]) if hold else (self.pending, "")
        return text

    def finish(self):
        text, self.pending = self.pending, ""
        return text if not self.blocked else ""


class FastWebBudget:
    """Bound actual web attempts, including concurrent batches, after authorization."""
    limits = {"web_search": 2, "web_fetch": 3}

    def __init__(self):
        self.lock = Lock()

    def acquire(self, runtime, name):
        if name not in self.limits:
            return True
        with self.lock:
            counts = runtime.setdefault("fast_web_calls", {})
            used = counts.get(name, 0)
            if used >= self.limits[name]:
                runtime["fast_synthesize"] = True
                return False
            counts[name] = used + 1
            return True
