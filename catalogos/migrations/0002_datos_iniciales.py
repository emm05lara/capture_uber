from django.db import migrations


COLORES_INICIALES = [
    "NEGRO", "BLANCO", "GRIS", "PLATA", "AZUL", "ROJO",
]

APPS_INICIALES = [
    "UBER", "DIDI",
]


def crear_datos_iniciales(apps, schema_editor):
    Color = apps.get_model("catalogos", "Color")
    AppTransporte = apps.get_model("catalogos", "AppTransporte")

    for nombre in COLORES_INICIALES:
        Color.objects.get_or_create(nombre_color=nombre)

    for nombre in APPS_INICIALES:
        AppTransporte.objects.get_or_create(nombre_app=nombre)


def revertir_datos_iniciales(apps, schema_editor):
    Color = apps.get_model("catalogos", "Color")
    AppTransporte = apps.get_model("catalogos", "AppTransporte")

    Color.objects.filter(nombre_color__in=COLORES_INICIALES).delete()
    AppTransporte.objects.filter(nombre_app__in=APPS_INICIALES).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("catalogos", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(crear_datos_iniciales, revertir_datos_iniciales),
    ]
