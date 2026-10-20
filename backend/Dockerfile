FROM python:3.12-slim

# Each game folder is a git repository (one commit per Pix turn, undo).
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py pix_agent.py res_tool.py prompt_fr.md ./

ENV GAMES_DIR=/games
EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
