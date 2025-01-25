# SolverGenie Stack Exchange Bot

A web-based control panel for managing the SolverGenie Stack Exchange bot that automatically answers questions across various Stack Exchange sites.

## Features

- Web-based control panel
- Real-time bot status monitoring
- Live output display
- Easy site management
- Start/Stop controls

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment variables in `.env`:
```
STACK_CLIENT_ID=your_client_id
STACK_CLIENT_SECRET=your_client_secret
STACK_KEY=your_api_key
STACK_ACCESS_TOKEN=your_access_token
OPENROUTER_API_KEY=your_openrouter_key
USER_AGENT="SolverGenie Bot/1.0.0 (https://solvergenie.site)"
BOT_USERNAME=your_stack_username
```

3. Configure sites in `sites.txt`:
- Add one Stack Exchange site per line
- Default sites are focused on education (math, physics, etc.)

## Running the Bot

1. Start the web interface:
```bash
python app.py
```

2. Open your browser and go to:
```
http://localhost:5000
```

3. Use the web interface to:
- Start/Stop the bot
- Monitor bot status
- View real-time output
- Manage target sites

## Deployment

To deploy on a server:

1. Install dependencies
2. Set up environment variables
3. Run with gunicorn (recommended for production):
```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## Directory Structure

```
├── app.py              # Flask web application
├── stackexchange_bot.py # Main bot script
├── templates/          # HTML templates
│   └── index.html     # Web interface
├── sites.txt          # Target Stack Exchange sites
├── .env               # Environment variables
└── requirements.txt   # Python dependencies
```

## Notes

- The bot requires at least 10 reputation on each Stack Exchange site to post answers
- Recommended to build reputation organically before running the bot
- Respect Stack Exchange's rate limits and terms of service 