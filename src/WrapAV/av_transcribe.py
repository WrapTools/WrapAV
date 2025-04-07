# av_transcribe.py

import io
import requests
from pathlib import Path
from pydub import AudioSegment
from .av_info import MediaFileInfo
from .av_split_combine import AudioSplitter  # Assuming we have the AudioSplitter class
import sys

import logging

# Logger Configuration
logger = logging.getLogger(__name__)

from WrapConfig import SecretsManager

SUPPORTED_FORMATS = ['flac', 'mp3', 'mp4', 'mpeg', 'mpga', 'm4a', 'ogg', 'wav', 'webm', 'amr']
SUPPORTED_AUDIO = ['mp3', 'wav']
TRANSCRIPTION_MODEL = "whisper-1"
MAX_FILE_SIZE = 20  # in MB


def get_ffmpeg_paths():
    exe_dir = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).parent
    ffmpeg_path = exe_dir / "ffmpeg"
    ffprobe_path = exe_dir / "ffprobe"

    if sys.platform == "win32":  # Add .exe extension for Windows
        ffmpeg_path = ffmpeg_path.with_suffix('.exe')
        ffprobe_path = ffprobe_path.with_suffix('.exe')

    return ffmpeg_path, ffprobe_path


class UnsupportedAudioFormatError(Exception):
    pass


class AudioTranscriber:
    def __init__(self):
        """
        Initializes the AudioTranscriber with the necessary runtime settings and FFmpeg path.
        """
        self.memory_file = io.BytesIO()

        ffmpeg_path, _ = get_ffmpeg_paths()  # Use the get_ffmpeg_paths utility
        if ffmpeg_path.exists():
            AudioSegment.converter = str(ffmpeg_path)
            logger.info(f"FFmpeg path set to: {ffmpeg_path}")
        else:
            raise FileNotFoundError(f"FFmpeg not found at {ffmpeg_path}. Please verify the path.")

    def load_api_key(self):
        """
        Loads the API key from the secrets file (e.g., .env).
        """
        try:
            # Initialize SecretsManager to load secrets from the .env file
            secrets_manager = SecretsManager(".env")
            api_key = secrets_manager.get_secret('OPENAI_API_KEY')  # Assuming the key is stored as OPENAI_API_KEY in .env
            if api_key:
                logger.info("API key loaded successfully.")
                return api_key
            else:
                logger.error("API key not found in secrets file.")
                return None
        except Exception as e:
            logger.error(f"Failed to load API key from secrets file: {e}")
            return None

    def load_file_to_memory(self, file_path):
        try:
            with open(file_path, 'rb') as file:
                self.memory_file = io.BytesIO(file.read())
                self.memory_file.seek(0)
        except Exception as e:
            # print(f"Failed to load file to memory: {e}")
            logger.error(f"Failed to load file to memory: {e}")

    def transcribe_audio(self, audio_file_path, time_stamps=False):
        """
        Transcribe an audio file, either with or without timestamps.
        """
        # Validate file format
        try:
            media_info = MediaFileInfo.from_file(audio_file_path)
            detected_type = self._detect_normalized_type(media_info, audio_file_path)
        except UnsupportedAudioFormatError:
            # Fallback to file extension if format detection fails
            detected_type = audio_file_path.suffix.lower().lstrip('.')

        if detected_type not in SUPPORTED_FORMATS:
            raise UnsupportedAudioFormatError(
                f"Unsupported format: {detected_type}. Supported formats are: {', '.join(SUPPORTED_FORMATS)}"
            )

        # Validate file size
        file_size_mb = self.calculate_file_size(audio_file_path)
        logger.info(f"Processing file: {audio_file_path.name} ({file_size_mb:.2f} MB)")

        # Choose transcription method
        if file_size_mb > MAX_FILE_SIZE:
            logger.info("File size exceeds limit. Transcribing in chunks...")
            return self.transcribe_in_chunks_with_timestamps(
                audio_file_path) if time_stamps else self.transcribe_in_chunks(audio_file_path)
        else:
            logger.info("File size within limit. Transcribing directly...")
            return self.transcribe_audio_with_timestamps(
                audio_file_path) if time_stamps else self.transcribe_audio_from_file(audio_file_path)

    def _detect_normalized_type(self, media_info, audio_file_path: Path):
        """
        Detects the actual format and normalizes it into a common file type for easier processing.
        """
        codec_names = {codec.strip() for codec in media_info.codec_name.lower().split(',') if codec.strip()}

        logger.debug(f"Detected codec(s): {codec_names}")
        logger.debug(f"File extension: {audio_file_path.suffix.lower().lstrip('.')}")

        # Known codec mappings
        codec_mapping = {
            'mp': 'mp3',
            'mpeg_audio': 'mp3',
            'pcm_s16le': 'wav',
            'aac': 'm4a',
            'opus': 'ogg',
            'vorbis': 'ogg',
            'mov': 'mp4',
        }

        # Use codec name if available
        for codec in codec_names:
            normalized_type = codec_mapping.get(codec, codec)
            if normalized_type in SUPPORTED_FORMATS:
                return normalized_type

        # Fallback to file extension detection
        if 'unknown' in codec_names:
            logger.warning("Codec unknown, falling back to file extension detection.")
            if audio_file_path.suffix.lower().lstrip('.') == 'mp3':
                return 'mp3'

        # If still unsupported, raise an error
        raise UnsupportedAudioFormatError(
            f"Unsupported format: {','.join(codec_names)} or extension: {audio_file_path.suffix.lower().lstrip('.')}"
        )

    def transcribe_audio_from_file(self, audio_file_path: Path) -> str:
        """
            Transcribes a smaller audio file directly without chunking.

            Args:
                audio_file_path (Path): The path to the audio file to transcribe.

            Returns:
                str: The transcribed text.

            Raises:
                Exception: If the API key is missing or the transcription fails.
        """
        api_key = self.load_api_key()
        if not api_key:
            logger.error("API key is missing or invalid.")
            raise Exception("Failed to load API key.")

        with open(audio_file_path, 'rb') as audio_file:
            headers = {'Authorization': f'Bearer {api_key}'}
            files = {'file': ('audio.mp3', audio_file, 'audio/mpeg')}
            data = {'model': TRANSCRIPTION_MODEL}

            try:
                response = requests.post('https://api.openai.com/v1/audio/transcriptions',
                                         headers=headers,
                                         files=files,
                                         data=data)
                response.raise_for_status()
                transcription_text = response.json()['text']
                logger.info(f"Transcription successful for {audio_file_path.name}.")
                self.load_file_to_memory(audio_file_path)
                return transcription_text

            except requests.exceptions.HTTPError as e:
                error_message = f"Error code: {e.response.status_code} - {e.response.json()}"
                logger.error(f"Error transcribing audio: {error_message}")
                raise e

    def transcribe_in_chunks(self, audio_file_path: Path):
        """
        Transcribes large audio files by splitting them into smaller chunks.
        """
        logger.info(f"Starting chunking for {audio_file_path.name}...")

        # ✅ Manual export test
        logger.info("Performing a manual export test...")
        try:
            audio = AudioSegment.from_file(audio_file_path)
            audio.export("test_output.mp3", format="mp3", codec="libmp3lame")
            logger.info("Manual export successful. Check for test_output.mp3.")
        except Exception as e:
            logger.error(f"Manual export test failed: {e}")
            raise

        audio_splitter = AudioSplitter(audio_file_path, max_chunk_size_mb=MAX_FILE_SIZE)
        chunks, split_info = audio_splitter.split_audio()
        logger.info(f"Total chunks created: {split_info.chunks_created}")

        full_transcription = []
        temp_chunk_paths = []
        total_duration = 0.0

        try:
            for i, chunk in enumerate(chunks):
                logger.debug(f"Chunk {i} length: {len(chunk)} ms")
                if len(chunk) < 1000:
                    logger.warning(f"Skipping very short chunk {i} (less than 1 second).")
                    continue

                chunk_path = Path(f"chunk_{i}.mp3")
                temp_chunk_paths.append(chunk_path)

                # Export each chunk as an MP3 file using the libmp3lame codec
                try:
                    chunk.export(chunk_path, format="mp3", codec="libmp3lame")
                    logger.debug(f"Exported chunk {i} to {chunk_path}")
                except Exception as export_error:
                    logger.error(f"Error exporting chunk {i}: {export_error}")
                    continue
                logger.debug(
                    f"Exported chunk {i} to {chunk_path} (size: {chunk_path.stat().st_size / 1024:.2f} KB)")

                # Check if the chunk file was created and is valid
                if not chunk_path.exists() or chunk_path.stat().st_size == 0:
                    raise Exception(f"Chunk {chunk_path} is empty or missing.")

                # Transcribe the chunk
                chunk_text = self.transcribe_audio_from_file(chunk_path)
                full_transcription.append(chunk_text)
                total_duration += len(chunk) / 1000  # Convert milliseconds to seconds

        except Exception as e:
            logger.error(f"Error during chunk transcription: {str(e)}")
            raise

        finally:
            # Clean up temp chunk files
            for temp_path in temp_chunk_paths:
                if temp_path.exists():
                    temp_path.unlink()
                    logger.debug(f"Deleted temporary chunk file: {temp_path}")

        self.load_file_to_memory(audio_file_path)
        return {
            'transcription': "\n".join(full_transcription).strip(),
            'duration': total_duration,
            'file_size_mb': self.calculate_file_size(audio_file_path),
        }

    def transcribe_audio_with_timestamps(self, audio_file_path):
        """
        Transcribes a single audio file and returns text with timestamps in verbose JSON format.
        """
        api_key = self.load_api_key()
        if not api_key:
            raise Exception("Failed to load API key.")

        with open(audio_file_path, 'rb') as audio_file:
            headers = {'Authorization': f'Bearer {api_key}'}
            files = {'file': ('audio.mp3', audio_file, 'audio/mpeg')}
            data = {
                'model': TRANSCRIPTION_MODEL,
                'response_format': 'verbose_json'  # Explicitly request verbose JSON
            }

            try:
                response = requests.post('https://api.openai.com/v1/audio/transcriptions',
                                         headers=headers,
                                         files=files,
                                         data=data)
                response.raise_for_status()

                result = response.json()

                self.load_file_to_memory(audio_file_path)

                # Check if 'segments' and 'duration' exist in the result
                segments = result.get('segments', [])
                duration = result.get('duration', 0)

                return {
                    'text': result['text'],
                    'segments': segments,
                    'duration': duration
                }
            except requests.exceptions.HTTPError as e:
                error_message = f"Error code: {e.response.status_code} - {e.response.json()}"
                # print(f"Error transcribing audio: {error_message}")
                logger.error(f"Error transcribing audio: {error_message}")
                raise e

    def transcribe_in_chunks_with_timestamps(self, audio_file_path: Path):
        """
        Transcribes large audio files by splitting them into smaller chunks,
        and returns the transcription with continuous timestamps across chunks.
        """
        # Use AudioSplitter to split the audio file
        audio_splitter = AudioSplitter(audio_file_path, max_chunk_size_mb=MAX_FILE_SIZE)
        chunks, split_info = audio_splitter.split_audio()
        logger.debug(f"Total chunks created: {split_info.chunks_created}")

        full_segments = []
        temp_chunk_paths = []
        current_time_offset = 0.0  # To keep track of cumulative time

        total_duration = 0

        try:
            for i, chunk in enumerate(chunks):
                chunk_path = Path(f"chunk_{i}.mp3")
                temp_chunk_paths.append(chunk_path)
                chunk.export(chunk_path, format="mp3")
                logger.debug(f"Exported chunk {i} to {chunk_path}")

                # Transcribe the chunk with timestamps
                chunk_transcription = self.transcribe_audio_with_timestamps(chunk_path)

                # Check if 'segments' exist in the chunk's transcription
                if 'segments' in chunk_transcription:
                    # Adjust segment timestamps by adding the current_time_offset
                    for segment in chunk_transcription['segments']:
                        segment['start'] += current_time_offset
                        segment['end'] += current_time_offset

                    # Append the adjusted segments to the full list
                    full_segments.extend(chunk_transcription['segments'])

                current_time_offset += chunk_transcription.get('duration', 0)
                total_duration += chunk_transcription.get('duration', 0)

        finally:
            # Clean up temp chunk files
            for temp_path in temp_chunk_paths:
                if temp_path.exists():
                    temp_path.unlink()  # Delete temp chunk file

        self.load_file_to_memory(audio_file_path)

        return {
            'text': " ".join([segment['text'] for segment in full_segments]),  # Combine all the segment texts
            'segments': full_segments,  # Return the combined segments with adjusted timestamps
            'duration': current_time_offset,  # Total duration of the full audio file
            # 'file_size_mb': audio_file_path.stat().st_size / (1024 * 1024),  # File size in MB
            'file_size_mb': self.calculate_file_size(audio_file_path)  # File size in MB
        }

    def get_memory_file(self):
        """
        Returns the memory file.

        Returns:
            io.BytesIO: The memory file containing the audio data.
        """
        return self.memory_file

    def calculate_file_size(self, file_path: Path) -> float:
        """
        Returns the file size in MB.
        """
        return file_path.stat().st_size / (1024 * 1024)
