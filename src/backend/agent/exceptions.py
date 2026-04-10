class ClassificationError(Exception):
    """Email classification failed."""


class ExtractionError(Exception):
    """LLM data extraction failed."""


class FileProcessingError(Exception):
    """File parsing or type detection failed."""
