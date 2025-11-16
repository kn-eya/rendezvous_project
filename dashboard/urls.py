from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('provider/', views.provider_dashboard, name='provider_dashboard'),
    path('accept/<int:appointment_id>/', views.accept_appointment, name='accept_appointment'),
    path('refuse/<int:appointment_id>/', views.refuse_appointment, name='refuse_appointment'),
]
