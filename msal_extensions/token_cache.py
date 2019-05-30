import sys

if sys.platform.startswith('win'):
    from .windows import WindowsTokenCache
elif sys.platform.startswith('darwin'):
    from .osx import OSXTokenCache


def get_protected_token_cache(enforce_encryption=False, **kwargs):
    if sys.platform.startswith('win'):
        return WindowsTokenCache(**kwargs)

    if sys.platform.startswith('darwin'):
        return OSXTokenCache(**kwargs)

    if enforce_encryption:
        raise RuntimeError('no protected token cache for platform {}'.format(sys.platform))

    raise NotImplementedError('No fallback TokenCache is implemented yet.')
