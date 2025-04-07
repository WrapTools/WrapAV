# av_converter_image.py

import subprocess
from pathlib import Path
import logging

# Logger Configuration
logger = logging.getLogger(__name__)

class ImageConverter:
    """
    A class to convert image files to platform-specific icon formats (ICO, PNG, ICNS) for Windows, Linux, and macOS.

    Attributes:
    -----------
    source_path : Path
        Path to the source image file.

    Methods:
    --------
    export(target_path: str, platform: str, size: int = None) -> None:
        Converts the image to the desired format based on the platform and size requirements.
    """

    SUPPORTED_IMAGE_FORMATS = ['png', 'jpg', 'jpeg', 'webp', 'ico']
    TARGET_SIZES = {
        'windows': [16, 32, 48, 64],  # Standard icon sizes for Windows
        'linux': [16, 24, 32, 48, 64],  # Common Linux icon sizes
        'mac': [16, 32, 48, 64, 128, 256, 512]  # ICNS sizes for macOS
    }

    def __init__(self, source_path: str):
        """
        Initializes the ImageConverter with the source file.

        Parameters:
        -----------
        source_path : str
            The path to the source image file.

        Raises:
        -------
        ValueError:
            If the source file format is not supported.
        """
        self.source_path = Path(source_path)
        self.detected_format = self._detect_image_format()

    def _detect_image_format(self):
        """
        Checks if the image format is supported.

        Returns:
        --------
        str : The image format.

        Raises:
        -------
        ValueError: If the format is not supported.
        """
        if self.source_path.suffix[1:].lower() not in self.SUPPORTED_IMAGE_FORMATS:
            raise ValueError(f"Unsupported image format: {self.source_path.suffix}")
        return self.source_path.suffix[1:].lower()

    def export(self, target_path: str, platform: str, size: int = None):
        """
        Exports the image to the desired icon format based on platform and size requirements.

        Parameters:
        -----------
        target_path : str
            The output file path.
        platform : str
            Target platform ('windows', 'linux', or 'mac').
        size : int, optional
            Target size for the icon. If None, all sizes for the platform will be generated.

        Raises:
        -------
        ValueError: If platform is unsupported or size is invalid.
        """
        if platform not in self.TARGET_SIZES:
            raise ValueError(f"Unsupported platform: {platform}")

        sizes = [size] if size else self.TARGET_SIZES[platform]
        for icon_size in sizes:
            self._convert_with_ffmpeg(target_path, platform, icon_size)

    def _convert_with_ffmpeg(self, target_path: str, platform: str, size: int):
        """
        Uses FFmpeg to convert the image to the desired format and size.

        Parameters:
        -----------
        target_path : str
            The output file path.
        platform : str
            Target platform ('windows', 'linux', 'mac').
        size : int
            Target size for the icon.
        """
        icon_dir = None
        if platform == 'mac':
            # macOS ICNS requires multiple sizes packed into a .iconset directory
            icon_dir = Path(target_path).with_suffix(".iconset")
            icon_dir.mkdir(exist_ok=True)
            output_file = icon_dir / f"icon_{size}x{size}.png"
            print(f"Creating macOS icon size {size}x{size}")
        else:
            # Windows and Linux icons go directly to target_path with correct extension
            ext = 'ico' if platform == 'windows' else 'png'
            output_file = Path(target_path).with_suffix(f".{ext}")
            print(f"Creating {platform} icon size {size}x{size}")

        subprocess.run([
            # 'ffmpeg', 'y', '-i', str(self.source_path),
            'ffmpeg', '-y', '-i', str(self.source_path),
            '-vf', f'scale={size}:{size}',
            # '-map', '0:0',
            str(output_file)
        ])

        if platform == 'mac':
            # Package all sizes into an ICNS file for macOS
            iconutil_command = ['iconutil', '-c', 'icns', '-o', target_path, icon_dir]
            subprocess.run(iconutil_command)
            print(f"Packaged macOS icons into {target_path}")


def main():
    try:
        input_file = r'C:\Users\davek\Downloads\crt.webp'
        output_file_windows = r'C:\Users\davek\Downloads\crt.ico'
        output_file_linux = r'C:\Users\davek\Downloads\crt.png'

        # Initialize ImageConverter
        converter = ImageConverter(input_file)

        # Convert for Windows
        print("Converting to Windows icon format (.ico)...")
        converter.export(output_file_windows, platform='windows', size=64)

        # Convert for Linux
        print("Converting to Linux icon format (.png)...")
        converter.export(output_file_linux, platform='linux', size=32)

    except ValueError as error:
        print(f"Error: {error}")


# Example usage:
if __name__ == "__main__":
    main()
