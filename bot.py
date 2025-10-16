from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from PIL import Image
import pytesseract
import io
import re
import os

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Download the image user sent
    photo_file = await update.message.photo[-1].get_file()
    image_data = await photo_file.download_as_bytearray()
    
    # Convert image to text using OCR
    img = Image.open(io.BytesIO(image_data))
    extracted_text = pytesseract.image_to_string(img)
    
    # Parse the extracted text to get course data
    courses = parse_attendance_data(extracted_text)
    
    # Calculate classes needed for each course
    result_table = calculate_classes_needed(courses)
    
    # Send formatted result to user
    await update.message.reply_text(result_table, parse_mode="HTML")

def parse_attendance_data(text):
    """Extract Code, TH, PH from OCR text"""
    courses = []
    lines = text.split('\n')
    
    for line in lines:
        # Look for patterns like "21CSC301T  47  34  13"
        match = re.search(r'(\d+[A-Z]+\d+[A-Z]?)\s+(\d+)\s+(\d+)\s+(\d+)', line)
        if match:
            code = match.group(1)
            th = int(match.group(2))      # Total Hours
            ph = int(match.group(3))      # Present Hours
            courses.append({'code': code, 'th': th, 'ph': ph})
    
    return courses

def calculate_classes_needed(courses):
    """Apply formula: X = 3*TH - 4*PH"""
    result = "<b>📚 Classes Needed to Reach 75%</b>\n\n"
    result += "<code>Code          | Classes\n"
    result += "────────────────────────\n"
    
    for course in courses:
        code = course['code']
        th = course['th']
        ph = course['ph']
        
        # Formula: X = 3*TH - 4*PH
        x = (3 * th) - (4 * ph)
        
        result += f"{code:13} | {x:+d}\n"
    
    result += "</code>"
    return result

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.run_polling()

if __name__ == '__main__':
    main()
