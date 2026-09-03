from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html

from .models import (
    BrandProfile,
    ChannelMetricSnapshot,
    City,
    CreatorProfile,
    NicheTag,
    ProfilePhoto,
    SocialLink,
    User,
    VerificationRequest,
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ["email"]
    list_display = ["email", "role", "is_active", "is_staff", "date_joined"]
    search_fields = ["email"]
    actions = ["gdpr_erase"]

    @admin.action(description="GDPR: anonymize & erase selected (irreversible)")
    def gdpr_erase(self, request, queryset):
        from .gdpr import erase_user

        for user in queryset:
            if user == request.user or user.is_superuser:
                self.message_user(request, f"Skipped {user.email} (self/superuser)", level="warning")
                continue
            self.message_user(request, f"{user.pk}: {erase_user(user)}")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups")}),
        ("Dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = ((None, {"classes": ("wide",), "fields": ("email", "password1", "password2")}),)


class SocialLinkInline(admin.TabularInline):
    model = SocialLink
    extra = 0
    fields = ["platform", "handle", "follower_count", "verification_method", "verified_at", "last_sync_at", "sync_failures", "external_id"]
    readonly_fields = ["last_sync_at", "sync_failures", "external_id"]


class ProfilePhotoInline(admin.TabularInline):
    model = ProfilePhoto
    extra = 0


@admin.register(CreatorProfile)
class CreatorProfileAdmin(admin.ModelAdmin):
    list_display = ["display_name", "user", "city", "listed", "is_verified", "created_at"]
    list_filter = ["listed"]

    @admin.display(boolean=True, description="Verified")
    def is_verified(self, obj):
        return obj.verified
    search_fields = ["display_name", "user__email"]
    inlines = [SocialLinkInline, ProfilePhotoInline]


@admin.register(BrandProfile)
class BrandProfileAdmin(admin.ModelAdmin):
    list_display = ["company_name", "user", "cvr", "city", "created_at"]
    search_fields = ["company_name", "cvr", "user__email"]


@admin.register(VerificationRequest)
class VerificationRequestAdmin(admin.ModelAdmin):
    list_display = ["creator", "channel", "status", "created_at", "reviewed_by", "evidence_link"]
    list_filter = ["status"]
    actions = ["approve", "reject"]
    exclude = ["evidence"]
    readonly_fields = ["evidence_link"]

    @admin.display(description="Evidence")
    def evidence_link(self, obj):
        if not obj.evidence:
            return "-"
        url = reverse("verification-evidence", args=[obj.pk])
        return format_html('<a href="{}" target="_blank">View evidence</a>', url)

    @admin.action(description="Approve selected (marks the channel verified)")
    def approve(self, request, queryset):
        for vr in queryset.filter(status=VerificationRequest.Status.PENDING).select_related("channel"):
            if vr.channel is None:
                self.message_user(request, f"{vr.pk}: no channel attached, skipped", level="warning")
                continue
            vr.status = VerificationRequest.Status.APPROVED
            vr.reviewed_by = request.user
            vr.reviewed_at = timezone.now()
            vr.save(update_fields=["status", "reviewed_by", "reviewed_at"])
            vr.channel.verification_method = SocialLink.VerificationMethod.MANUAL
            vr.channel.verified_at = timezone.now()
            vr.channel.save(update_fields=["verification_method", "verified_at"])

    @admin.action(description="Reject selected")
    def reject(self, request, queryset):
        queryset.filter(status=VerificationRequest.Status.PENDING).update(
            status=VerificationRequest.Status.REJECTED,
            reviewed_by=request.user,
            reviewed_at=timezone.now(),
        )


@admin.register(NicheTag)
class NicheTagAdmin(admin.ModelAdmin):
    list_display = ["name", "status", "suggested_by", "created_at", "creator_count"]
    list_filter = ["status"]
    search_fields = ["name"]
    actions = ["approve", "reject"]

    @admin.display(description="Creators")
    def creator_count(self, obj):
        return obj.creators.count()

    @admin.action(description="Approve selected (makes them public)")
    def approve(self, request, queryset):
        queryset.update(status=NicheTag.Status.APPROVED)

    @admin.action(description="Reject selected (removes them from profiles)")
    def reject(self, request, queryset):
        for tag in queryset:
            tag.creators.clear()
        queryset.update(status=NicheTag.Status.REJECTED)


@admin.register(ChannelMetricSnapshot)
class ChannelMetricSnapshotAdmin(admin.ModelAdmin):
    list_display = ["channel", "captured_at", "followers", "posts"]
    list_filter = ["channel__platform"]
    readonly_fields = ["channel", "captured_at", "followers", "posts", "engagement_rate", "raw"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ["name", "municipality"]
    search_fields = ["name", "municipality"]

