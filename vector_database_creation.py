import json
import numpy as np
import faiss
import pickle
from sentence_transformers import SentenceTransformer
import os
from datetime import datetime


class NewsVectorDB:
    def __init__(self, json_file="news_data.json",
                 faiss_index_file="news_index.faiss",
                 metadata_file="news_metadata.pkl",
                 model_name='all-MiniLM-L6-v2'):
        """
        Initialize the News Vector Database.

        Args:
            json_file: Path to JSON file containing news articles
            faiss_index_file: Path to save Faiss index
            metadata_file: Path to save article metadata
            model_name: SentenceTransformer model name
        """
        self.json_file = json_file
        self.faiss_index_file = faiss_index_file
        self.metadata_file = metadata_file
        self.model = SentenceTransformer(model_name)
        self.embeddings = None
        self.metadata = []

    def load_news_data(self):
        """Load news data from JSON file."""
        try:
            with open(self.json_file, 'r', encoding='utf-8') as f:
                news_data = json.load(f)
            print(f"✓ Loaded {len(news_data)} articles from {self.json_file}")
            return news_data
        except FileNotFoundError:
            print(f"✗ File {self.json_file} not found")
            return []
        except json.JSONDecodeError:
            print(f"✗ Error decoding JSON from {self.json_file}")
            return []

    def prepare_text_for_embedding(self, article):
        """Prepare text for embedding by combining relevant fields."""
        # Combine headline and full news for better representation
        text_parts = []

        # Add headline
        if article.get('headline'):
            text_parts.append(f"Headline: {article['headline']}")

        # Add full news content
        if article.get('full_news'):
            # Take first 1000 characters to avoid very long texts
            full_text = article['full_news'][:1000]
            text_parts.append(f"Content: {full_text}")

        # Add source if available
        if article.get('source'):
            text_parts.append(f"Source: {article['source']}")

        return " ".join(text_parts)

    def create_embeddings(self, news_data):
        """Create embeddings for all news articles."""
        if not news_data:
            print("✗ No news data to create embeddings")
            return None

        print("Creating embeddings for news articles...")

        # Prepare texts for embedding
        texts = []
        self.metadata = []

        for idx, article in enumerate(news_data):
            # Prepare text
            text = self.prepare_text_for_embedding(article)
            texts.append(text)

            # Store metadata
            metadata = {
                'id': idx,
                'headline': article.get('headline', ''),
                'source_url': article.get('source_url', ''),
                'published_time': article.get('published_time', ''),
                'source': article.get('source', 'Unknown'),
                'full_news_preview': article.get('full_news', '')[:200] + "..." if article.get('full_news') else ''
            }
            self.metadata.append(metadata)

        # Create embeddings
        print(f"Generating embeddings for {len(texts)} articles...")
        self.embeddings = self.model.encode(texts, show_progress_bar=True)

        print(f"✓ Created embeddings with shape: {self.embeddings.shape}")
        return self.embeddings

    def build_faiss_index(self, embeddings):
        """Build and save Faiss index."""
        if embeddings is None or len(embeddings) == 0:
            print("✗ No embeddings to build index")
            return None

        # Get embedding dimension
        dimension = embeddings.shape[1]
        print(f"Embedding dimension: {dimension}")

        # Create Faiss index (using L2 distance - Euclidean)
        # You can also use IndexFlatIP for cosine similarity if you normalize embeddings
        index = faiss.IndexFlatL2(dimension)

        # Normalize embeddings for cosine similarity (optional)
        # faiss.normalize_L2(embeddings)
        # index = faiss.IndexFlatIP(dimension)

        # Add embeddings to index
        index.add(embeddings)
        print(f"✓ Added {index.ntotal} vectors to Faiss index")

        return index

    def save_vector_db(self, index):
        """Save Faiss index and metadata."""
        if index is None:
            print("✗ No index to save")
            return

        # Save Faiss index
        faiss.write_index(index, self.faiss_index_file)
        print(f"✓ Saved Faiss index to {self.faiss_index_file}")

        # Save metadata
        with open(self.metadata_file, 'wb') as f:
            pickle.dump(self.metadata, f)
        print(f"✓ Saved metadata to {self.metadata_file}")

        # Save config
        config = {
            'created_at': datetime.now().isoformat(),
            'num_articles': len(self.metadata),
            'embedding_dim': index.d,
            'index_type': 'IndexFlatL2',
            'model_name': 'all-MiniLM-L6-v2'
        }

        config_file = "vector_db_config.json"
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        print(f"✓ Saved config to {config_file}")

    def load_vector_db(self):
        """Load existing Faiss index and metadata."""
        if not os.path.exists(self.faiss_index_file) or not os.path.exists(self.metadata_file):
            print("✗ Vector database files not found")
            return None, None

        try:
            # Load Faiss index
            index = faiss.read_index(self.faiss_index_file)

            # Load metadata
            with open(self.metadata_file, 'rb') as f:
                metadata = pickle.load(f)

            print(f"✓ Loaded vector database with {index.ntotal} articles")
            return index, metadata
        except Exception as e:
            print(f"✗ Error loading vector database: {e}")
            return None, None

    def search_similar(self, query, k=5, index=None, metadata=None):
        """Search for similar articles."""
        if index is None or metadata is None:
            print("Loading vector database...")
            index, metadata = self.load_vector_db()
            if index is None:
                return []

        # Create embedding for query
        query_embedding = self.model.encode([query])

        # Search
        distances, indices = index.search(query_embedding, k)

        # Prepare results
        results = []
        for i, (dist, idx) in enumerate(zip(distances[0], indices[0])):
            if idx < len(metadata):  # Ensure valid index
                article_info = metadata[idx].copy()
                article_info['similarity_score'] = float(dist)
                article_info['rank'] = i + 1
                results.append(article_info)

        return results

    def build_from_scratch(self):
        """Build vector database from scratch."""
        # Load news data
        news_data = self.load_news_data()
        if not news_data:
            return False

        # Create embeddings
        embeddings = self.create_embeddings(news_data)
        if embeddings is None:
            return False

        # Build Faiss index
        index = self.build_faiss_index(embeddings)
        if index is None:
            return False

        # Save everything
        self.save_vector_db(index)
        return True

    def print_search_results(self, results, query):
        """Print search results in a readable format."""
        print(f"\n{'=' * 80}")
        print(f"SEARCH RESULTS FOR: '{query}'")
        print(f"{'=' * 80}")

        if not results:
            print("No results found.")
            return

        for result in results:
            print(f"\n[{result['rank']}] Score: {result['similarity_score']:.4f}")
            print(f"Headline: {result['headline']}")
            print(f"Source: {result['source']}")
            print(f"Published: {result['published_time']}")
            print(f"Preview: {result['full_news_preview']}")
            print(f"URL: {result['source_url']}")
            print("-" * 60)


def main():
    """Main function to build and test the vector database."""
    print("=" * 80)
    print("NEWS VECTOR DATABASE BUILDER")
    print("=" * 80)

    # Initialize vector database
    vector_db = NewsVectorDB(
        json_file="news_data.json",
        faiss_index_file="news_index.faiss",
        metadata_file="news_metadata.pkl"
    )

    # Check if vector database already exists
    if os.path.exists("news_index.faiss") and os.path.exists("news_metadata.pkl"):
        print("Found existing vector database.")
        choice = input("Do you want to rebuild from scratch? (y/n): ").lower()

        if choice == 'y':
            print("\nRebuilding vector database from scratch...")
            if vector_db.build_from_scratch():
                print("✓ Vector database rebuilt successfully!")
            else:
                print("✗ Failed to rebuild vector database")
        else:
            print("Using existing vector database.")
    else:
        print("No existing vector database found. Building from scratch...")
        if vector_db.build_from_scratch():
            print("✓ Vector database built successfully!")
        else:
            print("✗ Failed to build vector database")
            return

    # Interactive search
    print("\n" + "=" * 80)
    print("INTERACTIVE SEARCH")
    print("=" * 80)
    print("Type 'exit' to quit the search")

    # Load the vector database for searching
    index, metadata = vector_db.load_vector_db()

    while True:
        query = input("\nEnter search query: ").strip()

        if query.lower() == 'exit':
            break

        if not query:
            print("Please enter a query.")
            continue

        # Search for similar articles
        results = vector_db.search_similar(query, k=5, index=index, metadata=metadata)

        # Print results
        vector_db.print_search_results(results, query)

    print("\nThank you for using the News Vector Database!")


def test_simple_build():
    """Simple function to just build the vector database without interactive search."""
    print("Building vector database...")

    vector_db = NewsVectorDB(
        json_file="news_data.json",
        faiss_index_file="news_index.faiss",
        metadata_file="news_metadata.pkl"
    )

    success = vector_db.build_from_scratch()

    if success:
        print("\n✓ Vector database built successfully!")
        print(f"Files created:")
        print(f"  - {vector_db.faiss_index_file} (Faiss index)")
        print(f"  - {vector_db.metadata_file} (Metadata)")
        print(f"  - vector_db_config.json (Configuration)")
    else:
        print("\n✗ Failed to build vector database")


if __name__ == "__main__":
    # For simple build (without interactive search), use:
    # test_simple_build()

    # For full interactive experience, use:
    main()