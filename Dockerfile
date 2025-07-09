FROM mcr.microsoft.com/playwright/python:v1.52.0-noble

WORKDIR /app

# Copy your code and dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./update_mymaps.py .
COPY ./retrieve_stations.py .

# Default command (adjust according to your script)
CMD ["sh", "-c", "python retrieve_stations.py && python update_mymaps.py"]
