"""Errors the chat channels turn into user-facing messages."""


class UpstreamError(Exception):
    """The model provider could not produce an answer."""


class UpstreamUnavailable(UpstreamError):
    """The connection to the provider kept failing or dropping."""


class UpstreamTimeout(UpstreamError):
    """The provider stopped sending data before the answer was complete."""
