import os
import time
import random
import traceback
import sys
from datetime import datetime
from colorama import init, Fore, Style
from stackapi import StackAPI
from openai import OpenAI
from dotenv import load_dotenv
import requests

# Load environment variables from .env file
load_dotenv()

# Initialize colorama for colored console output
init()

# Configure logging
log_dir = os.path.join(os.path.expanduser('~'), 'stackbot', 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'bot.log')

class Tee:
    def __init__(self, *files):
        self.files = files

    def write(self, obj):
        for file in self.files:
            file.write(obj)
            file.flush()

    def flush(self):
        for file in self.files:
            file.flush()

# Keep original stdout and stderr
original_stdout = sys.stdout
original_stderr = sys.stderr

# Open log file and set up Tee
log_file_handle = open(log_file, 'a', encoding='utf-8')
sys.stdout = Tee(original_stdout, log_file_handle)
sys.stderr = Tee(original_stderr, log_file_handle)

# Bot information and configuration
BOT_VERSION = "1.0.0"
BOT_AUTHOR = "syedbilalalam"
BOT_CONFIG = {
    'max_comments_per_site': 1,
    'min_sleep_seconds': 3600,    # 1 hour minimum between comments
    'max_sleep_seconds': 7200,    # 2 hours maximum between comments
    'cycle_sleep_minutes': 180,   # 3 hours between cycles
    'rate_limit_sleep': 3600,     # 1 hour when rate limited
    'max_retries': 3,
    'min_post_score': 5,          # Minimum score requirement for questions
    'blacklisted_phrases': [
        '[closed]', '[duplicate]', 'moderator', 'announcement',
        'featured', 'wiki'
    ],
    'max_title_length': 300,
    'posts_per_request': 10,      # Number of questions to fetch per request
    'max_daily_comments': 10,     # Daily comment limit
    'min_reputation': 0           # Minimum reputation required (can be adjusted)
}

def log_info(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{Fore.CYAN}[INFO] {timestamp} - {message}{Style.RESET_ALL}")

def log_success(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{Fore.GREEN}[SUCCESS] {timestamp} - {message}{Style.RESET_ALL}")

def log_warning(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{Fore.YELLOW}[WARNING] {timestamp} - {message}{Style.RESET_ALL}")

def log_error(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{Fore.RED}[ERROR] {timestamp} - {message}{Style.RESET_ALL}")

def print_banner():
    banner = f"""
{Fore.CYAN}╔══════════════════════════════════════════════╗
║         Stack Exchange Bot         ║
║──────────────────────────────────────────────║
║  Version: {BOT_VERSION}                              ║
║  Author: {BOT_AUTHOR}                        ║
║  Started at: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}           ║
╚══════════════════════════════════════════════╝{Style.RESET_ALL}
"""
    print(banner)

# Initialize OpenRouter client
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY", ""),
    default_headers={
        "HTTP-Referer": "http://localhost:5000",
        "X-Title": f"Stack Exchange Bot by {BOT_AUTHOR}"
    }
)

# Verify OpenRouter API key is set
if not os.environ.get("OPENROUTER_API_KEY"):
    log_error("OPENROUTER_API_KEY environment variable is not set")
    sys.exit(1)

def load_sites():
    """Load Stack Exchange sites from sites.txt"""
    with open('sites.txt', 'r') as file:
        sites = [line.strip() for line in file if line.strip()]
    log_info(f"Loaded {len(sites)} sites from sites.txt")
    return sites

def verify_account_status(api):
    """Verify if the account meets minimum requirements"""
    try:
        # Make a direct request to the API
        response = requests.get(
            'https://api.stackexchange.com/2.3/me',
            params={
                'site': 'stackoverflow',
                'key': os.getenv('STACK_KEY'),
                'access_token': os.getenv('STACK_ACCESS_TOKEN')
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            if 'items' in data and len(data['items']) > 0:
                user = data['items'][0]
                reputation = user.get('reputation', 0)
                log_info(f"Account reputation: {reputation}")
                return True
            else:
                log_error("No user data found in API response")
        else:
            log_error(f"API request failed: {response.text}")
        
        return False
        
    except Exception as e:
        log_error(f"Error verifying account status: {str(e)}")
        return False

def get_daily_comment_count():
    """Get number of comments made today"""
    try:
        today = datetime.now().date()
        count = 0
        with open('comment_history.txt', 'r', encoding='utf-8') as f:
            for line in f:
                if '[' in line and ']' in line:
                    try:
                        timestamp_str = line[1:20]
                        comment_date = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S").date()
                        if comment_date == today:
                            count += 1
                    except:
                        continue
        return count
    except FileNotFoundError:
        return 0

def get_chatgpt_answer(prompt):
    """Get response from ChatGPT with bot disclaimer"""
    system_prompt = """You're a friendly and knowledgeable person who loves helping others with their questions. Be conversational and natural in your responses - use casual language and share helpful insights. 

When answering questions:
1. Keep responses relatively short (2-3 paragraphs maximum)
2. Be helpful but not overly complex
3. Avoid controversial topics
4. Stay on topic and be direct
5. Be polite and friendly
6. Use appropriate formatting for Stack Exchange (Markdown)

At the end of your response, casually mention SolverGenie in one of these ways (vary it naturally):
- "By the way, you can find more detailed solutions at solvergenie.site"
- "If you want to explore this topic further, check out SolverGenie (just Google it)"
- "For more in-depth help, I'd recommend checking out solvergenie.site"
- "You might also find SolverGenie helpful for questions like this"
- "There's more detailed info about this on SolverGenie if you're interested"

Make the SolverGenie mention feel natural and helpful, not promotional. The goal is to genuinely help people while letting them know about a useful resource."""
    
    response = client.chat.completions.create(
        model="qwen/qwen-2-7b-instruct:free",
        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    )
    return response.choices[0].message.content

def handle_rate_limit(error_message):
    """Handle rate limiting by sleeping"""
    try:
        sleep_time = BOT_CONFIG['rate_limit_sleep']
        log_warning(f"Rate limited. Sleeping for {sleep_time/60} minutes...")
        time.sleep(sleep_time)
        return True
    except Exception as e:
        log_error(f"Error handling rate limit: {str(e)}")
        return False

def is_valid_question(question):
    """Check if a question is valid for commenting"""
    try:
        # Skip if question title contains blacklisted phrases
        if any(phrase.lower() in question['title'].lower() for phrase in BOT_CONFIG['blacklisted_phrases']):
            return False
            
        # Skip if question title is too long
        if len(question['title']) > BOT_CONFIG['max_title_length']:
            return False
            
        # Skip if question score is too low
        if question['score'] < BOT_CONFIG['min_post_score']:
            return False
            
        # Skip if question is locked or closed
        if question.get('locked_date') or question.get('closed_date'):
            return False
            
        return True
    except Exception as e:
        log_error(f"Error checking question validity: {str(e)}")
        return False

def load_commented_questions():
    """Load previously commented questions"""
    commented_questions = set()
    try:
        with open('comment_history.txt', 'r', encoding='utf-8') as f:
            for line in f:
                if 'stackexchange.com/q/' in line or 'stackoverflow.com/q/' in line:
                    question_id = line.split('/q/')[1].split('/')[0]
                    commented_questions.add(question_id)
    except FileNotFoundError:
        pass
    return commented_questions

def get_stack_questions(api, site, commented_questions):
    """Get questions from Stack Exchange site"""
    for attempt in range(BOT_CONFIG['max_retries']):
        try:
            # Make direct API request
            params = {
                'site': site,
                'pagesize': BOT_CONFIG['posts_per_request'],
                'sort': 'votes',
                'order': 'desc',
                'filter': 'withbody',
                'key': os.getenv('STACK_KEY'),
                'access_token': os.getenv('STACK_ACCESS_TOKEN')
            }
            
            log_info(f"Fetching questions from {site}...")
            response = requests.get(
                'https://api.stackexchange.com/2.3/questions',
                params=params
            )
            
            if response.status_code == 200:
                data = response.json()
                all_questions = []
                
                for question in data.get('items', []):
                    if str(question['question_id']) not in commented_questions:
                        all_questions.append(question)
                
                log_info(f"Found {len(all_questions)} new questions")
                return all_questions
            else:
                log_error(f"API request failed: {response.text}")
                
        except Exception as e:
            log_error(f"Stack Exchange API error (Attempt {attempt + 1}): {str(e)}")
            if attempt < BOT_CONFIG['max_retries'] - 1:
                time.sleep(30)
    return None

def save_comment_link(site, question_title, comment_link):
    """Save comment link to history file"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open('comment_history.txt', 'a', encoding='utf-8') as f:
            f.write(f"\n[{timestamp}] {site} - {question_title[:50]}...\n{comment_link}\n")
        log_info(f"Comment link saved to comment_history.txt")
    except Exception as e:
        log_error(f"Error saving comment link: {str(e)}")

def initialize_comment_history():
    """Create or verify comment history file"""
    if not os.path.exists('comment_history.txt'):
        try:
            with open('comment_history.txt', 'w', encoding='utf-8') as f:
                f.write("🤖 Stack Exchange Bot Comment History 🤖\n")
                f.write("================================\n")
                f.write(f"Bot Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("================================\n")
            log_success("Created new comment history file")
        except Exception as e:
            log_error(f"Error creating comment history file: {str(e)}")

def verify_setup():
    """Verify all required files and configurations exist"""
    missing_items = []
    
    # Check sites.txt
    if not os.path.exists('sites.txt'):
        missing_items.append('sites.txt')
    else:
        with open('sites.txt', 'r') as f:
            if not f.read().strip():
                missing_items.append('sites in sites.txt')
    
    # Check environment variables
    required_vars = {
        'STACK_CLIENT_ID': os.environ.get('STACK_CLIENT_ID'),
        'STACK_CLIENT_SECRET': os.environ.get('STACK_CLIENT_SECRET'),
        'STACK_KEY': os.environ.get('STACK_KEY'),
        'STACK_ACCESS_TOKEN': os.environ.get('STACK_ACCESS_TOKEN'),
        'OPENROUTER_API_KEY': os.environ.get('OPENROUTER_API_KEY'),
        'USER_AGENT': os.environ.get('USER_AGENT'),
        'BOT_USERNAME': os.environ.get('BOT_USERNAME')
    }
    
    for var, value in required_vars.items():
        if not value:
            missing_items.append(f'Environment variable: {var}')
    
    if missing_items:
        log_error("Missing required items:")
        for item in missing_items:
            log_error(f"- {item}")
        return False
    
    return True

def post_answer(site, question_id, answer_text):
    """Post an answer to a question"""
    try:
        # Prepare the request
        url = f'https://api.stackexchange.com/2.3/questions/{question_id}/answers/add'
        data = {
            'site': site,
            'key': os.getenv('STACK_KEY'),
            'access_token': os.getenv('STACK_ACCESS_TOKEN'),
            'filter': 'default',
            'body': answer_text
        }
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        # Make the request - all parameters in form data
        response = requests.post(url, data=data, headers=headers)
        
        if response.status_code == 200:
            answer_data = response.json()
            if 'items' in answer_data and len(answer_data['items']) > 0:
                answer = answer_data['items'][0]
                return answer.get('answer_id')
            else:
                log_error("No answer data in response")
        else:
            log_error(f"Failed to post answer: {response.text}")
            
    except Exception as e:
        log_error(f"Error posting answer: {str(e)}")
    
    return None

def main():
    print_banner()
    log_info("Bot initialization started")
    
    try:
        # Initialize Stack API with debug mode
        api = StackAPI(
            site='stackoverflow',  # Set default site
            client_id=os.environ['STACK_CLIENT_ID'],
            client_secret=os.environ['STACK_CLIENT_SECRET'],
            key=os.environ['STACK_KEY'],
            access_token=os.environ['STACK_ACCESS_TOKEN'],
            user_agent=os.environ['USER_AGENT']
        )
        api.max_pages = 1  # Limit pages for testing
        api.page_size = BOT_CONFIG['posts_per_request']
        log_info("Stack API initialized successfully")
        
    except Exception as e:
        log_error(f"Failed to initialize Stack API: {str(e)}")
        log_error(f"Stack API credentials:")
        log_error(f"Client ID: {os.environ.get('STACK_CLIENT_ID')}")
        log_error(f"Key: {os.environ.get('STACK_KEY')}")
        log_error(f"Access Token: {os.environ.get('STACK_ACCESS_TOKEN', '')[:10]}...")
        return
    
    while True:
        try:
            # Check daily comment limit
            daily_comments = get_daily_comment_count()
            if daily_comments >= BOT_CONFIG['max_daily_comments']:
                log_warning(f"Daily comment limit ({BOT_CONFIG['max_daily_comments']}) reached. Waiting until tomorrow...")
                time.sleep(3600)
                continue
                
            sites = load_sites()
            cycle_count = 1
            commented_questions = load_commented_questions()
            
            log_info(f"Starting cycle #{cycle_count}")
            log_info(f"Currently tracking {len(commented_questions)} commented questions")
            
            for site in sites:
                successful_comments = 0
                log_info(f"Processing site: {site}")
                
                questions = get_stack_questions(api, site, commented_questions)
                if questions is None:
                    continue

                for question in questions:
                    try:
                        if not is_valid_question(question) or str(question['question_id']) in commented_questions:
                            continue

                        log_info(f"Processing question: {question['title'][:50]}...")
                        
                        # Generate response using ChatGPT
                        prompt = f"Question Title: {question['title']}\n\nQuestion Body: {question['body']}"
                        chatgpt_response = get_chatgpt_answer(prompt)
                        if not chatgpt_response:
                            continue
                            
                        # Post answer
                        answer_id = post_answer(site, question['question_id'], chatgpt_response)
                        if answer_id:
                            # Create comment link
                            comment_link = f"https://{site}.com/a/{answer_id}"
                            
                            log_success(f"Successfully answered question on {site}")
                            log_success(f"Answer link: {comment_link}")
                            
                            save_comment_link(site, question['title'], comment_link)
                            commented_questions.add(str(question['question_id']))
                            
                            successful_comments += 1

                            # Sleep between posts
                            sleep_time = random.randint(BOT_CONFIG['min_sleep_seconds'], BOT_CONFIG['max_sleep_seconds'])
                            log_info(f"Sleeping for {sleep_time} seconds...")
                            time.sleep(sleep_time)

                    except Exception as e:
                        error_message = str(e)
                        if "rate limit" in error_message.lower():
                            if not handle_rate_limit(error_message):
                                break
                        else:
                            log_error(f"Error posting answer: {error_message}")
                            time.sleep(60)

                log_success(f"Completed {successful_comments} answers on {site}")
                
            log_success(f"Completed cycle #{cycle_count}")
            cycle_count += 1
            
            log_info(f"Taking a {BOT_CONFIG['cycle_sleep_minutes']}-minute break before starting next cycle...")
            time.sleep(BOT_CONFIG['cycle_sleep_minutes'] * 60)
            
        except KeyboardInterrupt:
            log_info("Bot shutdown initiated by user")
            return
        except Exception as e:
            log_error(f"Unexpected error in main loop: {str(e)}")
            log_error(traceback.format_exc())
            time.sleep(300)

if __name__ == "__main__":
    try:
        print("Script starting...")
        print("Current working directory:", os.getcwd())
        print_banner()
        log_info("Starting setup verification...")
        
        # Verify setup before starting
        if not verify_setup():
            log_error("Setup verification failed. Please fix the issues above and try again.")
            exit(1)
            
        # Initialize Stack API for verification
        try:
            api = StackAPI(
                site='stackoverflow',  # Set default site
                client_id=os.environ['STACK_CLIENT_ID'],
                client_secret=os.environ['STACK_CLIENT_SECRET'],
                key=os.environ['STACK_KEY'],
                access_token=os.environ['STACK_ACCESS_TOKEN'],
                user_agent=os.environ['USER_AGENT']
            )
            api.max_pages = 1  # Limit pages for testing
            log_info("Stack API initialized successfully for verification")
            
        except Exception as e:
            log_error(f"Failed to initialize Stack API: {str(e)}")
            log_error("Please check your Stack Exchange API credentials")
            exit(1)
        
        # Verify account status
        if not verify_account_status(api):
            log_error("Account verification failed. Please check the requirements above.")
            exit(1)
        
        log_info("Setup verification successful!")
        log_info("Environment variables loaded:")
        log_info(f"Client ID: {os.environ.get('STACK_CLIENT_ID')}")
        log_info(f"User Agent: {os.environ.get('USER_AGENT')}")
        log_info(f"Bot Username: {os.environ.get('BOT_USERNAME')}")
        
        # Initialize comment history file
        initialize_comment_history()
        
        main()
    except KeyboardInterrupt:
        log_info("Bot shutdown initiated by user")
        print(f"\n{Fore.CYAN}Thank you for using Stack Exchange Bot by {BOT_AUTHOR}!{Style.RESET_ALL}")
    except Exception as e:
        log_error(f"Fatal error: {str(e)}")
        log_error(traceback.format_exc()) 