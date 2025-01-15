import logging
from langchain_community.document_loaders import YoutubeLoader
from urllib.parse import parse_qs, urlparse
from youtube_transcript_api import YouTubeTranscriptApi
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = FastAPI()

origins = ["*", "http://localhost", "https://appsumo.com"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],

)

def extract_video_id(youtube_url):
    """Extracts the video ID from various YouTube URL formats."""
    parsed_url = urlparse(youtube_url)
    if "youtube.com" in parsed_url.netloc:
        query_params = parse_qs(parsed_url.query)
        return query_params.get("v", [None])[0]
    elif "youtu.be" in parsed_url.netloc:
        return parsed_url.path.lstrip("/")
    elif "youtube.com" in parsed_url.path:
        return parsed_url.path.split("/")[-1]
    return ""


async def ai_yt_long(url):
    """Fetches content using YoutubeLoader and falls back to YouTubeTranscriptApi."""
    try:
        logging.info("Initializing YouTube loader.")
        video_id = extract_video_id(url)
    except Exception as e:
        logging.info(f"Failed to extract video ID: {e}")
        return ""

    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        transcript = transcript_list.find_transcript(['en'])  # Replace 'en' with the desired language code
        text = transcript.fetch()
        final =  " ".join([entry['text'] for entry in text])

        logging.info(f"Loaded data using YouTubeTranscriptApi: {final[:20]}...")
        return final if final else ""
    except Exception as e:
        logging.info(f"YouTubeTranscriptApi failed: {e}")

    try:

        if video_id == "":
            raise ValueError("Invalid YouTube URL")

        loader = YoutubeLoader(video_id)
        youtube_data = loader.load()
        text = "\n".join(doc.page_content for doc in youtube_data if doc.page_content)

        if text:
            logging.info(f"Loaded data using YoutubeLoader: {text[:20]}...")
            return text
        else:
            logging.info("YoutubeLoader returned empty data. Falling back to YouTubeTranscriptApi.")
    except Exception as e:
        logging.info(f"YoutubeLoader failed: {e}")
        return ""


@app.post("/api/aiytlong")
async def youtube_scrapper_ai(data: dict):
    url = data.get('url', "")[0]
    try:
        text = await ai_yt_long(url)
    except Exception as e:
        logging.error(e)
        text = ""

    if text != "":
        response_payload = {
            "failed": False,
            "code": 200,
            "message": "Text Extracted",
            "data": {
                "text": text
            }
        }

        return response_payload
    else:
        return {
            "failed": True,
            "code": 204,
            "message": "No text found in the video.",
            "data": {"text": ""}
        }


@app.get("/api/v1/hello")
async def edit_hell():
    return {"data": "url"}


if __name__ == "__main__":
    uvicorn.run(app)