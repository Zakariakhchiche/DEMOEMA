FROM mcr.microsoft.com/playwright/python:v1.48.0-jammy

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl gnupg2 jq && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Sécurité : unprivileged user (playwright image vient avec pwuser)
USER pwuser

# Point d'entrée : orchestrator qui lit profile.yaml + exécute flows
CMD ["python", "-m", "signup_agent.main"]
