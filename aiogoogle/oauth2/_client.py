# Copyright 2016 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""OAuth 2.0 client.

This is a client for interacting with an OAuth 2.0 authorization server's
token endpoint.

For more information about the token endpoint, see
`Section 3.1 of rfc6749`_

.. _Section 3.1 of rfc6749: https://tools.ietf.org/html/rfc6749#section-3.2
"""

from urllib.parse import urlencode

import ujson as json

from google.auth import exceptions
from google.oauth2._client import _handle_error_response, _parse_expiry


_URLENCODED_CONTENT_TYPE = 'application/x-www-form-urlencoded'
_JWT_GRANT_TYPE = 'urn:ietf:params:oauth:grant-type:jwt-bearer'
_REFRESH_GRANT_TYPE = 'refresh_token'


async def _token_endpoint_request(session, token_uri, body):
    """Makes a request to the OAuth 2.0 authorization server's token endpoint.

    Args:
        session (aiohttp.client.ClientSession): ClientSession used to make
            HTTP requests.
        token_uri (str): The OAuth 2.0 authorizations server's token endpoint
            URI.
        body (Mapping[str, str]): The parameters to send in the request body.

    Returns:
        Mapping[str, str]: The JSON-decoded response data.

    Raises:
        google.auth.exceptions.RefreshError: If the token endpoint returned
            an error.
    """
    body = urlencode(body)
    headers = {
        'content-type': _URLENCODED_CONTENT_TYPE,
    }

    response = await session.post(url=token_uri, headers=headers, data=body)

    response_text = await response.text(encoding='utf-8')

    if response.status != 200:
        _handle_error_response(response_text)

    response_data = json.loads(response_text)

    return response_data


async def jwt_grant(session, token_uri, assertion):
    """Implements the JWT Profile for OAuth 2.0 Authorization Grants.

    For more details, see `rfc7523 section 4`_.

    Args:
        session (aiohttp.client.ClientSession): ClientSession used to make
            HTTP requests.
        token_uri (str): The OAuth 2.0 authorizations server's token endpoint
            URI.
        assertion (str): The OAuth 2.0 assertion.

    Returns:
        Tuple[str, Optional[datetime], Mapping[str, str]]: The access token,
            expiration, and additional data returned by the token endpoint.

    Raises:
        google.auth.exceptions.RefreshError: If the token endpoint returned
            an error.

    .. _rfc7523 section 4: https://tools.ietf.org/html/rfc7523#section-4
    """
    body = {
        'assertion': assertion,
        'grant_type': _JWT_GRANT_TYPE,
    }

    response_data = await _token_endpoint_request(session, token_uri, body)

    try:
        access_token = response_data['access_token']
    except KeyError:
        raise exceptions.RefreshError(
            'No access token in response.', response_data)

    expiry = _parse_expiry(response_data)

    return access_token, expiry, response_data


async def refresh_grant(session, token_uri, refresh_token, client_id,
                        client_secret):
    """Implements the OAuth 2.0 refresh token grant.

    For more details, see `rfc678 section 6`_.

    Args:
        session (aiohttp.client.ClientSession): ClientSession used to make
            HTTP requests.
        token_uri (str): The OAuth 2.0 authorizations server's token endpoint
            URI.
        refresh_token (str): The refresh token to use to get a new access
            token.
        client_id (str): The OAuth 2.0 application's client ID.
        client_secret (str): The Oauth 2.0 appliaction's client secret.

    Returns:
        Tuple[str, Optional[str], Optional[datetime], Mapping[str, str]]: The
            access token, new refresh token, expiration, and additional data
            returned by the token endpoint.

    Raises:
        google.auth.exceptions.RefreshError: If the token endpoint returned
            an error.

    .. _rfc6748 section 6: https://tools.ietf.org/html/rfc6749#section-6
    """
    body = {
        'grant_type': _REFRESH_GRANT_TYPE,
        'client_id': client_id,
        'client_secret': client_secret,
        'refresh_token': refresh_token,
    }

    response_data = await _token_endpoint_request(session, token_uri, body)

    try:
        access_token = response_data['access_token']
    except KeyError:
        raise exceptions.RefreshError(
            'No access token in response.', response_data)

    refresh_token = response_data.get('refresh_token', refresh_token)
    expiry = _parse_expiry(response_data)

    return access_token, refresh_token, expiry, response_data
