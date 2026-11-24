from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import User


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "user_type", "first_name", "last_name", "phone_number")
        read_only_fields = ("id", "email", "user_type")


class RegistrationSerializer(ProfileSerializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False, style={"input_type": "password"})
    confirm_password = serializers.CharField(write_only=True, trim_whitespace=False, style={"input_type": "password"})

    class Meta(ProfileSerializer.Meta):
        fields = (*ProfileSerializer.Meta.fields, "password", "confirm_password")
        read_only_fields = ("id",)

    def validate(self, attrs):
        if attrs.pop("confirm_password") != attrs["password"]:
            raise serializers.ValidationError({"confirm_password": "Passwords must match."})
        attrs["email"] = User.objects.normalize_email(attrs["email"])
        candidate = User(**attrs)
        try:
            validate_password(attrs["password"], candidate)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": exc.messages}) from exc
        return attrs

    def create(self, validated_data):
        try:
            with transaction.atomic():
                return User.objects.create_user(**validated_data)
        except IntegrityError:
            if User.objects.filter(email=validated_data["email"]).exists():
                raise serializers.ValidationError({"email": ["An account with this email already exists."]})
            raise


class EmailLoginSerializer(TokenObtainPairSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password"].trim_whitespace = False

    def validate(self, attrs):
        attrs["email"] = User.objects.normalize_email(attrs["email"])
        return super().validate(attrs)
