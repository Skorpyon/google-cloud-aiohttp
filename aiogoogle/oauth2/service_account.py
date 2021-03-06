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

"""Service Accounts: JSON Web Token (JWT) Profile for OAuth 2.0

This module implements the JWT Profile for OAuth 2.0 Authorization Grants
as defined by `RFC 7523`_ with particular support for how this RFC is
implemented in Google's infrastructure. Google refers to these credentials
as *Service Accounts*.

Service accounts are used for server-to-server communication, such as
interactions between a web application server and a Google service. The
service account belongs to your application instead of to an individual end
user. In contrast to other OAuth 2.0 profiles, no users are involved and your
application "acts" as the service account.

Typically an application uses a service account when the application uses
Google APIs to work with its own data rather than a user's data. For example,
an application that uses Google Cloud Datastore for data persistence would use
a service account to authenticate its calls to the Google Cloud Datastore API.
However, an application that needs to access a user's Drive documents would
use the normal OAuth 2.0 profile.

Additionally, Google Apps domain administrators can grant service accounts
`domain-wide delegation`_ authority to access user data on behalf of users in
the domain.

This profile uses a JWT to acquire an OAuth 2.0 access token. The JWT is used
in place of the usual authorization token returned during the standard
OAuth 2.0 Authorization Code grant. The JWT is only used for this purpose, as
the acquired access token is used as the bearer token when making requests
using these credentials.

This profile differs from normal OAuth 2.0 profile because no user consent
step is required. The use of the private key allows this profile to assert
identity directly.

This profile also differs from the :mod:`google.auth.jwt` authentication
because the JWT credentials use the JWT directly as the bearer token. This
profile instead only uses the JWT to obtain an OAuth 2.0 access token. The
obtained OAuth 2.0 access token is used as the bearer token.

Domain-wide delegation
----------------------

Domain-wide delegation allows a service account to access user data on
behalf of any user in a Google Apps domain without consent from the user.
For example, an application that uses the Google Calendar API to add events to
the calendars of all users in a Google Apps domain would use a service account
to access the Google Calendar API on behalf of users.

The Google Apps administrator must explicitly authorize the service account to
do this. This authorization step is referred to as "delegating domain-wide
authority" to a service account.

You can use domain-wise delegation by creating a set of credentials with a
specific subject using :meth:`~Credentials.with_subject`.

.. _RFC 7523: https://tools.ietf.org/html/rfc7523
"""

import copy

from google.auth import _helpers
from google.auth import credentials
from google.oauth2.service_account import Credentials as SyncCredentials

from aiogoogle.oauth2 import _client


_DEFAULT_TOKEN_LIFETIME_SECS = 3600  # 1 hour in sections


class Credentials(SyncCredentials):
    """Service account credentials

    Usually, you'll create these credentials with one of the helper
    constructors. To create credentials using a Google service account
    private key JSON file::

        credentials = service_account.Credentials.from_service_account_file(
            'service-account.json')

    Or if you already have the service account file loaded::

        service_account_info = json.load(open('service_account.json'))
        credentials = service_account.Credentials.from_service_account_info(
            service_account_info)

    Both helper methods pass on arguments to the constructor, so you can
    specify additional scopes and a subject if necessary::

        credentials = service_account.Credentials.from_service_account_file(
            'service-account.json',
            scopes=['email'],
            subject='user@example.com')

    The credentials are considered immutable. If you want to modify the scopes
    or the subject used for delegation, use :meth:`with_scopes` or
    :meth:`with_subject`::

        scoped_credentials = credentials.with_scopes(['email'])
        delegated_credentials = credentials.with_subject(subject)
    """
    def __init__(self, signer, service_account_email, token_uri, scopes=None,
                 subject=None, additional_claims=None):
        """
        Args:
            signer (google.auth.crypt.Signer): The signer used to sign JWTs.
            service_account_email (str): The service account's email.
            scopes (Sequence[str]): Scopes to request during the authorization
                grant.
            token_uri (str): The OAuth 2.0 Token URI.
            subject (str): For domain-wide delegation, the email address of the
                user to for which to request delegated access.
            additional_claims (Mapping[str, str]): Any additional claims for
                the JWT assertion used in the authorization grant.

        .. note:: Typically one of the helper constructors
            :meth:`from_service_account_file` or
            :meth:`from_service_account_info` are used instead of calling the
            constructor directly.
        """
        super(SyncCredentials, self).__init__()

        self._scopes = scopes
        self._signer = signer
        self._service_account_email = service_account_email
        self._subject = subject
        self._token_uri = token_uri

        if additional_claims is not None:
            self._additional_claims = additional_claims
        else:
            self._additional_claims = {}

    @_helpers.copy_docstring(credentials.Scoped)
    def with_scopes(self, scopes):
        return Credentials(
            self._signer,
            service_account_email=self._service_account_email,
            scopes=scopes,
            token_uri=self._token_uri,
            subject=self._subject,
            additional_claims=self._additional_claims.copy())

    def with_subject(self, subject):
        """Create a copy of these credentials with the specified subject.

        Args:
            subject (str): The subject claim.

        Returns:
            aiogoogle.oauth2.service_account.Credentials: A new credentials
                instance.
        """
        return Credentials(
            self._signer,
            service_account_email=self._service_account_email,
            scopes=self._scopes,
            token_uri=self._token_uri,
            subject=subject,
            additional_claims=self._additional_claims.copy())

    def with_claims(self, additional_claims):
        """Returns a copy of these credentials with modified claims.

        Args:
            additional_claims (Mapping[str, str]): Any additional claims for
                the JWT payload. This will be merged with the current
                additional claims.

        Returns:
            aiogoogle.oauth2.service_account.Credentials: A new credentials
                instance.
        """
        new_additional_claims = copy.deepcopy(self._additional_claims)
        new_additional_claims.update(additional_claims or {})

        return Credentials(
            self._signer,
            service_account_email=self._service_account_email,
            scopes=self._scopes,
            token_uri=self._token_uri,
            subject=self._subject,
            additional_claims=new_additional_claims)

    async def before_request(self, request, method, url, headers):
        """Performs credential-specific before request logic.

        Refreshes the credentials if necessary, then calls :meth:`apply` to
        apply the token to the authentication header.

        Args:
            request (google.auth.transport.Request): The object used to make
                HTTP requests.
            method (str): The request's HTTP method or the RPC method being
                invoked.
            url (str): The request's URI or the RPC service's URI.
            headers (Mapping): The request's headers.
        """
        # pylint: disable=unused-argument
        # (Subclasses may use these arguments to ascertain information about
        # the http request.)
        if not self.valid:
            await self.refresh(request)
        self.apply(headers)

    @_helpers.copy_docstring(credentials.Credentials)
    async def refresh(self, session):
        assertion = self._make_authorization_grant_assertion()
        access_token, expiry, _ = await _client.jwt_grant(
            session, self._token_uri, assertion)
        self.token = access_token
        self.expiry = expiry
