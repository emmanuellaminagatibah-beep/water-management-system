from django.db import migrations


def normalize_methods(apps, schema_editor):
	Payment = apps.get_model('billing', 'Payment')
	using = schema_editor.connection.alias
	Payment.objects.using(using).filter(method='bank').update(method='bank_transfer')
	Payment.objects.using(using).filter(method='mobile').update(method='mobile_money')


class Migration(migrations.Migration):

	dependencies = [
		('billing', '0004_payment_payment_date_payment_received_by_and_more'),
	]

	operations = [
		migrations.RunPython(normalize_methods, migrations.RunPython.noop),
	]