import logging
import logging.handlers
import os
import json
import requests
import smtplib
from bs4 import BeautifulSoup
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger_file_handler = logging.handlers.RotatingFileHandler(
    "status.log",
    maxBytes=1024 * 1024,
    backupCount=1,
    encoding="utf8",
)
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger_file_handler.setFormatter(formatter)
logger.addHandler(logger_file_handler)

# Email configuration
EMAIL_ADDRESS = f"{os.getenv('EMAIL_ADDRESS_USER')}@{os.getenv('EMAIL_ADDRESS_DOMAIN')}"
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD")
EMAIL_RECEIVER = EMAIL_ADDRESS  # Sending the email to yourself


def fetch_web_content():
    url = 'https://www.bindeleddet.no/jobs'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.text
    else:
        logger.error(
            f"Failed to retrieve the page. Status code: {response.status_code}")
        return None


def parse_with_gpt(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    job_listings = soup.find_all('div', class_='c-content-panel')

    job_data = []
    for job in job_listings:
        company = job.find('h5', class_='job_cname').text.strip()
        title = job.find('h3', class_='job_title').text.strip()
        deadline = job.find('h5', class_='job_deadline').text.strip()

        job_data.append({
            'company': company,
            'title': title,
            'deadline': deadline
        })

    return job_data


def check_for_updates():
    html_content = fetch_web_content()

    if (html_content):
        new_jobs = parse_with_gpt(html_content)

        old_jobs = []
        try:
            with open('old_jobs.json', 'r') as file:
                if os.stat('old_jobs.json').st_size > 0:
                    old_jobs = json.load(file)
        except FileNotFoundError:
            pass  # old_jobs will remain an empty list

        new_listings = [job for job in new_jobs if job not in old_jobs]

        if new_listings:
            send_email(new_listings)
            old_jobs.extend(new_listings)
            with open('old_jobs.json', 'w') as file:
                json.dump(old_jobs, file, indent=4)
        else:
            logger.info("No new job listings found.")


def send_email(jobs):
    msg = MIMEMultipart()
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = EMAIL_RECEIVER
    msg['Subject'] = 'New Job Listings'

    html = """\
    <html>
      <body>
        <h2>New Job Listings</h2>
        <ul>
    """
    for job in jobs:
        html += f"<li><strong>{job['title']}</strong> at {job['company']} - Deadline: {job['deadline']}</li>"

    html += """\
        </ul>
      </body>
    </html>
    """
    msg.attach(MIMEText(html, 'html'))

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_APP_PASSWORD)
            server.send_message(msg)
            logger.info("Email sent successfully.")
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"Failed to send email: {e}")
        logger.error("Check your email address and app password.")
    except Exception as e:
        logger.error(f"An error occurred: {e}")


if __name__ == "__main__":
    check_for_updates()
