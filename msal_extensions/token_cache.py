import sys

if sys.platform.startswith('win'):
    from .windows import WindowsTokenCache
elif sys.platform.startswith('darwin'):
    from .osx import OSXTokenCache


def get_protected_token_cache(enforce_encryption=False, **kwargs):
    if sys.platform.startswith('win'):
        return WindowsTokenCache(**kwargs)
    elif sys.platform.startswith('darwin'):
        return OSXTokenCache(**kwargs)
    elif enforce_encryption:
        raise RuntimeError('no protected token cache for platform {}'.format(sys.platform))
    else:
        raise NotImplementedError('No fallback TokenCache is implemented yet.')
