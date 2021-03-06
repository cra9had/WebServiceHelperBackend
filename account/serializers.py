from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from phonenumber_field.serializerfields import PhoneNumberField


User = get_user_model()


class UserPasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True, max_length=64)
    new_password = serializers.CharField(required=True, max_length=64)

    def validate(self, data):
        """add here additional check for password strength if needed"""
        if not self.context.get('request').user.check_password(data.get("old_password")):
            raise serializers.ValidationError({'old_password': 'Wrong password.'})
        return data

    def update(self, instance, validated_data):
        instance.set_password(validated_data['new_password'])
        instance.save()
        return instance

    def create(self, validated_data):
        pass

    @property
    def data(self):
        """just return success dictionary. you can change this to your need, but i dont think output should be user
        data after password change """
        return {'Success': True}


class ProfileSerializer(serializers.ModelSerializer):
    balance = serializers.SerializerMethodField("get_balance")
    avatar_url = serializers.SerializerMethodField("get_avatar_url")

    class Meta:
        model = User
        fields = ["balance", "avatar_url", "username"]

    @staticmethod
    def get_balance(obj):
        return obj.gifts

    def get_avatar_url(self, obj):
        request = self.context.get("request")
        return request.build_absolute_uri(obj.avatar.url)


class UserSettingsSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    city = serializers.CharField(max_length=100, required=True)
    district = serializers.CharField(max_length=100, required=True)
    phone_number = PhoneNumberField(required=True)

    email = serializers.SerializerMethodField("get_email")
    avatar = serializers.SerializerMethodField("get_avatar")
    username = serializers.SerializerMethodField("get_username")

    @staticmethod
    def get_email(obj):
        return obj.email

    @staticmethod
    def get_username(obj: User):
        return obj.username

    def get_avatar(self, obj: User):
        request = self.context.get("request")
        return request.build_absolute_uri(obj.avatar.url)

    def update(self, instance, validated_data):
        instance.first_name = validated_data.get('first_name', instance.first_name)
        instance.last_name = validated_data.get('last_name', instance.last_name)
        instance.city = validated_data.get('city', instance.city)
        instance.district = validated_data.get('district', instance.district)
        instance.phone_number = validated_data.get('phone_number', instance.phone_number)
        instance.save()
        return instance


class UserInfoSerializer(serializers.ModelSerializer):
    is_current_user = serializers.SerializerMethodField("is_current_session_user")
    is_online = serializers.SerializerMethodField("is_user_online")

    class Meta:
        model = User
        fields = ("username", "avatar", "description", "is_current_user", "is_online")

    def is_user_online(self, obj):
        return obj.is_online()

    def is_current_session_user(self, obj):
        """Check if current session user equals input user"""
        current_session_user = self.context.get("request").user
        if obj and current_session_user:
            if current_session_user == obj:
                return True
        return False


class RegisterPageSerializer(serializers.Serializer):
    url_hash = serializers.CharField(max_length=64, required=True)

    def validate(self, data):
        return {
            "url_hash": data["url_hash"]
        }


class RegisterUserSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=255, required=True)
    email = serializers.CharField(max_length=255, required=True)
    password = serializers.CharField(
        write_only=True,
        required=True,
        help_text='Leave empty if no change needed',
        style={'input_type': 'password', 'placeholder': 'Password'}
    )
    url_hash = serializers.CharField(max_length=64, required=True)

    def validate(self, data):
        return {
            "email": data["email"],
            "password": data["password"],
            "username": data["username"],
            "url_hash": data["url_hash"]
        }


class LoginSerializer(serializers.Serializer):
    email = serializers.CharField(max_length=255)
    username = serializers.CharField(max_length=255, read_only=True)
    password = serializers.CharField(max_length=128, write_only=True)
    token = serializers.CharField(max_length=255, read_only=True)

    def validate(self, data):
        email = data.get('email', None)
        password = data.get('password', None)

        if email is None:
            raise serializers.ValidationError(
                'An email address is required to log in.'
            )
        email = email.lower()
        if password is None:
            raise serializers.ValidationError(
                'A password is required to log in.'
            )

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError(
                {"email": ['???????????????????????? ?? ?????????? ???????????? ?????? ?????????????? ???? ????????????'],
                 "password": ['???????????????????????? ?? ?????????? ???????????? ?????? ?????????????? ???? ????????????']}
            )

        if not user.check_password(password):
            raise serializers.ValidationError(
                {"email": ['???????????????????????? ?? ?????????? ???????????? ?????? ?????????????? ???? ????????????'],
                 "password": ['???????????????????????? ?? ?????????? ???????????? ?????? ?????????????? ???? ????????????']}
            )

        if not user.is_active:
            raise serializers.ValidationError(
                '???????????????????????? ?????? ??????????????????????????'
            )

        token, _ = Token.objects.get_or_create(user=user)

        return {
            'email': user.email,
            'username': user.username,
            'token': token
        }


class Base64ImageField(serializers.ImageField):
    """
    A Django REST framework field for handling image-uploads through raw post data.
    It uses base64 for encoding and decoding the contents of the file.

    Heavily based on
    https://github.com/tomchristie/django-rest-framework/pull/1268

    Updated for Django REST framework 3.
    """

    def to_internal_value(self, data):
        from django.core.files.base import ContentFile
        import base64
        import six
        import uuid

        # Check if this is a base64 string
        if isinstance(data, six.string_types):
            # Check if the base64 string is in the "data:" format
            if 'data:' in data and ';base64,' in data:
                # Break out the header from the base64 content
                header, data = data.split(';base64,')

            # Try to decode the file. Return validation error if it fails.
            try:
                decoded_file = base64.b64decode(data)
            except TypeError:
                self.fail('invalid_image')

            # Generate file name:
            file_name = str(uuid.uuid4())[:12] # 12 characters are more than enough.
            # Get the file name extension:
            file_extension = self.get_file_extension(file_name, decoded_file)

            complete_file_name = "%s.%s" % (file_name, file_extension, )

            data = ContentFile(decoded_file, name=complete_file_name)

        return super(Base64ImageField, self).to_internal_value(data)

    def get_file_extension(self, file_name, decoded_file):
        import imghdr

        extension = imghdr.what(file_name, decoded_file)
        extension = "jpg" if extension == "jpeg" else extension

        return extension


class UserUploadSerializer(serializers.Serializer):
    avatar = Base64ImageField(
        max_length=None, use_url=True,
    )

    def validate(self, files):
        try:
            avatar = files["avatar"]
        except KeyError:
            return serializers.ValidationError({
                "avatar": "You must select a file"
            })
        return {
            "avatar": avatar
        }

    def update(self, instance: User, data) -> User:
        instance.avatar = data["avatar"]
        instance.save()
        return instance

    def perform_update(self, serializer):
        serializer.save()
