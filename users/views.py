from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from .forms import UserRegisterForm
from .models import Profile
from django.contrib import messages

def register_view(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()  # hash du mot de passe inclus
            role = form.cleaned_data.get('role')
            Profile.objects.create(user=user, role=role)
            messages.success(request, f'Compte créé pour {user.username} !')
            return redirect('users:login')
    else:
        form = UserRegisterForm()
    return render(request, 'users/register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('appointments:services_list')
        else:
            messages.error(request, 'Nom d’utilisateur ou mot de passe incorrect')
    return render(request, 'users/login.html')

def logout_view(request):
    logout(request)
    return redirect('users:login')
