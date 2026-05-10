import os
from PIL import Image
from django.core.management.base import BaseCommand
# Change 'reports' to the actual folder name of your app
from timesheet.models import TimesheetImage 

class Command(BaseCommand):
    help = 'Resizes all existing timesheet images to save disk space'

    def handle(self, *args, **kwargs):
        images = TimesheetImage.objects.all()
        self.stdout.write(f"Found {images.count()} images. Starting...")

        for ts_img in images:
            # Check if image field has a file and if that file exists on disk
            if not ts_img.image or not os.path.exists(ts_img.image.path):
                continue
            
            file_path = ts_img.image.path
            
            # Open the image using Pillow
            with Image.open(file_path) as img:
                # Only process if wide (>1200px) or heavy (>500KB)
                if img.width > 1200 or os.path.getsize(file_path) > 500000:
                    max_width = 1200
                    w_percent = (max_width / float(img.width))
                    h_size = int((float(img.height) * float(w_percent)))
                    
                    # Resize and handle transparency
                    resized_img = img.resize((max_width, h_size), Image.Resampling.LANCZOS)
                    if resized_img.mode in ("RGBA", "P"):
                        resized_img = resized_img.convert("RGB")
                    
                    # Save back to the same path
                    resized_img.save(file_path, "JPEG", quality=70, optimize=True)
                    self.stdout.write(self.style.SUCCESS(f"Compressed: {os.path.basename(file_path)}"))
                else:
                    self.stdout.write(f"Skipped: {os.path.basename(file_path)}")