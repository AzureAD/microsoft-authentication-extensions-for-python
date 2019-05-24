from msal_extensions import TokenProvider, TokenProviderChain


class NeverAvailableTokenProvider(TokenProvider):
    def __init__(self):
        self._available_call_count = 0
        self._get_token_call_count = 0

    @property
    def available_call_count(self):
        return self._available_call_count

    @property
    def get_token_call_count(self):
        return self._get_token_call_count

    def available(self):
        self._available_call_count += 1
        return False

    def get_token(self, scopes=None):
        self._get_token_call_count += 1
        return None


class AlwaysAvailableTokenProvider(TokenProvider):
    def __init__(self):
        self._available_call_count = 0
        self._get_token_call_count = 0

    @property
    def available_call_count(self):
        return self._available_call_count

    @property
    def get_token_call_count(self):
        return self._get_token_call_count

    def available(self):
        self._available_call_count += 1
        return True

    def get_token(self, scopes=None):
        self._get_token_call_count += 1
        return {
            'access_token': 'faux_credentials',
            'expires_in': 0}


def test_chain_no_token_call_if_unavailable():
    first = NeverAvailableTokenProvider()
    second = NeverAvailableTokenProvider()

    subject = TokenProviderChain(first, second)

    assert first.available_call_count == 0
    assert second.available_call_count == 0
    assert first.get_token_call_count == 0
    assert second.get_token_call_count == 0

    assert not subject.available()

    assert first.available_call_count == 1
    assert second.available_call_count == 1
    assert first.get_token_call_count == 0
    assert second.get_token_call_count == 0

    third = AlwaysAvailableTokenProvider()
    subject = TokenProviderChain(first, second, third)
    assert third.available_call_count == 0
    assert third.get_token_call_count == 0

    assert subject.available()

    assert first.available_call_count == 2
    assert second.available_call_count == 2
    assert third.available_call_count == 1
    assert first.get_token_call_count == 0
    assert second.get_token_call_count == 0

    assert subject.get_token(scopes=None)
    assert first.available_call_count == 3
    assert second.available_call_count == 3
    assert third.available_call_count == 2
    assert first.get_token_call_count == 0
    assert second.get_token_call_count == 0
    assert third.get_token_call_count == 1

