"""
Standardized JSON response handling for a FastAPI application.

This module defines a `ResponseHandler` class that provides static methods for
generating consistent JSON responses and HTTP exceptions for the FastAPI
application. It includes methods for handling successful responses, resource
creation, client errors (400, 401, 409, 422), and server errors (500).

Key Components:
- `success`: Returns an HTTP 200 JSON response for successful operations.
- `created`: Returns an HTTP 201 JSON response for successful resource creation.
- `bad_request`: Returns an HTTP 400 exception for bad requests.
- `unauthorized`: Returns an HTTP 401 exception for unauthorized access.
- `conflict`: Returns an HTTP 409 exception for conflicts.
- `unprocessable_entity`: Returns an HTTP 422 exception for unprocessable entities.
- `internal_error`: Returns an HTTP 500 exception for internal server errors.

Usage:
- Import the `response_handler` instance from this module and use its methods
  to return standardized JSON responses or raise HTTP exceptions in your
  FastAPI routes and middleware.

Dependencies:
- `fastapi`: For handling HTTP exceptions and JSON responses.
- `starlette.status`: For standard HTTP status codes.
"""

from fastapi.responses import JSONResponse
from fastapi import HTTPException, status


class ResponseHandler:
    """
    Class to handle standardized JSON responses for the FastAPI application.
    """

    @staticmethod
    def success(
        data, msg: str = "Success", internal_code: int = 1, status_code: int = 200
    ) -> JSONResponse:
        """
        Response for a successful operation (HTTP 200).

        Args:
            data (any): Data to be returned in the response.
            msg (str): Message describing the success.
            internal_code (int): Internal application code indicating success.
            status_code (int): HTTP status code.

        Returns:
            JSONResponse: HTTP 200 JSON response.
        """
        return JSONResponse(
            {"status": {"msg": msg, "rc": internal_code}, "data": data},
            status_code=status_code,
        )

    @staticmethod
    def created(
        data, msg: str = "Created successfully", internal_code: int = 2
    ) -> JSONResponse:
        """
        Response for a resource creation (HTTP 201).

        Args:
            data (any): Data to be returned in the response.
            msg (str): Message describing the creation.
            internal_code (int): Internal application code indicating creation success.

        Returns:
            JSONResponse: HTTP 201 JSON response.
        """
        return ResponseHandler.success(data, msg, internal_code, status_code=201)

    @staticmethod
    def bad_request(
        msg: str = "Bad request", internal_code: int = 400
    ) -> HTTPException:
        """
        Response for a bad request (HTTP 400).

        Args:
            msg (str): Message describing the error.
            internal_code (int): Internal application code indicating the error.

        Returns:
            JSONResponse: HTTP 400 JSON response.
        """
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

    @staticmethod
    def unauthorized(
        msg: str = "Unauthorized", internal_code: int = 401
    ) -> HTTPException:
        """
        Response for a unautorized request (HTTP 401).

        Args:
            msg (str): Message describing the error.
            internal_code (int): Internal application code indicating the error.

        Returns:
            JSONResponse: HTTP 401 JSON response.
        """
        return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=msg)

    @staticmethod
    def not_found(detail: str = "Resource not found") -> HTTPException:
        """
        Response for a resource not found (HTTP 404).

        Args:
            detail (str): Message detailing the error.

        Returns:
            HTTPException: HTTP 404 JSON response.
        """
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

    @staticmethod
    def conflict(msg: str = "Conflict", internal_code: int = 409) -> HTTPException:
        """
        Response for a conflict (HTTP 409).

        Args:
            msg (str): Message describing the conflict.
            internal_code (int): Internal application code indicating the conflict.

        Returns:
            JSONResponse: HTTP 409 JSON response.
        """
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=msg)

    @staticmethod
    def unprocessable_entity(detail: str = "Unprocessable entity") -> HTTPException:
        """
        Response for an unprocessable entity (HTTP 422).

        Args:
            detail (str): Message detailing the error.

        Returns:
            JSONResponse: HTTP 422 JSON response.
        """
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail
        )

    @staticmethod
    def internal_error(
        msg: str = "Internal server error", internal_code: int = 500
    ) -> HTTPException:
        """
        Response for an internal server error (HTTP 500).

        Args:
            msg (str): Message describing the error.
            internal_code (int): Internal application code indicating the error.

        Returns:
            JSONResponse: HTTP 500 JSON response.
        """
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=msg
        )


response_handler = ResponseHandler()
