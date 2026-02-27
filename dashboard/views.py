from datetime import timedelta

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from appointments.models import Appointment, Provider, Service
from users.models import Profile


@login_required
def provider_dashboard(request):
    provider = Provider.objects.filter(user=request.user).first()
    if not provider:
        messages.error(request, "Cet espace est reserve aux prestataires.")
        return redirect("appointments:services_list")

    base_qs = (
        Appointment.objects.filter(provider=provider)
        .select_related("client", "provider__user", "category__service")
    )
    today = timezone.localdate()

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

    appointments_qs = base_qs
    if search_query:
        appointments_qs = appointments_qs.filter(
            Q(client__username__icontains=search_query)
            | Q(category__name__icontains=search_query)
            | Q(category__service__name__icontains=search_query)
        )
    if status_filter != "all":
        appointments_qs = appointments_qs.filter(status=status_filter)

    if period_filter == "today":
        appointments_qs = appointments_qs.filter(date=today).order_by("date", "start_time")
    elif period_filter == "upcoming":
        appointments_qs = appointments_qs.filter(date__gte=today).order_by("date", "start_time")
    elif period_filter == "past":
        appointments_qs = appointments_qs.filter(date__lt=today).order_by("-date", "-start_time")
    else:
        appointments_qs = appointments_qs.order_by("-date", "-start_time")

    paginator = Paginator(appointments_qs, 8)
    page_number = request.GET.get("page")
    appointments = paginator.get_page(page_number)

    total_count = base_qs.count()
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


def _redirect_back_to_provider_dashboard(request):
    next_url = request.POST.get("next")
    if next_url and next_url.startswith("/"):
        return redirect(next_url)
    return redirect("appointments:provider_dashboard")


@login_required
def accept_appointment(request, appointment_id):
    if request.method != "POST":
        return _redirect_back_to_provider_dashboard(request)
    appointment = get_object_or_404(Appointment, id=appointment_id, provider__user=request.user)
    if appointment.transition_to("accepted"):
        messages.success(request, "Rendez-vous accepte.")
    else:
        messages.error(request, f"Transition invalide depuis '{appointment.get_status_display()}'.")
    return _redirect_back_to_provider_dashboard(request)


@login_required
def refuse_appointment(request, appointment_id):
    if request.method != "POST":
        return _redirect_back_to_provider_dashboard(request)
    appointment = get_object_or_404(Appointment, id=appointment_id, provider__user=request.user)
    if appointment.transition_to("refused"):
        messages.success(request, "Rendez-vous refuse.")
    else:
        messages.error(request, f"Transition invalide depuis '{appointment.get_status_display()}'.")
    return _redirect_back_to_provider_dashboard(request)


@login_required
def cancel_appointment_provider(request, appointment_id):
    if request.method != "POST":
        return _redirect_back_to_provider_dashboard(request)
    appointment = get_object_or_404(Appointment, id=appointment_id, provider__user=request.user)
    if appointment.transition_to("cancelled"):
        messages.success(request, "Rendez-vous annule.")
    else:
        messages.error(request, f"Transition invalide depuis '{appointment.get_status_display()}'.")
    return _redirect_back_to_provider_dashboard(request)


@login_required
def mark_appointment_done(request, appointment_id):
    if request.method != "POST":
        return _redirect_back_to_provider_dashboard(request)
    appointment = get_object_or_404(Appointment, id=appointment_id, provider__user=request.user)
    if appointment.transition_to("done"):
        messages.success(request, "Rendez-vous marque comme termine.")
    else:
        messages.error(request, f"Transition invalide depuis '{appointment.get_status_display()}'.")
    return _redirect_back_to_provider_dashboard(request)


@staff_member_required
def admin_dashboard(request):
    today = timezone.localdate()
    window_start = today - timedelta(days=6)

    appointments = Appointment.objects.select_related("client", "provider__user", "category__service")
    status_rows = appointments.values("status").annotate(total=Count("id"))
    status_counts = {row["status"]: row["total"] for row in status_rows}

    daily_rows = (
        appointments.filter(date__gte=window_start, date__lte=today)
        .values("date")
        .annotate(total=Count("id"))
        .order_by("date")
    )
    daily_map = {row["date"]: row["total"] for row in daily_rows}
    daily_stats = []
    for day_offset in range(7):
        day = window_start + timedelta(days=day_offset)
        daily_stats.append({
            "label": day.strftime("%d/%m"),
            "total": daily_map.get(day, 0),
        })

    max_daily_total = max((row["total"] for row in daily_stats), default=1) or 1
    for row in daily_stats:
        row["bar_width"] = int((row["total"] / max_daily_total) * 100) if row["total"] else 0

    top_services = list(
        appointments.values("category__service__name")
        .annotate(total=Count("id"))
        .order_by("-total", "category__service__name")[:5]
    )
    for row in top_services:
        row["name"] = row["category__service__name"] or "Service non defini"

    top_providers = list(
        appointments.values("provider__user__username")
        .annotate(total=Count("id"))
        .order_by("-total", "provider__user__username")[:5]
    )
    for row in top_providers:
        row["name"] = row["provider__user__username"] or "Prestataire inconnu"

    context = {
        "kpis": {
            "total_appointments": appointments.count(),
            "today_appointments": appointments.filter(date=today).count(),
            "pending_appointments": status_counts.get("pending", 0),
            "accepted_appointments": status_counts.get("accepted", 0),
            "refused_appointments": status_counts.get("refused", 0),
            "cancelled_appointments": status_counts.get("cancelled", 0),
            "done_appointments": status_counts.get("done", 0),
            "active_services": Service.objects.filter(is_active=True).count(),
            "providers_count": Provider.objects.count(),
            "clients_count": Profile.objects.filter(role="client").count(),
        },
        "top_services": top_services,
        "top_providers": top_providers,
        "daily_stats": daily_stats,
        "recent_appointments": appointments.order_by("-date", "-start_time")[:10],
    }
    return render(request, "dashboard/admin_dashboard.html", context)
