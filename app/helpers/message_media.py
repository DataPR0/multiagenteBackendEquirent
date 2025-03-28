import os
import magic
import requests
from app.models.message_media import MimeTypes

EXTENSION_TO_MIME = {
    '.jpg': MimeTypes.JPG.value,
    '.jpeg': MimeTypes.JPEG.value,
    '.png': MimeTypes.PNG.value,
    '.pdf': MimeTypes.PDF.value,
    '.doc': MimeTypes.WORD.value,
    '.docx': MimeTypes.WORD2003.value,
}

def detect_mime_type(url: str) -> list[str] | None:
    """
    Detects the MIME type of a file from its URL.

    Args:
    url (str): The URL of the file.

    Returns:
    list[str] | None: A list containing the file name, MIME type, and a placeholder value (-1) if the MIME type is detected from the file extension.
                     If the MIME type cannot be detected, returns None.
    """
    # Check the file extension in the URL
    name, ext = os.path.splitext(url)
    ext = ext.lower()  # Ensure lowercase for case-insensitive comparison
    name = name.rsplit('/')[-1]
    if ext in EXTENSION_TO_MIME:
        return [name, EXTENSION_TO_MIME[ext], -1]

    # If the extension is not recognized, use python-magic to detect the MIME type from the content
    try:
        # Make a request to fetch the content (head request to save bandwidth)
        response = requests.get(url, stream=True)
        if response.status_code != 200:
            raise Exception("Error: Unable to fetch file")
        
        # Read a portion of the file for MIME type detection
        file_content = response.raw.read(1000)  # Read the first 1000 bytes
        mime = magic.Magic(mime=True)
        mime_type = mime.from_buffer(file_content)
        if mime_type in EXTENSION_TO_MIME.values():
            return [name, mime_type, -1]
    except Exception as e:
        print(f"Error: {str(e)}")
    return None