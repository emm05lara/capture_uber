from django.contrib.auth import logout
from django.shortcuts import redirect
from django.views.decorators.http import require_POST


@require_POST
def cerrar_sesion(request):
    logout(request)
    return redirect("login")
