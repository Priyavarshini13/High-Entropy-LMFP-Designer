"""
Latent Semantic Analysis (LSA / TruncatedSVD) retrieval module.

Computes offline latent semantic representations using scikit-learn
TF-IDF vectorization and TruncatedSVD dimensionality reduction.

Note: This is classical linear subspace latent semantic retrieval,
NOT a neural dense embedding or transformer encoder. Operates completely
offline with deterministic reproducible indexing.
"""

import math
from typing import Dict, List, Optional, Tuple
import numpy as np

try:
    from sklearn.decomposition import TruncatedSVD
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.preprocessing import normalize
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

from copilot.models import EvidencePassage


class LSASemanticRetriever:
    """Offline Latent Semantic Analysis (LSA) index for scientific literature passages."""

    def __init__(self, n_components: int = 48):
        self.n_components = n_components
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.svd: Optional[TruncatedSVD] = None
        self.doc_vectors: Optional[np.ndarray] = None  # Normalized (N, d) matrix
        self.is_fitted: bool = False

    def fit(self, passages: List[EvidencePassage]) -> bool:
        """Fit TF-IDF and TruncatedSVD on passage text corpus."""
        if not SKLEARN_AVAILABLE or not passages:
            self.is_fitted = False
            return False

        corpus = [p.text for p in passages]
        # Fit TF-IDF with scientific character preservation
        self.vectorizer = TfidfVectorizer(
            max_features=8000,
            sublinear_tf=True,
            ngram_range=(1, 2),
            token_pattern=r"(?u)\b[\w\d\.\-\/\+\(\)°]{2,}\b",
            stop_words="english",
        )
        try:
            X_tfidf = self.vectorizer.fit_transform(corpus)
            n_features = X_tfidf.shape[1]
            actual_components = min(self.n_components, n_features - 1, len(passages) - 1)
            if actual_components < 2:
                self.is_fitted = False
                return False

            self.svd = TruncatedSVD(n_components=actual_components, random_state=42)
            X_lsa = self.svd.fit_transform(X_tfidf)
            self.doc_vectors = normalize(X_lsa, norm="l2")
            self.is_fitted = True
            return True
        except Exception as exc:
            print(f"[LSA Retriever] Warning during LSA fit: {exc}")
            self.is_fitted = False
            return False

    def get_lsa_scores(self, query: str, min_score: float = 0.05) -> Dict[int, float]:
        """Compute cosine similarity between query and passage vectors in LSA subspace."""
        if not self.is_fitted or self.vectorizer is None or self.svd is None or self.doc_vectors is None:
            return {}

        try:
            q_tfidf = self.vectorizer.transform([query])
            if q_tfidf.nnz == 0:
                return {}
            q_lsa = self.svd.transform(q_tfidf)
            q_norm = normalize(q_lsa, norm="l2")

            sims = (self.doc_vectors @ q_norm.T).flatten()
            scores = {}
            for doc_idx, s in enumerate(sims):
                if s >= min_score and not np.isnan(s):
                    scores[doc_idx] = float(round(s, 4))
            return scores
        except Exception:
            return {}
