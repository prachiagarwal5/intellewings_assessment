import logging
from transformers import pipeline

logger = logging.getLogger(__name__)

class SentimentAnalyzer:
    def __init__(self):
        try:
            logger.info("Loading sentiment analysis model...")
            self.sentiment_pipeline = pipeline(
                "sentiment-analysis",
                model="distilbert-base-uncased-finetuned-sst-2-english",
                max_length=512,
                truncation=True
            )
            logger.info("Sentiment analysis model loaded successfully")
            
            # Keywords that indicate negative sentiment in SEBI context
            self.negative_keywords = [
                "fraud", "penalty", "violation", "illegal", "misleading",
                "contravention", "breach", "improper", "manipulation", 
                "non-compliance", "fine", "cease and desist", "restrain",
                "suspend", "debar", "disgorgement", "ban", "prohibited",
                "unprofessional", "unfair", "warning", "reprimand", "sanction"
            ]
        except Exception as e:
            logger.error(f"Error loading sentiment model: {str(e)}")
            raise
    
    def analyze_sentiment(self, text):
        """Analyze sentiment of text using transformer model"""
        try:
            result = self.sentiment_pipeline(text)[0]
            label = result["label"]
            score = result["score"]
            
            # Map to required format
            if label == "NEGATIVE" and score > 0.6:
                return "Negative"
            return "Positive" if label == "POSITIVE" and score > 0.7 else "Neutral"
        except Exception as e:
            logger.error(f"Error in sentiment analysis: {str(e)}")
            return "Neutral"  # Default to neutral on error
    
    def analyze_entity_sentiment(self, entity_context):
        """Analyze sentiment specifically for entities in regulatory context"""
        # First check for regulatory negative keywords
        if any(keyword in entity_context.lower() for keyword in self.negative_keywords):
            return "Negative"
        
        # If no clear negative keywords, use the model
        return self.analyze_sentiment(entity_context)