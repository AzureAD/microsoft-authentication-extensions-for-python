"""Provides mechanisms for easily acquiring tokens."""
import os
from abc import ABCMeta, abstractmethod
from msal.application import ConfidentialClientApplication


class TokenProvider:  # pylint: disable=no-init
    """Provides a logical contract for the most common needs associated with fetching a token."""

    __metaclass__ = ABCMeta

    @abstractmethod
    def available(self):
        # type: () -> bool
        """
        Communicates whether or not this TokenProvider will ever be able to return a token.
        :return: True if this TokenProvider is enabled, False otherwise.
        """

        # Implementer's Note (from @marstr and @devigned):
        #
        # Q: Why doesn't this method take scopes? Wouldn't it be useful to know if a provider not
        # only was available, but would ultimately be successful in finding an access token?
        #
        # A: This method seeks only to determine whether or not it is worth the latency of seeing
        # whether or not a token request should be submitted. For example, consider Managed Service
        # Identity (MSI), which allows applications to make an HTTPS call to get an access token.
        # Quickly answering the question "Am I running in an environment that even has the
        # capability to provide an MSI endpoint?" is likely easier than calling the MSI endpoint and
        # dealing with the latency associated with a failed network call. Combined with the fact
        # that it is trivial to disregard "None" entries in a list, and it feels clear to the
        # original authors that all potentially latent calls should happen in "get_token" to keep
        # "available" as fast as possible.
        raise NotImplementedError()

    @abstractmethod
    def get_token(self, scopes=None):
        # type: (*str) -> {str:str}
        """
        Fetches an Access Token for a user needing a particular set of scopes.
        :param scopes: The resource access or capabilities that the entity which will be using the
            token is requesting.
        :param username: The account name for the token that is being requested.
        :return: A token ready to be decorated onto a web-request.
        """
        raise NotImplementedError()


class TokenProviderChain(TokenProvider):
    """Aggregates many TokenProviders into a single priority queue of places to look to acquire
    tokens.

    Note: For performance reasons, it is wise to put the most TokenProviders that add the most
    latency at the end of the chain.
    """

    def __init__(self, *args):  # pylint: disable=super-init-not-called
        self._links = list(args)

    def append(self, provider):
        # type: (TokenProvider) -> None
        """Add a link to the end of the chain.
        :param provider the additional TokenProvider to call."""
        self._links.append(provider)

    def available(self):
        # type: () -> bool
        """Searches to see if any of the token providers registered with this chain are "available".
        :return: True if any of the members of this chain declare themselves as available.
        """
        return any((item for item in self._links if item.available()))

    def get_token(self, scopes=None):
        # type: (list[str]) -> {str:str}
        """U"""
        available = (item.get_token(scopes=scopes) for item in self._links if item.available())
        return next((token for token in available if token))


class ServicePrincipalProvider(TokenProvider):
    """Uses Service Principal credentials to acquire access tokens."""
    DEFAULT_CLIENT_ID = os.getenv('AZURE_CLIENT_ID')
    DEFAULT_CLIENT_SECRET = os.getenv('AZURE_CLIENT_SECRET')

    def __init__(self,  # pylint: disable=super-init-not-called
                 client_id=None,
                 client_credential=None):
        client_id = client_id or ServicePrincipalProvider.DEFAULT_CLIENT_ID
        client_credential = client_credential or ServicePrincipalProvider.DEFAULT_CLIENT_SECRET

        self._app = ConfidentialClientApplication(
            client_id=client_id,
            client_credential=client_credential,
        )

    def available(self):
        """Indicates whether or not this instance was created with credentials or not.
        :return True if both client_id and client_credential have values.
        """
        return self._app.client_id and self._app.client_credential

    def get_token(self, scopes=None):
        """Acquires a token using a ConfidentialClient.
        :param scopes: The resource access or capabilities that the entity which will be using the
            token is requesting.
        :return A token ready to be decorated onto a web-request.
        """
        return self._app.acquire_token_for_client(scopes=scopes)


DEFAULT_TOKEN_CHAIN = TokenProviderChain()

if ServicePrincipalProvider.DEFAULT_CLIENT_ID and ServicePrincipalProvider.DEFAULT_CLIENT_SECRET:
    DEFAULT_TOKEN_CHAIN.append(ServicePrincipalProvider())
