class DocumentValidationError(ValueError):
    """Raised when an uploaded document fails validation."""


class DocumentTooLargeError(DocumentValidationError):
    """Raised when an uploaded document exceeds the configured size limit."""


class DocumentExtractionError(ValueError):
    """Raised when an uploaded document cannot be extracted safely."""
