# YouTube Class Quote Extractor

A Streamlit app that extracts the **5 best quotes** from YouTube lecture transcripts (Stanford, MIT, or any class video) using only free-tier services.

## Features

- Extract transcripts with `youtube-transcript-api` (no YouTube API quota)
- Use Google Gemini free tier to rank and extract top quotes
- Show quote text, context, importance, and timestamp
- Download results as JSON
- Toggle transcript preview
- Graceful error handling for missing transcripts and API failures

## Tech Stack

- Python 3.9+
- Streamlit
- `youtube-transcript-api`
- Google Gemini API (`google-generativeai`)

## Quick Start

1. Clone this repository.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run the app:

```bash
streamlit run app.py
```

4. In the app sidebar, add your Gemini API key (free):
   https://aistudio.google.com/app/apikeys

## Usage

1. Paste a YouTube URL or video ID.
2. Click **Extract Top 5 Quotes**.
3. Review quotes and optionally show transcript preview.
4. Download as JSON with the built-in button.

## Streamlit Cloud Deployment (Free)

1. Push this repository to GitHub.
2. Go to [Streamlit Community Cloud](https://share.streamlit.io/).
3. Create a new app and select this repo.
4. Set your app entrypoint to `app.py`.
5. Deploy.

## Notes

- Some videos do not provide transcripts; these are handled with user-friendly errors.
- Gemini free tier supports this use case well for small-to-medium workloads.
