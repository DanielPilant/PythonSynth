# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# System dependencies for audio and keyboard (Linux specific for containerized environments)
RUN apt-get update && apt-get install -y \
    libasound2-dev \
    libportaudio2 \
    alsa-utils \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container at /app
COPY . .

# Run the script
CMD ["python", "synth.py"]