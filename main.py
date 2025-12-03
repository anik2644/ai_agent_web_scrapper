import json
from datetime import datetime
from cnn import get_rss_feed  # Make sure this function exists in cnn.py
from get_headlines_links_news_dailystar import get_news_details_from_daily_star

JSON_FILE = "news_data.json"  # File to store the aggregated news


def load_existing_news():
    """Loads existing news from JSON file."""
    try:
        with open(JSON_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def merge_and_deduplicate_news(existing_news, new_news):
    """
    Merges new news with existing news, removing duplicates based on headline.
    Returns only the newly added items.
    """
    # Create a set of existing headlines for quick lookup
    existing_headlines = {news['headline'] for news in existing_news}

    # Filter out duplicates from new_news
    unique_new_news = []

    for news_item in new_news:
        if news_item['headline'] not in existing_headlines:
            unique_new_news.append(news_item)

    return unique_new_news


def get_formatted_cnn_news():
    """Gets CNN news and converts it to the same format as Daily Star."""
    cnn_news_dict = get_rss_feed()  # This should return the dictionary

    # Convert dictionary values to list format
    cnn_news_list = []
    for article_num, article_data in cnn_news_dict.items():
        # Ensure consistent field names
        cnn_news_list.append({
            "source_url": article_data.get('source_url', ''),
            "headline": article_data.get('headline', ''),
            "full_news": article_data.get('full_news', ''),
            "published_time": article_data.get('published_time', ''),
            "source": "CNN"  # Add source identifier
        })

    return cnn_news_list


def get_formatted_daily_star_news():
    """Gets Daily Star news and ensures consistent format."""
    daily_star_news = get_news_details_from_daily_star()

    # Add source identifier
    for news_item in daily_star_news:
        news_item["source"] = "Daily Star"

    return daily_star_news


def save_news_to_json(all_news):
    """Saves all news data to JSON file."""
    try:
        with open(JSON_FILE, 'w', encoding='utf-8') as f:
            json.dump(all_news, f, ensure_ascii=False, indent=4)
        print(f"✓ News data successfully saved to {JSON_FILE}")
        print(f"✓ Total articles: {len(all_news)}")
    except Exception as e:
        print(f"✗ Error saving news data to JSON: {e}")


def main():
    """Main function to collect and save all unique news data."""
    print("=" * 80)
    print("Fetching and processing news data...")
    print("=" * 80)

    # Load existing news
    existing_news = load_existing_news()
    print(f"✓ Loaded {len(existing_news)} existing articles from {JSON_FILE}")

    # Get new news from both sources
    print("\nFetching new articles...")

    # Get CNN news
    print("1. Fetching CNN news...")
    try:
        cnn_news = get_formatted_cnn_news()
        print(f"   Retrieved {len(cnn_news)} articles from CNN")
    except Exception as e:
        print(f"   ✗ Error fetching CNN news: {e}")
        cnn_news = []

    # Get Daily Star news
    print("2. Fetching Daily Star news...")
    try:
        daily_star_news = get_formatted_daily_star_news()
        print(f"   Retrieved {len(daily_star_news)} articles from Daily Star")
    except Exception as e:
        print(f"   ✗ Error fetching Daily Star news: {e}")
        daily_star_news = []

    # Combine all new articles
    all_new_news = cnn_news + daily_star_news
    print(f"\n✓ Total new articles fetched: {len(all_new_news)}")

    # Check for duplicates against existing data
    unique_new_news = merge_and_deduplicate_news(existing_news, all_new_news)
    print(f"✓ Unique new articles (not in existing data): {len(unique_new_news)}")

    if unique_new_news:
        # Display new articles
        print("\n" + "=" * 80)
        print("NEW ARTICLES ADDED:")
        print("=" * 80)
        for i, news in enumerate(unique_new_news, 1):
            print(f"\nArticle {i}:")
            print(f"  Source: {news.get('source', 'Unknown')}")
            print(f"  Headline: {news['headline'][:80]}...")
            print(f"  Published: {news.get('published_time', 'Not available')}")

        # Combine existing and new unique news
        all_news = existing_news + unique_new_news

        # Save to JSON
        print("\n" + "=" * 80)
        save_news_to_json(all_news)
    else:
        print("\n" + "=" * 80)
        print("No new unique articles to add.")
        print("=" * 80)


if __name__ == "__main__":
    main()