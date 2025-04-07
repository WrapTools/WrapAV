# av_split_combine.py

from pathlib import Path
from pydub import AudioSegment
import math
from dataclasses import dataclass
from typing import List
import logging

# Logger Configuration
logger = logging.getLogger(__name__)

from WrapAV.av_info import MediaFileInfo  # Assuming the earlier MediaFileInfo class is in a module named media_info

MAX_CHUNK_SIZE = 20
DEFAULT_COMBINED_BIT_RATE = "192k"

@dataclass
class AudioSplitInfo:
    file_type: str
    total_size_mb: float
    total_duration_seconds: float
    chunk_size_mb: float
    number_of_chunks: int
    chunk_duration_ms: int
    chunks_created: int
    original_bit_rate_kbps: int

class UnsupportedAudioFormatError(Exception):
    """Custom exception for unsupported audio formats."""
    pass


class AudioSplitter:
    """
    A class to split and combine audio files (MP3 and WAV only) based on size and duration.

    Attributes:
    -----------
    audio_file_path : Path
        Path to the audio file to be split or combined.
    max_chunk_size_mb : int
        Maximum size for each chunk in MB.
    audio : AudioSegment
        Loaded audio segment for processing.
    """

    # SUPPORTED_FORMATS = ['mp3', 'pcm_s16le']
    SUPPORTED_FORMATS = ['mp3', 'wav']

    def __init__(self, audio_file_path: Path, max_chunk_size_mb: int = MAX_CHUNK_SIZE, default_combine_bit_rate: str = DEFAULT_COMBINED_BIT_RATE):
        """
        Initializes the AudioSplitter with the audio file.

        Parameters:
        -----------
        audio_file_path : Path
            The path to the audio file (MP3 or WAV).
        max_chunk_size_mb : int, optional
            The maximum size for each chunk in MB (default is 10).
        """
        self.audio_file_path = audio_file_path
        self.max_chunk_size_mb = max_chunk_size_mb
        self.default_combine_bit_rate = default_combine_bit_rate

        # Use MediaFileInfo to detect file format
        media_info = MediaFileInfo.from_file(audio_file_path)
        codec = media_info.codec_name.lower()

        # Log detected codec
        print(f"Detected codec: {codec}")

        # If the codec is unknown, fallback to using the file extension
        if codec == 'unknown':
            print("Codec is unknown. Falling back to file extension detection.")
            codec = audio_file_path.suffix.lower().lstrip('.')

        # Validate the codec or extension
        if codec not in self.SUPPORTED_FORMATS:
            raise UnsupportedAudioFormatError(
                f"Unsupported codec: {codec}. Only {', '.join(self.SUPPORTED_FORMATS)} are allowed."
            )

        if codec == 'unknown':
            print("Codec is unknown. Falling back to file extension detection.")
            codec = self.audio_file_path.suffix.lower().lstrip('.')

        if codec not in self.SUPPORTED_FORMATS:
            raise UnsupportedAudioFormatError(f"Unsupported codec: {codec}. Only MP3 and WAV are allowed.")

        # Ensure the format is valid for export
        self.audio_format = 'mp3' if codec == 'mp3' else 'wav'

        # self.original_bit_rate_kbps = media_info.bit_rate_kbps
        self.original_bit_rate_kbps = media_info.bit_rate_kbps or 128  # Default to 128 kbps if unknown

        # Load the audio file
        # self.audio = AudioSegment.from_file(str(audio_file_path), format=self.audio_format)
        self.audio = AudioSegment.from_file(str(audio_file_path), format="mp3")

    def split_audio(self) -> (List[AudioSegment], AudioSplitInfo):
        """
        Splits the audio file into chunks based on the file size and max chunk size.

        Returns:
        --------
        (List[AudioSegment], AudioSplitInfo):
            A list of audio segments (chunks) and details of the split in an AudioSplitInfo dataclass.
        """
        file_size_bytes = self.audio_file_path.stat().st_size
        file_size_mb = file_size_bytes / (1024 * 1024)
        max_chunk_size_bytes = self.max_chunk_size_mb * 1024 * 1024  # Convert MB to bytes
        num_chunks = math.ceil(file_size_bytes / max_chunk_size_bytes)

        # Total duration of the audio in milliseconds
        total_duration_ms = len(self.audio)
        total_duration_seconds = total_duration_ms / 1000

        # Calculate the duration of each chunk in milliseconds
        # chunk_duration_ms = total_duration_ms // num_chunks
        chunk_duration_ms = min(total_duration_ms, int(max_chunk_size_bytes * 8 * 1000 / self.original_bit_rate_kbps))

        # Split the audio into chunks
        audio_parts = []
        print(f"Splitting {self.audio_file_path.name} into {num_chunks} chunks.")

        for start_time in range(0, total_duration_ms, chunk_duration_ms):
            end_time = min(start_time + chunk_duration_ms, total_duration_ms)
            chunk_duration = end_time - start_time
            if chunk_duration >= 1000:  # Ensure chunks are at least 1 second long
                audio_part = self.audio[start_time:end_time]
                audio_parts.append(audio_part)

        # Return both the audio chunks and split information as a dataclass
        split_info = AudioSplitInfo(
            file_type=self.audio_format,
            total_size_mb=file_size_mb,
            total_duration_seconds=total_duration_seconds,
            chunk_size_mb=self.max_chunk_size_mb,
            number_of_chunks=num_chunks,
            chunk_duration_ms=chunk_duration_ms,
            chunks_created=len(audio_parts),
            original_bit_rate_kbps=self.original_bit_rate_kbps,
        )

        return audio_parts, split_info

    def combine_audio(self, chunks: List[AudioSegment], output_path: Path, use_original_bit_rate: bool = True) -> None:
        """
        Combines a list of audio segments into a single file.
        """
        combined_audio = AudioSegment.empty()
        for chunk in chunks:
            combined_audio += chunk

        bit_rate = f"{self.original_bit_rate_kbps}k" if use_original_bit_rate else self.default_combine_bit_rate

        # Ensure valid export format
        if self.audio_format not in ['mp3', 'wav']:
            raise ValueError(f"Invalid audio format for export: {self.audio_format}")

        print(f"Exporting combined audio to {output_path} as {self.audio_format}")
        combined_audio.export(str(output_path), format=self.audio_format, bitrate=bit_rate)


# Example usage

if __name__ == "__main__":
    # Initialize splitter and detect info
    # splitter = AudioSplitter(Path('/home/dave/Python/WrapLibraries/WrapAV/data/test_long.mp3'))  # , max_chunk_size_mb=20
    splitter = AudioSplitter(Path('/home/dave/Python/WrapLibraries/WrapAV/data/test_long_fixed.mp3'))

    # Split the audio and receive the detailed split info
    chunks, split_info = splitter.split_audio()

    # Access split details
    print(f"Split Info: {split_info}")

    # Combine the chunks back into a file
    splitter.combine_audio(chunks, Path('/home/dave/Python/WrapLibraries/WrapAV/data/test_long_combined.mp3'))
