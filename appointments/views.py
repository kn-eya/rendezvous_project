from django.shortcuts import render, redirect, get_object_or_404
from .models import Service, SubService, Provider, Appointment
from django.contrib.auth.decorators import login_required
from .forms import AppointmentForm

@login_required
def services_list(request):
    services = Service.objects.all()
    return render(request, "appointments/services_list.html", {"services": services})

@login_required
def subservices_list(request, service_id):
    service = get_object_or_404(Service, id=service_id)
    subservices = service.subservices.all()
    return render(request, "appointments/subservices_list.html", {"service": service, "subservices": subservices})

@login_required
def providers_list(request, subservice_id):
    subservice = get_object_or_404(SubService, id=subservice_id)
    providers = subservice.providers.all()
    return render(request, "appointments/providers_list.html", {"subservice": subservice, "providers": providers})

@login_required
def book_appointment(request, provider_id):
    provider = get_object_or_404(Provider, id=provider_id)
    if request.method == "POST":
        form = AppointmentForm(request.POST)
        if form.is_valid():
            appointment = form.save(commit=False)
            appointment.client = request.user
            appointment.provider = provider
            appointment.save()
            return redirect("appointments:my_appointments")
    else:
        form = AppointmentForm()
    return render(request, "appointments/book_appointment.html", {"provider": provider, "form": form})

@login_required
def my_appointments(request):
    appointments = request.user.appointments.all()
    return render(request, "appointments/my_appointments.html", {"appointments": appointments})
