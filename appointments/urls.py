from django.urls import path
from . import views

app_name = 'appointments'

urlpatterns = [
    path('services/', views.services_list, name='services_list'),
    path('services/<int:service_id>/subservices/', views.subservices_list, name='subservices_list'),
    path('subservices/<int:subservice_id>/providers/', views.providers_list, name='providers_list'),
    path('book/<int:provider_id>/', views.book_appointment, name='book_appointment'),
]
