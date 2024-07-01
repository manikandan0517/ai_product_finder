from django.db import models
from PIL import Image

class ImageData(models.Model):
    object_name = models.CharField(max_length=100)
    color = models.CharField(max_length=100)
    count = models.IntegerField(default=1)
    image = models.ImageField(upload_to='images/',default='images/default.jpg')
    dimensions=models.CharField(max_length=100)
    image_hash = models.CharField(max_length=64)
    manufacturer=models.CharField(max_length=100)
    specification=models.CharField(max_length=1000) 
    description=models.CharField(max_length=1000)

    def __str__(self):
        return f"{self.object_name} ({self.color}): {self.count}"