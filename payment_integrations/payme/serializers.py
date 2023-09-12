from rest_framework import serializers

from .utils import PaymeMethods


class PaymeSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    method = serializers.ChoiceField(choices=PaymeMethods.choices())
    params = serializers.JSONField()


class PaymeLinkSerializer(serializers.Serializer):
    amount = serializers.IntegerField(required=True)

    def validate_amount(self, value):
        if value < 1000:
            raise serializers.ValidationError("Amount must be greater than 1000")
        return value
