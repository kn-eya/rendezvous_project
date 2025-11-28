from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required

from .models import Service, Provider, Appointment, Availability, Category
from .forms import AppointmentForm, CategoryForm, ProviderForm, AvailabilityForm, ServiceForm

# =====================
# Page d'accueil
# =====================

def acceuil(request):
    services = Service.objects.filter(is_active=True)
    return render(request, "acceuil.html", {"services": services})


# =====================
# Liste des services
# =====================
@login_required
def services_list(request):
    services = Service.objects.filter(is_active=True)
    return render(request, "appointments/services_list.html", {"services": services})


# =====================
# Prestataires par service
# =====================
@login_required
def providers_by_service(request, service_id):
    service = get_object_or_404(Service, id=service_id)
    providers = service.providers.all()
    return render(request, "appointments/providers_list.html", {
        "service": service,
        "providers": providers
    })


# =====================
# Réserver un rendez-vous
# =====================
@login_required
def book_appointment(request, provider_id):
    provider = get_object_or_404(Provider, id=provider_id)

    if request.method == "POST":
        form = AppointmentForm(request.POST)
        if form.is_valid():
            appointment = form.save(commit=False)
            appointment.client = request.user
            appointment.provider = provider
            appointment.category = get_object_or_404(Category, id=request.POST.get("category"))
            appointment.save()
            messages.success(request, "Rendez-vous créé avec succès ✅")
            return redirect("appointments:my_appointments")
    else:
        form = AppointmentForm()

    return render(request, "appointments/book_appointment.html", {
        "provider": provider,
        "form": form
    })


# =====================
# Mes rendez-vous
# =====================
@login_required
def my_appointments(request):
    appointments = request.user.appointments.all()
    return render(request, "appointments/my_appointments.html", {
        "appointments": appointments
    })


# =====================
# AJAX : obtenir les prestataires par service
# =====================
@login_required
def get_providers(request):
    service_id = request.GET.get("service_id")
    service = get_object_or_404(Service, id=service_id)

    data = [
        {
            "id": p.id,
            "name": p.user.username,
            "photo": p.photo.url if p.photo else "",
            "profile_url": f"/appointments/provider/{p.id}/"
        }
        for p in service.providers.all()
    ]
    return JsonResponse(data, safe=False)


# =====================
# AJAX : obtenir les catégories par service
# =====================
@login_required
def ajax_get_categories(request):
    service_id = request.GET.get("service_id")
    categories = Category.objects.filter(service_id=service_id)

    data = [
        {"id": c.id, "name": c.name}
        for c in categories
    ]
    return JsonResponse(data, safe=False)


# =====================
# Annuler un rendez-vous
# =====================
@login_required
def cancel_appointment(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id, client=request.user)

    if request.method == "POST":
        appointment.status = 'cancelled'
        appointment.save()
        messages.success(request, "Rendez-vous annulé ✅")

    return redirect('appointments:my_appointments')


# =====================
# Édition profil prestataire
# =====================
@login_required
def provider_edit_profile(request):
    provider, created = Provider.objects.get_or_create(user=request.user)
    provider_form = ProviderForm(request.POST or None, request.FILES or None, instance=provider)

    if request.method == "POST" and provider_form.is_valid():
        provider_instance = provider_form.save()

        # Suppression anciennes disponibilités
        provider.availabilities.all().delete()

        # Création multiples jours
        days = request.POST.getlist("day_of_week")
        starts = request.POST.getlist("start_time")
        ends = request.POST.getlist("end_time")

        for day, start, end in zip(days, starts, ends):
            if day and start and end:
                Availability.objects.create(
                    provider=provider_instance,
                    day_of_week=day,
                    start_time=start,
                    end_time=end
                )

        messages.success(request, "Profil mis à jour ✅")
        return redirect('appointments:provider_detail', provider_id=provider.id)

    return render(request, 'appointments/provider_edit_profile.html', {
        'provider_form': provider_form,
        'availabilities': provider.availabilities.all()
    })
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.forms import inlineformset_factory

from .models import Service, Category
from .forms import ServiceForm, CategoryForm

@staff_member_required
def admin_services_list(request):
    services = Service.objects.prefetch_related('category_set').all()

    # Inline formset pour créer plusieurs catégories en même temps pour un service
    CategoryFormSet = inlineformset_factory(
        Service, Category, form=CategoryForm, extra=1, can_delete=True
    )

    service_form = ServiceForm()
    category_formset = CategoryFormSet()

    if request.method == "POST":
        # ----- Création Service avec catégories -----
        if "create_service" in request.POST:
            service_form = ServiceForm(request.POST, request.FILES)
            category_formset = CategoryFormSet(request.POST)
            if service_form.is_valid() and category_formset.is_valid():
                service = service_form.save()
                category_formset.instance = service
                category_formset.save()
                messages.success(request, "Service et ses catégories ajoutés ✅")
                return redirect("appointments:admin_services_list")

        # ----- Modification Service -----
        elif "edit_service" in request.POST:
            service_id = request.POST.get("service_id")
            service = get_object_or_404(Service, id=service_id)
            service_form = ServiceForm(request.POST, request.FILES, instance=service)
            category_formset = CategoryFormSet(request.POST, instance=service)
            if service_form.is_valid() and category_formset.is_valid():
                service_form.save()
                category_formset.save()
                messages.success(request, f"Service '{service.name}' et ses catégories modifiés ✅")
                return redirect("appointments:admin_services_list")

        # ----- Création Catégorie seule -----
        elif "create_category" in request.POST:
            category_form = CategoryForm(request.POST)
            if category_form.is_valid():
                category_form.save()
                messages.success(request, "Catégorie ajoutée ✅")
                return redirect("appointments:admin_services_list")

        # ----- Modification Catégorie seule -----
        elif "edit_category" in request.POST:
            category_id = request.POST.get("category_id")
            category = get_object_or_404(Category, id=category_id)
            category_form = CategoryForm(request.POST, instance=category)
            if category_form.is_valid():
                category_form.save()
                messages.success(request, f"Catégorie '{category.name}' modifiée ✅")
                return redirect("appointments:admin_services_list")

    return render(request, "appointments/admin_services_list.html", {
        "services": services,
        "service_form": service_form,
        "category_formset": category_formset,
    })
# =====================
# Réservation sur une seule page
# =====================
@login_required
def single_page_booking(request):
    from .models import Service, Category, Provider
    from .forms import AppointmentForm

    services = Service.objects.filter(is_active=True)
    categories = Category.objects.all()
    providers = Provider.objects.all()

    if request.method == "POST":
        provider_id = request.POST.get("provider")
        category_id = request.POST.get("category")
        date = request.POST.get("date")
        time = request.POST.get("time")

        if not (provider_id and category_id and date and time):
            messages.error(request, "Veuillez remplir tous les champs !")
            return redirect("appointments:single_booking")

        provider = get_object_or_404(Provider, id=provider_id)
        category = get_object_or_404(Category, id=category_id)

        Appointment.objects.create(
            client=request.user,
            provider=provider,
            category=category,
            date=date,
            time=time
        )
        messages.success(request, "Rendez-vous créé avec succès ✅")
        return redirect("appointments:my_appointments")

    return render(request, "appointments/single_booking.html", {
        "services": services,
        "categories": categories,
        "providers": providers,
    })
# =====================
# Détails d'un prestataire
# =====================
@login_required
def provider_detail(request, provider_id):
    provider = get_object_or_404(Provider, id=provider_id)
    return render(request, "appointments/provider_detail.html", {"provider": provider})

@login_required
def single_page_booking(request, service_id):
    from .models import Service, Category, Provider
    from .forms import AppointmentForm

    service = get_object_or_404(Service, id=service_id, is_active=True)
    categories = Category.objects.filter(service=service)  # <-- seulement les catégories de ce service
    providers = service.providers.all()  # <-- seulement les prestataires de ce service

    if request.method == "POST":
        provider_id = request.POST.get("provider")
        category_id = request.POST.get("category")
        date = request.POST.get("date")
        time = request.POST.get("time")

        if not (provider_id and category_id and date and time):
            messages.error(request, "Veuillez remplir tous les champs !")
            return redirect("appointments:single_booking", service_id=service_id)

        provider = get_object_or_404(Provider, id=provider_id)
        category = get_object_or_404(Category, id=category_id)

        Appointment.objects.create(
            client=request.user,
            provider=provider,
            category=category,
            date=date,
            time=time
        )
        messages.success(request, "Rendez-vous créé avec succès ✅")
        return redirect("appointments:my_appointments")

    return render(request, "appointments/single_booking.html", {
        "service": service,
        "categories": categories,
        "providers": providers,
    })
