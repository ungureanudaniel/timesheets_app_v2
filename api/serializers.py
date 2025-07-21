from rest_framework import serializers
from reports.models import MonthlyReport


class MonthlyReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = MonthlyReport
        fields = '__all__'

    def validate(self, data):
        # custom validation logic
        if data['end_date'] < data['start_date']:
            raise serializers.ValidationError("End date cannot be earlier than start date.")
        return data
