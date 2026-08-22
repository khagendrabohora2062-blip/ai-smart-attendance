import os
import qrcode


# ==========================================
# Generate Student QR Code
# ==========================================
def generate_qr(student_code):
    """
    Generate QR code image for a student.
    QR data will store exact student_id format.
    """

    output_folder = "static/qr_codes"

    os.makedirs(
        output_folder,
        exist_ok=True
    )


    # --------------------------------------
    # Keep Student ID format
    # Example:
    # 1  -> 01
    # 9  -> 09
    # 17 -> 17
    # --------------------------------------

    student_code = str(student_code).strip()

    if student_code.isdigit():

        student_code = student_code.zfill(2)


    qr_path = os.path.join(
        output_folder,
        f"{student_code}.png"
    )


    qr = qrcode.QRCode(

        version=1,

        error_correction=qrcode.constants.ERROR_CORRECT_H,

        box_size=10,

        border=4
    )


    # Store student_id inside QR

    qr.add_data(student_code)

    qr.make(
        fit=True
    )


    img = qr.make_image(

        fill_color="black",

        back_color="white"

    )


    img.save(
        qr_path
    )


    return qr_path



# ==========================================
# Test QR Generator
# ==========================================

if __name__ == "__main__":


    student_code = input(
        "Enter Student ID (Example: 01, 02, 09, 17): "
    ).strip()


    path = generate_qr(
        student_code
    )


    print("\nQR Generated Successfully!")

    print(
        "Saved Path:",
        path
    )