from django.conf import settings
from django.core.files.storage import FileSystemStorage

# No base_url on purpose: .url must never resolve — files here are served only
# through authenticated staff views.
private_storage = FileSystemStorage(location=settings.PRIVATE_MEDIA_ROOT)
