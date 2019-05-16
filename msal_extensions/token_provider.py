import os
import abc
from msal.application import ConfidentialClientApplication


class TokenProvider(abc.ABC):
    @abc.abstractmethod
    def available(self):
        # type: () -> bool
        """
        Communicates whether or not this TokenProvider will ever be able to return a token.
        :return: True if this TokenProvider is enabled, False otherwise.
        """

        # Implementer's Note (from @marstr and @devigned):
        #
        # Q: Why doesn't this method take scopes? Wouldn't it be useful to know if a provider not only was available,
        # but would ultimately be successful in finding an access token?
        # A: This method seeks only to determine whether or not it is worth the latency of seeing whether or not a token
        # request should be submitted. For example, consider Managed Service Identity (MSI), which allows applications
        # to make an HTTPS call to get an access token. Quickly answering the question "Am I running in an environment
        # that even has the capability to provide an MSI endpoint?" is likely easier than calling the MSI endpoint and
        # and dealing with the latency associated with a failed network call. Combined with the fact that it is trivial
        # to disregard "None" entries in a list, and it feels clear to the original authors that all potentially latent
        # calls should happen in "get_token" to keep "available" as fast as possible.
        raise NotImplementedError()

    @abc.abstractmethod
    def get_token(self, scopes=None, username=None):
        # type: (*str) -> {str:str}
        """
        Fetches an Access Token for a user needing a particular set of scopes.
        :param scopes: The resource access or capabilities that the entity which will be using the token is requesting.
        :param username: The account name for the token that is being requested.
        :return: An Access Token.
        """
        raise NotImplementedError()


class TokenProviderChain(TokenProvider):
    def __init__(self, *args):
        self._links = list(args)

    def append(self, provider):
        self._links.append(provider)

    def available(self):
        """
        Searches to see if any of the token providers
        :return: True
        """
        return any((item for item in self._links if item.available()))

    def get_token(self, scopes=None, username=None):
        available = (item.get_token(scopes=scopes) for item in self._links if item.available())
        return next((for token in available if token))


class ServicePrincipalProvider(TokenProvider):
    DEFAULT_CLIENT_ID = os.getenv('AZURE_CLIENT_ID')
    DEFAULT_CLIENT_SECRET = os.getenv('AZURE_CLIENT_SECRET')

    def __init__(self, client_id=None, client_secret=None):
        client_id = client_id or ServicePrincipalProvider.DEFAULT_CLIENT_ID
        client_secret = client_secret or ServicePrincipalProvider.DEFAULT_CLIENT_SECRET

        self._app = ConfidentialClientApplication(
            client_id=client_id,
            client_secret=client_secret,
        )

    def available(self):
        """ Always returns true, because if it was able to be instantiated, it is available for use."""
        return True

    def get_token(self, scopes=None):
        return self._app.acquire_token_for_client(scopes=scopes)


DEFAULT_TOKEN_CHAIN = TokenProviderChain()

if ServicePrincipalProvider.DEFAULT_CLIENT_ID and ServicePrincipalProvider.DEFAULT_CLIENT_SECRET:
    DEFAULT_TOKEN_CHAIN.append(ServicePrincipalProvider())
