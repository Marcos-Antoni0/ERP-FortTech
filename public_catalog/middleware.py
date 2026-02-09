from __future__ import annotations

from urllib.parse import urlparse

from django.conf import settings
from django.http import HttpResponseForbidden
from django.utils.deprecation import MiddlewareMixin


class PublicCatalogOriginValidationMiddleware(MiddlewareMixin):
    """Valida origem das requisições para endpoints sensíveis do catálogo."""

    def process_request(self, request):
        if request.method not in ('POST', 'PUT', 'PATCH', 'DELETE'):
            return None

        if not request.path.startswith('/catalogo/'):
            return None

        origin = request.headers.get('Origin')
        referer = request.headers.get('Referer')
        if not origin and not referer:
            return None

        allowed_hosts = self._build_allowed_hosts(request)
        allowed_origins = self._build_allowed_origins(request, allowed_hosts)

        if origin and not self._is_allowed_source(origin, allowed_origins, allowed_hosts):
            return HttpResponseForbidden('Origem inválida.')
        if referer and not self._is_allowed_source(referer, allowed_origins, allowed_hosts):
            return HttpResponseForbidden('Origem inválida.')

        return None

    @staticmethod
    def _build_allowed_hosts(request):
        allowed_hosts = set()

        host = request.get_host()
        if host:
            allowed_hosts.add(host)
            allowed_hosts.add(host.split(':')[0])

        for configured_host in getattr(settings, 'ALLOWED_HOSTS', []):
            if configured_host and configured_host != '*':
                allowed_hosts.add(configured_host)
                allowed_hosts.add(configured_host.split(':')[0])

        return allowed_hosts

    @staticmethod
    def _build_allowed_origins(request, allowed_hosts):
        allowed_origins = set()
        schemes = {'http', 'https'}

        forwarded_proto = request.headers.get('X-Forwarded-Proto')
        if forwarded_proto:
            schemes.update({proto.strip() for proto in forwarded_proto.split(',') if proto.strip()})

        for host in allowed_hosts:
            for scheme in schemes:
                allowed_origins.add(f'{scheme}://{host}')

        for origin in getattr(settings, 'CSRF_TRUSTED_ORIGINS', []):
            parsed = urlparse(origin)
            if parsed.scheme and parsed.netloc:
                allowed_origins.add(f'{parsed.scheme}://{parsed.netloc}')

        return allowed_origins

    @staticmethod
    def _is_allowed_source(source, allowed_origins, allowed_hosts):
        parsed = urlparse(source)
        if not parsed.scheme or not parsed.netloc:
            return False

        normalized = f'{parsed.scheme}://{parsed.netloc}'
        if normalized in allowed_origins:
            return True

        host = parsed.netloc.split(':')[0]
        return parsed.netloc in allowed_hosts or host in allowed_hosts
