import requests

def get_page_html(url):
    """Fetches and returns the raw HTML content of a page."""
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return resp.text


# Example usage:
if __name__ == "__main__":
    # Replace with the URL of the page you want to get the HTML for
    url = "https://www.thedailystar.net/todays-news"  # Example URL
    page_html = get_page_html(url)
    print(page_html)  # Prints the raw HTML content of the page
