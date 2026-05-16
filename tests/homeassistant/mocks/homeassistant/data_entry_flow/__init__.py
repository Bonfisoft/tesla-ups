"""Mock Home Assistant data_entry_flow module."""


class FlowResult:
    """Mock FlowResult type."""
    pass


class AbortFlow(Exception):
    """Mock AbortFlow exception."""
    
    def __init__(self, reason):
        self.reason = reason
        super().__init__(f"Flow aborted: {reason}")
