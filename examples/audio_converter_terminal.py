# audio_converter_terminal.py

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

from WrapAV import AudioConverter

def main():
    print("=== Audio Converter ===")
    try:
        # Prompt the user for input and output file paths
        input_file = input("Enter the path of the audio file to convert: ").strip()
        output_format = input("Enter the desired output format (e.g., wav, mp3, m4a): ").strip()

        # Validate inputs
        if not input_file:
            raise ValueError("Input file path cannot be empty.")
        if not output_format:
            raise ValueError("Output format cannot be empty.")

        # Generate output file path by replacing the original file extension
        output_file = input_file.rsplit('.', 1)[0] + f".{output_format}"

        # Perform the conversion
        converter = AudioConverter(input_file)
        converter.export(output_file)

        print(f"Conversion successful! File saved as: {output_file}")

    except ValueError as error:
        print(f"Error: {error}")
    except FileNotFoundError:
        print("Error: Input file not found.")
    except Exception as error:
        print(f"Unexpected error: {error}")


# Run the program
if __name__ == "__main__":
    main()
