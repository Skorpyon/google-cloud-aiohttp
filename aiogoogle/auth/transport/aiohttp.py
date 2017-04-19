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

"""Transport adapter for aiohttp.ClientSession."""

import logging

import aiohttp

from google.auth import transport

_LOGGER = logging.getLogger(__name__)


class AuthorizedAiohttpClientSession(aiohttp.ClientSession):
    """A Requests Session class with credentials.

    This class is used to perform requests to API endpoints that require
    authorization::

        from aiogoogle.auth.transport.aiohttp import AuthorizedAiohttpClientSession

        authed_session = AuthorizedAiohttpSessionSession(credentials)

        response = await authed_session.request(
            'GET', 'https://www.googleapis.com/storage/v1/b')

    The underlying :meth:`request` implementation handles adding the
    credentials' headers to the request and refreshing credentials as needed.

    Args:
        credentials (aiogoogle.oauth2.Credentials): The credentials to
            add to the request.
        refresh_status_codes (Sequence[int]): Which HTTP status codes indicate
            that credentials should be refreshed and the request should be
            retried.
        max_refresh_attempts (int): The maximum number of times to attempt to
            refresh the credentials and retry the request.
        kwargs: Additional arguments passed to the :class:`aiohttp.ClientSession`
            constructor.
    """
    def __init__(self, credentials,
                 refresh_status_codes=transport.DEFAULT_REFRESH_STATUS_CODES,
                 max_refresh_attempts=transport.DEFAULT_MAX_REFRESH_ATTEMPTS,
                 connector=None, loop=None, cookies=None,
                 headers=None, skip_auto_headers=None,
                 auth=None, request_class=aiohttp.client_reqrep.ClientRequest,
                 response_class=aiohttp.client_reqrep.ClientResponse,
                 ws_response_class=aiohttp.client_ws.ClientWebSocketResponse,
                 version=aiohttp.HttpVersion11,
                 cookie_jar=None, read_timeout=None, time_service=None):

        super(AuthorizedAiohttpClientSession, self).__init__(
            connector=connector, loop=loop, cookies=cookies,
            headers=headers, skip_auto_headers=skip_auto_headers,
            auth=auth, request_class=request_class,
            response_class=response_class,
            ws_response_class=ws_response_class,
            version=version, cookie_jar=cookie_jar, read_timeout=read_timeout,
            time_service=time_service)

        self.credentials = credentials
        self._refresh_status_codes = refresh_status_codes
        self._max_refresh_attempts = max_refresh_attempts
        # Request instance used by internal methods (for example,
        # credentials.refresh).
        # Do not pass `self` as the session here, as it can lead to infinite
        # recursion.

    async def request(self, method, url, data=None, headers=None, **kwargs):
        """Implementation of aiohttp.ClientSession' request."""
        # pylint: disable=arguments-differ
        # Requests has a ton of arguments to request, but only two
        # (method, url) are required. We pass through all of the other
        # arguments to super, so no need to exhaustively list them here.

        # Use a kwarg for this instead of an attribute to maintain
        # thread-safety.
        _credential_refresh_attempt = kwargs.pop(
            '_credential_refresh_attempt', 0)

        # Make a copy of the headers. They will be modified by the credentials
        # and we want to pass the original headers if we recurse.
        request_headers = headers.copy() if headers is not None else {}

        self.credentials.before_request(self, method, url, request_headers)

        response = await super(AuthorizedAiohttpClientSession, self).request(
            method, url, data=data, headers=request_headers, **kwargs)

        # If the response indicated that the credentials needed to be
        # refreshed, then refresh the credentials and re-attempt the
        # request.
        # A stored token may expire between the time it is retrieved and
        # the time the request is made, so we may need to try twice.
        if (response.status in self._refresh_status_codes
                and _credential_refresh_attempt < self._max_refresh_attempts):

            _LOGGER.info(
                'Refreshing credentials due to a %s response. Attempt %s/%s.',
                response.status, _credential_refresh_attempt + 1,
                self._max_refresh_attempts)

            self.credentials.refresh(self)

            # Recurse. Pass in the original headers, not our modified set.
            response = await self.request(
                method, url, data=data, headers=headers,
                _credential_refresh_attempt=_credential_refresh_attempt + 1,
                **kwargs)
            return response

        return response
