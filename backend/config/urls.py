from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from django.views.decorators.csrf import ensure_csrf_cookie

from .api import api


@ensure_csrf_cookie
def csrf(request):
    return JsonResponse({"ok": True})


from accounts.views import verification_evidence

urlpatterns = [
    path("admin/", admin.site.urls),
    path("staff/verification-evidence/<int:pk>/", verification_evidence, name="verification-evidence"),
    path("_allauth/", include("allauth.headless.urls")),
    # Only the social provider callback views are live here (HEADLESS_ONLY
    # disables the HTML account views). Google redirects back to
    # /accounts/google/login/callback/.
    path("accounts/", include("allauth.urls")),
    path("api/csrf", csrf),
    path("api/", api.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
