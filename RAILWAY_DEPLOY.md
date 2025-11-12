# Engineering Reports RAG Backend - Railway Deployment

## Required Services on Railway

This application requires the following services:

1. **PostgreSQL Database** - For tracking uploads and errors
2. **Qdrant Vector Database** - For storing embeddings (you'll need to deploy separately or use Qdrant Cloud)

## Environment Variables Required

Set these in Railway dashboard:

```
# API Keys
VOYAGE_API_KEY=your_voyage_api_key
OPENAI_API_KEY=your_openai_api_key
APP_API_KEY=your_custom_api_key_for_gpt

# Database (Railway will auto-provide DATABASE_URL for PostgreSQL)
DATABASE_URL=${{Postgres.DATABASE_URL}}

# Qdrant (use Qdrant Cloud or deploy separately)
QDRANT_URL=your_qdrant_url
QDRANT_COLLECTION=report-paragraphs

# Models
EMBEDDING_MODEL=voyage-3-large
EMBEDDING_DIMENSION=1024
RERANK_MODEL=rerank-2.5-lite
```

## Deployment Steps

1. **Connect GitHub repo to Railway**
2. **Add PostgreSQL service** in Railway
3. **Set up Qdrant** (Qdrant Cloud or separate Railway service)
4. **Add all environment variables** in Railway dashboard
5. **Deploy!**

## After Deployment

1. Get your Railway app URL (e.g., `https://your-app.railway.app`)
2. Update Custom GPT action schema with new URL
3. Upload PDFs through the web portal to populate database
4. Test with Custom GPT!

## Local Development

See main README.md for local setup instructions.
