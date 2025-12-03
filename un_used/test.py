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


def get_rss_feed(num_articles=5):
    """Fetches and parses the RSS feed, then scrapes full articles for each entry."""
    feed = feedparser.parse(CNN_RSS_URL)
    news_data = []

    print(f"Fetching RSS feed and scraping {num_articles} articles...")
    print("=" * 80)

    for i, entry in enumerate(feed.entries[:num_articles]):
        print(f"Processing article {i + 1}/{num_articles}: {entry.title[:80]}...")

        try:
            full_article = scrape_cnn_article(entry.link)

            # Get publication date if available
            pub_date = entry.get('published', 'No date available')

            news_data.append({
                "headline": entry.title,
                "source_url": entry.link,
                "publication_date": pub_date,
                "full_news": full_article,
                "summary": entry.get('summary', '')[:200] + '...' if entry.get('summary') else '',
                "article_length": len(full_article) if full_article else 0
            })

            print(f"  ✓ Successfully scraped ({len(full_article)} characters)")
        except Exception as e:
            print(f"  ✗ Failed to scrape: {str(e)}")
            news_data.append({
                "headline": entry.title,
                "source_url": entry.link,
                "publication_date": entry.get('published', 'No date available'),
                "full_news": f"Failed to retrieve full article: {str(e)}",
                "summary": entry.get('summary', '')[:200] + '...' if entry.get('summary') else '',
                "article_length": 0
            })

    return news_data


def display_news(news_data):
    """Displays the news details from the dictionary."""
    print("\n" + "=" * 80)
    print(f"Displaying {len(news_data)} News Articles:")
    print("=" * 80 + "\n")

    for i, news in enumerate(news_data, 1):
        print(f"ARTICLE {i}:")
        print(f"  Headline: {news['headline']}")
        print(f"  Publication Date: {news['publication_date']}")
        print(f"  Source URL: {news['source_url']}")
        print(f"  Summary: {news['summary']}")
        print(f"  Article Length: {news['article_length']} characters")
        print(f"\n  Full News Content:")
        print("-" * 40)

        # Display first 500 characters of full article
        if news['full_news']:
            preview = news['full_news'][:500]
            if len(news['full_news']) > 500:
                preview += "..."
            print(preview)
        else:
            print("No content available")

        print("\n" + "=" * 80)


def save_to_file(news_data, filename="cnn_news_collection.txt"):
    """Saves all news articles to a text file."""
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"CNN NEWS COLLECTION - {len(news_data)} ARTICLES\n")
        f.write("=" * 80 + "\n\n")

        for i, news in enumerate(news_data, 1):
            f.write(f"ARTICLE {i}:\n")
            f.write(f"Headline: {news['headline']}\n")
            f.write(f"Publication Date: {news['publication_date']}\n")
            f.write(f"Source URL: {news['source_url']}\n")
            f.write(f"Article Length: {news['article_length']} characters\n")
            f.write(f"\nSummary:\n{news['summary']}\n")
            f.write(f"\nFull News:\n")
            f.write("-" * 40 + "\n")
            f.write(news['full_news'])
            f.write("\n" + "=" * 80 + "\n\n")

    print(f"\nAll articles saved to '{filename}'")


def get_statistics(news_data):
    """Returns statistics about the collected news."""
    total_articles = len(news_data)
    total_chars = sum(news['article_length'] for news in news_data)
    avg_chars = total_chars // total_articles if total_articles > 0 else 0

    return {
        "total_articles": total_articles,
        "total_characters": total_chars,
        "average_article_length": avg_chars,
        "successful_scrapes": sum(1 for news in news_data if news['article_length'] > 0)
    }


if __name__ == "__main__":
    # Fetch 5 articles by default
    news_data = get_rss_feed(num_articles=5)

    # Display articles
    display_news(news_data)

    # Save to file
    save_to_file(news_data)

    # Show statistics
    stats = get_statistics(news_data)
    print("\n" + "=" * 80)
    print("STATISTICS:")
    print("=" * 80)
    print(f"Total articles processed: {stats['total_articles']}")
    print(f"Successful scrapes: {stats['successful_scrapes']}")
    print(f"Total characters collected: {stats['total_characters']:,}")
    print(f"Average article length: {stats['average_article_length']:,} characters")
    print("=" * 80)