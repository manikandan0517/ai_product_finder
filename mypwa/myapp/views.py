from django.shortcuts import render, get_object_or_404
from django.core.files.storage import FileSystemStorage
from .models import ImageData
import openai
import base64
import os
import hashlib
from django.views.decorators.csrf import csrf_exempt
import json
from django.conf import settings


# Set your OpenAI API key
openai.api_key =settings.OPENAI_API_KEY

@csrf_exempt
def upload_files(request):
    if request.method == 'POST':
        transcription = None
        image_description = None

        # Handle audio file
        if 'audio_file' in request.FILES:
            audio_file = request.FILES['audio_file']
            fs = FileSystemStorage()
            audio_filename = fs.save(audio_file.name, audio_file)
            audio_file_path = fs.path(audio_filename)
            transcription = transcribe_audio(audio_file_path)
            try:
                os.remove(audio_file_path)  # Delete the audio file after processing
            except OSError as e:
                print(f"Error deleting audio file: {e}")

        # Handle image file
        if 'image_file' in request.FILES:
            image_file = request.FILES['image_file']
            fs = FileSystemStorage()
            image_filename = fs.save(image_file.name, image_file)
            image_file_path = fs.path(image_filename)
            
            # Generate hash for the image
            image_hash = generate_image_hash(image_file_path)
            image_description = process_image(image_file_path, image_file, image_hash, transcription)
            
            try:
                os.remove(image_file_path)  # Delete the image file after processing
            except OSError as e:
                print(f"Error deleting image file: {e}")

            images = ImageData.objects.all()
            # Render results
            return render(request, 'imagelist.html', {'images': images, 'image_description': image_description})

    return render(request, 'upload.html')

def generate_image_hash(image_path):
    hash_md5 = hashlib.md5()
    with open(image_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def transcribe_audio(file_path):
    with open(file_path, "rb") as audio_file:
        response = openai.Audio.transcribe(
            model="whisper-1",
            file=audio_file
        )
    return response['text']

def image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read())
        return encoded_string.decode("utf-8")

def process_image(image_path, image_file, image_hash, transcription=None):
    # Generate description using OpenAI API
    image_base64 = image_to_base64(image_path)
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": """please describe the objects in the image, 
                        mention their dominant color and height&width of object in the image in centimeters and 
                        i want to find the manufacturer of the product in the image check for manufacturer name in the product
                        if the manufacturer is unknown for exact product try to get similar product manufacturer and return any one manufacturer necessarily
                        if two or more manufacturer have the exact products or similar products give the well known manufacturer and 
                        also the finished specification of the product,specification must contain what is the material used with less than 5 words and its description must contains what is the product and its speciality must contain minimum 10 to 20 words without fail and it should be clear and concise,specification and description should be without any subheadings .The examples are (laptop,black,23x40,dell,its specification,its description phone,white,10x20,redmi,its specification,its description etc.) 
                        please provide the answer only in the format as I mentioned in the examples.
                        if there are too many objects then give only the name big object, its color and height&width 
                        in the example format and there will be no spaces or extra words between the output and
                        specify the color names only in American English don't try to give the exact color
                        give only the parent color name."""
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpg;base64,{image_base64}"
                        },
                    },
                ],
            }
        ],
        max_tokens=300
    )
    description = response['choices'][0]['message']['content']
    data = description.split(',')
    object_name = data[0]
    color = data[1]
    dimension = data[2].split('x')
    height = dimension[0]
    width = dimension[1]
    dimensions_str = f"Height={height}cm, Width={width}cm"
    manufacturer = data[3].strip() if len(data) > 3 else ""
    specification = data[4].strip() if len(data) > 4 else ""
    description = transcription if transcription else (data[5].strip() if len(data) > 5 else "")

    # Check if an image with the same hash or details exists
    image_entry = ImageData.objects.filter(image_hash=image_hash).first()
    if image_entry:
        # Update existing entry if image hash exists
        image_entry.count += 1
        image_entry.description=description
        image_entry.image = image_file
        image_entry.save()
        return {
            "object_name": image_entry.object_name,
            "color": image_entry.color,
            "dimensions": image_entry.dimensions,
            "manufacturer": image_entry.manufacturer,
            "specifications": image_entry.specification,
            "description": image_entry.description
        }

    # Otherwise, create a new entry in the database
    ImageData.objects.create(
        object_name=object_name,
        color=color,
        count=1,
        image=image_file,
        dimensions=dimensions_str,
        image_hash=image_hash,
        manufacturer=manufacturer,
        specification=specification,
        description=description
    )

    return {
        "object_name": object_name,
        "color": color,
        "dimensions": dimensions_str,
        "manufacturer": manufacturer,
        "specifications": specification,
        "description": description
    }

def image_list(request):
    images = ImageData.objects.all()
    return render(request, 'imagelist.html', {'images': images})

def image_detail(request, pk):
    image = get_object_or_404(ImageData, pk=pk)
    return render(request, 'image_detail.html', {'image': image})
