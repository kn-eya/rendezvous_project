from django.contrib import admin
from .models import Service, Category, Provider, Availability, Appointment, Notification

# -------------------------
# Admin pour Service
# -------------------------
@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')
    search_fields = ('name',)
    list_filter = ('is_active',)
    ordering = ('name',)

# -------------------------
# Admin pour Category
# -------------------------
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'service', 'price')
    search_fields = ('name',)
    list_filter = ('service',)
    ordering = ('service', 'name')

# -------------------------
# Admin pour Provider
# -------------------------
@admin.register(Provider)
class ProviderAdmin(admin.ModelAdmin):
    list_display = ('user', 'service', 'category', 'city', 'phone')
    search_fields = ('user__username', 'city', 'phone')
    list_filter = ('service', 'category', 'city')
    ordering = ('service', 'category')

# -------------------------
# Admin pour Availability
# -------------------------
@admin.register(Availability)
class AvailabilityAdmin(admin.ModelAdmin):
    list_display = ('provider', 'day_of_week', 'start_time', 'end_time')
    list_filter = ('day_of_week', 'provider__service')
    search_fields = ('provider__user__username',)

# -------------------------
# Admin pour Appointment
# -------------------------
@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('client', 'provider', 'category', 'date', 'time', 'status')
    list_filter = ('status', 'date', 'provider__service')
    search_fields = ('client__username', 'provider__user__username', 'category__name')
    ordering = ('date', 'time')

# -------------------------
# Admin pour Notification
# -------------------------
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'appointment', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('user__username', 'title', 'message')
    ordering = ('-created_at',)
