from __future__ import annotations

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

        host = request.get_host()
        allowed_prefix = f'{request.scheme}://{host}'
        if origin and not origin.startswith(allowed_prefix):
            return HttpResponseForbidden('Origem inválida.')
        if referer and not referer.startswith(allowed_prefix):
            return HttpResponseForbidden('Origem inválida.')

        return None
