from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .forms import UserRegisterForm
from .models import Profile
from django.utils.http import url_has_allowed_host_and_scheme  # ✅ remplace is_safe_url

# -------------------
# Registration
# -------------------
def register_view(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            role = form.cleaned_data.get('role')
            Profile.objects.create(user=user, role=role)
            messages.success(request, f'Compte créé pour {user.username} !')
            return redirect('users:login')
    else:
        form = UserRegisterForm()
    return render(request, 'users/register.html', {'form': form})

# -------------------
# Login
# -------------------
def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user:
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

    role = getattr(user.profile, 'role', 'client')
    if role == 'client':
        return redirect('appointments:single_booking')  # client → booking
    elif role == 'provider':
        return redirect('appointments:provider_edit_profile')  # prestataire → éditer profil
    else:
        return redirect('appointments:single_booking')

# -------------------
# Logout
# -------------------
def logout_view(request):
    logout(request)
    return redirect('users:login')
