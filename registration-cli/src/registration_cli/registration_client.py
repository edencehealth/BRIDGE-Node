#!/usr/bin/env python3
import logging
import requests
from datetime import datetime
from pydantic import BaseModel


logger = logging.getLogger(__name__)


class SiteRegistrationRequest(BaseModel):
    site_name: str
    public_key: str


class SiteRegistrationResponse(BaseModel):
    id: int
    site_name: str
    created_at: datetime
    created_by: str
    github_repo_name: str
    github_org_name: str


class RegistrationApiError(Exception):
    """Raised when the Registration API returns an error."""
    pass


class RegistrationClient:
    """
    Client for interacting with the Registration API.
    """

    def __init__(self, api_url,
                 oidc_token_url, oidc_client_id, oidc_client_secret,
                 timeout: int = 10):
        self.api_url = api_url.rstrip("/")
        self.oidc_token_url = oidc_token_url
        self.oidc_client_id = oidc_client_id
        self.oidc_client_secret = oidc_client_secret
        self.timeout = timeout

    def _get_jwt_access_token(self):
        token_resp = requests.post(
            self.oidc_token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": self.oidc_client_id,
                "client_secret": self.oidc_client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=self.timeout
        )
        token_resp.raise_for_status()
        return token_resp.json()["access_token"]

    def _get_headers(self):
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        access_token = self._get_jwt_access_token()
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
        return headers

    def register_site(self, site_name: str, public_key: str) -> SiteRegistrationResponse:
        payload = SiteRegistrationRequest(
            site_name=site_name,
            public_key=public_key
        ).model_dump()

        # Fetch the token/headers before the try so a token-endpoint failure is not
        # misreported as a registration-endpoint error.
        headers = self._get_headers()

        try:
            response = requests.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
        except Exception as request_exc:
            logger.error(
                "Error while calling registration endpoint",
                extra={
                    "url": self.api_url,
                    "payload": payload,
                    "exception_type": request_exc.__class__.__name__,
                    "exception": str(request_exc),
                }
            )
            raise

        if response.status_code != 201:
            logger.error(
                "Registration API error",
                extra={
                    "url": self.api_url,
                    "payload": payload,
                    "status_code": response.status_code,
                    "response_text": response.text,
                    "response_json": self._safe_json(response),
                }
            )
            raise RegistrationApiError(
                f"Error {response.status_code}: {response.text}"
            )

        return SiteRegistrationResponse(**response.json())

    @staticmethod
    def _safe_json(response):
        try:
            return response.json()
        except Exception:
            return None
