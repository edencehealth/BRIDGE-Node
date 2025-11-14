#!/usr/bin/env python3
import logging
import sys
import platform
import socket
import requests
import uuid
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
        )
        token_resp.raise_for_status()
        access_token = token_resp.json()["access_token"]
        return access_token

    def _get_headers(self):
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        access_token = self._get_jwt_access_token()
        logger.info(f"Access token: {access_token}")
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
        return headers

    def register_site(self, site_name: str, public_key: str) -> SiteRegistrationResponse:
        url = f"{self.api_url}/register"
        payload = SiteRegistrationRequest(
            site_name=site_name,
            public_key=public_key
        ).model_dump()

        try:
            response = requests.post(
                url,
                json=payload,
                headers=self._get_headers(),
                timeout=self.timeout
            )
        except Exception as request_exc:
            logger.error(
                "Error while calling registration endpoint",
                extra={
                    "url": url,
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
                    "url": url,
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


def main():
    if len(sys.argv) < 7:
        print("Usage: register.py <api_url> <site_name> <public_key> <oidc_token_url> <oidc_client_id> <oidc_client_secret>", file=sys.stderr)
        sys.exit(1)

    api_url = sys.argv[1]
    site_name = sys.argv[2]
    public_key = sys.argv[3]
    oidc_token_url = sys.argv[4]
    oidc_client_id = sys.argv[5]
    oidc_client_secret = sys.argv[6]

    logger.info(f"Registering site '{site_name} @ '{api_url}")
    logger.info(f"OIDC token URL: {oidc_token_url}, OIDC client: {oidc_client_id}, OIDC secret: {oidc_client_secret}")

    registration_client = RegistrationClient(
        api_url=api_url,
        oidc_token_url=oidc_token_url,
        oidc_client_id=oidc_client_id,
        oidc_client_secret=oidc_client_secret)

    # Prepare metadata
    metadata = {
        "hostname": socket.gethostname(),
        "os": platform.system(),
        "uuid": str(uuid.uuid4()),
        "public_key": public_key,
    }

    try:
        result = registration_client.register_site(
            site_name=site_name,
            public_key=public_key
        )
        logger.info("Registration successful!")
        logger.info("Assigned ID:", result.get("id"))
        logger.info("Github repo: ", result.get("github_repo_url"))
        logger.info("Created at:", result.get("created_at"))

    except Exception as e:
        print("Registration failed:", e)

if __name__ == "__main__":
    main()
