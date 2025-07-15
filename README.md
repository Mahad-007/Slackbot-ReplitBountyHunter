# Slack Replit Bounty Bot

## Overview
This Flask app scrapes the latest open bounties from Replit, finds the highest-value bounty posted in the last 24 hours, and sends it to a Slack channel. It avoids duplicates and is designed for easy deployment on Vercel with scheduled scraping every 24 hours.

## Features
- Scrapes https://replit.com/bounties for open bounties
- Filters for bounties posted in the last 24 hours
- Sends the highest-value new bounty to Slack
- Avoids duplicate notifications
- Deployable on Vercel (free tier)
- Can be triggered via endpoint or scheduled job

## Deployment (Vercel)
1. **Fork/clone this repo.**
2. **Set environment variables in Vercel dashboard:**
   - `SLACK_WEBHOOK_URL`: Your Slack Incoming Webhook URL
   - `FIRECRAWL_API_KEY`: Your Firecrawl API key
3. **Deploy using the [Flask Hello World template](https://vercel.com/templates/python/flask-hello-world) or your own repo.**
4. **Vercel will auto-detect the `vercel.json` config and deploy the Flask app.**

## Scheduling (Cron)
- **Recommended:** Use [Vercel Cron Jobs](https://vercel.com/docs/cron-jobs) to call `/api/scrape` every 24 hours.
- **Alternative:** Use an external service like [EasyCron](https://www.easycron.com/) or [GitHub Actions] to make a GET request to your deployed `/api/scrape` endpoint every 24 hours.

Example Vercel cron config (in Vercel dashboard):
```
Path: /api/scrape
Schedule: 0 0 * * *
```

## Local Testing
1. Create a `.env` file with your secrets:
   ```
   SLACK_WEBHOOK_URL=your-slack-webhook-url
   FIRECRAWL_API_KEY=your-firecrawl-api-key
   ```
2. Run locally:
   ```bash
   pip install -r requirements.txt
   python api/index.py
   ```
3. Visit `http://localhost:5000/scrape` to trigger the bot manually.

## Notes
- The app writes sent bounty links to `sent_bounties.txt` to avoid duplicates.
- For production, consider using a persistent storage solution if needed.
- For Slack testing, use a private channel until the bot is finalized.

## Learning Goals
- Flask basics
- Python web scraping
- Slack API integration
- Vercel deployment
- Cron job scheduling 