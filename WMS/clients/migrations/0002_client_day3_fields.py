from django.db import migrations, models
import django.db.models.deletion


def populate_client_fields(apps, schema_editor):
    Client = apps.get_model('clients', 'Client')

    for client in Client.objects.order_by('pk'):
        client.client_id = f'CL{client.pk:03d}'
        client.status = 'active' if client.is_active else 'inactive'
        client.save(update_fields=['client_id', 'status'])


def reverse_client_fields(apps, schema_editor):
    Client = apps.get_model('clients', 'Client')

    for client in Client.objects.all():
        client.is_active = client.status == 'active'
        client.save(update_fields=['is_active'])


class Migration(migrations.Migration):
    dependencies = [
        ('clients', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='client',
            old_name='name',
            new_name='business_name',
        ),
        migrations.AddField(
            model_name='client',
            name='category',
            field=models.CharField(
                choices=[
                    ('individual', 'Individual'),
                    ('business', 'Business'),
                    ('institution', 'Institution'),
                ],
                default='individual',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='client',
            name='client_id',
            field=models.CharField(max_length=20, null=True),
        ),
        migrations.AddField(
            model_name='client',
            name='status',
            field=models.CharField(max_length=20, null=True),
        ),
        migrations.AddField(
            model_name='client',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.RunPython(populate_client_fields, reverse_client_fields),
        migrations.RemoveField(
            model_name='client',
            name='is_active',
        ),
        migrations.AlterField(
            model_name='client',
            name='address',
            field=models.TextField(),
        ),
        migrations.AlterField(
            model_name='client',
            name='business_name',
            field=models.CharField(blank=True, max_length=150),
        ),
        migrations.AlterField(
            model_name='client',
            name='client_id',
            field=models.CharField(max_length=20, unique=True),
        ),
        migrations.AlterField(
            model_name='client',
            name='phone',
            field=models.CharField(max_length=20),
        ),
        migrations.AlterField(
            model_name='client',
            name='status',
            field=models.CharField(
                choices=[('active', 'Active'), ('inactive', 'Inactive')],
                default='active',
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name='client',
            name='user',
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='client_profile',
                to='accounts.user',
            ),
        ),
    ]
