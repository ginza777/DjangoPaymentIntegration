from django.db import models
from payments.models import BasePayment
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

User=get_user_model()

class Transaction(BasePayment):
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='transactions')
    paid_at = models.DateTimeField(verbose_name=_("Paid At"), null=True, blank=True)
    cancel_time = models.DateTimeField(verbose_name=_("Cancel Time"), null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)



    def save(self, *args, **kwargs):
        # If transaction_id is not provided, set it to the id field
        if not self.transaction_id:
            self.transaction_id = str(self.id)
        if self.transaction_id is None:
            self.transaction_id = str(self.id)
        super().save(*args, **kwargs)


    class Meta(BasePayment.Meta):
        unique_together = ('variant', 'transaction_id')



class Provider(models.TextChoices):
    PAYME = "payme", _("Payme")
    CLICK = "click", _("Click")
    PAYLOV = "paylov", _("Paylov")
    UZUM_BANK = "uzum_bank", _("Uzum Bank")
    CARD = "card", _("Card")

class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated at"))
    paid_at = models.DateTimeField(verbose_name=_("Paid At"), null=True, blank=True)
    cancel_time = models.DateTimeField(verbose_name=_("Cancel Time"), null=True, blank=True)

    class Meta:
        abstract = True

class PaymentMerchantRequestLog(TimeStampedModel):
    provider = models.CharField(max_length=63, verbose_name=_("Provider"), choices=Provider.choices)
    header = models.TextField(verbose_name=_("Header"))
    body = models.TextField(verbose_name=_("Body"))
    method = models.CharField(verbose_name=_("Method"), max_length=32)
    response = models.TextField(null=True, blank=True)
    response_status_code = models.IntegerField(null=True, blank=True)
    type = models.CharField(max_length=32)

    class Meta:
        verbose_name = _("Payment Merchant Request Log")
        verbose_name_plural = _("Payment Merchant Request Logs")



OPERATION = (
        (1, _('Hisob to\'ldirildi')),
        (2, _('Hisob raqamidan pul yechib olindi')),
)


class UserBalanceHistory(models.Model):
    user = models.ForeignKey(User, verbose_name=_("Foydalanuvchi"), on_delete=models.PROTECT, related_name="balance_history")
    amount = models.FloatField(_("Summa"))
    operation = models.IntegerField(_('Bajarilgan amal'), choices=OPERATION)
    prev_balance = models.FloatField(_("O'zgarishdan oldingi balans"))
    new_balance = models.FloatField(_("O'zgarishdan keyingi balans"))
    comment = models.TextField(_('Qo\'shimcha ma\'lumot'), null=True, blank=True)
    created_at = models.DateTimeField(_('Vaqt'), auto_now_add=True)
    title = models.CharField(_('Title'), max_length=256)
    transaction = models.ForeignKey(Transaction, on_delete=models.PROTECT, related_name='hist', null=True, blank=True)

    class Meta:
        db_table = 'balance_history'
        verbose_name = _('Foydalanuvchi hisobi tarixi')
        verbose_name_plural = _('Foydalanuvchi hisobi tarixlari')

    def __str__(self):
        return '{0} - {1} - {2}'.format(self.user.get_full_name, str(self.amount), self.created_at.strftime("%d.%m.%Y %H:%M"))

