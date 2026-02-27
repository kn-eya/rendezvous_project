from django.urls import path

from . import views

app_name = "appointments"

urlpatterns = [
    path("", views.acceuil, name="acceuil"),
    path("services/", views.services_list, name="services_list"),
    path("services/<int:service_id>/providers/", views.providers_by_service, name="providers_by_service"),
    path("booking/", views.single_page_booking, name="single_booking"),
    path("booking/<int:service_id>/", views.single_page_booking, name="single_booking_service"),
    path("single-booking/<int:service_id>/", views.single_page_booking, name="single_booking_legacy"),
    path("book/<int:provider_id>/", views.book_appointment, name="book_appointment"),
    path("my-appointments/", views.my_appointments, name="my_appointments"),
    path("cancel/<int:appointment_id>/", views.cancel_appointment, name="cancel_appointment"),
    path("provider/<int:provider_id>/", views.provider_detail, name="provider_detail"),
    path("provider/edit-profile/", views.provider_edit_profile, name="provider_edit_profile"),
    path("provider/dashboard/", views.provider_dashboard, name="provider_dashboard"),
    path("provider/<int:provider_id>/agenda/", views.provider_agenda, name="provider_agenda"),
    path("provider/<int:provider_id>/agenda/events/", views.provider_agenda_events, name="provider_agenda_events"),
    path("provider/agenda/blocked/", views.provider_blocked_slots_ajax, name="provider_blocked_slots_ajax"),
    path(
        "provider/agenda/blocked/create/",
        views.provider_create_blocked_slot_ajax,
        name="provider_create_blocked_slot_ajax",
    ),
    path(
        "provider/agenda/blocked/<int:slot_id>/delete/",
        views.provider_delete_blocked_slot_ajax,
        name="provider_delete_blocked_slot_ajax",
    ),
    path("provider/agenda/slot/toggle/", views.provider_toggle_slot_block_ajax, name="provider_toggle_slot_block_ajax"),
    path(
        "provider/agenda/appointment/<int:appointment_id>/status/",
        views.provider_update_appointment_status_ajax,
        name="provider_update_appointment_status_ajax",
    ),
    path("provider/agenda/book/", views.book_appointment_ajax, name="book_appointment_ajax"),
    path("notifications/", views.notifications_page, name="notifications_page"),
    path("admin/services/", views.admin_services_list, name="admin_services_list"),
    path("ajax/get_categories/", views.ajax_get_categories, name="get_categories"),
    path("ajax/get_providers/", views.get_providers, name="get_providers"),
    path("ajax/get_services/", views.ajax_get_services, name="ajax_get_services"),
    path("ajax/available-slots/", views.ajax_available_slots, name="ajax_available_slots"),
    path("ajax/unread-count/", views.ajax_unread_count, name="ajax_unread_count"),
    path("ajax/portfolio/save/", views.ajax_save_portfolio, name="ajax_save_portfolio"),
    path("ajax/portfolio/delete/<int:item_id>/", views.ajax_delete_portfolio, name="ajax_delete_portfolio"),
    path("ajax/apply-availability-template/", views.ajax_apply_availability_template, name="ajax_apply_availability_template"),
    path(
        "ajax/apply-custom-availability-template/",
        views.ajax_apply_custom_availability_template,
        name="ajax_apply_custom_availability_template",
    ),
    path("ajax/save-availability/", views.ajax_save_availability, name="ajax_save_availability"),
    path("ajax/availability/delete/<int:availability_id>/", views.ajax_delete_availability, name="ajax_delete_availability"),
]
