"""Local bearer requests never use environment proxies or follow redirects."""
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def urlopen(request, timeout=120):
    if not isinstance(request, Request):
        raise ValueError('Local HTTP requires an explicit request')
    target = urlsplit(request.full_url)
    if (target.scheme != 'http' or target.hostname != '127.0.0.1'
            or target.username is not None or target.password is not None
            or target.fragment or target.port is None or not 1 <= target.port <= 65535):
        raise ValueError('Local HTTP target must be an explicit loopback port')
    return build_opener(ProxyHandler({}), _NoRedirect()).open(request, timeout=timeout)
