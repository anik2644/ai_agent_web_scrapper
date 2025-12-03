import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

BASE_URL = "https://www.thedailystar.net"


def fetch_page_content(url):
    """Fetches and returns the content of the page with a User-Agent header."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()  # This will raise an error if the status code is not 200
    return resp.text


def get_headlines_and_links(soup):
    """Extracts and returns headlines and links from the soup object."""
    headlines = []
    links = []
    for h3 in soup.find_all('h3', class_='title'):
        a = h3.find('a', href=True)
        if a and a.text.strip():
            headlines.append(a.text.strip())
            links.append(urljoin(BASE_URL, a['href']))
    return headlines, links


def get_full_news(url):
    """Fetches and returns the full news content for a given URL."""
    page_content = fetch_page_content(url)
    soup = BeautifulSoup(page_content, "html.parser")

    # Extract the published time
    published_time_tag = soup.find('div', class_='date text-14')  # Adjust class name based on the screenshot
    if published_time_tag:
        published_time = published_time_tag.get_text(strip=True)
    else:
        published_time = "Not available"

    # Extract full article content
    content_div = soup.find('div', class_='field-items')
    if not content_div:
        content_div = soup.find('article')
    if not content_div:
        content_div = soup.find('div', id='main-content')
    if not content_div:
        return "Content not available — could not locate main container."

    paragraphs = content_div.find_all('p')
    if not paragraphs:
        return "Content not available — article seems empty."

    full_text = "\n\n".join(p.get_text(strip=True) for p in paragraphs)

    # Return the full news content along with the published time
    return f"{full_text}"
# Published Time: {published_time}\n\nFull Article:\n


def get_today_news():
    """Fetches today's news headlines and links."""
    today_url = urljoin(BASE_URL, "/todays-news")
    html = fetch_page_content(today_url)
    soup = BeautifulSoup(html, "html.parser")
    return get_headlines_and_links(soup)


def get_news_details_from_daily_star():
    """Stores news details (source_url, headline, full_news, published_time) into a list of dictionaries."""
    headlines, links = get_today_news()

    news_data = []
    for i, (title, link) in enumerate(zip(headlines, links), 1):  # Limit to 5 headlines
        full_article = get_full_news(link)

        # Extract the published time (assuming the published time is in a <time> tag or similar)
        # Modify the extraction as per the actual HTML structure of the page
        soup = BeautifulSoup(fetch_page_content(link), "html.parser")
        published_time = soup.find('time')  # Assuming there's a <time> tag
        if published_time:
            published_time = published_time.get_text(strip=True)
        else:
            published_time = "Not available"

        # Create a dictionary for each article
        news_item = {
            "source_url": link,
            "headline": title,
            "full_news": full_article,
            "published_time": published_time
        }

        news_data.append(news_item)

    return news_data


def display_news(news_data):
    """Displays the news details from the dictionary."""
    print("Displaying the News Articles:\n")
    for i, news in enumerate(news_data[4:10], 1):  # Display only the first 5
        print(f"Article {i}:")
        print(f"  Headline: {news['headline']}")
        print(f"  Source URL: {news['source_url']}")
        # print(f"  Published Time: {news['published_time']}")
        print(f"  Full News:\n{news['full_news']}\n")
        print("-" * 80)  # Separator for better readability


if __name__ == "__main__":
    # Get the news data as a list of dictionaries
    news_data = get_news_details_from_daily_star()

    # Display the news in a formatted way
    display_news(news_data)
