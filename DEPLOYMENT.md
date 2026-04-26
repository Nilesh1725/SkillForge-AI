# 🚀 Deployment Guide

This guide covers how to deploy the AI Interview Agent to production environments.

## 📋 Prerequisites
- A Google Cloud Project with **Gemini API** access (recommended).
- Or a **Hugging Face** account for fallback models.
- A production server or PaaS provider (Render, Heroku, AWS).

## ☁️ Deploying to Render (Recommended)
1. **Connect GitHub**: Link your repository to a new "Web Service".
2. **Environment**: Select `Python` as the runtime.
3. **Build Command**:
   ```bash
   pip install -r requirements.txt
   ```
4. **Start Command**:
   ```bash
   gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT
   ```
5. **Environment Variables**: Add the following in the Render dashboard:
   - `GEMINI_API_KEY`: Your Google API Key.
   - `HF_API_TOKEN`: Your Hugging Face token.
   - `DEBUG`: `false`
   - `PORT`: `8000`

## 🐳 Deploying with Docker
A `Dockerfile` is provided for containerized deployments.

1. **Build the Image**:
   ```bash
   docker build -t ai-interview-agent .
   ```
2. **Run the Container**:
   ```bash
   docker run -p 8000:8000 --env-file .env ai-interview-agent
   ```

## 🔐 Security Best Practices
- **Never commit `.env`**: Ensure `.env` is in your `.gitignore`.
- **CORS Configuration**: In `main.py`, restrict `allow_origins` to your production domain instead of `["*"]`.
- **Rate Limiting**: Consider adding a rate limiter (like `slowapi`) to prevent API abuse and high LLM costs.

## 🛠️ Performance Tuning
- **Workers**: Adjust the number of Gunicorn workers based on your CPU cores (`2 * cores + 1`).
- **Timeout**: The `LLM_TIMEOUT` is set to 120s by default to account for slow LLM inference.
