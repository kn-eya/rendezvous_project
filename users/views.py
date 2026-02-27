from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib import messages
from allauth.account.models import EmailAddress
from .forms import UserRegisterForm
from .models import Profile
from django.utils.http import url_has_allowed_host_and_scheme  # ✅ remplace is_safe_url
from django.views.decorators.http import require_http_methods

User = get_user_model()

def _clear_messages(request):
    """
    Purge les anciens messages pour éviter leur accumulation
    sur les redirections (ex: après profil/prestations).
    """
    list(messages.get_messages(request))

# -------------------
# Registration
# -------------------
def register_view(request):
    _clear_messages(request)
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            role = form.cleaned_data.get('role')
            # Profile is created by signal; update its role from the form
            if hasattr(user, "profile"):
                user.profile.role = role
                user.profile.save()
            # Envoi d'un email de confirmation via allauth
            EmailAddress.objects.add_email(request, user, user.email, confirm=True, signup=True)
            messages.success(request, f'Compte créé pour {user.username} ! Vérifie tes emails pour confirmer ton adresse.')
            return redirect('users:login')
    else:
        form = UserRegisterForm()
    return render(request, 'users/register.html', {'form': form})

# -------------------
# Login
# -------------------
def login_view(request):
    if request.method == 'POST':
        identifier = request.POST['username']
        password = request.POST['password']

        # Autoriser la connexion via email ou username
        if '@' in identifier:
            try:
                identifier = User.objects.get(email__iexact=identifier).username
            except User.DoesNotExist:
                pass

        user = authenticate(request, username=identifier, password=password)
        if user:
            # Refuser la connexion si l'email n'est pas confirmé
            email_obj, _ = EmailAddress.objects.get_or_create(
                user=user,
                email=user.email,
                defaults={"primary": True}
            )
            if not email_obj.verified:
                email_obj.send_confirmation(request, signup=False)
                messages.error(request, "Veuillez confirmer votre email avant de vous connecter. Un nouveau lien vient d'être envoyé.")
                return redirect('users:login')

            login(request, user)
            return redirect_after_login(request, user)  # ✅ passe request aussi
        else:
            messages.error(request, 'Nom d’utilisateur ou mot de passe incorrect')
    return render(request, 'users/login.html')

# -------------------
# Social login
# -------------------
def social_login_redirect(request):
    user = request.user
    if not hasattr(user, 'profile'):
        Profile.objects.create(user=user, role='client')
    return redirect_after_login(request, user)

# -------------------
# Redirection après login
# -------------------
def redirect_after_login(request, user):
    """
    Redirige un utilisateur après login selon son rôle et l'URL de provenance.
    """
    next_url = request.GET.get('next')
    
    if next_url and next_url.startswith('/'):
        return redirect(next_url)

    profile = getattr(user, "profile", None)
    if profile is None:
        profile = Profile.objects.create(user=user, role='client')

    role = getattr(profile, 'role', 'client')
    if role == 'client':
        return redirect('appointments:services_list')  # client → booking
    elif role == 'provider':
        return redirect('appointments:provider_dashboard')  # prestataire → dashboard
    else:
        return redirect('appointments:services_list')

# -------------------
# Logout
# -------------------
def logout_view(request):
    logout(request)
    return redirect('acceuil')


@require_http_methods(["GET", "POST"])
def resend_confirmation(request):
    """
    Permet de renvoyer un email de confirmation pour une adresse non verifiee.
    """
    _clear_messages(request)

    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        if not email:
            messages.error(request, "Merci de renseigner votre e-mail.")
            return redirect("users:resend_confirmation")

        user = User.objects.filter(email__iexact=email).first()
        if not user:
            messages.error(request, "Aucun compte n'est associé à cet e-mail.")
            return redirect("users:resend_confirmation")

        email_obj, _ = EmailAddress.objects.get_or_create(
            user=user,
            email=user.email,
            defaults={"primary": True}
        )

        if email_obj.verified:
            messages.info(request, "Cet e-mail est déjà vérifié. Vous pouvez vous connecter.")
            return redirect("users:login")

        email_obj.send_confirmation(request)
        messages.success(request, "Un nouveau lien de confirmation a été envoyé.")
        return redirect("users:login")

    return render(request, "users/resend_confirmation.html")
