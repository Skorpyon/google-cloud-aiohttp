# Copyright 2015 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Base classes for client used to interact with Google Cloud APIs."""

from pickle import PicklingError

from google.auth.credentials import with_scopes_if_required
from google.cloud.credentials import get_credentials
from google.cloud.client import _ClientFactoryMixin, _ClientProjectMixin

from aiogoogle.oauth2 import service_account
from aiogoogle.auth.transport.aiohttp import AuthorizedAiohttpClientSession


_GOOGLE_AUTH_CREDENTIALS_HELP = (
    'This library only supports credentials from google-auth-library-python. '
    'See https://google-cloud-python.readthedocs.io/en/latest/'
    'google-cloud-auth.html for help on authentication with this library.'
)


class Client(_ClientFactoryMixin):
    """Client to bundle configuration needed for API requests.

    Stores ``credentials`` and an HTTP object so that subclasses
    can pass them along to a connection class.

    If no value is passed in for ``_http``, a :class:`httplib2.Http` object
    will be created and authorized with the ``credentials``. If not, the
    ``credentials`` and ``_http`` need not be related.

    Callers and subclasses may seek to use the private key from
    ``credentials`` to sign data.

    A custom (non-``httplib2``) HTTP object must have a ``request`` method
    which accepts the following arguments:

    * ``uri``
    * ``method``
    * ``body``
    * ``headers``

    In addition, ``redirections`` and ``connection_type`` may be used.

    A custom ``_http`` object will also need to be able to add a bearer token
    to API requests and handle token refresh on 401 errors.

    :type credentials: :class:`~google.auth.credentials.Credentials`
    :param credentials: (Optional) The OAuth2 Credentials to use for this
                        client. If not passed (and if no ``_http`` object is
                        passed), falls back to the default inferred from the
                        environment.

    :type _http: :class:`~httplib2.Http`
    :param _http: (Optional) HTTP object to make requests. Can be any object
                  that defines ``request()`` with the same interface as
                  :meth:`~httplib2.Http.request`. If not passed, an
                  ``_http`` object is created that is bound to the
                  ``credentials`` for the current object.
                  This parameter should be considered private, and could
                  change in the future.
    """

    SCOPE = None
    """The scopes required for authenticating with a service.

    Needs to be set by subclasses.
    """

    def __init__(self, credentials=None, _http=None):
        if (credentials is not None and
                not isinstance(credentials, service_account.Credentials)):
            raise ValueError(_GOOGLE_AUTH_CREDENTIALS_HELP)
        if credentials is None and _http is None:
            credentials = get_credentials()
        self._credentials = with_scopes_if_required(
            credentials, self.SCOPE)
        self._http_internal = _http

    @property
    def _http(self):
        """Getter for object used for HTTP transport.

        :rtype: :class:`~aiogoogle.transport.`
        :returns: An HTTP object.
        """
        if self._http_internal is None:
            self._http_internal = AuthorizedAiohttpClientSession(
                self._credentials)
        return self._http_internal


class ClientWithProject(Client, _ClientProjectMixin):
    """Client that also stores a project.

    :type project: str
    :param project: the project which the client acts on behalf of. If not
                    passed falls back to the default inferred from the
                    environment.

    :type credentials: :class:`~google.auth.credentials.Credentials`
    :param credentials: (Optional) The OAuth2 Credentials to use for this
                        client. If not passed (and if no ``_http`` object is
                        passed), falls back to the default inferred from the
                        environment.

    :type _http: :class:`~httplib2.Http`
    :param _http: (Optional) HTTP object to make requests. Can be any object
                  that defines ``request()`` with the same interface as
                  :meth:`~httplib2.Http.request`. If not passed, an
                  ``_http`` object is created that is bound to the
                  ``credentials`` for the current object.
                  This parameter should be considered private, and could
                  change in the future.

    :raises: :class:`ValueError` if the project is neither passed in nor
             set in the environment.
    """

    def __init__(self, project=None, credentials=None, _http=None):
        _ClientProjectMixin.__init__(self, project=project)
        Client.__init__(self, credentials=credentials, _http=_http)
