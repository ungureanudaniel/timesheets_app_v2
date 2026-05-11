from django.db import models
from django.conf import settings

class RangerDocumentRegistry(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    doc_number = models.CharField(max_length=50, verbose_name="Nr. Înregistrare")
    doc_date = models.DateField(verbose_name="Data Document")
    explanation = models.TextField(verbose_name="Explicație pe scurt")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Înregistrare Document"

    def __str__(self):
        return f"{self.doc_number} - {self.user.last_name}"
