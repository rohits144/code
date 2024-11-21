
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import feedparser
from typing import List, Dict
from dotenv import load_dotenv
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders


class NewsFetcher:
    """
    A class to fetch news articles from RSS feeds.
    """

    def __init__(self, rss_feeds: List[str]):
        """
        Initialize with a list of RSS feed URLs.
        """
        self.rss_feeds = rss_feeds

    def fetch_news(self) -> List[Dict[str, str]]:
        """
        Fetch news articles from all the RSS feeds.

        Returns:
            List[Dict[str, str]]: A list of dictionaries containing news details.
        """
        news_articles = []
        for feed in self.rss_feeds:
            try:
                parsed_feed = feedparser.parse(feed)
                for entry in parsed_feed.entries:
                    news_article = {
                        "title": entry.title,
                        "link": entry.link,
                        "summary": entry.summary if 'summary' in entry else "",
                        "published": entry.published if 'published' in entry else "",
                        "source": parsed_feed.feed.title if 'title' in parsed_feed.feed else "Unknown Source"
                    }
                    news_articles.append(news_article)
            except Exception as e:
                print(f"Error fetching feed {feed}: {e}")
        return news_articles


def draw_wrapped_text(canvas_obj, text, x, y, max_width, line_height):
    """
    Draw text with wrapping.

    Args:
        canvas_obj: The canvas object.
        text: The text to wrap.
        x: The starting x-coordinate.
        y: The starting y-coordinate.
        max_width: The maximum width for wrapping.
        line_height: The line height.
    Returns:
        The y-coordinate after drawing the wrapped text.
    """
    words = text.split()
    line = ""
    lines = []

    for word in words:
        if canvas_obj.stringWidth(line + word + " ", "Helvetica", 10) <= max_width:
            line += word + " "
        else:
            lines.append(line.strip())
            line = word + " "
    if line:
        lines.append(line.strip())

    for line in lines:
        canvas_obj.drawString(x, y, line)
        y -= line_height

    return y


def create_pdf(news: List[Dict[str, str]], filename: str):
    """
    Create a PDF file with the news articles.

    Args:
        news (List[Dict[str, str]]): List of news articles.
        filename (str): Name of the PDF file.
    """
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter
    left_margin = 50
    right_margin = 20  # Reduced right margin for better content space
    text_width = width - left_margin - right_margin
    y = height - left_margin  # Start near the top of the page

    # Title for the PDF
    c.setFont("Helvetica-Bold", 16)
    c.drawString(left_margin, y, "News Articles")
    y -= 30

    for article in news:
        if y < left_margin + 50:  # Check if space is running out on the page
            c.showPage()
            c.setFont("Helvetica", 12)
            y = height - left_margin

        # Add news details
        c.setFont("Helvetica-Bold", 12)
        y = draw_wrapped_text(c, f"Title: {article['title']}", left_margin, y, text_width, 14)

        c.setFont("Helvetica", 10)
        y = draw_wrapped_text(c, f"Source: {article['source']}", left_margin, y, text_width, 12)
        y = draw_wrapped_text(c, f"Published: {article['published']}", left_margin, y, text_width, 12)

        # Add hyperlink for the article
        link_text = "Read more"
        c.setFont("Helvetica", 10)
        c.drawString(left_margin, y, link_text)
        c.linkURL(article['link'], (left_margin, y - 2, left_margin + 50, y + 10), relative=0)
        y -= 15

        # Wrap and align the article summary
        y = draw_wrapped_text(c, f"Summary: {article['summary']}", left_margin, y, text_width, 12)

        y -= 20  # Add space before the next article

    # Save the PDF
    c.save()
    print(f"PDF created successfully: {filename}")


def send_email_with_attachment(sender_email, recipient_email, subject, body, attachment_path, smtp_server, smtp_port, login_email, login_password):
    """
    Send an email with a PDF attachment.

    Args:
        sender_email (str): Sender's email address.
        recipient_email (str): Recipient's email address.
        subject (str): Email subject.
        body (str): Email body.
        attachment_path (str): Path to the PDF file to attach.
        smtp_server (str): SMTP server address.
        smtp_port (int): SMTP server port.
        login_email (str): Email address for authentication.
        login_password (str): Password for authentication.
    """
    try:
        # Set up the email
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = subject

        # Attach the body
        msg.attach(MIMEText(body, 'plain'))

        # Attach the file
        with open(attachment_path, 'rb') as attachment:
            mime_base = MIMEBase('application', 'octet-stream')
            mime_base.set_payload(attachment.read())
            encoders.encode_base64(mime_base)
            mime_base.add_header(
                'Content-Disposition',
                f'attachment; filename={attachment_path.split("/")[-1]}'
            )
            msg.attach(mime_base)

        # Send the email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()  # Secure the connection
            server.login(login_email, login_password)
            server.send_message(msg)

        print(f"Email sent successfully to {recipient_email}")

    except Exception as e:
        print(f"Failed to send email: {e}")


if __name__ == "__main__":
    # List of RSS feeds from Indian news websites
    rss_feed_urls = [
        "https://www.thehindu.com/news/national/feeder/default.rss",  # The Hindu National News
        "https://indianexpress.com/section/india/feed/",             # Indian Express India Section
        "https://theprint.in/feed/"                                  # The Print Feed
    ]

    # Initialize the news fetcher
    fetcher = NewsFetcher(rss_feed_urls)

    # Fetch news
    news_articles = fetcher.fetch_news()

    # Generate PDF
    pdf_filename = "news_articles_with_hyperlinks.pdf"
    create_pdf(news_articles, pdf_filename)

# Load environment variables from .env file
load_dotenv()

# Get credentials from environment variables
sender_email = os.getenv("EMAIL")
login_password = os.getenv("PASSWORD")
recipient_email = os.getenv("RECIPIENT_EMAIL")
smtp_server = "smtp.gmail.com"
smtp_port = 587

# Send the email with the PDF attachment
send_email_with_attachment(
        sender_email,
        recipient_email,
        "Daily News PDF",
        "Please find attached the latest news PDF.",
        pdf_filename,
        smtp_server,
        smtp_port,
        sender_email,
        login_password
    )