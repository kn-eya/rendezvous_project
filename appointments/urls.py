from django.urls import include, path
from . import views

app_name = 'appointments'

urlpatterns = [
    # Page d'accueil
    path("", views.acceuil, name="acceuil"),
   

    # Liste des services
    path('services/', views.services_list, name='services_list'),
    
    # Liste des prestataires d’un service
    path('services/<int:service_id>/providers/', views.providers_by_service, name='providers_by_service'),
    
    # Réserver un rendez-vous pour un prestataire
    path('book/<int:provider_id>/', views.book_appointment, name='book_appointment'),
    
    # Mes rendez-vous
    path('my-appointments/', views.my_appointments, name='my_appointments'),
    
    # Page de réservation unique (catégorie → service → prestataire)
    path("booking/", views.single_page_booking, name="single_booking"),
    
    # AJAX pour obtenir les prestataires
    path("ajax/get_providers/", views.get_providers, name="get_providers"),
    
    # Détails d’un prestataire
    path('provider/<int:provider_id>/', views.provider_detail, name='provider_detail'),
    
    # AJAX pour obtenir le service lié à une catégorie
  path('ajax/get_categories/', views.ajax_get_categories, name='get_categories'),
 # Annuler un rendez-vous
    path('cancel/<int:appointment_id>/', views.cancel_appointment, name='cancel_appointment'),
    
    # Édition du profil prestataire
    path('provider/edit-profile/', views.provider_edit_profile, name='provider_edit_profile'),
    
    # Admin
# Admin services & categories
path("admin/services/", views.admin_services_list, name="admin_services_list"),

path('single-booking/<int:service_id>/', views.single_page_booking, name='single_booking'),

path('ajax/get_services/', views.ajax_get_services, name='ajax_get_services'),
   
path("provider/dashboard/", views.provider_dashboard, name="provider_dashboard"),
  path("notifications/", views.notifications_page, name="notifications_page"),
     path('ajax/unread-count/', views.ajax_unread_count, name='ajax_unread_count'),

]
