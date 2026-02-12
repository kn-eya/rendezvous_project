from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.forms import inlineformset_factory
from django.contrib.auth import authenticate, login

from .models import Notification, Service, Provider, Appointment, Availability, Category
from .forms import AppointmentForm, CategoryForm, ProviderForm, AvailabilityForm, ServiceForm
from django.shortcuts import render, redirect
from .forms import PortfolioItemForm
from .models import Provider
from django.forms import modelformset_factory
from .models import Availability, PortfolioItem
from .forms import AvailabilityForm, PortfolioItemForm
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from .models import PortfolioItem
from .forms import PortfolioItemForm
from django.shortcuts import render, get_object_or_404
from .models import Provider, Availability, Appointment
from datetime import datetime, timedelta
from django.core.paginator import Paginator
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
        category = provider.category.first() if provider.category.exists() else None

    if request.method == "POST":
        form = AppointmentForm(request.POST)
        if form.is_valid():
            appointment_date = form.cleaned_data['date']
            appointment_start_time = form.cleaned_data['start_time']
            appointment_end_time = form.cleaned_data.get('end_time')  # si tu as end_time dans ton formulaire

            day_str = appointment_date.strftime('%a')
            availabilities = provider.availabilities.filter(day_of_week=day_str)

            # Vérifier si le créneau est disponible dans les disponibilités
            if not any(a.start_time <= appointment_start_time <= a.end_time for a in availabilities):
                messages.error(request, "Le prestataire n'est pas disponible à cette heure.")
            # Vérifier si le créneau est déjà réservé
            elif Appointment.objects.filter(
                provider=provider, 
                date=appointment_date,
                start_time=appointment_start_time
            ).exists():
                messages.error(request, "Ce créneau est déjà réservé.")
            else:
                # Création du rendez-vous
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
                    message=f"Vous avez un nouveau rendez-vous avec {appointment.client.username} le {appointment.date} à {appointment.start_time}.",
                    appointment=appointment
                )
                Notification.objects.create(
                    user=appointment.client,
                    title="Rendez-vous confirmé",
                    message=f"Votre rendez-vous avec {appointment.provider.user.username} le {appointment.date} à {appointment.start_time} a été créé.",
                    appointment=appointment
                )

                # ================================
                # Notifications par email
                # ================================
                subject_provider = "Nouveau rendez-vous sur AlloRDV"
                message_provider = (
                    f"Bonjour {appointment.provider.user.username},\n\n"
                    f"Vous avez un nouveau rendez-vous avec {appointment.client.username} "
                    f"le {appointment.date} à {appointment.start_time}.\n\nMerci, AlloRDV"
                )
                send_mail(subject_provider, message_provider, settings.DEFAULT_FROM_EMAIL, [appointment.provider.user.email])

                subject_client = "Rendez-vous confirmé sur AlloRDV"
                message_client = (
                    f"Bonjour {appointment.client.username},\n\n"
                    f"Votre rendez-vous avec {appointment.provider.user.username} "
                    f"le {appointment.date} à {appointment.start_time} a été créé.\n\nMerci, AlloRDV"
                )
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
        start_time = request.POST.get("start_time")
        end_time = request.POST.get("end_time")  # si tu veux gérer end_time

        if not (provider_id and category_id and date and start_time):
            messages.error(request, "Veuillez remplir tous les champs !")
            return redirect("appointments:single_booking", service_id=service_id)

        provider = get_object_or_404(Provider, id=provider_id)
        category = get_object_or_404(Category, id=category_id)

        appointment_date_obj = datetime.datetime.strptime(date, "%Y-%m-%d").date()
        appointment_start_time_obj = datetime.datetime.strptime(start_time, "%H:%M").time()
        appointment_end_time_obj = datetime.datetime.strptime(end_time, "%H:%M").time() if end_time else None

        day_str = appointment_date_obj.strftime('%a')
        availabilities = provider.availabilities.filter(day_of_week=day_str)

        # Vérifier si le créneau est disponible dans les disponibilités
        if not any(a.start_time <= appointment_start_time_obj <= a.end_time for a in availabilities):
            messages.error(request, "Le prestataire n'est pas disponible à cette heure.")
            return redirect("appointments:single_booking", service_id=service_id)

        # Vérifier si le créneau est déjà réservé
        if Appointment.objects.filter(
            provider=provider, 
            date=appointment_date_obj,
            start_time=appointment_start_time_obj
        ).exists():
            messages.error(request, "Ce créneau est déjà réservé.")
            return redirect("appointments:single_booking", service_id=service_id)

        # Création du rendez-vous
        appointment = Appointment.objects.create(
            client=request.user,
            provider=provider,
            category=category,
            date=appointment_date_obj,
            start_time=appointment_start_time_obj,
            end_time=appointment_end_time_obj
        )

        # ================================
        # Notifications plateforme
        # ================================
        Notification.objects.create(
            user=appointment.provider.user,
            title="Nouveau rendez-vous",
            message=f"Vous avez un nouveau rendez-vous avec {appointment.client.username} le {appointment.date} à {appointment.start_time}.",
            appointment=appointment
        )
        Notification.objects.create(
            user=appointment.client,
            title="Rendez-vous confirmé",
            message=f"Votre rendez-vous avec {appointment.provider.user.username} le {appointment.date} à {appointment.start_time} a été créé.",
            appointment=appointment
        )

        # ================================
        # Notifications par email
        # ================================
        subject_provider = "Nouveau rendez-vous sur AlloRDV"
        message_provider = f"Bonjour {appointment.provider.user.username},\n\nVous avez un nouveau rendez-vous avec {appointment.client.username} le {appointment.date} à {appointment.start_time}.\n\nMerci, AlloRDV"
        send_mail(subject_provider, message_provider, settings.DEFAULT_FROM_EMAIL, [appointment.provider.user.email])

        subject_client = "Rendez-vous confirmé sur AlloRDV"
        message_client = f"Bonjour {appointment.client.username},\n\nVotre rendez-vous avec {appointment.provider.user.username} le {appointment.date} à {appointment.start_time} a été créé.\n\nMerci, AlloRDV"
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
    # On trie d'abord par date décroissante, puis par heure de début décroissante
    appointments = Appointment.objects.filter(client=request.user).order_by('-date', '-start_time')
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

    from django.forms import inlineformset_factory, modelformset_factory

    AvailabilityFormSet = modelformset_factory(
        Availability, form=AvailabilityForm, extra=0, can_delete=True
    )
    PortfolioFormSet = inlineformset_factory(
        Provider, PortfolioItem, form=PortfolioItemForm, extra=0, can_delete=True
    )

    if request.method == "POST":
        provider_form = ProviderForm(request.POST, request.FILES, instance=provider)
        availability_formset = AvailabilityFormSet(
            request.POST, queryset=provider.availabilities.all()
        )
        portfolio_formset = PortfolioFormSet(
            request.POST, request.FILES, instance=provider
        )

        if provider_form.is_valid() and availability_formset.is_valid() and portfolio_formset.is_valid():
            provider_form.save()
            availability_formset.save()
            portfolio_formset.save()
            messages.success(request, "Profil mis à jour ✅")
            return redirect('appointments:provider_detail', provider_id=provider.id)
        else:
            messages.error(request, "Erreur de validation. Vérifiez les champs et les fichiers uploadés.")
    else:
        provider_form = ProviderForm(instance=provider)
        availability_formset = AvailabilityFormSet(queryset=provider.availabilities.all())
        portfolio_formset = PortfolioFormSet(instance=provider)

    return render(request, "appointments/provider_edit_profile.html", {
        "provider_form": provider_form,
        "availability_formset": availability_formset,
        "portfolio_formset": portfolio_formset,
    })



@login_required
def provider_dashboard(request):
    provider = get_object_or_404(Provider, user=request.user)
    appointments_list = Appointment.objects.filter(provider=provider).order_by('-date', '-start_time')

    paginator = Paginator(appointments_list, 5)  # 5 rendez-vous par page
    page_number = request.GET.get('page')
    appointments = paginator.get_page(page_number)

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
@login_required
def add_portfolio_item(request):
    provider = request.user.provider
    if request.method == "POST":
        form = PortfolioItemForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.provider = provider
            item.save()
            return redirect('provider_profile', provider.id)
    else:
        form = PortfolioItemForm()
    return render(request, 'appointments/provider_detail.html', {'form': form})
@login_required
def ajax_save_portfolio(request):
    from django.http import JsonResponse
    provider = request.user.provider
    item_id = request.POST.get('portfolio_id')
    
    if item_id:
        item = get_object_or_404(PortfolioItem, id=item_id, provider=provider)
        form = PortfolioItemForm(request.POST, request.FILES, instance=item)
    else:
        form = PortfolioItemForm(request.POST, request.FILES)
    
    if form.is_valid():
        new_item = form.save(commit=False)
        new_item.provider = provider
        new_item.save()
        return JsonResponse({
            'status':'success',
            'id': new_item.id,
            'title': new_item.title,
            'description': new_item.description,
            'price': str(new_item.price),
            'image_url': new_item.image.url
        })
    return JsonResponse({'status':'error', 'errors': form.errors})
def provider_agenda(request, provider_id):
    provider = get_object_or_404(Provider, id=provider_id)
    return render(request, 'appointments/provider_agenda.html', {'provider': provider})





SLOT_DURATION = 60  # durée par défaut d’un créneau en minutes
@login_required
def provider_agenda_events(request, provider_id):
    provider = get_object_or_404(Provider, id=provider_id)
    events = []

    today = datetime.today().date()
    next_days = [today + timedelta(days=i) for i in range(7)]  # 7 prochains jours

    # Récupérer les rendez-vous du prestataire
    appointments = Appointment.objects.filter(
        provider=provider,
        date__gte=today,
        date__lte=today + timedelta(days=6)
    )
    booked_slots = {}
    for a in appointments:
        booked_slots.setdefault(a.date, []).append((a.start_time, a.end_time))

    # Parcours des disponibilités
    for avail in provider.availabilities.all():
        for day_date in next_days:
            if day_date.strftime('%a') != avail.day_of_week:
                continue

            current_time = datetime.combine(day_date, avail.start_time)
            end_time = datetime.combine(day_date, avail.end_time)

            while current_time + timedelta(minutes=SLOT_DURATION) <= end_time:
                slot_end = current_time + timedelta(minutes=SLOT_DURATION)

                # ===== Gestion des pauses =====
                in_break = False
                if avail.break_start and avail.break_end:
                    break_start_dt = datetime.combine(day_date, avail.break_start)
                    break_end_dt = datetime.combine(day_date, avail.break_end)
                    # Vérifie si le slot chevauche la pause
                    if current_time < break_end_dt and slot_end > break_start_dt:
                        in_break = True

                if not in_break:
                    # Vérifier si le créneau est déjà réservé
                    booked = False
                    for b_start, b_end in booked_slots.get(day_date, []):
                        # Ignorer si b_start ou b_end est None
                        if b_start and b_end and b_start < slot_end.time() and b_end > current_time.time():
                            booked = True
                            break

                    events.append({
                        'title': 'Réservé' if booked else 'Libre',
                        'start': current_time.isoformat(),
                        'end': slot_end.isoformat(),
                        'color': '#d63031' if booked else '#00b894',
                        'editable': False,
                        'extendedProps': {'booked': booked}
                    })

                current_time = slot_end

    return JsonResponse(events, safe=False)



@login_required
def book_appointment_ajax(request):
    if request.method == 'POST' and request.user.is_authenticated:
        provider_id = request.POST.get('provider_id')
        start = request.POST.get('start')
        provider = get_object_or_404(Provider, id=provider_id)

        start_dt = datetime.fromisoformat(start)
        end_dt = start_dt + timedelta(minutes=SLOT_DURATION)  # durée du créneau

        # Vérifier si le créneau est déjà réservé
        conflict = Appointment.objects.filter(
            provider=provider,
            date=start_dt.date(),
            start_time__lt=end_dt.time(),
            end_time__gt=start_dt.time()
        ).exists()

        if conflict:
            return JsonResponse({'status': 'error', 'message': 'Créneau déjà réservé'})

        # Créer le rendez-vous
        Appointment.objects.create(
            provider=provider,
            client=request.user,
            date=start_dt.date(),
            start_time=start_dt.time(),
            end_time=end_dt.time()
        )

        return JsonResponse({'status': 'success'})

    return JsonResponse({'status': 'error', 'message': 'Méthode invalide'})
@login_required
def ajax_save_availability(request):
    provider = request.user.provider
    if request.method == "POST":
        avail_id = request.POST.get('availability_id')
        if avail_id:
            availability = get_object_or_404(Availability, id=avail_id, provider=provider)
            form = AvailabilityForm(request.POST, instance=availability)
        else:
            form = AvailabilityForm(request.POST)
        
        if form.is_valid():
            availability = form.save(commit=False)
            availability.provider = provider
            availability.save()
            return JsonResponse({
                'status': 'success',
                'id': availability.id,
                'day_of_week': availability.day_of_week,
                'start_time': availability.start_time.strftime('%H:%M'),
                'end_time': availability.end_time.strftime('%H:%M'),
                'break_start': availability.break_start.strftime('%H:%M') if availability.break_start else '',
                'break_end': availability.break_end.strftime('%H:%M') if availability.break_end else '',
            })
        else:
            return JsonResponse({'status': 'error', 'errors': form.errors})
    return JsonResponse({'status': 'error', 'message': 'Méthode invalide'})

