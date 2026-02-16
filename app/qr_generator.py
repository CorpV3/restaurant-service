"""
QR Code generation utility
"""
import qrcode
from qrcode.image.pil import PilImage
from io import BytesIO
import base64
from typing import Tuple
from shared.config.settings import settings
import uuid


def generate_qr_code(table_id: uuid.UUID, restaurant_id: uuid.UUID, table_number: str) -> Tuple[str, str, str]:
    """
    Generate QR code for a table

    Args:
        table_id: UUID of the table
        restaurant_id: UUID of the restaurant
        table_number: Table number for display

    Returns:
        Tuple of (qr_code_image_data_url, qr_url, qr_token)
        - qr_code_image_data_url: Base64 image data for display
        - qr_url: The actual URL that the QR code points to
        - qr_token: Unique security token
    """
    # Create unique token for the table
    qr_token = f"{restaurant_id}:{table_id}:{uuid.uuid4()}"

    # Create QR code URL that customers will scan
    # Format: /menu/{restaurantId}/{tableId}
    qr_url = f"{settings.qr_code_base_url}/{restaurant_id}/{table_id}"

    # Determine error correction level
    error_correction_map = {
        "L": qrcode.constants.ERROR_CORRECT_L,
        "M": qrcode.constants.ERROR_CORRECT_M,
        "Q": qrcode.constants.ERROR_CORRECT_Q,
        "H": qrcode.constants.ERROR_CORRECT_H,
    }
    error_correction = error_correction_map.get(
        settings.qr_code_error_correction,
        qrcode.constants.ERROR_CORRECT_M
    )

    # Create QR code
    qr = qrcode.QRCode(
        version=1,  # Auto-adjust size
        error_correction=error_correction,
        box_size=10,
        border=4,
    )

    qr.add_data(qr_url)
    qr.make(fit=True)

    # Create image
    img = qr.make_image(fill_color="black", back_color="white")

    # Convert to base64 for storage/display
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()

    # Create data URL for the image
    qr_code_image_data_url = f"data:image/png;base64,{img_str}"

    return qr_code_image_data_url, qr_url, qr_token


def regenerate_qr_code(table_id: uuid.UUID, restaurant_id: uuid.UUID, table_number: str) -> Tuple[str, str, str]:
    """
    Regenerate QR code for a table (same as generate but for clarity)

    Args:
        table_id: UUID of the table
        restaurant_id: UUID of the restaurant
        table_number: Table number for display

    Returns:
        Tuple of (qr_code_image_data_url, qr_url, qr_token)
    """
    return generate_qr_code(table_id, restaurant_id, table_number)


def generate_qr_code_file(table_id: uuid.UUID, restaurant_id: uuid.UUID, table_number: str, file_path: str) -> str:
    """
    Generate QR code and save to file

    Args:
        table_id: UUID of the table
        restaurant_id: UUID of the restaurant
        table_number: Table number for display
        file_path: Path to save the QR code image

    Returns:
        Unique token for the QR code
    """
    # Create unique token
    qr_token = f"{restaurant_id}:{table_id}:{uuid.uuid4()}"

    # Create QR code URL
    qr_url = f"{settings.qr_code_base_url}/{table_id}?restaurant={restaurant_id}&token={qr_token}"

    # Create QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )

    qr.add_data(qr_url)
    qr.make(fit=True)

    # Create and save image
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(file_path)

    return qr_token
