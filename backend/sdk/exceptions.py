class ApiError(RuntimeError):
    """Raised when the backend API returns an unexpected response."""

    def __init__(self, status_code: int, message: str, payload: dict | None = None) -> None:
        super().__init__(f"HTTP {status_code}: {message}")
        self.status_code = status_code
        self.payload = payload or {}
