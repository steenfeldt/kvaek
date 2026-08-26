from django.contrib.admin.views.decorators import staff_member_required
from django.http import FileResponse, Http404

from .models import VerificationRequest


@staff_member_required
def verification_evidence(request, pk: int):
    vr = VerificationRequest.objects.filter(pk=pk).first()
    if vr is None or not vr.evidence:
        raise Http404
    return FileResponse(vr.evidence.open("rb"), content_type="image/webp")
