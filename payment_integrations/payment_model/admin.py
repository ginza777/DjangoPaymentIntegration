from django.contrib import admin
from payment_integrations.payment_model import models


@admin.register(models.Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['id', 'variant', 'total', 'user', 'status','transaction_id', 'created', 'modified']
    autocomplete_fields = ['user']
    list_editable = ['status','transaction_id', 'total']

@admin.register(models.PaymentMerchantRequestLog)
class PaymentMerchantRequestLogAdmin(admin.ModelAdmin):
    list_display = ["id", "provider", "type", "response_status_code", "created_at"]
    search_fields = ["id", "body", "header", "response", "method"]
    list_filter = ["provider"]
