# load_data.py — KALRO Advisory seed script
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kalro_advisory.settings')

import django
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


def load_counties():
    """Seed the 47 Kenyan counties."""
    from apps.farmers.models import County

    counties = [
        'Baringo', 'Bomet', 'Bungoma', 'Busia', 'Elgeyo-Marakwet',
        'Embu', 'Garissa', 'Homa Bay', 'Isiolo', 'Kajiado',
        'Kakamega', 'Kericho', 'Kiambu', 'Kilifi', 'Kirinyaga',
        'Kisii', 'Kisumu', 'Kitui', 'Kwale', 'Laikipia',
        'Lamu', 'Machakos', 'Makueni', 'Mandera', 'Marsabit',
        'Meru', 'Migori', 'Mombasa', 'Muranga', "Nairobi",
        'Nakuru', 'Nandi', 'Narok', 'Nyamira', 'Nyandarua',
        'Nyeri', 'Samburu', 'Siaya', 'Taita-Taveta', 'Tana River',
        'Tharaka-Nithi', 'Trans Nzoia', 'Turkana', 'Uasin Gishu',
        'Vihiga', 'Wajir', 'West Pokot',
    ]

    created = 0
    for name in counties:
        _, was_created = County.objects.get_or_create(name=name)
        if was_created:
            created += 1
    print(f"✅ Counties: {created} created, {County.objects.count()} total")


def load_crop_categories():
    from apps.crops.models import CropCategory

    categories = [
        ('Cereals', 'Maize, wheat, rice, sorghum, millet'),
        ('Legumes', 'Beans, peas, groundnuts, soybeans'),
        ('Tubers', 'Potatoes, sweet potatoes, cassava, yams'),
        ('Horticulture', 'Tomatoes, onions, kale, cabbage, carrots'),
        ('Cash Crops', 'Coffee, tea, sugarcane, cotton'),
        ('Fruits', 'Bananas, mangoes, avocados, oranges'),
        ('Fodder', 'Napier grass, lucerne, desmodium'),
    ]

    created = 0
    for name, desc in categories:
        _, was_created = CropCategory.objects.get_or_create(
            name=name, defaults={'description': desc}
        )
        if was_created:
            created += 1
    print(f"✅ Crop categories: {created} created, {CropCategory.objects.count()} total")


def load_crops():
    from apps.crops.models import Crop, CropCategory

    crops = [
        # (name, scientific, category, season, water_mm, days_to_maturity)
        ('Maize',         'Zea mays',            'Cereals',      'BOTH', 500, 120),
        ('Beans',         'Phaseolus vulgaris',  'Legumes',      'BOTH', 350, 90),
        ('Wheat',         'Triticum aestivum',   'Cereals',      'LR',   450, 130),
        ('Rice',          'Oryza sativa',        'Cereals',      'BOTH', 900, 120),
        ('Sorghum',       'Sorghum bicolor',     'Cereals',      'DRY',  400, 110),
        ('Millet',        'Eleusine coracana',   'Cereals',      'DRY',  350, 100),
        ('Irish Potato',  'Solanum tuberosum',   'Tubers',       'BOTH', 500, 100),
        ('Sweet Potato',  'Ipomoea batatas',     'Tubers',       'BOTH', 450, 120),
        ('Cassava',       'Manihot esculenta',   'Tubers',       'BOTH', 600, 270),
        ('Tomato',        'Solanum lycopersicum','Horticulture', 'BOTH', 400, 90),
        ('Onion',         'Allium cepa',         'Horticulture', 'BOTH', 400, 120),
        ('Kale',          'Brassica oleracea',   'Horticulture', 'BOTH', 350, 75),
        ('Cabbage',       'Brassica oleracea',   'Horticulture', 'BOTH', 400, 90),
        ('Carrot',        'Daucus carota',       'Horticulture', 'BOTH', 400, 90),
        ('Coffee',        'Coffea arabica',      'Cash Crops',   'PER',  1200, 1095),
        ('Tea',           'Camellia sinensis',   'Cash Crops',   'PER',  1400, 1460),
        ('Sugarcane',     'Saccharum officinarum','Cash Crops',  'PER',  1500, 540),
        ('Banana',        'Musa spp.',           'Fruits',       'PER',  1200, 365),
        ('Mango',         'Mangifera indica',    'Fruits',       'PER',  1000, 1095),
        ('Avocado',       'Persea americana',    'Fruits',       'PER',  1100, 1460),
    ]

    created = 0
    for name, sci, cat_name, season, water, days in crops:
        cat = CropCategory.objects.filter(name=cat_name).first()
        _, was_created = Crop.objects.get_or_create(
            name=name,
            defaults={
                'scientific_name': sci,
                'category': cat,
                'season': season,
                'water_requirement_mm': water,
                'days_to_maturity': days,
                'is_active': True,
            },
        )
        if was_created:
            created += 1
    print(f"✅ Crops: {created} created, {Crop.objects.count()} total")


def load_physics_constraints():
    from apps.pinn_engine.models import PhysicsConstraint

    constraints = [
        {
            'name': 'Water Balance',
            'kind': 'WATER',
            'domain': 'COMB',
            'description': 'Change in soil moisture equals precipitation minus evapotranspiration, runoff, and deep drainage.',
            'mathematical_form': 'dS/dt = P − ET − R − D',
            'weight': 1.0,
        },
        {
            'name': 'Nitrogen Cycling',
            'kind': 'NUTRIENT',
            'domain': 'SOIL',
            'description': 'Soil nitrogen changes based on fertilizer input, mineralization, and crop uptake.',
            'mathematical_form': 'dN/dt = F + M − U − L',
            'weight': 0.8,
        },
        {
            'name': 'Energy Conservation',
            'kind': 'ENERGY',
            'domain': 'ATM',
            'description': 'Net radiation equals latent, sensible, and ground heat flux.',
            'mathematical_form': 'Rn = LE + H + G',
            'weight': 0.6,
        },
    ]

    created = 0
    for data in constraints:
        _, was_created = PhysicsConstraint.objects.get_or_create(
            name=data['name'], defaults=data
        )
        if was_created:
            created += 1
    print(f"✅ Physics constraints: {created} created, {PhysicsConstraint.objects.count()} total")


def create_superuser():
    from decouple import config

    username = config('DJANGO_SUPERUSER_USERNAME', default='admin')
    email    = config('DJANGO_SUPERUSER_EMAIL', default='admin@kalro.go.ke')
    password = config('DJANGO_SUPERUSER_PASSWORD', default=None)

    if not password:
        print('⚠️  DJANGO_SUPERUSER_PASSWORD not set — skipping superuser creation.')
        return

    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            'email': email,
            'role': 'SYS_ADMIN',
            'is_staff': True,
            'is_superuser': True,
            'is_verified': True,
        },
    )
    if created:
        user.set_password(password)
        user.save()
        print(f"✅ Superuser created: {username}")
    else:
        print(f"ℹ️  Superuser {username} already exists")


def main():
    print("\n" + "=" * 60)
    print("🌱 KALRO Advisory — Seeding initial data")
    print("=" * 60 + "\n")

    load_counties()
    load_crop_categories()
    load_crops()
    load_physics_constraints()
    create_superuser()

    print("\n" + "=" * 60)
    print("✅ Seeding complete")
    print("=" * 60 + "\n")


if __name__ == '__main__':
    main()