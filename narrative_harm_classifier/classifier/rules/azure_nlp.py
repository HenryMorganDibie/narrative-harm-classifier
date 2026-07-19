"""
classifier/rules/azure_nlp.py — Azure Text Analytics connector.

Wraps Azure Cognitive Services Text Analytics for:
- Sentiment analysis (used as negative signal amplifier)
- Named Entity Recognition (detects group/identity mentions)
- Key phrase extraction (surface-level harm signal detection)

Falls back gracefully when Azure credentials are not configured (dev mode).
"""

import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class AzureNLPResult:
    sentiment: str                    # positive | negative | neutral | mixed
    sentiment_score_negative: float   # 0.0–1.0
    entities: list[dict]              # [{text, category, confidence}]
    key_phrases: list[str]
    language: str
    is_fallback: bool = False         # True when Azure not configured


class AzureNLPClient:
    """
    Azure Text Analytics client with graceful dev-mode fallback.

    In production: set AZURE_TEXT_ANALYTICS_ENDPOINT and AZURE_TEXT_ANALYTICS_KEY.
    In dev/test: client operates in fallback mode with neutral scores.
    """

    def __init__(self, endpoint: str = "", key: str = ""):
        self.endpoint = endpoint
        self.key = key
        self._client = None

        if endpoint and key:
            try:
                from azure.ai.textanalytics import TextAnalyticsClient
                from azure.core.credentials import AzureKeyCredential
                self._client = TextAnalyticsClient(
                    endpoint=endpoint,
                    credential=AzureKeyCredential(key)
                )
                logger.info("Azure Text Analytics client initialized")
            except ImportError:
                logger.warning("azure-ai-textanalytics not installed — running in fallback mode")
            except Exception as e:
                logger.warning(f"Azure Text Analytics init failed: {e} — running in fallback mode")
        else:
            logger.info("Azure credentials not configured — running in fallback/dev mode")

    @property
    def is_configured(self) -> bool:
        return self._client is not None

    def analyze(self, text: str, language: str = "en") -> AzureNLPResult:
        """Run sentiment + NER + key phrases in a single batched call."""
        if not self.is_configured:
            return self._fallback_result(text)

        try:
            from azure.ai.textanalytics import (
                RecognizeEntitiesAction,
                AnalyzeSentimentAction,
                ExtractKeyPhrasesAction,
            )

            poller = self._client.begin_analyze_actions(
                documents=[{"id": "1", "text": text, "language": language}],
                actions=[
                    AnalyzeSentimentAction(),
                    RecognizeEntitiesAction(),
                    ExtractKeyPhrasesAction(),
                ],
            )
            results = list(poller.result())

            sentiment_result = None
            entity_result = None
            keyphrase_result = None

            for action_result in results[0]:
                if action_result.kind == "SentimentAnalysis" and not action_result.is_error:
                    sentiment_result = action_result
                elif action_result.kind == "EntityRecognition" and not action_result.is_error:
                    entity_result = action_result
                elif action_result.kind == "KeyPhraseExtraction" and not action_result.is_error:
                    keyphrase_result = action_result

            sentiment = "neutral"
            neg_score = 0.0
            if sentiment_result:
                sentiment = sentiment_result.sentiment
                neg_score = sentiment_result.confidence_scores.negative

            entities = []
            if entity_result:
                for ent in entity_result.entities:
                    entities.append({
                        "text": ent.text,
                        "category": ent.category,
                        "confidence": ent.confidence_score,
                    })

            key_phrases = []
            if keyphrase_result:
                key_phrases = list(keyphrase_result.key_phrases)

            return AzureNLPResult(
                sentiment=sentiment,
                sentiment_score_negative=neg_score,
                entities=entities,
                key_phrases=key_phrases,
                language=language,
                is_fallback=False,
            )

        except Exception as e:
            logger.error(f"Azure NLP analysis failed: {e}")
            return self._fallback_result(text)

    def _fallback_result(self, text: str) -> AzureNLPResult:
        """Dev-mode fallback: neutral scores, no entities."""
        return AzureNLPResult(
            sentiment="neutral",
            sentiment_score_negative=0.0,
            entities=[],
            key_phrases=[],
            language="en",
            is_fallback=True,
        )
