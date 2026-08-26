from django.contrib import admin

from .models import Message, Review


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ["deal", "sender", "created_at", "read_at"]


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ["deal", "author", "rating", "created_at"]
