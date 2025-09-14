"""Grok AI analysis service for token evaluation."""

from typing import Optional, Tuple

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import settings
from ..logging import get_logger

logger = get_logger(__name__)


class GrokAnalysisService:
    """Service for analyzing tokens using Grok AI."""
    
    def __init__(self):
        self._client: Optional[OpenAI] = None
    
    @property
    def client(self) -> Optional[OpenAI]:
        """Get OpenAI client for Grok API."""
        if not self._client and settings.xai_api_key:
            self._client = OpenAI(
                api_key=settings.xai_api_key,
                base_url="https://api.x.ai/v1"
            )
        return self._client
    
    def is_available(self) -> bool:
        """Check if Grok API is configured and available."""
        return bool(settings.xai_api_key)
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def analyze_token(self, token_address: str, token_name: Optional[str] = None) -> Tuple[str, float]:
        """
        Analyze a token using Grok AI.
        
        Returns:
            Tuple of (analysis_text, score) where score is 1-10
        """
        if not self.is_available():
            logger.warning("Grok API not configured", extra={'event': 'grok_not_configured'})
            return "Grok API not configured", 0.0
        
        token_name = token_name or "Unknown"
        
        if settings.dry_run:
            logger.info(
                "DRY RUN: Would analyze token with Grok",
                extra={
                    'token_address': token_address,
                    'token_name': token_name,
                    'event': 'dry_run_grok_analysis'
                }
            )
            return f"DRY RUN: Mock analysis for {token_name}", 5.0
        
        try:
            client = self.client
            if not client:
                return "Grok client not available", 0.0
            
            prompt = self._build_analysis_prompt(token_address, token_name)
            
            response = client.chat.completions.create(
                model=settings.grok_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.7
            )
            
            analysis_text = response.choices[0].message.content
            score = self._extract_score(analysis_text)
            
            logger.info(
                "Token analysis completed",
                extra={
                    'token_address': token_address,
                    'token_name': token_name,
                    'score': score,
                    'analysis_length': len(analysis_text),
                    'event': 'grok_analysis_completed'
                }
            )
            
            return analysis_text, score
            
        except Exception as e:
            logger.error(
                "Grok analysis failed",
                extra={
                    'token_address': token_address,
                    'token_name': token_name,
                    'error': str(e),
                    'event': 'grok_analysis_failed'
                }
            )
            return f"Analysis failed: {str(e)}", 0.0
    
    def _build_analysis_prompt(self, token_address: str, token_name: str) -> str:
        """Build the analysis prompt for Grok."""
        return (
            f"Analyze this new Solana meme coin: Address {token_address}, Name {token_name}. "
            f"Check real-time sentiment on X, hype potential, risk of rug pull, community strength, "
            f"and overall buy recommendation (score 1-10). Be truthful and cite sources if possible. "
            f"Format end with 'Score: X/10'."
        )
    
    def _extract_score(self, analysis_text: str) -> float:
        """Extract numerical score from analysis text."""
        try:
            # Look for "Score: X/10" pattern
            if "Score:" in analysis_text:
                score_part = analysis_text.split("Score:")[-1].strip()
                score_str = score_part.split("/")[0].strip()
                score = float(score_str)
                
                # Ensure score is within valid range
                return max(0.0, min(10.0, score))
            
            # Fallback: look for any number followed by "/10"
            import re
            matches = re.findall(r'(\d+(?:\.\d+)?)/10', analysis_text)
            if matches:
                score = float(matches[-1])  # Take the last match
                return max(0.0, min(10.0, score))
            
            # No score found
            logger.warning(
                "Could not extract score from analysis",
                extra={
                    'analysis_text': analysis_text[:100],
                    'event': 'score_extraction_failed'
                }
            )
            return 0.0
            
        except Exception as e:
            logger.error(
                "Error extracting score",
                extra={
                    'analysis_text': analysis_text[:100],
                    'error': str(e),
                    'event': 'score_extraction_error'
                }
            )
            return 0.0
    
    async def get_quick_sentiment(self, token_address: str) -> float:
        """Get a quick sentiment score without full analysis."""
        if not self.is_available():
            return 5.0  # Neutral score
        
        if settings.dry_run:
            return 6.0  # Slightly positive for testing
        
        try:
            client = self.client
            if not client:
                return 5.0
            
            prompt = (
                f"Quick sentiment analysis for Solana token {token_address}. "
                f"Rate sentiment 1-10 based on recent X activity. Just respond with number."
            )
            
            response = client.chat.completions.create(
                model=settings.grok_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=10,
                temperature=0.3
            )
            
            sentiment_text = response.choices[0].message.content
            score = float(sentiment_text.strip())
            return max(0.0, min(10.0, score))
            
        except Exception as e:
            logger.error(
                "Quick sentiment analysis failed",
                extra={
                    'token_address': token_address,
                    'error': str(e),
                    'event': 'quick_sentiment_failed'
                }
            )
            return 5.0  # Neutral fallback


# Global analysis service instance
analysis_service = GrokAnalysisService()


async def analyze_token(token_address: str, token_name: Optional[str] = None) -> Tuple[str, float]:
    """Analyze a token using Grok AI."""
    return await analysis_service.analyze_token(token_address, token_name)


async def get_quick_sentiment(token_address: str) -> float:
    """Get quick sentiment score for a token."""
    return await analysis_service.get_quick_sentiment(token_address)


def is_analysis_available() -> bool:
    """Check if Grok analysis is available."""
    return analysis_service.is_available()