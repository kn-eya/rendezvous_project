from django.shortcuts import render, redirect, get_object_or_404
from appointments.models import Appointment
from django.contrib.auth.decorators import login_required
from django.contrib import messages

@login_required
def provider_dashboard(request):
    appointments = Appointment.objects.filter(provider__user=request.user)
    return render(request, 'dashboard/provider_dashboard.html', {'appointments': appointments})

@login_required
def accept_appointment(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)
    appointment.status = 'accepted'
    appointment.save()
    messages.success(request, 'Rendez-vous accepté.')
    return redirect('dashboard:provider_dashboard')

@login_required
def refuse_appointment(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)
    appointment.status = 'refused'
    appointment.save()
    messages.success(request, 'Rendez-vous refusé.')
    return redirect('dashboard:provider_dashboard')
