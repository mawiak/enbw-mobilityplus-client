"""EnBW mobility+ API Client with OAuth2 PKCE Authentication"""

import base64
import hashlib
import json
import re
import secrets
import uuid
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urljoin, urlparse

import httpx

from .config import settings
from .models import ChargingHistoryEntry, ChargingHistoryResponse, Profile, TokenResponse


class EnBWMobilityPlusClient:
    """Client for EnBW mobility+ API with OAuth2 PKCE authentication"""

    # Default OAuth2 configuration (from EnBW mobility+ iOS app)
    DEFAULT_AUTH_BASE_URL = "https://myenergykey.com"
    DEFAULT_API_BASE_URL = "https://api.emp.emob-enbw.com/emobility-complete/api/v2"
    DEFAULT_CLIENT_ID = "MCVlPomnunRHO86S3Ju1JUJENA8hEI4i"
    DEFAULT_REDIRECT_URI = "com.enbw.ev://myenergykey.com/ios/com.enbw.ev/callback"
    DEFAULT_AUDIENCE = "https://pro-login.enbw.com/"
    DEFAULT_SCOPE = "email offline_access openid"
    DEFAULT_CUSTOM_SCOPE = (
        "read:bsr:emp read:bsr:lms read:bsr:cmdm read:bsr:permission "
        "read:bsr:airship read:bsr:thunderhead read:bsr:smart-mobility read:bsr:mobilityplus-engage"
    )
    DEFAULT_API_KEY = "g6dm9b1vnhs456m98cre53dj5x"
    DEFAULT_OCP_APIM_SUBSCRIPTION_KEY = "c7097f4712dd4c20aae95ff6ad95d171"

    def __init__(
        self,
        auth_base_url: Optional[str] = None,
        api_base_url: Optional[str] = None,
        client_id: Optional[str] = None,
        redirect_uri: Optional[str] = None,
        audience: Optional[str] = None,
        scope: Optional[str] = None,
        custom_scope: Optional[str] = None,
        api_key: Optional[str] = None,
        ocp_apim_subscription_key: Optional[str] = None,
    ):
        """
        Initialize EnBW mobility+ API Client.

        Args:
            auth_base_url: OAuth2 authorization server URL
            api_base_url: EnBW API base URL
            client_id: OAuth2 client ID
            redirect_uri: OAuth2 redirect URI
            audience: OAuth2 audience
            scope: OAuth2 scope
            custom_scope: EnBW custom scope
            api_key: API key for EnBW API
            ocp_apim_subscription_key: Azure APIM subscription key
        """
        # Use cookies to maintain session state (required for EnBW API)
        self.client = httpx.Client(timeout=30.0, follow_redirects=False, cookies=httpx.Cookies())
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.charging_account_id: Optional[str] = None
        self.session_cookies: Dict[str, str] = {}  # ARRAffinity cookies for EnBW API

        # Generate unique device identifiers for this client instance
        self.device_id = str(uuid.uuid4()).upper()
        self.installation_id = str(uuid.uuid4()).upper()

        # Load config: parameter > environment > default
        self.auth_base_url = auth_base_url or settings.auth_base_url or self.DEFAULT_AUTH_BASE_URL
        self.api_base_url = api_base_url or settings.api_base_url or self.DEFAULT_API_BASE_URL
        self.client_id = client_id or settings.client_id or self.DEFAULT_CLIENT_ID
        self.redirect_uri = redirect_uri or self.DEFAULT_REDIRECT_URI
        self.audience = audience or self.DEFAULT_AUDIENCE
        self.scope = scope or self.DEFAULT_SCOPE
        self.custom_scope = custom_scope or self.DEFAULT_CUSTOM_SCOPE
        self.api_key = api_key or settings.api_key or self.DEFAULT_API_KEY
        self.ocp_apim_subscription_key = (
            ocp_apim_subscription_key or settings.ocp_apim_subscription_key or self.DEFAULT_OCP_APIM_SUBSCRIPTION_KEY
        )

    def _generate_pkce_pair(self) -> tuple[str, str]:
        """Generate PKCE code verifier and code challenge"""
        # Generate code verifier (43-128 characters)
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("utf-8").rstrip("=")

        # Generate code challenge (SHA256 hash of verifier)
        code_challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode("utf-8")).digest()).decode("utf-8").rstrip("=")
        )

        return code_verifier, code_challenge

    def _generate_state(self) -> str:
        """Generate random state parameter for OAuth2"""
        return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("utf-8").rstrip("=")

    def _extract_charging_account_id(self, access_token: str) -> Optional[str]:
        """Extract charging account ID from JWT access token"""
        try:
            # Decode JWT payload (without verification as we trust the source)
            parts = access_token.split(".")
            if len(parts) < 2:
                return None

            # Add padding if needed
            payload = parts[1]
            padding = 4 - len(payload) % 4
            if padding != 4:
                payload += "=" * padding

            decoded = base64.urlsafe_b64decode(payload)
            data = json.loads(decoded)

            # Extract emp reference ID from business system references
            identity = data.get("https://login.ciam.com/identity_v2", {})
            business_refs = identity.get("businessSystemReferences", [])

            for ref in business_refs:
                if ref.get("businessSystemCode") == "emp":
                    return ref.get("referenceId")

            return None
        except Exception:
            return None

    def login(self, email: str, password: str) -> TokenResponse:
        """
        Login to EnBW mobility+ API using email/password with OAuth2 PKCE flow.

        Args:
            email: EnBW mobility+ account email
            password: EnBW mobility+ account password

        Returns:
            TokenResponse with access_token, refresh_token, etc.

        Raises:
            ValueError: If login fails or authorization code cannot be extracted
        """
        # Step 0: Initialize session by calling /version endpoint
        # This sets ARRAffinity cookies that are required for all subsequent API calls
        try:
            version_resp = self.client.get(
                f"{self.api_base_url.replace('/api/v2', '/api/v1')}/version",
                params={
                    "termsAndconditions": "07032023",
                    "termsOfUse": "02052023",
                    "privacy": "07032023",
                },
                headers={
                    "accept": "application/json",
                    "apikey": self.api_key,
                    "ocp-apim-subscription-key": self.ocp_apim_subscription_key,
                },
            )
            # Extract ARRAffinity cookies from Set-Cookie headers
            if "set-cookie" in version_resp.headers:
                for cookie_header in version_resp.headers.get_list("set-cookie"):
                    if "ARRAffinity" in cookie_header:
                        cookie_parts = cookie_header.split(";")[0].split("=", 1)
                        if len(cookie_parts) == 2:
                            self.session_cookies[cookie_parts[0]] = cookie_parts[1]
        except Exception:
            pass  # Session initialization is optional, will retry after login

        # Generate PKCE parameters
        code_verifier, code_challenge = self._generate_pkce_pair()
        state = self._generate_state()

        # Step 1: Initiate authorization with PKCE
        authorize_params = {
            "client_id": self.client_id,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "audience": self.audience,
            "redirect_uri": self.redirect_uri,
            "scope": self.scope,
            "custom_scope": self.custom_scope,
            "response_type": "code",
            "state": state,
            "viewsignup": "false",
        }

        # Get login page - follow all redirects to establish session
        auth_response = self.client.get(f"{self.auth_base_url}/authorize", params=authorize_params)

        # Follow redirect chain until we get a 200 response
        while auth_response.status_code == 302:
            location = auth_response.headers.get("Location", "")
            if not location:
                break
            # Make location absolute if relative
            if location.startswith("/"):
                location = urljoin(self.auth_base_url, location)
            auth_response = self.client.get(location)

        if auth_response.status_code != 200:
            raise ValueError(f"Authorization failed: {auth_response.status_code}")

        # Step 2: Extract auth state from the current URL
        auth_state = state
        current_url = str(auth_response.url) if hasattr(auth_response, "url") else ""

        # If we got redirected, extract the state from the URL
        if "state=" in current_url:
            parsed = urlparse(current_url)
            query_params = parse_qs(parsed.query)
            if "state" in query_params:
                auth_state = query_params["state"][0]

        # Step 3: POST username to identifier endpoint
        identifier_url = f"{self.auth_base_url}/u/login/identifier"

        identifier_data = {
            "username": email,
            "captcha": "",
            "js-available": "true",
            "is-brave": "false",
            "webauthn-available": "true",
            "webauthn-platform-available": "true",
            "allow-passkeys": "true",
            "state": auth_state,
            "acul-sdk": "@auth0/auth0-acul-js@1.3.0",
        }

        identifier_response = self.client.post(
            identifier_url,
            params={"state": auth_state},
            data=identifier_data,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": self.auth_base_url,
                "Referer": f"{identifier_url}?state={auth_state}",
            },
        )

        # Should redirect to password page
        if identifier_response.status_code != 302:
            raise ValueError(f"Identifier submission failed: {identifier_response.status_code}")

        # Step 4: Follow redirect to password page
        password_location = identifier_response.headers.get("Location", "")
        if not password_location:
            raise ValueError("No redirect to password page")

        if password_location.startswith("/"):
            password_location = urljoin(self.auth_base_url, password_location)

        password_page = self.client.get(password_location)

        if password_page.status_code != 200:
            raise ValueError(f"Failed to load password page: {password_page.status_code}")

        # Step 5: Submit password
        password_url = f"{self.auth_base_url}/u/login/password"

        login_data = {
            "username": email,
            "password": password,
            "captcha": "",
            "js-available": "true",
            "is-brave": "false",
            "webauthn-available": "true",
            "webauthn-platform-available": "true",
            "allow-passkeys": "true",
            "state": auth_state,
            "acul-sdk": "@auth0/auth0-acul-js@1.3.0",
        }

        login_response = self.client.post(
            password_url,
            params={"state": auth_state},
            data=login_data,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": self.auth_base_url,
                "Referer": f"{password_url}?state={auth_state}",
            },
        )

        if login_response.status_code != 302:
            raise ValueError(f"Login failed: {login_response.status_code}")

        # Step 4: Follow redirect to /authorize/resume
        resume_location = login_response.headers.get("Location", "")
        if not resume_location:
            raise ValueError("No redirect location after login")

        # Make location absolute
        if resume_location.startswith("/"):
            resume_location = urljoin(self.auth_base_url, resume_location)

        resume_response = self.client.get(resume_location)

        # Step 5: Follow any additional redirects to get the authorization code
        auth_code = None

        # Keep following redirects until we hit the custom URI scheme or find the code
        current_response = resume_response
        max_redirects = 10
        redirect_count = 0

        while redirect_count < max_redirects:
            if current_response.status_code == 302:
                location = current_response.headers.get("Location", "")
                if not location:
                    break

                # Check if this redirect contains the authorization code
                if "code=" in location:
                    code_match = re.search(r"code=([^&]+)", location)
                    if code_match:
                        auth_code = code_match.group(1)
                        break

                # If redirecting to the custom URI scheme, check for code there
                if location.startswith("com.enbw.ev://") or location.startswith(self.redirect_uri):
                    if "code=" in location:
                        code_match = re.search(r"code=([^&]+)", location)
                        if code_match:
                            auth_code = code_match.group(1)
                    elif "error=" in location:
                        # Extract error details
                        error_match = re.search(r"error=([^&]+)", location)
                        error_desc_match = re.search(r"error_description=([^&]+)", location)
                        error = error_match.group(1) if error_match else "unknown"
                        error_desc = error_desc_match.group(1) if error_desc_match else ""
                        raise ValueError(f"Auth0 error: {error} - {error_desc}")
                    break

                # Make location absolute if relative
                if location.startswith("/"):
                    location = urljoin(self.auth_base_url, location)

                # Follow the redirect
                current_response = self.client.get(location)
                redirect_count += 1
            elif current_response.status_code == 200 and self._is_passkey_enrollment(current_response):
                # Auth0 may interrupt the flow with a passkey enrollment prompt - skip it ("Not now")
                current_response = self._skip_passkey_enrollment(current_response)
                redirect_count += 1
            elif current_response.status_code == 200:
                # Check response text for redirect or code
                if "code=" in current_response.text:
                    code_match = re.search(r'code=([^&"\'\s]+)', current_response.text)
                    if code_match:
                        auth_code = code_match.group(1)
                break
            else:
                break

        if not auth_code:
            raise ValueError(
                f"Could not extract authorization code. Status: {current_response.status_code}, "
                f"URL: {current_response.url if hasattr(current_response, 'url') else 'N/A'}"
            )

        # Step 6: Exchange authorization code for tokens
        token_data = {
            "redirect_uri": self.redirect_uri,
            "code_verifier": code_verifier,
            "grant_type": "authorization_code",
            "code": auth_code,
            "client_id": self.client_id,
        }

        token_response = self.client.post(
            f"{self.auth_base_url}/oauth/token",
            json=token_data,
            headers={
                "Content-Type": "application/json",
                "Accept": "*/*",
                "User-Agent": "mobility+/506 CFNetwork/3860.600.12 Darwin/25.5.0",
            },
        )

        if token_response.status_code != 200:
            raise ValueError(f"Token exchange failed: {token_response.status_code} - {token_response.text}")

        token_data_response = token_response.json()
        token = TokenResponse(**token_data_response)

        # Store tokens
        self.access_token = token.access_token
        self.refresh_token = token.refresh_token

        # CRITICAL: Use the FIRST token (without refresh) for initial API calls
        # The app uses the initial token, NOT a refreshed one
        # Make a dummy API call to activate the session
        # The backend sets ARRAffinity cookies that we need for subsequent requests
        # httpx can't use these cookies automatically because they're set for a different domain
        # (emp-shared-apim-v2-prod.azure-api.net) than we're requesting (api.emp.emob-enbw.com)
        try:
            resp = self.client.get(
                f"{self.api_base_url}/chargestations/favorites?myLat=0&myLon=0",
                headers=self._get_headers(include_charging_account=False),
            )
            # Extract ARRAffinity cookies from Set-Cookie headers
            if "set-cookie" in resp.headers:
                for cookie_header in resp.headers.get_list("set-cookie"):
                    if "ARRAffinity" in cookie_header:
                        # Parse cookie: "ARRAffinity=value;Path=/;..." -> extract name and value
                        cookie_parts = cookie_header.split(";")[0].split("=", 1)
                        if len(cookie_parts) == 2:
                            self.session_cookies[cookie_parts[0]] = cookie_parts[1]
        except Exception:
            pass  # Session activation is optional

        # Fetch profiles to get the charging account ID (UUID)
        try:
            profiles = self.get_profiles()
            if profiles and len(profiles) > 0:
                # Use the first active profile's charging account ID
                profile = profiles[0]
                self.charging_account_id = profile.charging_account_id

                # CRITICAL: Call /permissions to set JSESSIONID cookie
                # This is required for the session to be fully authenticated
                try:
                    permissions_resp = self.client.get(
                        f"{self.api_base_url.replace('/api/v2', '/b2b/v1/api')}/permissions",
                        params={
                            "profileId": str(profile.id),
                            "endUserId": str(profile.end_user_id),
                        },
                        headers=self._get_headers(include_charging_account=False),
                    )
                    # Extract JSESSIONID cookie from Set-Cookie header
                    if "set-cookie" in permissions_resp.headers:
                        for cookie_header in permissions_resp.headers.get_list("set-cookie"):
                            if "JSESSIONID" in cookie_header:
                                cookie_parts = cookie_header.split(";")[0].split("=", 1)
                                if len(cookie_parts) == 2:
                                    self.session_cookies[cookie_parts[0]] = cookie_parts[1]
                except Exception:
                    pass  # Permissions call is optional
        except Exception as e:
            raise ValueError(f"Failed to fetch user profile: {e}. Unable to initialize charging account.")

        return token

    @staticmethod
    def _is_passkey_enrollment(response: httpx.Response) -> bool:
        """Check if the response is an Auth0 passkey enrollment prompt"""
        return response.url.path.startswith("/u/passkey-enrollment")

    def _skip_passkey_enrollment(self, response: httpx.Response) -> httpx.Response:
        """Decline the Auth0 passkey enrollment prompt and continue the login flow"""
        enrollment_url = str(response.url)
        enrollment_state = response.url.params.get("state", "")

        skip_data = {
            "state": enrollment_state,
            "action": "abort-passkey-enrollment",
        }
        # The local variant offers a "don't show again" checkbox
        if response.url.path.startswith("/u/passkey-enrollment-local"):
            skip_data["dont-show-again"] = "true"

        return self.client.post(
            enrollment_url,
            data=skip_data,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": self.auth_base_url,
                "Referer": enrollment_url,
            },
        )

    def refresh_access_token(self) -> TokenResponse:
        """
        Refresh the access token using the refresh token.

        Returns:
            TokenResponse with new access_token

        Raises:
            ValueError: If refresh token is not available or refresh fails
        """
        if not self.refresh_token:
            raise ValueError("No refresh token available. Please login first.")

        token_data = {
            "grant_type": "refresh_token",
            "custom_scope": self.custom_scope,
            "client_id": self.client_id,
            "refresh_token": self.refresh_token,
        }

        token_response = self.client.post(
            f"{self.auth_base_url}/oauth/token",
            json=token_data,
            headers={
                "Content-Type": "application/json",
                "Accept": "*/*",
                "User-Agent": "mobility+/506 CFNetwork/3860.600.12 Darwin/25.5.0",
            },
        )

        if token_response.status_code != 200:
            raise ValueError(f"Token refresh failed: {token_response.status_code} - {token_response.text}")

        token_data_response = token_response.json()
        token = TokenResponse(**token_data_response)

        # Store new access token
        self.access_token = token.access_token

        # Update refresh token if provided (might be rotated)
        if token.refresh_token:
            self.refresh_token = token.refresh_token

        return token

    def _get_headers(self, include_charging_account: bool = True) -> Dict[str, str]:
        """Get headers for API requests"""
        if not self.access_token:
            raise ValueError("Not authenticated. Call login() first.")

        headers = {
            "accept": "application/json",
            "accept-encoding": "gzip, deflate, br",
            "accept-language": "de",
            "apikey": self.api_key,
            "appversion": "8.18.0 (build 506)",
            "authorization": f"Bearer {self.access_token}",
            "devicemodel": "iPhone18,1",
            "identifierforvendor": self.device_id,
            "installationidentifier": self.installation_id,
            "messagingtoken": f"claude-code-client-{self.installation_id[:8]}",
            "ocp-apim-subscription-key": self.ocp_apim_subscription_key,
            "osversion": "26.5.2",
            "platform": "iOS",
            "priority": "u=3",
            "user-agent": "mobility+/506 CFNetwork/3860.600.12 Darwin/25.5.0",
            "versioncode": "506",
        }

        if include_charging_account and self.charging_account_id:
            headers["charging-account-id"] = self.charging_account_id

        # Add session cookies as Cookie header (manual workaround for domain mismatch)
        if self.session_cookies:
            cookie_string = "; ".join([f"{k}={v}" for k, v in self.session_cookies.items()])
            headers["cookie"] = cookie_string

        return headers

    def set_charging_account_id(self, account_id: str) -> None:
        """
        Set the charging account ID for API requests.

        Args:
            account_id: The charging account ID (UUID)
        """
        self.charging_account_id = account_id

    def get_profiles(self) -> list[Profile]:
        """
        Get user profiles from EnBW API.

        Returns:
            List of Profile objects

        Raises:
            ValueError: If not authenticated or API request fails
        """
        # Profiles endpoint is on v1, not v2
        api_v1_url = self.api_base_url.replace("/api/v2", "/api/v1")

        headers = self._get_headers(include_charging_account=False)

        response = self.client.get(
            f"{api_v1_url}/profiles",
            headers=headers,
        )

        if response.status_code != 200:
            raise ValueError(f"Failed to get profiles: {response.status_code} - {response.text}")

        data = response.json()
        return [Profile(**profile) for profile in data]

    def get_charging_history(
        self, limit: int = 25, offset: int = 0, charging_account_id: Optional[str] = None
    ) -> list[ChargingHistoryEntry]:
        """
        Get charging session history.

        Args:
            limit: Maximum number of entries to return (default: 25)
            offset: Pagination offset (default: 0)
            charging_account_id: Optional charging account ID (uses stored ID if not provided)

        Returns:
            List of ChargingHistoryEntry objects

        Raises:
            ValueError: If not authenticated or API request fails
        """
        # Use provided account ID or stored one
        if charging_account_id:
            self.charging_account_id = charging_account_id

        if not self.charging_account_id:
            raise ValueError("Charging account ID not set. Call set_charging_account_id() first.")

        params = {"limit": limit, "offset": offset}

        response = self.client.get(
            f"{self.api_base_url}/chargings/history", headers=self._get_headers(), params=params
        )

        if response.status_code != 200:
            raise ValueError(f"Failed to get charging history: {response.status_code} - {response.text}")

        data = response.json()
        history_response = ChargingHistoryResponse(**data)

        return history_response.charging_history_entries

    def close(self):
        """
        Close the HTTP client and cleanup resources.

        Should be called when done using the client, or use context manager (with statement).
        """
        self.client.close()

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures cleanup"""
        self.close()
