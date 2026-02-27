from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('provider/', views.provider_dashboard, name='provider_dashboard'),
    path('admin/', views.admin_dashboard, name='admin_dashboard'),
    path('accept/<int:appointment_id>/', views.accept_appointment, name='accept_appointment'),
    path('refuse/<int:appointment_id>/', views.refuse_appointment, name='refuse_appointment'),
    path('cancel/<int:appointment_id>/', views.cancel_appointment_provider, name='cancel_appointment_provider'),
    path('done/<int:appointment_id>/', views.mark_appointment_done, name='mark_appointment_done'),
]
