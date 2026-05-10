import os
from PIL import Image
from django.core.management.base import BaseCommand
from django.apps import apps

class Command(BaseCommand):
    help = 'Resizes all existing timesheet images to save disk space'

    def handle(self, *args, **kwargs):
        # Automatically find your model
        TimesheetImage = apps.get_model('timesheets', 'TimesheetImage') # Replace 'timesheets' with your app name
        images = TimesheetImage.objects.all()
        
        self.stdout.write(f"Found {images.count()} images. Starting...")

        for ts_img in images:
            if not ts_img.image or not os.path.exists(ts_img.image.path):
                continue
            
            file_path = ts_img.image.path
            img = Image.open(file_path)
            
            # Only process if wide or heavy
            if img.width > 1200 or os.path.getsize(file_path) > 500000:
                # Resize logic
                max_width = 1200
                w_percent = (max_width / float(img.width))
                h_size = int((float(img.height) * float(w_percent)))
                
                img = img.resize((max_width, h_size), Image.Resampling.LANCZOS)
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                
                img.save(file_path, "JPEG", quality=70, optimize=True)
                self.stdout.write(self.style.SUCCESS(f"Compressed: {os.path.basename(file_path)}"))
            else:
                self.stdout.write(f"Skipped: {os.path.basename(file_path)}")