"""Generic functions and types for working with a TokenCache that is not platform specific."""
import sys

if sys.platform.startswith('win'):
    from .windows import WindowsTokenCache
elif sys.platform.startswith('darwin'):
    from .osx import OSXTokenCache


def get_protected_token_cache(enforce_encryption=False, **kwargs):
    """Detects the current system, and constructs a TokenCache of the appropriate type for the
    environment in which it's running.

    :param enforce_encryption: When 'True' an error will be raised if there isn't an encrypted
    option available for the current system. When 'False', a plain-text option will be returned.
    :param kwargs: Any options that should be passed to the platform-specific constructor of the
    TokenCache being instantiated by this method.
    :return: A fully instantiated TokenCache able to encrypt/decrypt tokens on the current system.
    """
    if sys.platform.startswith('win'):
        return WindowsTokenCache(**kwargs)

    if sys.platform.startswith('darwin'):
        return OSXTokenCache(**kwargs)

    if enforce_encryption:
        raise RuntimeError('no protected token cache for platform {}'.format(sys.platform))

    raise NotImplementedError('No fallback TokenCache is implemented yet.')
