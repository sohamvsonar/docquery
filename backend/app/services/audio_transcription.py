"""
Audio transcription service using OpenAI Whisper API.
Supports various audio formats (MP3, WAV, M4A, etc.).
"""

import logging
from typing import Dict, Any, Optional
from pathlib import Path
import openai

from app.config import settings

logger = logging.getLogger(__name__)


class AudioTranscriptionService:
    """Service for transcribing audio files using OpenAI Whisper API."""

    def __init__(self, api_key: str = None):
        """
        Initialize audio transcription service.

        Args:
            api_key: OpenAI API key (defaults to settings.openai_api_key)
        """
        self.api_key = api_key or settings.openai_api_key
        self.client = openai.OpenAI(api_key=self.api_key)

    def transcribe(self, audio_path: str, language: Optional[str] = None) -> Dict[str, Any]:
        """
        Transcribe an audio file to text.

        Args:
            audio_path: Path to the audio file
            language: Optional language code (e.g., "en", "es", "fr")
                     If not specified, Whisper will auto-detect

        Returns:
            Dictionary containing:
            {
                "text": str,              # Transcribed text
                "language": str,          # Detected/specified language
                "duration": float,        # Audio duration (if available)
                "error": Optional[str]
            }

        Raises:
            FileNotFoundError: If audio file doesn't exist
            Exception: If transcription fails
        """
        result = {
            "text": "",
            "language": language or "auto",
            "duration": None,
            "error": None
        }

        try:
            # Check if file exists
            if not Path(audio_path).exists():
                raise FileNotFoundError(f"Audio file not found: {audio_path}")

            logger.info(f"Transcribing audio file: {audio_path}")

            # Prepare transcription request
            with open(audio_path, "rb") as audio_file:
                # Call Whisper API
                transcription_params = {
                    "model": "whisper-1",
                    "file": audio_file,
                    "response_format": "verbose_json"  # Get detailed response
                }

                # Add language if specified
                if language:
                    transcription_params["language"] = language

                response = self.client.audio.transcriptions.create(**transcription_params)

                # Extract results
                result["text"] = response.text.strip()

                # Get detected language if available
                if hasattr(response, 'language'):
                    result["language"] = response.language

                # Get duration if available
                if hasattr(response, 'duration'):
                    result["duration"] = response.duration

                logger.info(
                    f"Transcribed audio: {len(result['text'])} characters, "
                    f"language: {result['language']}"
                )

        except FileNotFoundError:
            raise
        except openai.OpenAIError as e:
            logger.error(f"OpenAI Whisper API error: {e}")
            result["error"] = f"Whisper API error: {str(e)}"
            raise
        except Exception as e:
            logger.error(f"Audio transcription failed for {audio_path}: {e}")
            result["error"] = str(e)
            raise

        return result

    def transcribe_with_timestamps(self, audio_path: str) -> Dict[str, Any]:
        """
        Transcribe audio with word-level timestamps.

        Args:
            audio_path: Path to the audio file

        Returns:
            Dictionary with transcription and timestamp data
        """
        result = {
            "text": "",
            "segments": [],
            "error": None
        }

        try:
            with open(audio_path, "rb") as audio_file:
                response = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="verbose_json",
                    timestamp_granularities=["segment"]
                )

                result["text"] = response.text

                # Extract segments with timestamps
                if hasattr(response, 'segments'):
                    result["segments"] = [
                        {
                            "text": seg.text,
                            "start": seg.start,
                            "end": seg.end
                        }
                        for seg in response.segments
                    ]

                logger.info(f"Transcribed with {len(result['segments'])} segments")

        except Exception as e:
            logger.error(f"Timestamp transcription failed: {e}")
            result["error"] = str(e)
            raise

        return result


# Global instance
audio_transcription_service = AudioTranscriptionService()
