# Use an official lightweight Python image.
# 3.10-slim is good balance of size and compatibility.
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies required for OpenCV and DocTR
# libgl1-mesa-glx: for OpenCV
# libpango: for some OCR/font text operations if needed
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
# --no-cache-dir to keep image smaller
RUN pip install --no-cache-dir -r requirements.txt

# Download DocTR models during build to speed up first startup
# We run a small script to trigger the download
RUN python -c "from doctr.models import ocr_predictor; ocr_predictor(det_arch='db_resnet50', reco_arch='crnn_vgg16_bn', pretrained=True)"

# Copy the rest of the application
COPY . .

# Set environment variable to ensure output is flushed immediately
ENV PYTHONUNBUFFERED=1

# Command to run the bot
CMD ["python", "bot.py"]
