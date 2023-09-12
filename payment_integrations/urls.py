from django.urls import path
from payment_integrations.payme.views import PaymeAPIView, PaymeLinkAPIView

urlpatterns = [
    # Payme
    path("payme/", PaymeAPIView.as_view(), name="payme"),
    path("payme/link/", PaymeLinkAPIView.as_view(), name="payme"),
    ]

