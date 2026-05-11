from django.shortcuts import render

from django.views import generic
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from .models import RangerDocumentRegistry
from .forms import DocumentRegistryForm

class DocumentListView(LoginRequiredMixin, generic.ListView):
    model = RangerDocumentRegistry
    template_name = 'registry/registry_list.html'
    context_object_name = 'documents'

    def get_queryset(self):
        # Rangers only see their own issued numbers
        return RangerDocumentRegistry.objects.filter(user=self.request.user)

class DocumentCreateView(LoginRequiredMixin, generic.CreateView):
    model = RangerDocumentRegistry
    form_class = DocumentRegistryForm
    template_name = 'registry/registry_form.html'
    success_url = reverse_lazy('registry_list')

    def form_valid(self, form):
        # Automatically assign the logged-in ranger
        form.instance.user = self.request.user
        return super().form_valid(form)
    
class DocumentUpdateView(LoginRequiredMixin, generic.UpdateView):
    model = RangerDocumentRegistry
    form_class = DocumentRegistryForm
    template_name = 'registry/registry_form.html'
    success_url = reverse_lazy('registry_list')

    def form_valid(self, form):
        # Automatically assign the logged-in ranger
        form.instance.user = self.request.user
        return super().form_valid(form)