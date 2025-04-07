# av_info.py

from dataclasses import dataclass
import subprocess
import re
from pathlib import Path
import sys
import logging

# Logger Configuration
logger = logging.getLogger(__name__)

AUDIO_CODEC_FORMATS = {
    'mp3': 'mp3',
    'pcm_s16le': 'wav',
    'wmav2': 'wma',
    'vorbis': 'ogg',
    'aac': 'm4a',
    'opus': 'ogg',
    'flv': 'flv',
}

VIDEO_CODEC_FORMATS = {
    'h264': 'mp4',
    'vp9': 'mkv',
    'mpeg4': 'avi',
    'flv1': 'flv',
}

IMAGE_CODEC_FORMATS = {
    'jpeg': 'jpg',
    'jpg': 'jpg',
    'png': 'png',
    'webp': 'webp',
    'bmp': 'bmp',
    'ico': 'ico',
    'gif': 'gif',
    'tiff': 'tiff',
}

@dataclass
class MediaFileInfo:
    file_type: str
    codec_name: str
    duration_seconds: float
    bit_rate_kbps: int
    file_size_mb: float
    sample_rate: int = None
    channels: int = None
    resolution: str = None
    frame_rate: str = None
    interpreted_format: str = None
    media_type: str = None
    color_mode: str = None  # Added for images

    @staticmethod
    def from_file(file_path: Path) -> "MediaFileInfo":
        """
        Creates a MediaFileInfo object by analyzing the media file.

        Parameters:
        -----------
        file_path : Path
            The path to the media file.

        Returns:
        --------
        MediaFileInfo
            The media file information dataclass.
        """
        analyzer = MediaFileAnalyzer(file_path)
        return analyzer.get_all_info()


def get_ffmpeg_paths():
    exe_dir = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).parent
    ffmpeg_path = exe_dir / "ffmpeg"
    ffprobe_path = exe_dir / "ffprobe"

    if sys.platform == "win32":  # Add .exe extension for Windows
        ffmpeg_path = ffmpeg_path.with_suffix('.exe')
        ffprobe_path = ffprobe_path.with_suffix('.exe')

    return ffmpeg_path, ffprobe_path

class MediaFileAnalyzer:
    def __init__(self, file_path):
        self.file_path = Path(file_path)
        self.media_type = None
        self.data = self._get_file_info()

    # def _get_file_info(self):
    #     """Runs ffprobe to extract metadata."""
    #     command = f'ffprobe -v error -show_format -show_streams "{self.file_path}"'
    #     result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True, text=True)
    #     return result.stdout

    def _get_file_info(self):
        """Runs ffprobe to extract metadata."""
        _, ffprobe = get_ffmpeg_paths()
        # command = f'"{ffprobe}" -v error -show_format -show_streams "{self.file_path}"'
        command = f'"{ffprobe}" -v error -show_format -show_streams -select_streams v "{self.file_path}"'

        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True, text=True)
        return result.stdout

    def get_file_type(self):
        """Returns the file type based on the format."""
        match = re.search(r'format_name=([a-z,]+)', self.data)
        return match.group(1) if match else "Unknown"

    def get_codec_name(self):
        """Returns the codec name."""
        match = re.search(r'codec_name=([a-zA-Z0-9]+)', self.data)
        return match.group(1) if match else "Unknown"

    def get_duration_seconds(self):
        """Returns the duration of the media in seconds."""
        match = re.search(r'duration=([\d.]+)', self.data)
        return float(match.group(1)) if match else 0.0

    def get_bit_rate(self):
        """Returns the bit_rate in kbps."""
        match = re.search(r'bit_rate=(\d+)', self.data)
        return int(match.group(1)) // 1000 if match else 0

    def get_file_size(self):
        """Returns the file size in MB."""
        return self.file_path.stat().st_size / (1024 * 1024)

    def get_sample_rate(self):
        """Returns the sample rate of the audio."""
        match = re.search(r'sample_rate=(\d+)', self.data)
        return int(match.group(1)) if match else None

    def get_channels(self):
        """Returns the number of audio channels."""
        match = re.search(r'channels=(\d+)', self.data)
        return int(match.group(1)) if match else None

    def is_video(self):
        """Determines if the file contains a video stream."""
        return 'codec_type=video' in self.data

    # def get_resolution(self):
    #     """Returns the resolution for video files."""
    #     if self.is_video():
    #         width = re.search(r'width=(\d+)', self.data).group(1)
    #         height = re.search(r'height=(\d+)', self.data).group(1)
    #         return f'{width}x{height}'
    #     return None

    def get_resolutions(self):
        """Returns a list of resolutions for all video streams."""
        resolutions = []
        for match in re.finditer(r'width=(\d+)\s+height=(\d+)', self.data):
            width, height = match.groups()
            resolutions.append(f"{width}x{height}")
        return resolutions

    def get_color_mode(self):
        """Returns color mode if present (useful for image files)."""
        match = re.search(r'pix_fmt=([a-zA-Z0-9_]+)', self.data)
        return match.group(1) if match else "Unknown"

    def get_frame_rate(self):
        """Returns the frame rate for video files."""
        if self.is_video():
            return re.search(r'avg_frame_rate=([\d/]+)', self.data).group(1)
        return None

    def get_interpreted_format(self):
        """Maps the codec to a more human-readable format (like mp3, wav, mp4), using partial matching for common codecs."""
        codec_name = self.get_codec_name().lower()  # Make sure we're case-insensitive
        file_type = self.get_file_type().lower()

        # Handle common partial matches for audio
        if codec_name.startswith('pcm'):
            self.media_type = 'a'
            return 'wav'  # Match any pcm-based codec to wav
        elif codec_name.startswith('aac'):
            self.media_type = 'a'
            return 'm4a'  # AAC codecs map to m4a
        elif codec_name == 'flac':
            self.media_type = 'a'
            return 'flac'
        elif codec_name == 'opus':
            self.media_type = 'a'
            return 'ogg'

        # Handle common partial matches for video
        elif codec_name.startswith('h264') or codec_name.startswith('libx264'):
            self.media_type = 'v'
            return 'mp4'  # H.264 maps to mp4
        elif codec_name.startswith('vp9'):
            self.media_type = 'v'
            return 'mkv'
        elif codec_name.startswith('mpeg'):
            self.media_type = 'v'
            return 'mp4' if '4' in codec_name else 'avi'  # MPEG-4 maps to mp4, others to avi

        # Use exact match fallback for audio and video
        if codec_name in AUDIO_CODEC_FORMATS:
            self.media_type = 'a'
            return AUDIO_CODEC_FORMATS[codec_name]

        if codec_name in VIDEO_CODEC_FORMATS:
            self.media_type = 'v'
            return VIDEO_CODEC_FORMATS[codec_name]

        # Special cases
        if codec_name == "bmp" and file_type == "ico":
            self.media_type = 'i'
            return "ico"
        if codec_name == "mjpeg" and file_type == "jpeg":
            self.media_type = 'i'
            return "jpg"

        # Image format mappings
        if codec_name in IMAGE_CODEC_FORMATS:
            self.media_type = 'i'
            return IMAGE_CODEC_FORMATS[codec_name]


        # Default to unknown
        self.media_type = None
        return "Unknown"

    def get_all_info(self):
        """Returns all the media information in a MediaFileInfo dataclass."""
        # print(MediaFileInfo)
        resolutions = self.get_resolutions()
        return MediaFileInfo(
            file_type=self.get_file_type(),
            codec_name=self.get_codec_name(),
            duration_seconds=self.get_duration_seconds(),
            bit_rate_kbps=self.get_bit_rate(),
            file_size_mb=self.get_file_size(),
            sample_rate=self.get_sample_rate(),
            channels=self.get_channels(),
            # resolution=self.get_resolution(),
            resolution=", ".join(resolutions),
            frame_rate=self.get_frame_rate(),
            interpreted_format=self.get_interpreted_format(),
            media_type=self.media_type,
            color_mode=self.get_color_mode()
        )


def main():
    if __name__ == "__main__":
        try:
            # r'S:\databases\CRLibrary\General\90\mp4.mp4'
            # r'C:\Users\davek\OneDrive\Documents\import\JI_vm_15.mp3'
            # r'C:\Users\davek\OneDrive\Documents\import\test_long.mp3'
            # r'C:\Users\davek\OneDrive\Documents\import\test_short_fixed2.mp3'
            # r'C:\Users\davek\OneDrive\Documents\import\test_long.wav'
            # r'C:\Users\davek\OneDrive\Documents\import\test_short.mp3'
            # r'C:\Users\davek\Downloads\FOSS_sage.mp3'
            # r'C:\Users\davek\OneDrive\Documents\import\test_short.mp3'
            # r'C:\Users\davek\Downloads\crt.webp'
            # r'C:\Users\davek\Downloads\crt.ico'
            # r'C:\Users\davek\Downloads\clr.jpg'
            analyzer = MediaFileAnalyzer(r'C:\Users\davek\Downloads\clr.jpg')


            media_info = analyzer.get_all_info()
            print(media_info)
            print(f'Interpreted Format: {media_info.interpreted_format}')

        except ValueError as error:
            print(f"Error: {error}")


# Example usage:
if __name__ == "__main__":
    main()
