class ServerDetectionException(Exception):
    def __init__(self, msg, *, context=None):
        self.msg = str(msg)
        self.context = context or {}
        super().__init__(self.msg)

    def __str__(self):
        if not self.context:
            return self.msg
        context_text = ", ".join(
            f"{key}={value}" for key, value in self.context.items())
        return f"{self.msg} ({context_text})"
