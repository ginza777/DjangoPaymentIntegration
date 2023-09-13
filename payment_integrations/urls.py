from django.urls import path
from payment_integrations.payme.views import PaymeAPIView, PaymeLinkAPIView
from payment_integrations.paylov.views import PaylovWithCard, PaylovWithCardConfirm, PaylovAPIView, PaylovLink, PaylovLinkStatus
urlpatterns = [
    # Payme
    path("payme/", PaymeAPIView.as_view(), name="payme"),
    path("payme/link/", PaymeLinkAPIView.as_view(), name="payme"),
    # Paylov
    path('paylov/with-card/', PaylovWithCard.as_view()),
    path('paylov/with-card-confirm/', PaylovWithCardConfirm.as_view()),
    # paylov link
    path('paylov/link/', PaylovLink.as_view()),
    path('paylov/link/status/', PaylovLinkStatus.as_view()),
    path("paylov/", PaylovAPIView.as_view(), name="paylov"),

    ]

