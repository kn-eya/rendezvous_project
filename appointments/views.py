from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.forms import inlineformset_factory
from django.contrib.auth import authenticate, login

from .models import Notification, Service, Provider, Appointment, Availability, Category
from .forms import AppointmentForm, CategoryForm, ProviderForm, AvailabilityForm, ServiceForm

# =======================================================
# 🏠 VUES GÉNÉRALES
# =======================================================

def acceuil(request):
    services = Service.objects.filter(is_active=True)
    return render(request, "acceuil.html", {"services": services})

@login_required
def services_list(request):
    services = Service.objects.filter(is_active=True)
    return render(request, "appointments/services_list.html", {"services": services})

@login_required
def providers_by_service(request, service_id):
    service = get_object_or_404(Service, id=service_id)
    providers = service.providers.all()
    return render(request, "appointments/providers_list.html", {
        "service": service,
        "providers": providers
    })

# =======================================================
# 📅 RÉSERVATION CLIENT
# =======================================================
@login_required
def book_appointment(request, provider_id):
    from django.core.mail import send_mail
    from django.conf import settings

    provider = get_object_or_404(Provider, id=provider_id)

    category_id = request.GET.get("category")
    if category_id:
        category = get_object_or_404(Category, id=category_id)
    else:
        category = provider.category or provider.category.first()

    if request.method == "POST":
        form = AppointmentForm(request.POST)
        if form.is_valid():
            appointment_date = form.cleaned_data['date']
            appointment_time = form.cleaned_data['time']

            day_str = appointment_date.strftime('%a')
            availabilities = provider.availabilities.filter(day_of_week=day_str)
            if not any(a.start_time <= appointment_time <= a.end_time for a in availabilities):
                messages.error(request, "Le prestataire n'est pas disponible à cette heure.")
            elif Appointment.objects.filter(provider=provider, date=appointment_date, time=appointment_time).exists():
                messages.error(request, "Ce créneau est déjà réservé.")
            else:
                appointment = form.save(commit=False)
                appointment.client = request.user
                appointment.provider = provider
                appointment.category = category
                appointment.save()

                # ================================
                # Notifications plateforme
                # ================================
                Notification.objects.create(
                    user=appointment.provider.user,
                    title="Nouveau rendez-vous",
                    message=f"Vous avez un nouveau rendez-vous avec {appointment.client.username} le {appointment.date} à {appointment.time}.",
                    appointment=appointment
                )
                Notification.objects.create(
                    user=appointment.client,
                    title="Rendez-vous confirmé",
                    message=f"Votre rendez-vous avec {appointment.provider.user.username} le {appointment.date} à {appointment.time} a été créé.",
                    appointment=appointment
                )

                # ================================
                # Notifications par email
                # ================================
                subject_provider = "Nouveau rendez-vous sur AlloRDV"
                message_provider = f"Bonjour {appointment.provider.user.username},\n\nVous avez un nouveau rendez-vous avec {appointment.client.username} le {appointment.date} à {appointment.time}.\n\nMerci, AlloRDV"
                send_mail(subject_provider, message_provider, settings.DEFAULT_FROM_EMAIL, [appointment.provider.user.email])

                subject_client = "Rendez-vous confirmé sur AlloRDV"
                message_client = f"Bonjour {appointment.client.username},\n\nVotre rendez-vous avec {appointment.provider.user.username} le {appointment.date} à {appointment.time} a été créé.\n\nMerci, AlloRDV"
                send_mail(subject_client, message_client, settings.DEFAULT_FROM_EMAIL, [appointment.client.email])

                messages.success(request, "Rendez-vous créé avec succès ! ✅")
                return redirect("appointments:my_appointments")
        else:
            messages.error(request, "Erreur de validation. Vérifiez les champs.")
    else:
        form = AppointmentForm()

    return render(request, "appointments/book_appointment.html", {
        "provider": provider,
        "form": form,
        "category": category,
    })
@login_required
def single_page_booking(request, service_id):
    from django.core.mail import send_mail
    from django.conf import settings
    import datetime

    service = get_object_or_404(Service, id=service_id, is_active=True)
    categories = Category.objects.filter(service=service)
    providers = service.providers.all()

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

        appointment_date_obj = datetime.datetime.strptime(date, "%Y-%m-%d").date()
        appointment_time_obj = datetime.datetime.strptime(time, "%H:%M").time()
        day_str = appointment_date_obj.strftime('%a')
        availabilities = provider.availabilities.filter(day_of_week=day_str)

        if not any(a.start_time <= appointment_time_obj <= a.end_time for a in availabilities):
            messages.error(request, "Le prestataire n'est pas disponible à cette heure.")
            return redirect("appointments:single_booking", service_id=service_id)

        if Appointment.objects.filter(provider=provider, date=appointment_date_obj, time=appointment_time_obj).exists():
            messages.error(request, "Ce créneau est déjà réservé.")
            return redirect("appointments:single_booking", service_id=service_id)

        # Création du rendez-vous
        appointment = Appointment.objects.create(
            client=request.user,
            provider=provider,
            category=category,
            date=appointment_date_obj,
            time=appointment_time_obj
        )

        # ================================
        # Notifications plateforme
        # ================================
        Notification.objects.create(
            user=appointment.provider.user,
            title="Nouveau rendez-vous",
            message=f"Vous avez un nouveau rendez-vous avec {appointment.client.username} le {appointment.date} à {appointment.time}.",
            appointment=appointment
        )
        Notification.objects.create(
            user=appointment.client,
            title="Rendez-vous confirmé",
            message=f"Votre rendez-vous avec {appointment.provider.user.username} le {appointment.date} à {appointment.time} a été créé.",
            appointment=appointment
        )

        # ================================
        # Notifications par email
        # ================================
        subject_provider = "Nouveau rendez-vous sur AlloRDV"
        message_provider = f"Bonjour {appointment.provider.user.username},\n\nVous avez un nouveau rendez-vous avec {appointment.client.username} le {appointment.date} à {appointment.time}.\n\nMerci, AlloRDV"
        send_mail(subject_provider, message_provider, settings.DEFAULT_FROM_EMAIL, [appointment.provider.user.email])

        subject_client = "Rendez-vous confirmé sur AlloRDV"
        message_client = f"Bonjour {appointment.client.username},\n\nVotre rendez-vous avec {appointment.provider.user.username} le {appointment.date} à {appointment.time} a été créé.\n\nMerci, AlloRDV"
        send_mail(subject_client, message_client, settings.DEFAULT_FROM_EMAIL, [appointment.client.email])

        messages.success(request, "Rendez-vous créé avec succès ✅")
        return redirect("appointments:my_appointments")

    return render(request, "appointments/single_booking.html", {
        "service": service,
        "categories": categories,
        "providers": providers,
    })





@login_required
def my_appointments(request):
    appointments = Appointment.objects.filter(client=request.user).order_by('-date', '-time')
    return render(request, "appointments/my_appointments.html", {"appointments": appointments})

@login_required
def cancel_appointment(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id, client=request.user)

    if request.method == "POST":
        appointment.status = 'cancelled'
        appointment.save()
        messages.success(request, "Rendez-vous annulé ✅")

    return redirect('appointments:my_appointments')

# =======================================================
# 🧑‍🔧 VUES PRESTATAIRE
# =======================================================

@login_required
def provider_detail(request, provider_id):
    provider = get_object_or_404(Provider, id=provider_id)
    return render(request, "appointments/provider_detail.html", {"provider": provider})

@login_required
def provider_edit_profile(request):
    provider, created = Provider.objects.get_or_create(user=request.user)
    provider_form = ProviderForm(request.POST or None, request.FILES or None, instance=provider)

    if request.method == "POST" and provider_form.is_valid():
        provider_instance = provider_form.save()
        provider.availabilities.all().delete()

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

@login_required
def provider_dashboard(request):
    provider = get_object_or_404(Provider, user=request.user)
    appointments = Appointment.objects.filter(provider=provider).order_by('-date', '-time')
    return render(request, "dashboard/provider_dashboard.html", {"appointments": appointments})

# =======================================================
# ⚙️ VUES ADMIN
# =======================================================

@staff_member_required
def admin_services_list(request):
    services = Service.objects.prefetch_related('category_set').all()
    CategoryFormSet = inlineformset_factory(Service, Category, form=CategoryForm, extra=1, can_delete=True)

    service_form = ServiceForm()
    category_formset = CategoryFormSet()

    if request.method == "POST":
        if "create_service" in request.POST:
            service_form = ServiceForm(request.POST, request.FILES)
            category_formset = CategoryFormSet(request.POST)
            if service_form.is_valid() and category_formset.is_valid():
                service = service_form.save()
                category_formset.instance = service
                category_formset.save()
                messages.success(request, "Service et ses catégories ajoutés ✅")
                return redirect("appointments:admin_services_list")

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

        elif "create_category" in request.POST:
            category_form = CategoryForm(request.POST)
            if category_form.is_valid():
                category_form.save()
                messages.success(request, "Catégorie ajoutée ✅")
                return redirect("appointments:admin_services_list")

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

# =======================================================
# ⚡ VUES AJAX
# =======================================================

@login_required
def ajax_get_categories(request):
    service_id = request.GET.get("service_id")
    if not service_id:
        return JsonResponse([], safe=False)
    categories = Category.objects.filter(service_id=service_id)
    data = [{"id": c.id, "name": c.name} for c in categories]
    return JsonResponse(data, safe=False)

@login_required
def get_providers(request):
    category_id = request.GET.get("category_id")
    if not category_id:
        return JsonResponse([], safe=False)

    providers = Provider.objects.filter(category_id=category_id)
    data = [{
        "id": p.id,
        "name": p.user.username,
        "city": p.city or ""
    } for p in providers]

    return JsonResponse(data, safe=False)


@login_required
def ajax_get_services(request):
    category_id = request.GET.get("category_id")
    if not category_id:
        return JsonResponse([], safe=False)
    services = Service.objects.filter(categories__id=category_id).values("id", "name")
    return JsonResponse(list(services), safe=False)

# =======================================================
# 🔑 AUTHENTIFICATION
# =======================================================

def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)

            if user.is_staff:
                return redirect("/admin/")

            try:
                if user.provider:
                    return redirect("appointments:provider_edit_profile")
            except Provider.DoesNotExist:
                pass

            return redirect("appointments:services_list")
        else:
            return render(request, "accounts/login.html", {"error": "Identifiants incorrects"})

    return render(request, "accounts/login.html")
@login_required
def ajax_unread_count(request):
    # Évite l'erreur en utilisant 'notifications' via RelatedManager
    count = Notification.objects.filter(user=request.user, is_read=False).count()
    return JsonResponse({"unread": count})
@login_required
def notifications_page(request):
    # Marquer une seule notification comme lue
    if request.method == "POST":
        if "mark_one" in request.POST:
            notif_id = request.POST.get("notif_id")
            notif = get_object_or_404(Notification, id=notif_id, user=request.user)
            notif.is_read = True
            notif.save()
        elif "mark_all" in request.POST:
            Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)

    notifications = Notification.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "notifications/notifications_page.html", {
        "notifications": notifications
    })

