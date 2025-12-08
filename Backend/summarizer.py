"""
Text Summarization Engine for Smart Text Summarizer
Supports both Extractive and Abstractive summarization with dynamic compression
"""
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
from nltk.probability import FreqDist
import re
from collections import defaultdict

# Download required NLTK data
def ensure_nltk_data():
    """Ensure required NLTK data is downloaded"""
    required_packages = ['punkt', 'punkt_tab', 'stopwords']
    for package in required_packages:
        try:
            nltk.data.find(f'tokenizers/{package}' if 'punkt' in package else f'corpora/{package}')
        except LookupError:
            nltk.download(package, quiet=True)

# Initialize NLTK data
ensure_nltk_data()


class TextSummarizer:
    """Text summarization engine with extractive and abstractive modes"""
    
    def _init_(self):
        self.stop_words = set(stopwords.words('english'))
    
    def preprocess_text(self, text):
        """Clean and preprocess text"""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        # Remove special characters but keep sentence punctuation
        text = re.sub(r'[^\w\s.,!?;:\'-]', '', text)
        return text
    
    def get_sentences(self, text):
        """Tokenize text into sentences"""
        return sent_tokenize(text)
    
    def get_words(self, text):
        """Tokenize and filter words"""
        words = word_tokenize(text.lower())
        # Filter: alphanumeric, not stopwords, length > 2
        return [w for w in words if w.isalnum() and w not in self.stop_words and len(w) > 2]
    
    def calculate_sentence_scores(self, sentences, word_freq):
        """Score sentences based on word frequency"""
        sentence_scores = {}
        
        for i, sentence in enumerate(sentences):
            words = self.get_words(sentence)
            if not words:
                sentence_scores[i] = 0
                continue
            
            # Calculate score based on word frequency
            # Common words = Higher score (Extractive assumption)
            score = sum(word_freq.get(word, 0) for word in words)
            # Normalize by sentence length to avoid bias towards long sentences
            sentence_scores[i] = score / len(words)
            
            # Boost score for sentences at the beginning (often contain key info)
            if i < 3:
                sentence_scores[i] *= 1.2
        
        return sentence_scores
    
    def extractive_summarize(self, text, target_word_count=None, target_percentage=None):
        """
        Extractive summarization - selects most important sentences
        
        Args:
            text: Input text to summarize
            target_word_count: Target number of words in summary
            target_percentage: Target percentage of original text (alternative to word count)
        
        Returns:
            Summary string
        """
        text = self.preprocess_text(text)
        sentences = self.get_sentences(text)
        
        if len(sentences) <= 1:
            return text
        
        # Calculate target based on percentage or word count
        total_words = len(text.split())
        
        if target_word_count:
            target = target_word_count
        elif target_percentage:
            target = max(10, int(total_words * target_percentage / 100))
        else:
            target = max(10, int(total_words * 0.4))  # Default 40%
        
        # Get word frequency distribution
        words = self.get_words(text)
        word_freq = FreqDist(words)
        
        # Score sentences
        sentence_scores = self.calculate_sentence_scores(sentences, word_freq)
        
        # Sort sentences by score
        ranked_indices = sorted(sentence_scores.keys(), key=lambda x: sentence_scores[x], reverse=True)
        
        # Select sentences until we reach target word count
        selected_indices = []
        current_word_count = 0
        
        for idx in ranked_indices:
            sentence_words = len(sentences[idx].split())
            if current_word_count + sentence_words <= target or len(selected_indices) == 0:
                selected_indices.append(idx)
                current_word_count += sentence_words
                
                # Stop if we've reached our target
                if current_word_count >= target * 0.9:  # Allow 10% tolerance
                    break
        
        # Sort selected indices to maintain original order
        selected_indices.sort()
        
        # Combine sentences
        summary = ' '.join(sentences[i] for i in selected_indices)
        return summary
    
    def abstractive_summarize(self, text, target_word_count=None, target_percentage=None):
        """
        Abstractive summarization using sentence compression
        Uses extraction with additional compression techniques
        """
        text = self.preprocess_text(text)
        sentences = self.get_sentences(text)
        
        if len(sentences) <= 1:
            return text
        
        # Calculate target
        total_words = len(text.split())
        
        if target_word_count:
            target = target_word_count
        elif target_percentage:
            # Aim for 80% of target since compression will reduce further
            target = max(10, int(total_words * target_percentage / 100 * 1.2))
        else:
            target = max(10, int(total_words * 0.5))
        
        # Get word frequency distribution
        words = self.get_words(text)
        word_freq = FreqDist(words)
        
        # Score sentences
        sentence_scores = self.calculate_sentence_scores(sentences, word_freq)
        
        # Sort sentences by score
        ranked_indices = sorted(sentence_scores.keys(), key=lambda x: sentence_scores[x], reverse=True)
        
        # Select and compress sentences until we reach target
        selected_sentences = []
        current_word_count = 0
        
        for idx in ranked_indices:
            compressed = self.compress_sentence(sentences[idx], word_freq)
            sentence_words = len(compressed.split())
            
            if current_word_count + sentence_words <= target or len(selected_sentences) == 0:
                selected_sentences.append((idx, compressed))
                current_word_count += sentence_words
                
                if current_word_count >= target * 0.85:
                    break
        
        # Sort by original order
        selected_sentences.sort(key=lambda x: x[0])
        
        return ' '.join(sent for _, sent in selected_sentences)
    
    def compress_sentence(self, sentence, word_freq):
        """
        Compress a sentence by removing less important words/phrases
        """
        # Remove parenthetical content
        sentence = re.sub(r'\([^)]*\)', '', sentence)
        sentence = re.sub(r'\[[^\]]*\]', '', sentence)
        
        # Remove redundant phrases
        redundant_phrases = [
            r'\bin fact\b', r'\bactually\b', r'\bbasically\b',
            r'\bin other words\b', r'\bthat is to say\b',
            r'\bto be honest\b', r'\bfrankly speaking\b',
            r'\bas a matter of fact\b', r'\bto be precise\b',
            r'\bit is worth noting that\b', r'\bit should be noted that\b',
            r'\bneedless to say\b', r'\bas we know\b',
            r'\bof course\b', r'\bobviously\b', r'\bclearly\b',
            r'\bundoubtedly\b', r'\bwithout a doubt\b'
        ]
        for phrase in redundant_phrases:
            sentence = re.sub(phrase, '', sentence, flags=re.IGNORECASE)
        
        # Clean up extra spaces and punctuation
        sentence = re.sub(r'\s+', ' ', sentence).strip()
        sentence = re.sub(r'\s+([.,!?;:])', r'\1', sentence)
        
        return sentence

    def _get_transformers_pipeline(self):
        """Lazy load transformers pipeline from local offline model"""
        if hasattr(self, '_pipeline'):
            return self._pipeline
            
        try:
            from transformers import pipeline
            import os
            
            # Path to local model (downloaded via download_models.py)
            model_path = os.path.join(os.path.dirname(_file_), 'models', 'transformers_model')
            
            if not os.path.exists(model_path) or not os.listdir(model_path):
                print(f"[WARNING] Transformer model not found at {model_path}. Fallback to NLTK.")
                return None
                
            print(f"[INFO] Loading Transformer model from {model_path}...")
            self._pipeline = pipeline("summarization", model=model_path, device=-1) # CPU
            return self._pipeline
        except Exception as e:
            print(f"[ERROR] Failed to load Transformer model: {e}")
            return None

    def transformer_summarize(self, text, target_word_count=None, target_percentage=None):
        """Summarize using offline Transformers model"""
        summarizer = self._get_transformers_pipeline()
        
        # If model loading failed, fallback to abstractive
        if not summarizer:
            return self.abstractive_summarize(text, target_word_count, target_percentage)
            
        # Calculate length constraints
        input_len = len(text.split())
        
        if target_word_count:
            target = target_word_count
        elif target_percentage:
            target = int(input_len * target_percentage / 100)
        else:
            target = int(input_len * 0.4)
            
        # Transformers params
        max_len = max(30, int(target * 1.5))
        min_len = max(10, int(target * 0.8))
        
        # Chunk text if too long (simple chunking)
        # BART/Transformer models have a max token limit (usually 1024 or 512).
        # We split long text into smaller chunks, summarize each, and combine.
        # Rough est: 1 token ~= 0.75 words. 1024 tokens ~= 750 words.
        # We'll use a safe limit of 600 words per chunk.
        
        words = text.split()
        if len(words) > 600:
            chunks = []
            for i in range(0, len(words), 600):
                chunk = ' '.join(words[i:i+600])
                chunks.append(chunk)
            
            summaries = []
            for chunk in chunks:
                try:
                    res = summarizer(chunk, max_length=max_len // len(chunks), min_length=min_len // len(chunks), do_sample=False)
                    summaries.append(res[0]['summary_text'])
                except:
                    pass
            return ' '.join(summaries)
        else:
            try:
                res = summarizer(text, max_length=max_len, min_length=min_len, do_sample=False)
                return res[0]['summary_text']
            except Exception as e:
                print(f"Transformer error: {e}")
                return self.abstractive_summarize(text, target_word_count, target_percentage)

    def summarize(self, text, length='medium', mode='extractive', settings=None, custom_percentage=None, engine='nltk'):
        """
        Main summarization method
        
        Args:
            text: Input text to summarize
            length: 'short', 'medium', 'long', or 'custom'
            mode: 'extractive', 'abstractive', or 'both'
            settings: Dictionary with percentage settings
            custom_percentage: Custom percentage for 'custom' length (1-100)
        
        Returns:
            Dictionary with summary info
        """
        if settings is None:
            settings = {
                'short_percentage': 20,
                'medium_percentage': 40,
                'long_percentage': 60
            }
        
        # Determine target percentage
        if length == 'custom' and custom_percentage is not None:
            percentage = max(5, min(95, int(custom_percentage)))
        elif length == 'short':
            percentage = int(settings.get('short_percentage', 20))
        elif length == 'long':
            percentage = int(settings.get('long_percentage', 60))
        else:  # medium
            percentage = int(settings.get('medium_percentage', 40))
        
        # Calculate target word count
        total_words = len(text.split())
        target_words = max(10, int(total_words * percentage / 100))
        
        # Generate summary based on mode
        if engine == 'transformers':
            # Transformers is inherently abstractive
            summary = self.transformer_summarize(text, target_percentage=percentage)
            summary_type = 'transformers'
        elif mode == 'abstractive':
            summary = self.abstractive_summarize(text, target_percentage=percentage)
            summary_type = 'abstractive'
        elif mode == 'both':
            # Use extractive for reliability
            summary = self.extractive_summarize(text, target_percentage=percentage)
            summary_type = 'extractive'
        else:  # extractive
            summary = self.extractive_summarize(text, target_percentage=percentage)
            summary_type = 'extractive'
        
        # Calculate actual word counts
        input_words = total_words
        summary_words = len(summary.split())
        
        # If summary is too long, trim it
        if summary_words > target_words * 1.3:
            # Re-summarize with stricter target
            if mode == 'abstractive':
                summary = self.abstractive_summarize(text, target_word_count=target_words)
            else:
                summary = self.extractive_summarize(text, target_word_count=target_words)
            summary_words = len(summary.split())
        
        return {
            'summary': summary,
            'summary_type': summary_type,
            'summary_length': length,
            'target_percentage': percentage,
            'input_word_count': input_words,
            'summary_word_count': summary_words,
            'actual_percentage': round(summary_words / max(input_words, 1) * 100, 1),
            'compression_ratio': round((1 - summary_words / max(input_words, 1)) * 100, 1)
        }


# Global summarizer instance
summarizer = TextSummarizer()


def summarize_text(text, length='medium', mode='extractive', settings=None, custom_percentage=None, engine='nltk'):
    """
    Convenience function to summarize text
    
    Args:
        text: Input text
        length: 'short', 'medium', 'long', or 'custom'
        mode: 'extractive', 'abstractive', or 'both'
        settings: Optional settings dictionary
        custom_percentage: Custom percentage for 'custom' length
        engine: 'nltk' or 'transformers'
    
    Returns:
        Dictionary with summary results
    """
    return summarizer.summarize(text, length, mode, settings, custom_percentage, engine)