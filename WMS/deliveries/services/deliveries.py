from django.db import transaction

from deliveries.models import Delivery


@transaction.atomic
def schedule_delivery(order, driver, vehicle, destination, scheduled_date):
	delivery = Delivery(
		order=order,
		driver=driver,
		vehicle=vehicle,
		destination=destination,
		scheduled_date=scheduled_date,
		status='scheduled',
	)
	delivery.full_clean()
	delivery.save()
	return delivery