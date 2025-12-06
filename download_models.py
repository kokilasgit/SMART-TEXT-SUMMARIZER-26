import os
from transformers import pipeline

# Configuration
MODEL_NAME = "sshleifer/distilbart-cnn-12-6"
MODEL_DIR = os.path.join("Backend", "models", "transformers_model")

def download_model():
    print(f"Downloading model '{MODEL_NAME}' to '{MODEL_DIR}'...")
    print("This may take a few minutes depending on your internet connection.")
    print("Files will be approx 300MB.")

    # Create directory if not exists
    os.makedirs(MODEL_DIR, exist_ok=True)

    try:
        # Initialize pipeline which downloads the model caching it
        # We explicitly save it to our local directory for offline use
        summarizer = pipeline("summarization", model=MODEL_NAME)
        summarizer.save_pretrained(MODEL_DIR)
        print("✅ Model downloaded successfully!")
        print(f"Model saved to: {os.path.abspath(MODEL_DIR)}")
    except Exception as e:
        print(f"❌ Error downloading model: {str(e)}")

if __name__ == "__main__":
    download_model()
