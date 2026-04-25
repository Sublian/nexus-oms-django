# src/interfaces/web/auth_views.py

from django import forms
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.views import View

from src.domain.models import Organization


class EmailLoginForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'placeholder': 'correo@empresa.com',
            'class': 'w-full bg-gray-900 border border-gray-700 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all',
            'autofocus': True,
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': '••••••••',
            'class': 'w-full bg-gray-900 border border-gray-700 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all',
        })
    )


class LoginView(View):
    template = 'auth/login.html'

    def get(self, request):
        if request.user.is_authenticated:
            return self._redirect_after_login(request.user)
        return render(request, self.template, {'form': EmailLoginForm()})

    def post(self, request):
        form = EmailLoginForm(request.POST)
        if form.is_valid():
            user = authenticate(
                request,
                username=form.cleaned_data['email'],
                password=form.cleaned_data['password'],
            )
            if user is not None:
                login(request, user)
                return self._redirect_after_login(user)
            form.add_error(None, 'Correo o contraseña incorrectos.')
        return render(request, self.template, {'form': form})

    def _redirect_after_login(self, user):
        if user.organization:
            return redirect('web:dashboard_home', org_slug=user.organization.slug)
        # Superuser without org: pick first available tenant
        first_org = Organization.objects.order_by('name').first()
        if first_org:
            return redirect('web:dashboard_home', org_slug=first_org.slug)
        return redirect('/admin/')


class LogoutView(View):
    def post(self, request):
        logout(request)
        return redirect('auth:login')
