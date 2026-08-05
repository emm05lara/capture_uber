"""Middleware de apoyo a la política de acceso."""


class SinCacheParaSesionMiddleware:
    """Evita que el navegador conserve páginas privadas después del logout.

    Sin esto, el botón "atrás" puede mostrar desde la caché una pantalla que
    el usuario ya no tiene derecho a ver (o que corresponde a otra cuenta).
    Solo se aplica a respuestas de usuarios autenticados y respeta cualquier
    `Cache-Control` que la propia vista haya fijado.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        usuario = getattr(request, "user", None)
        if (
            usuario is not None
            and getattr(usuario, "is_authenticated", False)
            and not response.has_header("Cache-Control")
        ):
            response["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
        return response
