FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg2 \
    unzip \
    curl \
    xvfb \
    ca-certificates \
    fonts-liberation \
    libappindicator3-1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libc6 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libexpat1 \
    libfontconfig1 \
    libgcc1 \
    libgconf-2-4 \
    libgdk-pixbuf2.0-0 \
    libglib2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libstdc++6 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libxss1 \
    libxtst6 \
    lsb-release \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Download and install Chrome
RUN wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get update \
    && dpkg -i google-chrome-stable_current_amd64.deb || apt-get -fy install \
    && rm google-chrome-stable_current_amd64.deb \
    && google-chrome --version

# Download and install ChromeDriver with fallback
RUN CHROME_VERSION=$(google-chrome --version | grep -oE "[0-9]+\.[0-9]+\.[0-9]+" | head -1) \
    && echo "Chrome version: $CHROME_VERSION" \
    && CHROME_MAJOR=$(echo $CHROME_VERSION | cut -d. -f1) \
    && echo "Chrome major version: $CHROME_MAJOR" \
    && if [ "$CHROME_MAJOR" -ge "115" ]; then \
        # For Chrome 115+, use new ChromeDriver API
        CHROMEDRIVER_URL="https://googlechromelabs.github.io/chrome-for-testing/latest-versions-per-milestone.json"; \
        CHROMEDRIVER_VERSION=$(curl -s $CHROMEDRIVER_URL | grep -o "\"$CHROME_MAJOR\":{\"version\":\"[^\"]*" | cut -d'"' -f4); \
        if [ -z "$CHROMEDRIVER_VERSION" ]; then \
            CHROMEDRIVER_VERSION="120.0.6099.109"; \
        fi; \
        echo "Using ChromeDriver version: $CHROMEDRIVER_VERSION"; \
        wget -q "https://storage.googleapis.com/chrome-for-testing-public/${CHROMEDRIVER_VERSION}/linux64/chromedriver-linux64.zip" \
        && unzip chromedriver-linux64.zip \
        && mv chromedriver-linux64/chromedriver /usr/local/bin/ \
        && rm -rf chromedriver-linux64.zip chromedriver-linux64; \
    else \
        # For Chrome < 115, use legacy API
        CHROMEDRIVER_VERSION=$(curl -s "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_${CHROME_MAJOR}"); \
        echo "Using legacy ChromeDriver version: $CHROMEDRIVER_VERSION"; \
        wget -q "https://chromedriver.storage.googleapis.com/${CHROMEDRIVER_VERSION}/chromedriver_linux64.zip" \
        && unzip chromedriver_linux64.zip \
        && mv chromedriver /usr/local/bin/ \
        && rm chromedriver_linux64.zip; \
    fi \
    && chmod +x /usr/local/bin/chromedriver \
    && chromedriver --version

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:99

# Expose port for webhook (if needed)
EXPOSE 8000

# Start command
CMD ["python", "main.py"]