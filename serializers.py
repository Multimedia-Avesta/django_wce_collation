from rest_framework import serializers
from api import serializers as api_serializers
from transcriptions.models import Transcription
from . import models


class CollationProjectSerializer(api_serializers.BaseModelSerializer):
    witnesses = serializers.SlugRelatedField(
        slug_field='identifier',
        queryset=Transcription.objects.all(),
        allow_null=True,
        many=True
    )
    basetext = serializers.SlugRelatedField(
        slug_field='identifier',
        queryset=Transcription.objects.all(),
        allow_null=True
    )

    class Meta:
        model = models.Project


class DecisionSerializer(api_serializers.BaseModelSerializer):

    class Meta:
        model = models.Decision


class CollationSerializer(api_serializers.BaseModelSerializer):

    class Meta:
        model = models.Collation
