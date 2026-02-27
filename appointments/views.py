from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.conf import settings
from django.forms import inlineformset_factory
from django.contrib.auth import authenticate, login
from django.core.mail import EmailMultiAlternatives
from django.http import HttpResponseForbidden
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.urls import reverse
from django.utils import timezone
from django.db.models import Count, Q

from .models import (
    Appointment,
    Availability,
    BlockedSlot,
    Category,
    Notification,
    Provider,
    Service,
)
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


AVAILABILITY_TEMPLATES = {
    "classic_9_17": {
        "label": "Semaine classique (Lun-Ven 09:00-17:00, pause 12:30-13:30)",
        "entries": [
            {"day": "Mon", "start": "09:00", "end": "17:00", "break_start": "12:30", "break_end": "13:30"},
            {"day": "Tue", "start": "09:00", "end": "17:00", "break_start": "12:30", "break_end": "13:30"},
            {"day": "Wed", "start": "09:00", "end": "17:00", "break_start": "12:30", "break_end": "13:30"},
            {"day": "Thu", "start": "09:00", "end": "17:00", "break_start": "12:30", "break_end": "13:30"},
            {"day": "Fri", "start": "09:00", "end": "17:00", "break_start": "12:30", "break_end": "13:30"},
        ],
    },
    "extended_8_18": {
        "label": "Semaine etendue (Lun-Sam 08:00-18:00, pause 13:00-14:00)",
        "entries": [
            {"day": "Mon", "start": "08:00", "end": "18:00", "break_start": "13:00", "break_end": "14:00"},
            {"day": "Tue", "start": "08:00", "end": "18:00", "break_start": "13:00", "break_end": "14:00"},
            {"day": "Wed", "start": "08:00", "end": "18:00", "break_start": "13:00", "break_end": "14:00"},
            {"day": "Thu", "start": "08:00", "end": "18:00", "break_start": "13:00", "break_end": "14:00"},
            {"day": "Fri", "start": "08:00", "end": "18:00", "break_start": "13:00", "break_end": "14:00"},
            {"day": "Sat", "start": "08:00", "end": "13:00", "break_start": "", "break_end": ""},
        ],
    },
    "continuous_morning": {
        "label": "Matinee continue (Lun-Sam 07:30-14:30, sans pause)",
        "entries": [
            {"day": "Mon", "start": "07:30", "end": "14:30", "break_start": "", "break_end": ""},
            {"day": "Tue", "start": "07:30", "end": "14:30", "break_start": "", "break_end": ""},
            {"day": "Wed", "start": "07:30", "end": "14:30", "break_start": "", "break_end": ""},
            {"day": "Thu", "start": "07:30", "end": "14:30", "break_start": "", "break_end": ""},
            {"day": "Fri", "start": "07:30", "end": "14:30", "break_start": "", "break_end": ""},
            {"day": "Sat", "start": "07:30", "end": "14:30", "break_start": "", "break_end": ""},
        ],
    },
}
# =======================================================
# 🏠 VUES GÉNÉRALES
# =======================================================

def _build_booking_email_context(request, appointment, recipient_type):
    provider_user = appointment.provider.user
    client_user = appointment.client
    recipient_user = provider_user if recipient_type == "provider" else client_user
    recipient_email = recipient_user.email
    recipient_name = recipient_user.get_full_name().strip() or recipient_user.username

    date_label = appointment.date.strftime("%d/%m/%Y")
    start_label = appointment.start_time.strftime("%H:%M")
    end_label = appointment.end_time.strftime("%H:%M") if appointment.end_time else ""
    slot_label = f"{start_label} - {end_label}" if end_label else start_label
    category_name = appointment.category.name if appointment.category else "-"
    service_name = (
        appointment.category.service.name
        if appointment.category and appointment.category.service
        else "-"
    )
    notes = (appointment.notes or "").strip()

    if recipient_type == "provider":
        subject = "Nouveau rendez-vous sur AlloRDV"
        eyebrow = "Nouveau rendez-vous"
        heading = "Un client a reserve un creneau"
        intro = f"{client_user.username} vient de faire une reservation avec vous."
        action_label = "Ouvrir mon dashboard"
        action_url = request.build_absolute_uri(reverse("appointments:provider_dashboard"))
        role_note = "Confirmez ou mettez a jour le statut du rendez-vous depuis votre espace prestataire."
    else:
        subject = "Rendez-vous confirme sur AlloRDV"
        eyebrow = "Reservation confirmee"
        heading = "Votre rendez-vous est bien enregistre"
        intro = f"Votre demande avec {provider_user.username} a bien ete prise en compte."
        action_label = "Voir mes rendez-vous"
        action_url = request.build_absolute_uri(reverse("appointments:my_appointments"))
        role_note = "Retrouvez ce rendez-vous et son statut dans votre espace client."

    return {
        "subject": subject,
        "recipient_email": recipient_email,
        "recipient_name": recipient_name,
        "eyebrow": eyebrow,
        "heading": heading,
        "intro": intro,
        "role_note": role_note,
        "action_label": action_label,
        "action_url": action_url,
        "provider_name": provider_user.username,
        "client_name": client_user.username,
        "service_name": service_name,
        "category_name": category_name,
        "date_label": date_label,
        "slot_label": slot_label,
        "notes": notes,
        "logo_url": request.build_absolute_uri(static("images/Logo..png")),
        "current_year": timezone.now().year,
    }


def _send_booking_email(request, appointment, recipient_type):
    context = _build_booking_email_context(request, appointment, recipient_type)
    recipient_email = context.get("recipient_email")
    if not recipient_email:
        return

    html_body = render_to_string(
        "appointments/email/booking_notification_message.html",
        context,
    )
    text_body = render_to_string(
        "appointments/email/booking_notification_message.txt",
        context,
    )

    email = EmailMultiAlternatives(
        subject=context["subject"],
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[recipient_email],
    )
    email.attach_alternative(html_body, "text/html")
    email.send(fail_silently=True)


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


def _time_overlaps(start_a, end_a, start_b, end_b):
    return start_a < end_b and end_a > start_b


def _appointment_end_datetime(target_date, start_time_obj, end_time_obj=None):
    start_dt = datetime.combine(target_date, start_time_obj)
    if end_time_obj:
        return datetime.combine(target_date, end_time_obj)
    return start_dt + timedelta(minutes=SLOT_DURATION)


def _compute_available_slots(provider, target_date):
    day_str = target_date.strftime("%a")
    slot_delta = timedelta(minutes=SLOT_DURATION)
    slots = []

    appointments = Appointment.objects.filter(
        provider=provider,
        date=target_date,
        status__in=["pending", "accepted", "done"],
    ).only("start_time", "end_time")
    blocked_slots = BlockedSlot.objects.filter(
        provider=provider,
        date=target_date,
    ).only("start_time", "end_time")

    existing_windows = []
    for appointment in appointments:
        start_dt = datetime.combine(target_date, appointment.start_time)
        end_dt = _appointment_end_datetime(
            target_date,
            appointment.start_time,
            appointment.end_time,
        )
        existing_windows.append((start_dt, end_dt))

    for blocked_slot in blocked_slots:
        start_dt = datetime.combine(target_date, blocked_slot.start_time)
        end_dt = datetime.combine(target_date, blocked_slot.end_time)
        existing_windows.append((start_dt, end_dt))

    now_dt = datetime.now()
    for availability in provider.availabilities.filter(day_of_week=day_str):
        current = datetime.combine(target_date, availability.start_time)
        availability_end = datetime.combine(target_date, availability.end_time)

        break_start_dt = (
            datetime.combine(target_date, availability.break_start)
            if availability.break_start
            else None
        )
        break_end_dt = (
            datetime.combine(target_date, availability.break_end)
            if availability.break_end
            else None
        )

        while current + slot_delta <= availability_end:
            slot_end = current + slot_delta

            if target_date == now_dt.date() and current <= now_dt:
                current = slot_end
                continue

            if break_start_dt and break_end_dt and _time_overlaps(current, slot_end, break_start_dt, break_end_dt):
                current = slot_end
                continue

            if any(_time_overlaps(current, slot_end, appt_start, appt_end) for appt_start, appt_end in existing_windows):
                current = slot_end
                continue

            slots.append(current.time())
            current = slot_end

    return slots

# =======================================================
# 📅 RÉSERVATION CLIENT
# =======================================================
@login_required
def book_appointment(request, provider_id):
    provider = get_object_or_404(Provider, id=provider_id)
    category = provider.category
    category_id = request.GET.get("category")
    if category_id:
        category = get_object_or_404(Category, id=category_id, service=provider.service)

    if not category:
        messages.error(request, "Aucune categorie n'est liee a ce prestataire.")
        return redirect("appointments:services_list")

    if request.method == "POST":
        form = AppointmentForm(request.POST)
        if form.is_valid():
            appointment_date = form.cleaned_data["date"]
            appointment_start_time = form.cleaned_data["start_time"]
            appointment_end_time = form.cleaned_data.get("end_time")

            if appointment_date < datetime.today().date():
                messages.error(request, "La date du rendez-vous doit etre aujourd'hui ou plus tard.")
                return redirect("appointments:book_appointment", provider_id=provider.id)

            available_slots = _compute_available_slots(provider, appointment_date)
            if appointment_start_time not in available_slots:
                messages.error(request, "Ce creneau n'est plus disponible.")
                return redirect("appointments:book_appointment", provider_id=provider.id)

            if not appointment_end_time:
                appointment_end_time = _appointment_end_datetime(
                    appointment_date,
                    appointment_start_time,
                ).time()

            appointment = form.save(commit=False)
            appointment.client = request.user
            appointment.provider = provider
            appointment.category = category
            appointment.end_time = appointment_end_time
            appointment.save()

            Notification.objects.create(
                user=appointment.provider.user,
                title="Nouveau rendez-vous",
                message=f"Vous avez un nouveau rendez-vous avec {appointment.client.username} le {appointment.date} a {appointment.start_time}.",
                appointment=appointment,
            )
            Notification.objects.create(
                user=appointment.client,
                title="Rendez-vous confirme",
                message=f"Votre rendez-vous avec {appointment.provider.user.username} le {appointment.date} a {appointment.start_time} a ete cree.",
                appointment=appointment,
            )

            _send_booking_email(request, appointment, "provider")
            _send_booking_email(request, appointment, "client")

            messages.success(request, "Rendez-vous cree avec succes.")
            return redirect("appointments:my_appointments")
        else:
            messages.error(request, "Erreur de validation. Verifiez les champs.")
    else:
        form = AppointmentForm()

    return render(request, "appointments/book_appointment.html", {
        "provider": provider,
        "form": form,
        "category": category,
        "min_date": datetime.today().date().isoformat(),
    })


@login_required
def single_page_booking(request, service_id=None):
    if service_id is None:
        return redirect("appointments:services_list")

    service = get_object_or_404(Service, id=service_id, is_active=True)
    categories = Category.objects.filter(service=service).order_by("name")
    providers = service.providers.select_related("user").order_by("user__username")
    is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"

    def fail(message, status=400):
        if is_ajax:
            return JsonResponse({"status": "error", "message": message}, status=status)
        messages.error(request, message)
        return redirect("appointments:single_booking_service", service_id=service_id)

    if request.method == "POST":
        provider_id = request.POST.get("provider")
        category_id = request.POST.get("category")
        date = request.POST.get("date")
        start_time = request.POST.get("start_time")
        notes = (request.POST.get("notes") or "").strip()

        if not (provider_id and category_id and date and start_time):
            return fail("Veuillez remplir tous les champs !")

        provider = get_object_or_404(Provider, id=provider_id, service=service)
        category = get_object_or_404(Category, id=category_id, service=service)

        if provider.category_id and provider.category_id != category.id:
            return fail("La categorie choisie ne correspond pas au prestataire.")

        try:
            appointment_date_obj = datetime.strptime(date, "%Y-%m-%d").date()
            appointment_start_time_obj = datetime.strptime(start_time, "%H:%M").time()
        except ValueError:
            return fail("Format de date ou d'heure invalide.")

        if appointment_date_obj < datetime.today().date():
            return fail("La date du rendez-vous doit etre aujourd'hui ou plus tard.")

        available_slots = _compute_available_slots(provider, appointment_date_obj)
        if appointment_start_time_obj not in available_slots:
            return fail("Ce creneau n'est plus disponible.")

        appointment_end_time_obj = _appointment_end_datetime(
            appointment_date_obj,
            appointment_start_time_obj,
        ).time()

        appointment = Appointment.objects.create(
            client=request.user,
            provider=provider,
            category=category,
            date=appointment_date_obj,
            start_time=appointment_start_time_obj,
            end_time=appointment_end_time_obj,
            notes=notes,
        )

        Notification.objects.create(
            user=appointment.provider.user,
            title="Nouveau rendez-vous",
            message=f"Vous avez un nouveau rendez-vous avec {appointment.client.username} le {appointment.date} a {appointment.start_time}.",
            appointment=appointment,
        )
        Notification.objects.create(
            user=appointment.client,
            title="Rendez-vous confirme",
            message=f"Votre rendez-vous avec {appointment.provider.user.username} le {appointment.date} a {appointment.start_time} a ete cree.",
            appointment=appointment,
        )

        _send_booking_email(request, appointment, "provider")
        _send_booking_email(request, appointment, "client")

        if is_ajax:
            return JsonResponse(
                {
                    "status": "success",
                    "message": "Rendez-vous cree avec succes.",
                    "redirect_url": reverse("appointments:my_appointments"),
                }
            )

        messages.success(request, "Rendez-vous cree avec succes.")
        return redirect("appointments:my_appointments")

    return render(request, "appointments/single_booking.html", {
        "service": service,
        "categories": categories,
        "providers": providers,
        "min_date": datetime.today().date().isoformat(),
    })


@login_required
def my_appointments(request):
    # On trie d'abord par date décroissante, puis par heure de début décroissante
    appointments = Appointment.objects.filter(client=request.user).order_by('-date', '-start_time')
    return render(request, "appointments/my_appointments.html", {"appointments": appointments})

@login_required
def cancel_appointment(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id, client=request.user)

    if request.method != "POST":
        return redirect('appointments:my_appointments')

    if appointment.transition_to('cancelled'):
        messages.success(request, "Rendez-vous annulé.")
    else:
        messages.error(
            request,
            f"Impossible d'annuler un rendez-vous '{appointment.get_status_display()}'.",
        )

    return redirect('appointments:my_appointments')

# =======================================================
# 🧑‍🔧 VUES PRESTATAIRE
# =======================================================

@login_required
def provider_detail(request, provider_id):
    provider = get_object_or_404(
        Provider.objects.select_related("user", "service", "category").prefetch_related(
            "portfolio",
            "availabilities",
        ),
        id=provider_id,
    )

    profile = getattr(request.user, "profile", None)
    is_owner = provider.user_id == request.user.id
    can_book = not is_owner and getattr(profile, "role", "") == "client"

    display_name = (
        f"{provider.user.first_name} {provider.user.last_name}".strip()
        or provider.user.username
    )

    availability_map = {day_code: [] for day_code, _ in Availability.DAYS_OF_WEEK}
    for availability in provider.availabilities.all():
        slot = (
            f"{availability.start_time.strftime('%H:%M')} - "
            f"{availability.end_time.strftime('%H:%M')}"
        )
        if availability.break_start and availability.break_end:
            slot += (
                f" (pause {availability.break_start.strftime('%H:%M')}"
                f"-{availability.break_end.strftime('%H:%M')})"
            )
        availability_map.setdefault(availability.day_of_week, []).append(slot)

    weekly_availability = []
    open_days_count = 0
    for day_code, day_label in Availability.DAYS_OF_WEEK:
        slots = availability_map.get(day_code, [])
        if slots:
            open_days_count += 1
        weekly_availability.append(
            {
                "code": day_code,
                "label": day_label,
                "slots": slots,
            }
        )

    portfolio_items = list(provider.portfolio.all().order_by("-created_at"))
    context = {
        "provider": provider,
        "display_name": display_name,
        "is_owner": is_owner,
        "can_book": can_book,
        "weekly_availability": weekly_availability,
        "open_days_count": open_days_count,
        "portfolio_items": portfolio_items,
        "portfolio_count": len(portfolio_items),
    }
    return render(request, "appointments/provider_detail.html", context)


@login_required
def provider_edit_profile(request):
    provider = _ensure_provider_access(request)
    if not provider:
        return redirect('appointments:services_list')

    from django.forms import inlineformset_factory, modelformset_factory

    AvailabilityFormSet = modelformset_factory(
        Availability, form=AvailabilityForm, extra=0, can_delete=True
    )
    PortfolioFormSet = inlineformset_factory(
        Provider, PortfolioItem, form=PortfolioItemForm, extra=0, can_delete=True
    )

    if request.method == "POST":
        provider_form = ProviderForm(request.POST, request.FILES, instance=provider)
        if provider_form.is_valid():
            provider_form.save()
            messages.success(request, "Profil mis à jour ✅")
            return redirect('appointments:provider_edit_profile')
        else:
            messages.error(request, "Erreur de validation. Vérifiez les champs et les fichiers uploadés.")
    else:
        provider_form = ProviderForm(instance=provider)

    # Les disponibilités et le portfolio sont gérés via AJAX sur cette page,
    # donc on affiche simplement la liste existante.
    availability_formset = AvailabilityFormSet(queryset=provider.availabilities.all())
    portfolio_formset = PortfolioFormSet(instance=provider)

    return render(request, "appointments/provider_edit_profile.html", {
        "provider_form": provider_form,
        "availability_formset": availability_formset,
        "portfolio_formset": portfolio_formset,
        "availability_templates": [
            {"key": key, "label": value["label"]}
            for key, value in AVAILABILITY_TEMPLATES.items()
        ],
        "days_of_week": Availability.DAYS_OF_WEEK,
    })



@login_required
def provider_dashboard(request):
    provider = _ensure_provider_access(request)
    if not provider:
        return redirect('appointments:services_list')

    base_qs = (
        Appointment.objects.filter(provider=provider)
        .select_related("client", "category__service")
    )
    today = timezone.localdate()
    total_count = base_qs.count()

    status_rows = base_qs.values("status").annotate(total=Count("id"))
    status_counts = {row["status"]: row["total"] for row in status_rows}

    search_query = (request.GET.get("q") or "").strip()
    status_filter = (request.GET.get("status") or "all").strip()
    period_filter = (request.GET.get("period") or "all").strip()

    allowed_status = {"all", "pending", "accepted", "refused", "cancelled", "done"}
    allowed_period = {"all", "today", "upcoming", "past"}
    if status_filter not in allowed_status:
        status_filter = "all"
    if period_filter not in allowed_period:
        period_filter = "all"

    appointments_list = base_qs
    if search_query:
        appointments_list = appointments_list.filter(
            Q(client__username__icontains=search_query)
            | Q(category__name__icontains=search_query)
            | Q(category__service__name__icontains=search_query)
        )
    if status_filter != "all":
        appointments_list = appointments_list.filter(status=status_filter)

    if period_filter == "today":
        appointments_list = appointments_list.filter(date=today).order_by("date", "start_time")
    elif period_filter == "upcoming":
        appointments_list = appointments_list.filter(date__gte=today).order_by("date", "start_time")
    elif period_filter == "past":
        appointments_list = appointments_list.filter(date__lt=today).order_by("-date", "-start_time")
    else:
        appointments_list = appointments_list.order_by("-date", "-start_time")

    paginator = Paginator(appointments_list, 8)
    page_number = request.GET.get('page')
    appointments = paginator.get_page(page_number)

    status_meta = [
        ("all", "Tous"),
        ("pending", "En attente"),
        ("accepted", "Acceptes"),
        ("done", "Termines"),
        ("refused", "Refuses"),
        ("cancelled", "Annules"),
    ]
    status_filters = []
    for key, label in status_meta:
        params = request.GET.copy()
        params.pop("page", None)
        if key == "all":
            params.pop("status", None)
        else:
            params["status"] = key
        query = params.urlencode()
        status_filters.append(
            {
                "key": key,
                "label": label,
                "count": total_count if key == "all" else status_counts.get(key, 0),
                "active": key == status_filter,
                "url": f"?{query}" if query else "?",
            }
        )

    pagination_params = request.GET.copy()
    pagination_params.pop("page", None)

    next_appointment = (
        base_qs.filter(date__gte=today, status__in=["pending", "accepted"])
        .order_by("date", "start_time")
        .first()
    )

    context = {
        "appointments": appointments,
        "provider": provider,
        "today": today,
        "next_appointment": next_appointment,
        "search_query": search_query,
        "active_status": status_filter,
        "active_period": period_filter,
        "status_filters": status_filters,
        "pagination_query": pagination_params.urlencode(),
        "kpis": {
            "total": total_count,
            "today": base_qs.filter(date=today).count(),
            "pending": status_counts.get("pending", 0),
            "accepted": status_counts.get("accepted", 0),
            "done": status_counts.get("done", 0),
        },
    }
    return render(request, "dashboard/provider_dashboard.html", context)

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

    providers = Provider.objects.filter(category_id=category_id).select_related("user").order_by("user__username")
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

@login_required
def ajax_available_slots(request):
    provider_id = request.GET.get("provider_id")
    date_str = request.GET.get("date")

    if not provider_id or not date_str:
        return JsonResponse(
            {"status": "error", "message": "Parametres manquants."},
            status=400,
        )

    provider = get_object_or_404(Provider, id=provider_id)
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return JsonResponse(
            {"status": "error", "message": "Date invalide."},
            status=400,
        )

    if target_date < datetime.today().date():
        return JsonResponse({"status": "success", "slots": []})

    slots = _compute_available_slots(provider, target_date)
    return JsonResponse(
        {
            "status": "success",
            "slots": [slot.strftime("%H:%M") for slot in slots],
        }
    )


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
    tab = (request.GET.get("tab") or request.POST.get("tab") or "all").strip().lower()
    if tab not in {"all", "unread"}:
        tab = "all"

    if request.method == "POST":
        if "mark_one" in request.POST:
            notif_id = request.POST.get("notif_id")
            notif = get_object_or_404(Notification, id=notif_id, user=request.user)
            if not notif.is_read:
                notif.is_read = True
                notif.save(update_fields=["is_read"])
        elif "mark_all" in request.POST:
            Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        query = f"?tab={tab}" if tab != "all" else ""
        return redirect(f"{request.path}{query}")

    notifications_qs = Notification.objects.filter(user=request.user).order_by("-created_at")
    if tab == "unread":
        notifications_qs = notifications_qs.filter(is_read=False)

    total_count = Notification.objects.filter(user=request.user).count()
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()

    return render(
        request,
        "notifications/notifications_page.html",
        {
            "notifications": notifications_qs,
            "total_count": total_count,
            "unread_count": unread_count,
            "active_tab": tab,
        },
    )
@login_required
def add_portfolio_item(request):
    provider = _ensure_provider_access(request)
    if not provider:
        return redirect('appointments:services_list')
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
    provider = _ensure_provider_access(request)
    if not provider:
        return JsonResponse({'status': 'error', 'message': 'Accès refusé'})
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


@login_required
def ajax_delete_portfolio(request, item_id):
    provider = _ensure_provider_access(request)
    if not provider:
        return JsonResponse({'status': 'error', 'message': 'Acces refuse'}, status=403)
    if request.method != "POST":
        return JsonResponse({'status': 'error', 'message': 'Methode invalide'}, status=405)

    item = get_object_or_404(PortfolioItem, id=item_id, provider=provider)
    item.delete()
    return JsonResponse({'status': 'success'})


@login_required
def provider_agenda(request, provider_id):
    provider = get_object_or_404(Provider, id=provider_id)
    owner = _ensure_provider_access(request)
    if not owner or owner.id != provider.id:
        return redirect("appointments:provider_dashboard")
    return render(request, "appointments/provider_agenda.html", {"provider": provider})


SLOT_DURATION = 60  # default slot duration in minutes


def _parse_iso_datetime(value):
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(timezone.get_current_timezone()).replace(tzinfo=None)
        return parsed
    except (AttributeError, ValueError):
        return None


@login_required
def provider_agenda_events(request, provider_id):
    provider = get_object_or_404(Provider, id=provider_id)
    owner = _ensure_provider_access(request)
    if not owner or owner.id != provider.id:
        return HttpResponseForbidden()

    start_dt = _parse_iso_datetime(request.GET.get("start"))
    end_dt = _parse_iso_datetime(request.GET.get("end"))
    if start_dt and end_dt:
        window_start = start_dt.date()
        window_end = (end_dt - timedelta(days=1)).date()
    else:
        window_start = datetime.today().date()
        window_end = window_start + timedelta(days=6)
    if window_end < window_start:
        window_end = window_start

    events = []
    status_colors = {
        "pending": "#f59e0b",
        "accepted": "#22c55e",
        "refused": "#ef4444",
        "cancelled": "#6b7280",
        "done": "#3b82f6",
    }
    blocking_statuses = {"pending", "accepted", "done"}

    appointments = list(
        Appointment.objects.filter(
            provider=provider,
            date__gte=window_start,
            date__lte=window_end,
        )
        .select_related("client", "category__service")
        .order_by("date", "start_time")
    )
    blocked_slots = list(
        BlockedSlot.objects.filter(
            provider=provider,
            date__gte=window_start,
            date__lte=window_end,
        ).order_by("date", "start_time")
    )

    occupied_by_day = {}
    for appointment in appointments:
        appointment_start = datetime.combine(appointment.date, appointment.start_time)
        appointment_end = _appointment_end_datetime(
            appointment.date,
            appointment.start_time,
            appointment.end_time,
        )
        if appointment.status in blocking_statuses:
            occupied_by_day.setdefault(appointment.date, []).append((appointment_start, appointment_end))

        events.append(
            {
                "id": f"appt-{appointment.id}",
                "title": f"{appointment.client.username} - {appointment.category.name}",
                "start": appointment_start.isoformat(),
                "end": appointment_end.isoformat(),
                "color": status_colors.get(appointment.status, "#334155"),
                "extendedProps": {
                    "eventType": "appointment",
                    "appointmentId": appointment.id,
                    "status": appointment.status,
                    "statusLabel": appointment.get_status_display(),
                    "client": appointment.client.username,
                    "service": appointment.category.service.name if appointment.category_id else "",
                    "category": appointment.category.name if appointment.category_id else "",
                    "notes": appointment.notes or "",
                    "canAccept": appointment.can_transition_to("accepted"),
                    "canRefuse": appointment.can_transition_to("refused"),
                    "canCancel": appointment.can_transition_to("cancelled"),
                    "canDone": appointment.can_transition_to("done"),
                },
            }
        )

    for block in blocked_slots:
        blocked_start = datetime.combine(block.date, block.start_time)
        blocked_end = datetime.combine(block.date, block.end_time)
        occupied_by_day.setdefault(block.date, []).append((blocked_start, blocked_end))
        events.append(
            {
                "id": f"block-{block.id}",
                "title": "Bloque",
                "start": blocked_start.isoformat(),
                "end": blocked_end.isoformat(),
                "color": "#475569",
                "extendedProps": {
                    "eventType": "blocked",
                    "blockId": block.id,
                    "reason": block.reason or "",
                },
            }
        )

    now_dt = datetime.now()
    for availability in provider.availabilities.all():
        current_day = window_start
        while current_day <= window_end:
            if current_day.strftime("%a") != availability.day_of_week:
                current_day += timedelta(days=1)
                continue

            current_slot = datetime.combine(current_day, availability.start_time)
            availability_end = datetime.combine(current_day, availability.end_time)
            break_start_dt = (
                datetime.combine(current_day, availability.break_start)
                if availability.break_start
                else None
            )
            break_end_dt = (
                datetime.combine(current_day, availability.break_end)
                if availability.break_end
                else None
            )

            while current_slot + timedelta(minutes=SLOT_DURATION) <= availability_end:
                slot_end = current_slot + timedelta(minutes=SLOT_DURATION)

                if current_day == now_dt.date() and current_slot <= now_dt:
                    current_slot = slot_end
                    continue

                if break_start_dt and break_end_dt and _time_overlaps(
                    current_slot,
                    slot_end,
                    break_start_dt,
                    break_end_dt,
                ):
                    current_slot = slot_end
                    continue

                occupied_windows = occupied_by_day.get(current_day, [])
                if any(_time_overlaps(current_slot, slot_end, start, end) for start, end in occupied_windows):
                    current_slot = slot_end
                    continue

                events.append(
                    {
                        "id": f"slot-{current_slot.isoformat()}",
                        "title": "Libre",
                        "start": current_slot.isoformat(),
                        "end": slot_end.isoformat(),
                        "color": "#0ea5a4",
                        "extendedProps": {
                            "eventType": "slot",
                        },
                    }
                )
                current_slot = slot_end

            current_day += timedelta(days=1)

    return JsonResponse(events, safe=False)


@login_required
def provider_toggle_slot_block_ajax(request):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Methode invalide"}, status=405)

    provider_id = request.POST.get("provider_id")
    start = request.POST.get("start")
    end = request.POST.get("end")
    if not provider_id or not start or not end:
        return JsonResponse({"status": "error", "message": "Parametres manquants."}, status=400)

    provider = get_object_or_404(Provider, id=provider_id)
    owner = _ensure_provider_access(request)
    if not owner or owner.id != provider.id:
        return JsonResponse({"status": "error", "message": "Acces refuse"}, status=403)

    start_dt = _parse_iso_datetime(start)
    end_dt = _parse_iso_datetime(end)
    if not start_dt or not end_dt or end_dt <= start_dt:
        return JsonResponse({"status": "error", "message": "Creneau invalide."}, status=400)

    target_date = start_dt.date()
    if target_date < datetime.today().date():
        return JsonResponse({"status": "error", "message": "Impossible de modifier un creneau passe."}, status=400)

    day_str = target_date.strftime("%a")
    slot_is_within_availability = False
    for availability in provider.availabilities.filter(day_of_week=day_str):
        availability_start = datetime.combine(target_date, availability.start_time)
        availability_end = datetime.combine(target_date, availability.end_time)
        if start_dt < availability_start or end_dt > availability_end:
            continue

        break_start_dt = (
            datetime.combine(target_date, availability.break_start)
            if availability.break_start
            else None
        )
        break_end_dt = (
            datetime.combine(target_date, availability.break_end)
            if availability.break_end
            else None
        )
        if break_start_dt and break_end_dt and _time_overlaps(start_dt, end_dt, break_start_dt, break_end_dt):
            continue

        slot_is_within_availability = True
        break

    if not slot_is_within_availability:
        return JsonResponse(
            {"status": "error", "message": "Le creneau n'est pas dans vos disponibilites."},
            status=400,
        )

    blocking_statuses = {"pending", "accepted", "done"}
    same_day_appointments = Appointment.objects.filter(
        provider=provider,
        date=target_date,
        status__in=blocking_statuses,
    ).only("start_time", "end_time")
    for appointment in same_day_appointments:
        appointment_start = datetime.combine(target_date, appointment.start_time)
        appointment_end = _appointment_end_datetime(
            target_date,
            appointment.start_time,
            appointment.end_time,
        )
        if _time_overlaps(start_dt, end_dt, appointment_start, appointment_end):
            return JsonResponse(
                {"status": "error", "message": "Ce creneau contient deja un rendez-vous."},
                status=400,
            )

    existing_block = BlockedSlot.objects.filter(
        provider=provider,
        date=target_date,
        start_time=start_dt.time(),
        end_time=end_dt.time(),
    ).first()

    if existing_block:
        existing_block.delete()
        return JsonResponse(
            {
                "status": "success",
                "action": "unblocked",
                "message": "Creneau debloque.",
            }
        )

    BlockedSlot.objects.create(
        provider=provider,
        date=target_date,
        start_time=start_dt.time(),
        end_time=end_dt.time(),
        reason=(request.POST.get("reason") or "").strip(),
    )
    return JsonResponse(
        {
            "status": "success",
            "action": "blocked",
            "message": "Creneau bloque.",
        }
    )


@login_required
def provider_update_appointment_status_ajax(request, appointment_id):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Methode invalide"}, status=405)

    provider = _ensure_provider_access(request)
    if not provider:
        return JsonResponse({"status": "error", "message": "Acces refuse"}, status=403)

    appointment = get_object_or_404(Appointment, id=appointment_id, provider=provider)
    target_status = (request.POST.get("status") or "").strip()
    allowed_statuses = {"accepted", "refused", "cancelled", "done"}
    if target_status not in allowed_statuses:
        return JsonResponse({"status": "error", "message": "Statut invalide."}, status=400)

    if not appointment.transition_to(target_status):
        return JsonResponse(
            {
                "status": "error",
                "message": f"Transition invalide depuis '{appointment.get_status_display()}'.",
            },
            status=400,
        )

    return JsonResponse(
        {
            "status": "success",
            "appointment_id": appointment.id,
            "new_status": appointment.status,
            "status_label": appointment.get_status_display(),
        }
    )


@login_required
def provider_blocked_slots_ajax(request):
    provider = _ensure_provider_access(request)
    if not provider:
        return JsonResponse({"status": "error", "message": "Acces refuse"}, status=403)

    date_str = request.GET.get("date")
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else datetime.today().date()
    except ValueError:
        return JsonResponse({"status": "error", "message": "Date invalide."}, status=400)

    blocked_slots = (
        BlockedSlot.objects.filter(provider=provider, date=target_date)
        .order_by("start_time")
        .only("id", "start_time", "end_time", "reason")
    )
    return JsonResponse(
        {
            "status": "success",
            "date": target_date.isoformat(),
            "slots": [
                {
                    "id": slot.id,
                    "start_time": slot.start_time.strftime("%H:%M"),
                    "end_time": slot.end_time.strftime("%H:%M"),
                    "reason": slot.reason or "",
                }
                for slot in blocked_slots
            ],
        }
    )


@login_required
def provider_create_blocked_slot_ajax(request):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Methode invalide"}, status=405)

    provider = _ensure_provider_access(request)
    if not provider:
        return JsonResponse({"status": "error", "message": "Acces refuse"}, status=403)

    date_str = (request.POST.get("date") or "").strip()
    start_time_str = (request.POST.get("start_time") or "").strip()
    reason = (request.POST.get("reason") or "").strip()
    duration_raw = (request.POST.get("duration") or "").strip()

    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        start_time = datetime.strptime(start_time_str, "%H:%M").time()
        duration = int(duration_raw)
    except (TypeError, ValueError):
        return JsonResponse({"status": "error", "message": "Champs invalides."}, status=400)

    if duration not in {30, 60, 90, 120}:
        return JsonResponse({"status": "error", "message": "Duree invalide."}, status=400)
    if target_date < datetime.today().date():
        return JsonResponse({"status": "error", "message": "Impossible de bloquer une date passee."}, status=400)

    start_dt = datetime.combine(target_date, start_time)
    end_dt = start_dt + timedelta(minutes=duration)
    if end_dt.date() != target_date:
        return JsonResponse({"status": "error", "message": "Le creneau doit rester sur la meme journee."}, status=400)

    day_str = target_date.strftime("%a")
    slot_is_within_availability = False
    for availability in provider.availabilities.filter(day_of_week=day_str):
        availability_start = datetime.combine(target_date, availability.start_time)
        availability_end = datetime.combine(target_date, availability.end_time)
        if start_dt < availability_start or end_dt > availability_end:
            continue

        break_start_dt = (
            datetime.combine(target_date, availability.break_start)
            if availability.break_start
            else None
        )
        break_end_dt = (
            datetime.combine(target_date, availability.break_end)
            if availability.break_end
            else None
        )
        if break_start_dt and break_end_dt and _time_overlaps(start_dt, end_dt, break_start_dt, break_end_dt):
            continue

        slot_is_within_availability = True
        break

    if not slot_is_within_availability:
        return JsonResponse(
            {"status": "error", "message": "Le creneau doit etre dans vos disponibilites (hors pause)."},
            status=400,
        )

    blocking_statuses = {"pending", "accepted", "done"}
    appointments = Appointment.objects.filter(
        provider=provider,
        date=target_date,
        status__in=blocking_statuses,
    ).only("start_time", "end_time")
    for appointment in appointments:
        appointment_start = datetime.combine(target_date, appointment.start_time)
        appointment_end = _appointment_end_datetime(
            target_date,
            appointment.start_time,
            appointment.end_time,
        )
        if _time_overlaps(start_dt, end_dt, appointment_start, appointment_end):
            return JsonResponse({"status": "error", "message": "Conflit avec un rendez-vous existant."}, status=400)

    blocks = BlockedSlot.objects.filter(provider=provider, date=target_date).only("start_time", "end_time")
    for block in blocks:
        block_start = datetime.combine(target_date, block.start_time)
        block_end = datetime.combine(target_date, block.end_time)
        if _time_overlaps(start_dt, end_dt, block_start, block_end):
            return JsonResponse({"status": "error", "message": "Conflit avec un creneau deja bloque."}, status=400)

    blocked_slot = BlockedSlot.objects.create(
        provider=provider,
        date=target_date,
        start_time=start_dt.time(),
        end_time=end_dt.time(),
        reason=reason,
    )
    return JsonResponse(
        {
            "status": "success",
            "message": "Creneau bloque avec succes.",
            "slot": {
                "id": blocked_slot.id,
                "date": blocked_slot.date.isoformat(),
                "start_time": blocked_slot.start_time.strftime("%H:%M"),
                "end_time": blocked_slot.end_time.strftime("%H:%M"),
                "reason": blocked_slot.reason or "",
            },
        }
    )


@login_required
def provider_delete_blocked_slot_ajax(request, slot_id):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Methode invalide"}, status=405)

    provider = _ensure_provider_access(request)
    if not provider:
        return JsonResponse({"status": "error", "message": "Acces refuse"}, status=403)

    blocked_slot = get_object_or_404(BlockedSlot, id=slot_id, provider=provider)
    blocked_slot.delete()
    return JsonResponse({"status": "success", "message": "Creneau supprime."})


@login_required
def book_appointment_ajax(request):
    if request.method == 'POST' and request.user.is_authenticated:
        provider_id = request.POST.get('provider_id')
        start = request.POST.get('start')
        provider = get_object_or_404(Provider, id=provider_id)
        owner = _ensure_provider_access(request)
        if not owner or owner.id != provider.id:
            return JsonResponse({'status': 'error', 'message': 'Accès refusé'})

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
def ajax_apply_availability_template(request):
    provider = _ensure_provider_access(request)
    if not provider:
        return JsonResponse({"status": "error", "message": "Acces refuse"}, status=403)
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Methode invalide"}, status=405)

    template_key = (request.POST.get("template_key") or "").strip()
    template = AVAILABILITY_TEMPLATES.get(template_key)
    if not template:
        return JsonResponse({"status": "error", "message": "Template indisponible."}, status=400)

    replace_existing = (request.POST.get("replace_existing") or "1") == "1"
    entries = template.get("entries", [])
    if not entries:
        return JsonResponse({"status": "error", "message": "Template vide."}, status=400)

    if replace_existing:
        provider.availabilities.all().delete()

    created_count = 0
    for entry in entries:
        day = entry["day"]
        start_time = datetime.strptime(entry["start"], "%H:%M").time()
        end_time = datetime.strptime(entry["end"], "%H:%M").time()
        break_start = datetime.strptime(entry["break_start"], "%H:%M").time() if entry.get("break_start") else None
        break_end = datetime.strptime(entry["break_end"], "%H:%M").time() if entry.get("break_end") else None

        if not replace_existing:
            provider.availabilities.filter(day_of_week=day).delete()

        Availability.objects.create(
            provider=provider,
            day_of_week=day,
            start_time=start_time,
            end_time=end_time,
            break_start=break_start,
            break_end=break_end,
        )
        created_count += 1

    return JsonResponse(
        {
            "status": "success",
            "template_key": template_key,
            "created_count": created_count,
            "message": f"Template applique ({created_count} horaires).",
        }
    )


@login_required
def ajax_apply_custom_availability_template(request):
    provider = _ensure_provider_access(request)
    if not provider:
        return JsonResponse({"status": "error", "message": "Acces refuse"}, status=403)
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Methode invalide"}, status=405)

    selected_days = list(
        dict.fromkeys(
            [value.strip() for value in request.POST.getlist("days") if value and value.strip()]
        )
    )
    if not selected_days:
        return JsonResponse(
            {"status": "error", "message": "Selectionne au moins un jour."},
            status=400,
        )

    valid_days = {code for code, _ in Availability.DAYS_OF_WEEK}
    invalid_days = [day for day in selected_days if day not in valid_days]
    if invalid_days:
        return JsonResponse(
            {"status": "error", "message": "Jours invalides detectes."},
            status=400,
        )

    start_raw = (request.POST.get("start_time") or "").strip()
    end_raw = (request.POST.get("end_time") or "").strip()
    break_start_raw = (request.POST.get("break_start") or "").strip()
    break_end_raw = (request.POST.get("break_end") or "").strip()

    if not start_raw or not end_raw:
        return JsonResponse(
            {"status": "error", "message": "Heure debut et fin obligatoires."},
            status=400,
        )

    try:
        start_time = datetime.strptime(start_raw, "%H:%M").time()
        end_time = datetime.strptime(end_raw, "%H:%M").time()
    except ValueError:
        return JsonResponse(
            {"status": "error", "message": "Format heure invalide (HH:MM)."},
            status=400,
        )

    if start_time >= end_time:
        return JsonResponse(
            {"status": "error", "message": "L heure de fin doit etre apres l heure de debut."},
            status=400,
        )

    if bool(break_start_raw) ^ bool(break_end_raw):
        return JsonResponse(
            {"status": "error", "message": "Renseigne la pause debut et fin, ou laisse les deux vides."},
            status=400,
        )

    break_start = None
    break_end = None
    if break_start_raw and break_end_raw:
        try:
            break_start = datetime.strptime(break_start_raw, "%H:%M").time()
            break_end = datetime.strptime(break_end_raw, "%H:%M").time()
        except ValueError:
            return JsonResponse(
                {"status": "error", "message": "Format pause invalide (HH:MM)."},
                status=400,
            )
        if break_start >= break_end:
            return JsonResponse(
                {"status": "error", "message": "La fin de pause doit etre apres son debut."},
                status=400,
            )
        if break_start <= start_time or break_end >= end_time:
            return JsonResponse(
                {
                    "status": "error",
                    "message": "La pause doit etre strictement comprise dans le creneau d ouverture.",
                },
                status=400,
            )

    replace_existing = (request.POST.get("replace_existing") or "0") == "1"
    if replace_existing:
        provider.availabilities.all().delete()

    created_count = 0
    for day in selected_days:
        if not replace_existing:
            provider.availabilities.filter(day_of_week=day).delete()
        Availability.objects.create(
            provider=provider,
            day_of_week=day,
            start_time=start_time,
            end_time=end_time,
            break_start=break_start,
            break_end=break_end,
        )
        created_count += 1

    return JsonResponse(
        {
            "status": "success",
            "created_count": created_count,
            "message": f"Template personnalise applique sur {created_count} jour(s).",
        }
    )


@login_required
def ajax_save_availability(request):
    provider = _ensure_provider_access(request)
    if not provider:
        return JsonResponse({'status': 'error', 'message': 'Accès refusé'})
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

# AJAX suppression disponibilites
@login_required
def ajax_delete_availability(request, availability_id):
    provider = _ensure_provider_access(request)
    if not provider:
        return JsonResponse({'status': 'error', 'message': 'Acces refuse'}, status=403)
    if request.method != "POST":
        return JsonResponse({'status': 'error', 'message': 'Methode invalide'}, status=405)

    availability = get_object_or_404(Availability, id=availability_id, provider=provider)
    availability.delete()
    return JsonResponse({'status': 'success'})


# Helper pour verifier role prestataire
def _ensure_provider_access(request):
    profile = getattr(request.user, "profile", None)
    if not profile or profile.role != "provider":
        messages.error(request, "Accès réservé aux prestataires.")
        return None
    try:
        return request.user.provider
    except Provider.DoesNotExist:
        messages.error(request, "Profil prestataire manquant. Contactez l'administrateur pour l'activer.")
        return None
