from django.contrib import admin

from .models import ProfileView, Shortlist, ShortlistEntry, SwipeEvent


class ShortlistEntryInline(admin.TabularInline):
    model = ShortlistEntry
    extra = 0


@admin.register(Shortlist)
class ShortlistAdmin(admin.ModelAdmin):
    list_display = ["name", "brand", "created_at"]
    inlines = [ShortlistEntryInline]


@admin.register(SwipeEvent)
class SwipeEventAdmin(admin.ModelAdmin):
    list_display = ["brand", "creator", "direction", "created_at"]
    list_filter = ["direction"]


admin.site.register(ProfileView)
