from django.shortcuts import render, redirect


def landing_view(request):
    """Public landing page — no auth required. Stats pulled live from the DB."""
    if request.user.is_authenticated:
        return redirect('advisories:advisory_dashboard')

    from apps.accounts.models import User
    from apps.farmers.models import County
    from apps.trials.models import Trial
    from apps.advisories.models import Advisory

    stats = {
        'counties': County.objects.count(),
        'farmers': User.objects.filter(role='FARMER', is_active=True).count(),
        'trials': Trial.objects.count(),
        'advisories': Advisory.objects.count(),
    }

    return render(request, 'landing.html', {'stats': stats})


def features_view(request):
    """Public Features page."""
    return render(request, 'pages/features.html')


def how_it_works_view(request):
    """Public How It Works page."""
    return render(request, 'pages/how_it_works.html')


def handler403(request, exception=None):
    return render(request, 'errors/403.html', status=403)


def handler404(request, exception=None):
    return render(request, 'errors/404.html', status=404)


def handler500(request):
    return render(request, 'errors/500.html', status=500)