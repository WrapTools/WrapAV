# audio_transcriber_terminal.py

from pathlib import Path
import logging

logging.basicConfig(
    level=logging.INFO,
    format = '%(name)s - %(levelname)s - %(message)s (line: %(lineno)d)',
    handlers=[
        logging.StreamHandler(),  # Log to console
        # logging.FileHandler('app.log')  # Log to file
    ]
)

logger = logging.getLogger(__name__)

from WrapAV import AudioTranscriber
from WrapAV import MediaFileInfo


def main():
    print("=== Audio Transcriber ===")
    audio_file_path_str = input("Enter the path of the audio file to convert: ").strip()
    audio_file_path = Path(audio_file_path_str)

    try:
        # Output file type and codec info
        media_info = MediaFileInfo.from_file(audio_file_path)
        print(f"File: {audio_file_path.name}")
        print(f"Codec: {media_info.codec_name}")
        print(f"File Type: {audio_file_path.suffix.lower().lstrip('.')}")

        # Ensure you pass a Path object instead of a string
        transcriber = AudioTranscriber()
        transcribed_text = transcriber.transcribe_audio(audio_file_path, time_stamps=True)
        print(f"Transcribed data: {transcribed_text}")

        # Extract the transcribed text
        transcribed_text_str = transcribed_text.get('text', 'No transcription available.')

        print(f"Transcribed text: {transcribed_text_str}")

        # Save the transcribed text to a .txt file in the same directory as the input audio file
        output_file = audio_file_path.with_suffix(".txt")  # Replace audio extension with .txt
        with open(output_file, "w") as f:
            f.write(transcribed_text_str)

        print(f"Transcription saved to: {output_file}")

    except Exception as e:
        print(f"Error: {e}")


# Run the program
if __name__ == "__main__":
    main()