from typing import Protocol


class TrackingProvider(Protocol):
    async def get_tracking_status(self, tracking_number: str):
        """Return a provider-specific tracking result when an integration is configured."""
        raise NotImplementedError
