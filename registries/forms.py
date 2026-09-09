from django import forms
from django.core.validators import MinValueValidator, MaxValueValidator
from .models import RangerDocumentRegistry

class DocumentRegistryForm(forms.ModelForm):
    doc_number = forms.IntegerField(
        validators=[
            MinValueValidator(1, message="Numărul trebuie să fie minim 001."),
            MaxValueValidator(999, message="Numărul nu poate depăși 999.")
        ],
    widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'maxlength': '3',
            'inputmode': 'numeric',
            'pattern': r'\d{3}',
            'oninput': "this.value = this.value.replace(/\\D/g, '').slice(0, 3);"
        })
    )
    class Meta:
        model = RangerDocumentRegistry
        fields = ['doc_number', 'doc_date', 'explanation']
        widgets = {
            'doc_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'explanation': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    def clean_doc_number(self):
        doc_number = self.cleaned_data.get('doc_number')
        if doc_number is not None and (doc_number < 1 or doc_number > 999):
            raise forms.ValidationError("Numărul de înregistrare trebuie să aibă maxim 3 cifre.")
        return doc_number