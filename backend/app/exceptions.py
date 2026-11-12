"""
Paddy Farming Assistant - Application Exceptions
Defines structured, domain-specific exception types for request validation,
upload safety, and AI model error handling.
"""


class AppBaseException(Exception):
    """
    Base class for application exceptions with associated HTTP status code.
    """
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class EmptyFileError(AppBaseException):
    """Raised when an uploaded file contains 0 bytes."""
    def __init__(self, message: str = "Uploaded image file is empty (0 bytes)."):
        super().__init__(message, status_code=400)


class FileTooLargeError(AppBaseException):
    """Raised when an uploaded file exceeds the configured size limit (HTTP 413)."""
    def __init__(self, message: str = "Uploaded file exceeds the maximum allowed size."):
        super().__init__(message, status_code=413)


class UnsupportedFormatError(AppBaseException):
    """Raised when an uploaded file has an unsupported format or extension (HTTP 415)."""
    def __init__(self, message: str = "File format is not supported."):
        super().__init__(message, status_code=415)


class CorruptedImageError(AppBaseException):
    """Raised when a file cannot be parsed or decoded as a valid image."""
    def __init__(self, message: str = "Uploaded file is corrupted or not a valid image format."):
        super().__init__(message, status_code=400)


class ModelUnavailableError(AppBaseException):
    """Raised when the AI model checkpoint cannot be found or loaded (HTTP 503)."""
    def __init__(self, message: str = "AI Model is currently unavailable. Please check backend configuration."):
        super().__init__(message, status_code=503)


class ModelInferenceError(AppBaseException):
    """Raised when an unexpected error occurs during model forward pass (HTTP 500)."""
    def __init__(self, message: str = "An error occurred during model inference."):
        super().__init__(message, status_code=500)


class FieldNotFoundError(AppBaseException):
    """Raised when a requested field ID is not found in the master mapping (HTTP 404)."""
    def __init__(self, message: str = "Field not found in master catalog."):
        super().__init__(message, status_code=404)


class SatelliteDataUnavailableError(AppBaseException):
    """Raised when satellite sequence data is missing or corrupted (HTTP 503)."""
    def __init__(self, message: str = "Satellite time-series data is unavailable."):
        super().__init__(message, status_code=503)


# Weather Service Domain Exceptions (Step 11E)
class InvalidCoordinatesError(AppBaseException):
    """Raised when requested latitude/longitude coordinates are out of valid bounds (HTTP 400)."""
    def __init__(self, message: str = "Invalid coordinates: latitude must be between -90 and 90, and longitude between -180 and 180."):
        super().__init__(message, status_code=400)


class WeatherServiceDisabledError(AppBaseException):
    """Raised when the weather service is disabled in configuration (HTTP 503)."""
    def __init__(self, message: str = "Weather service is currently disabled in backend configuration."):
        super().__init__(message, status_code=503)


class WeatherServiceUnavailableError(AppBaseException):
    """Raised when the weather provider network connection fails, times out, or returns a 5xx error (HTTP 503)."""
    def __init__(self, message: str = "Weather service provider is currently unavailable or timed out."):
        super().__init__(message, status_code=503)


class WeatherProviderError(AppBaseException):
    """Raised when the weather provider returns an error response (HTTP 502)."""
    def __init__(self, message: str = "Weather service provider returned an error response."):
        super().__init__(message, status_code=502)


class WeatherParsingError(AppBaseException):
    """Raised when the weather provider payload is malformed or missing expected structure (HTTP 502)."""
    def __init__(self, message: str = "Failed to parse weather provider response payload."):
        super().__init__(message, status_code=502)


class InvalidForecastDaysError(AppBaseException):
    """Raised when requested forecast_days is not between 1 and 7 (HTTP 400)."""
    def __init__(self, message: str = "Invalid forecast_days: must be an integer between 1 and 7."):
        super().__init__(message, status_code=400)


class BuyerNotFoundError(AppBaseException):
    """Raised when a requested buyer identifier is not found in the directory (HTTP 404)."""
    def __init__(self, message: str = "Buyer was not found in the master directory."):
        super().__init__(message, status_code=404)


# Market Price Service Domain Exceptions (Step 11G)
class MarketServiceDisabledError(AppBaseException):
    """Raised when the market service is disabled by configuration (HTTP 503)."""
    def __init__(self, message: str = "Market price service is currently disabled in backend configuration."):
        super().__init__(message, status_code=503)


class MarketApiKeyMissingError(AppBaseException):
    """Raised when an operation requires an API key for Data.gov.in that is not configured (HTTP 503)."""
    def __init__(self, message: str = "Data.gov.in API key is not configured in backend environment."):
        super().__init__(message, status_code=503)


class MarketProviderError(AppBaseException):
    """Raised when the market data provider returns an error response (HTTP 502)."""
    def __init__(self, message: str = "Market data provider returned an error response."):
        super().__init__(message, status_code=502)


class MarketServiceUnavailableError(AppBaseException):
    """Raised when the market data provider is unreachable or times out (HTTP 503)."""
    def __init__(self, message: str = "Market data provider is currently unavailable or timed out."):
        super().__init__(message, status_code=503)


class MarketParsingError(AppBaseException):
    """Raised when the market provider response payload is malformed or invalid (HTTP 502)."""
    def __init__(self, message: str = "Failed to parse market provider response payload."):
        super().__init__(message, status_code=502)


# Security and Authentication Exceptions (STEP 1)
class AuthenticationError(AppBaseException):
    """Base class for authentication failures (HTTP 401)."""
    def __init__(self, message: str = "Authentication failed.", status_code: int = 401):
        super().__init__(message, status_code=status_code)


class TokenExpiredError(AuthenticationError):
    """Raised when an authentication JWT has expired (HTTP 401)."""
    def __init__(self, message: str = "Authentication token has expired. Please log in again."):
        super().__init__(message, status_code=401)


class InvalidTokenError(AuthenticationError):
    """Raised when an authentication JWT is invalid, malformed, or tampered (HTTP 401)."""
    def __init__(self, message: str = "Invalid or malformed authentication token."):
        super().__init__(message, status_code=401)


class SecurityConfigurationError(AppBaseException):
    """Raised when critical security configuration (e.g. JWT_SECRET_KEY) is missing or insecure (HTTP 500)."""
    def __init__(self, message: str = "Security configuration is missing or invalid."):
        super().__init__(message, status_code=500)
