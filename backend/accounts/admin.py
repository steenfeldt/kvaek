from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import (
    BrandProfile,
    CreatorProfile,
    InviteCode,
    NicheTag,
    ProfilePhoto,
    SocialLink,
    User,
    VerificationRequest,
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


@admin.register(InviteCode)
class InviteCodeAdmin(admin.ModelAdmin):
    list_display = ["code", "is_active", "used_by", "used_at", "note"]
    list_filter = ["is_active"]


admin.site.register(NicheTag)
