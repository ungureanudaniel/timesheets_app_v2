from django import forms
from .models import RangerDocumentRegistry

class DocumentRegistryForm(forms.ModelForm):
    class Meta:
        model = RangerDocumentRegistry
        fields = ['doc_number', 'doc_date', 'explanation']
        widgets = {
            'doc_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 123/TP (de la Traian Popescu)'}),
            'doc_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'explanation': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }