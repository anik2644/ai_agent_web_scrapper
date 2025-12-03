import requests
from bs4 import BeautifulSoup
import re
import feedparser
from urllib.parse import urljoin

CNN_RSS_URL = "http://rss.cnn.com/rss/cnn_topstories.rss"


def scrape_cnn_article(url):
    """Scrapes full article content from CNN using the working scraper function."""
    # Set headers to mimic a browser request
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }

    try:
        # Send GET request
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        # Parse HTML content
        soup = BeautifulSoup(response.content, 'html.parser')

        # Find the main article content - more specific selectors for CNN
        article_content = None

        # Try to find the main article container
        # CNN often uses these classes for article content
        article_selectors = [
            '[class*="article__content"]',
            '[class*="article-content"]',
            '.article__main',
            '.zn-body__paragraph',
            'div[data-component-name="article-body"]',
            '.l-container .zn-body__paragraph',
            '.pg-rail-tall__body',
            '.layout__content-wrapper'
        ]

        for selector in article_selectors:
            elements = soup.select(selector)
            if elements:
                # Get the largest text container (usually the main article)
                article_content = max(elements, key=lambda x: len(x.get_text()))
                break

        # If still not found, try more specific approach
        if not article_content:
            # Look for paragraphs with article text
            paragraphs = soup.find_all('p')
            article_paragraphs = []

            for p in paragraphs:
                text = p.get_text(strip=True)
                # Filter out short paragraphs and navigation/button text
                if len(text) > 50 and not any(
                        x in text.lower() for x in ['video', 'play', 'share', 'comment', 'sign up', 'subscribe']):
                    # Check if paragraph is likely part of article (has parent with article classes)
                    parent_classes = ' '.join(p.parent.get('class', [])) + ' ' + ' '.join(
                        p.parent.parent.get('class', []))
                    if any(x in parent_classes.lower() for x in ['article', 'content', 'body', 'paragraph']):
                        article_paragraphs.append(p)

            if article_paragraphs:
                # Create a new div to hold all article paragraphs
                article_content = soup.new_tag('div')
                for p in article_paragraphs:
                    article_content.append(p)

        # If still not found, try to extract by structure
        if not article_content:
            # Look for the main content area
            main = soup.find('main') or soup.find('article') or soup.find('div', role='main')
            if main:
                article_content = main

        # Get text from article content
        if article_content:
            # Remove unwanted elements within the article
            for element in article_content.find_all(
                    ['script', 'style', 'aside', 'figure', 'blockquote', 'div[class*="video"]',
                     'div[class*="ad"]', 'div[class*="social"]', 'div[class*="related"]']):
                element.decompose()

            # Get all paragraph text
            paragraphs = article_content.find_all('p')
            text_parts = []

            for p in paragraphs:
                text = p.get_text(strip=True)
                # Filter out non-article content
                if (len(text) > 30 and
                        not any(x in text.lower() for x in [
                            'video', 'play', 'share', 'tweet', 'facebook', 'instagram',
                            'sign up', 'subscribe', 'newsletter', 'click here',
                            'advertisement', 'sponsored', 'read more', 'watch',
                            'follow us', 'also read', 'related:', 'popular now'
                        ])):
                    text_parts.append(text)

            # Join all valid paragraphs
            if text_parts:
                text = '\n\n'.join(text_parts)
            else:
                # Fallback: get all text
                text = article_content.get_text(separator='\n', strip=True)
        else:
            # Last resort: get body text and clean it
            body = soup.body
            if body:
                for element in body.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside',
                                              'div[class*="video"]', 'div[class*="ad"]']):
                    element.decompose()
                text = body.get_text(separator='\n', strip=True)
            else:
                text = ""

        # Clean up the text
        if text:
            # Remove excessive whitespace and empty lines
            text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
            text = re.sub(r'^\s+', '', text, flags=re.MULTILINE)

            # Remove common non-article patterns
            lines = text.split('\n')
            cleaned_lines = []
            for line in lines:
                line_stripped = line.strip()
                if (len(line_stripped) > 30 and
                        not any(x in line_stripped.lower() for x in [
                            'video ad feedback', 'source:', 'now playing',
                            'watch this video', 'play video', 'read:', 'more:'
                        ])):
                    cleaned_lines.append(line_stripped)

            text = '\n'.join(cleaned_lines)

        return text

    except requests.exceptions.RequestException as e:
        print(f"Error fetching the page {url}: {e}")
        return f"Error fetching article: {str(e)}"
    except Exception as e:
        print(f"Error parsing the page {url}: {e}")
        return f"Error parsing article: {str(e)}"


def get_rss_feed():
    """Fetches and parses the RSS feed, then scrapes full articles for each entry."""
    feed = feedparser.parse(CNN_RSS_URL)
    news_data = {}

    print(f"Fetching RSS feed and scraping  articles...")
    print("=" * 80)

    for i, entry in enumerate(feed.entries):
        # print(f"Processing article {i + 1}/{num_articles}: {entry.title[:80]}...")

        try:
            full_article = scrape_cnn_article(entry.link)

            # Get publication date/time
            published_time = entry.get('published', 'No time available')

            # Add to dictionary with article number as key
            news_data[i + 1] = {
                "headline": entry.title,
                "source_url": entry.link,
                "published_time": published_time,
                "full_news": full_article
            }

            # print(f"  ✓ Successfully scraped")
        except Exception as e:
            print(f"  ✗ Failed to scrape: {str(e)}")
            news_data[i + 1] = {
                "headline": entry.title,
                "source_url": entry.link,
                "published_time": entry.get('published', 'No time available'),
                "full_news": f"Failed to retrieve full article: {str(e)}"
            }

    print(f"\n✓ Successfully collected {len(news_data)} articles")
    return news_data


def display_news(news_data):
    """Displays the news details from the dictionary in the specified format."""
    print("\n" + "=" * 80)
    print(f"Displaying News Articles:")
    print("=" * 80 + "\n")

    for i, news in news_data.items():
        print(f"Article {i}:")
        print(f"  Headline: {news['headline']}")
        print(f"  Source URL: {news['source_url']}")
        print(f"  Published Time: {news['published_time']}")
        print(f"  Full News:\n{news['full_news']}\n")
        print("-" * 80)


def get_all_news_entries():
    """
    Main function to get all news entries in a dictionary.

    Args:
        num_articles (int): Number of articles to fetch (default: 5)

    Returns:
        dict: Dictionary with article numbers as keys and article data as values
    """
    print("Starting CNN News Aggregator...")
    print(f"RSS Feed URL: {CNN_RSS_URL}")
    print("-" * 80)

    # Get all news data
    all_news = get_rss_feed()

    # Display the news
    display_news(all_news)

    return all_news


# Example usage
if __name__ == "__main__":
    # Get 5 news articles (you can change this number)
    news_dictionary = get_all_news_entries()

    # print("\n" + "=" * 80)
    # print("DICTIONARY STRUCTURE:")
    # print("=" * 80)
    # print(f"Type: {type(news_dictionary)}")
    # print(f"Total entries: {len(news_dictionary)}")

    # Show how to access individual articles
    # print("\nAccessing individual articles:")
    # print("-" * 40)
    # if news_dictionary:
    #     first_key = list(news_dictionary.keys())[0]
    #     print(f"First article key: {first_key}")
    #     print(f"First article headline: {news_dictionary[first_key]['headline']}")

        # # You can iterate through all articles
        # print("\nIterating through all articles:")
        # for article_num, article_data in news_dictionary.items():
        #     print(f"Article {article_num}: {article_data['headline'][:50]}...")

    print("=" * 80)