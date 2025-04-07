# av_converter_audio.py

import subprocess
from pathlib import Path
from pydub import AudioSegment
from pydub.exceptions import CouldntEncodeError
import logging

# Logger Configuration
logger = logging.getLogger(__name__)

DEFAULT_BIT_RATE = "192k"


class AudioConverter:
    """
    A class to convert audio files from one format to another using pydub and ffmpeg, with optional bitrate management.

    Attributes:
    -----------
    audio : AudioSegment
        The audio segment object for manipulation.
    source_path : Path
        The path to the source audio file.
    original_bit_rate : str
        The original bitrate of the audio file.

    Methods:
    --------
    export(target_path: str, use_original_bit_rate: bool = True, custom_bit_rate: str = None) -> None:
        Export the audio file to the desired format, with the option to specify bitrate.
    """

    SUPPORTED_AUDIO_FORMATS = ['mp3', 'wav', 'wma', 'ogg', 'flv', 'm4a']
    SUPPORTED_VIDEO_FORMATS = ['mp4', 'mkv', 'avi', 'mov', 'flv']

    def __init__(self, source_path: str):
        """
        Initializes the MediaConverter with the source file.

        Parameters:
        -----------
        source_path : str
            The path to the source audio or video file.

        Raises:
        -------
        ValueError:
            If the source file format is not supported.
        """
        self.source_path = Path(source_path)
        self.is_video = False
        self.detected_format = self._detect_media_format()  # Detect the actual format or codec
        self.original_bit_rate = self._detect_bit_rate()  # Detect the original bitrate
        # self.audio = self._load_media()

        if not self.is_video:
            self.audio = self._load_media()  # Load the audio for audio formats only
        else:
            self.audio = None  # Skip loading for video formats

    def _detect_media_format(self):
        """
        Uses ffprobe to detect the actual audio codec or media format of the file.
        """
        # Extract the file extension to check if it is a video format
        if self.source_path.suffix[1:].lower() in self.SUPPORTED_VIDEO_FORMATS:
            self.is_video = True
            print(f"{self.source_path} is identified as a video file.")
            return 'video'

        # Extract audio stream codec if video, or detect audio format directly
        command = f'ffprobe -v error -select_streams a:0 -show_entries stream=codec_name -of default=noprint_wrappers=1:nokey=1 "{self.source_path}"'
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True, text=True)

        detected_format = result.stdout.strip()

        if not detected_format:
            raise ValueError(f"Failed to detect audio codec for {self.source_path}")

        # Handle pcm_s16le (common for wav) and treat it as wav
        if detected_format == 'pcm_s16le':
            print(f"Detected WAV format: {detected_format}")
            return 'wav'

        # AAC and other audio formats within video containers should still be handled by ffmpeg
        if detected_format in self.SUPPORTED_AUDIO_FORMATS + ['aac', 'opus']:
            print(f"Detected audio codec: {detected_format}")
            return detected_format
        else:
            raise ValueError(f"Unsupported or unknown media format detected: {detected_format}")

    def _detect_bit_rate(self):
        """
        Uses ffprobe to detect the original bitrate of the audio file.
        """
        command = f'ffprobe -v error -show_entries format=bit_rate -of default=noprint_wrappers=1:nokey=1 "{self.source_path}"'
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True, text=True)

        bit_rate = result.stdout.strip()
        if bit_rate.isdigit():
            bit_rate_kbps = int(bit_rate) // 1000  # Convert to kbps
            print(f"Original Bitrate: {bit_rate_kbps} kbps")
            return f"{bit_rate_kbps}k"
        else:
            print(f"Could not detect bitrate, using default: {DEFAULT_BIT_RATE}")
            return DEFAULT_BIT_RATE

    def _load_media(self):
        """
        Loads the media file based on its detected format. If it's a video file, it extracts the audio stream.
        """
        if self.is_video:
            raise ValueError("For video formats, use the direct ffmpeg conversion method.")
        else:
            return AudioSegment.from_file(self.source_path, format=self.detected_format)

    def export(self, target_path: str, use_original_bit_rate: bool = True, custom_bit_rate: str = None) -> None:
        """
        Exports the audio to the desired format using either pydub or direct ffmpeg if necessary.

        Parameters:
        -----------
        target_path : str
            The path (including filename and extension) where the converted file should be saved.
        use_original_bit_rate : bool, optional
            Whether to use the original bit_rate (default: True).
        custom_bit_rate : str, optional
            A custom bit_rate for the output file, overriding both the default and original bit_rate.
        """

        target = Path(target_path)
        target_format = target.suffix[1:].lower()  # Get extension without the dot

        if target_format not in self.SUPPORTED_AUDIO_FORMATS:
            raise ValueError(f"Unsupported target format: {target_format}")

        # Determine which bitrate to use
        bit_rate = custom_bit_rate if custom_bit_rate else (
            self.original_bit_rate if use_original_bit_rate else DEFAULT_BIT_RATE)

        if self.is_video or self.detected_format in ['aac', 'mov', 'mp4', 'm4a']:
            # Use direct ffmpeg for video or specific audio formats
            self._ffmpeg_audio_extract(target_path, target_format, bit_rate)
        else:
            # Use pydub for supported audio formats
            try:
                self.audio = self._load_media()  # Load if not already loaded
                self.audio.export(target_path, format=target_format, bitrate=bit_rate)
                print(f"File successfully exported to {target_path}")
            except CouldntEncodeError as e:
                raise CouldntEncodeError(f"Failed to encode the file to {target_format}: {e}")

    def _ffmpeg_audio_extract(self, target_path: str, target_format: str, bit_rate: str):
        """
        Use ffmpeg directly to extract and convert audio for video files or complex audio formats like AAC.
        """
        print(f"Using ffmpeg for conversion from {self.detected_format} to {target_format} at {bit_rate}...")
        command = [
            'ffmpeg', '-i', str(self.source_path),
            '-codec:a', 'libmp3lame' if target_format == 'mp3' else target_format,
            '-b:a', bit_rate,
            str(target_path)
        ]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if result.returncode != 0:
            raise CouldntEncodeError(f"ffmpeg conversion failed: {result.stderr.decode('utf-8')}")

        print(f"ffmpeg successfully converted the file to {target_format} at {bit_rate}.")




def main():
    if __name__ == "__main__":
        try:
            # r'S:\databases\CRLibrary\General\90\mp4.mp4'
            # r'C:\Users\davek\OneDrive\Documents\import\JI_vm_15.mp3'
            converter = AudioConverter(r'C:\Users\davek\OneDrive\Documents\import\test_long.mp3')
            converter.export(r'C:\Users\davek\OneDrive\Documents\import\test_long.wav')
            # converter = AudioConverter(r'C:\Users\davek\OneDrive\Documents\import\test_short.mp3')
            # converter.export(r'C:\Users\davek\OneDrive\Documents\import\test_short_fixed2.mp3')

        except ValueError as error:
            print(f"Error: {error}")


# Example usage:
if __name__ == "__main__":
    main()
