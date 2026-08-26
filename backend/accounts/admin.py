import secrets

from django.conf import settings
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.core.mail import send_mail
from django.utils import timezone

from .models import (
    BrandProfile,
    CreatorProfile,
    InviteCode,
    NicheTag,
    ProfilePhoto,
    SocialLink,
    User,
    VerificationRequest,
    WaitlistEntry,
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ["email"]
    list_display = ["email", "role", "is_staff", "date_joined"]
    search_fields = ["email"]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups")}),
        ("Dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = ((None, {"classes": ("wide",), "fields": ("email", "password1", "password2")}),)


class SocialLinkInline(admin.TabularInline):
    model = SocialLink
    extra = 0


class ProfilePhotoInline(admin.TabularInline):
    model = ProfilePhoto
    extra = 0


@admin.register(CreatorProfile)
class CreatorProfileAdmin(admin.ModelAdmin):
    list_display = ["display_name", "user", "city", "listed", "verified", "created_at"]
    list_filter = ["listed", "verified"]
    search_fields = ["display_name", "user__email"]
    inlines = [SocialLinkInline, ProfilePhotoInline]


@admin.register(BrandProfile)
class BrandProfileAdmin(admin.ModelAdmin):
    list_display = ["company_name", "user", "cvr", "city", "created_at"]
    search_fields = ["company_name", "cvr", "user__email"]


@admin.register(VerificationRequest)
class VerificationRequestAdmin(admin.ModelAdmin):
    list_display = ["creator", "status", "created_at", "reviewed_by"]
    list_filter = ["status"]
    actions = ["approve", "reject"]

    @admin.action(description="Approve selected (marks creator verified)")
    def approve(self, request, queryset):
        for vr in queryset.filter(status=VerificationRequest.Status.PENDING):
            vr.status = VerificationRequest.Status.APPROVED
            vr.reviewed_by = request.user
            vr.reviewed_at = timezone.now()
            vr.save(update_fields=["status", "reviewed_by", "reviewed_at"])
            vr.creator.verified = True
            vr.creator.save(update_fields=["verified"])

    @admin.action(description="Reject selected")
    def reject(self, request, queryset):
        queryset.filter(status=VerificationRequest.Status.PENDING).update(
            status=VerificationRequest.Status.REJECTED,
            reviewed_by=request.user,
            reviewed_at=timezone.now(),
        )


@admin.register(WaitlistEntry)
class WaitlistEntryAdmin(admin.ModelAdmin):
    list_display = ["email", "name", "handle", "created_at", "invited_at"]
    list_filter = [("invited_at", admin.EmptyFieldListFilter)]
    actions = ["send_invites"]

    @admin.action(description="Create invite codes and email selected")
    def send_invites(self, request, queryset):
        for entry in queryset.filter(invited_at__isnull=True):
            code = f"KVAEK-{secrets.token_hex(3).upper()}"
            InviteCode.objects.create(code=code, note=f"waitlist: {entry.email}")
            send_mail(
                "Din invitation er klar",
                f"Hej{' ' + entry.name if entry.name else ''},\n\n"
                f"Du står på ventelisten — nu er der plads til dig!\n\n"
                f"Din invitationskode: {code}\n\n"
                f"Opret din profil her: {settings.FRONTEND_URL}/creators\n\n"
                f"Venlig hilsen\nKvæk",
                None,
                [entry.email],
                fail_silently=False,
            )
            entry.invited_at = timezone.now()
            entry.save(update_fields=["invited_at"])


@admin.register(InviteCode)
class InviteCodeAdmin(admin.ModelAdmin):
    list_display = ["code", "is_active", "used_by", "used_at", "note"]
    list_filter = ["is_active"]


admin.site.register(NicheTag)
