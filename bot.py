import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from dotenv import load_dotenv
from analyzer import AttendanceAnalyzer
from calculator import calculate_requirements

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# Initialize Analyzer (global to avoid reloading model)
# Note: EasyOCR loads model into memory
try:
    analyzer = AttendanceAnalyzer()
except Exception as e:
    logger.error(f"Failed to initialize AttendanceAnalyzer: {e}")
    analyzer = None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="👋 Hi! Send me a screenshot of your attendance portal, and I'll tell you how many classes you need to attend to reach 75%."
    )

async def check_attendance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not analyzer:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="⚠️ Service temporarily unavailable (OCR module failed to load)."
        )
        return

    user = update.effective_user
    logger.info(f"Received photo from {user.first_name} (ID: {user.id})")
    
    status_msg = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Processing image... 🔍"
    )

    try:
        # Get the photo file
        photo_file = await update.message.photo[-1].get_file()
        file_path = f"temp_{user.id}.jpg"
        await photo_file.download_to_drive(file_path)
        
        # Analyze
        structured_data = analyzer.analyze_image(file_path)
        
        # Clean up
        if os.path.exists(file_path):
            os.remove(file_path)
            
        if not structured_data:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=status_msg.message_id,
                text="❌ Could not detect any attendance data. Please ensure the image is clear and contains course names and numbers."
            )
            return

        # Calculate and Format Response
        response_lines = ["📊 **Attendance Analysis**\n"]
        
        # Header
        response_lines.append(f"`{'Subject':<20} | {'%':<5} | {'Status'}`")
        response_lines.append("-" * 35)

        for item in structured_data:
            stats = calculate_requirements(item['attended'], item['total'])
            
            # Shorten course name if too long for cleaner display
            course_short = item['course']
            if len(course_short) > 20:
                course_short = course_short[:17] + "..."
            
            status_icon = "✅" if stats['status'] == 'Safe' else "⚠️"
            status_text = "Safe" if stats['status'] == 'Safe' else f"+{stats['hours_needed']}h"

            # Using code block for alignment
            line = f"`{course_short:<20} | {stats['current_percent']:<5} | {status_icon} {status_text}`"
            response_lines.append(line)
        
        response_lines.append("\n_Note: +Xh means you need to attend X more hours._")
            
        response_text = "\n".join(response_lines)
        
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=status_msg.message_id,
            text=response_text,
            parse_mode='Markdown'
        )

    except Exception as e:
        logger.error(f"Error processing image: {e}")
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=status_msg.message_id,
            text="❌ An error occurred while processing the image."
        )

async def easter_egg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower().strip()
    if "who is your father" in text:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Nishant Awasthi"
        )

if __name__ == '__main__':
    TOKEN = os.getenv('TELEGRAM_TOKEN')
    
    if not TOKEN:
        print("Error: TELEGRAM_TOKEN not found in environment variables.")
        print("Please create a .env file with TELEGRAM_TOKEN=your_token_here")
    else:
        application = ApplicationBuilder().token(TOKEN).build()
        
        start_handler = CommandHandler('start', start)
        image_handler = MessageHandler(filters.PHOTO, check_attendance)
        text_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), easter_egg)
        
        application.add_handler(start_handler)
        application.add_handler(image_handler)
        application.add_handler(text_handler)
        
        print("Bot is running...")
        application.run_polling()
