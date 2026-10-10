"""Cross-encoder reranker: score (query, chunk) pairs jointly, so relevance is judged on the two texts together.

The dense retriever compares a query vector with chunk vectors computed independently, and BM25 counts shared words;
a cross-encoder reads query and passage side by side and is the usual second stage that sharpens a candidate list. It
is slower per pair, so it only sees the fused top candidates (RERANKER_TOP_K, default 20), never the whole corpus.

    reranker = load_reranker()                       # ONNX model from the pinned Hugging Face revision
    reranker.score("what is a semaphore?", texts)    # -> [float, ...], higher = more relevant (raw logits)

Same runtime as the embedding model (onnxruntime on the CPU provider, one pair per call, fixed thread count, so a pair's
score does not depend on what else is in the list; `tokenizers`; `huggingface_hub`): no new dependency. The model is
`cross-encoder/ms-marco-MiniLM-L-6-v2` (Apache-2.0, trained on MS MARCO passage ranking). It reads at most 512 tokens
per pair; the query is never cut and a longer chunk loses its tail, which is a limit of this model, not of the corpus
(the dense embedding model refuses to truncate; a reranker has a hard 512-token input). The downloaded weights are checked
against the pinned SHA-256 before use; a mismatch is an error (the product pipeline then falls back to hybrid).
"""
import hashlib
from dataclasses import dataclass

import numpy as np

from .embeddings import _fetch


@dataclass(frozen=True)
class RerankerSpec:
    key: str
    repo: str
    revision: str  # pinned commit
    onnx_file: str
    max_tokens: int
    license: str
    weights_sha256: str


RERANKERS = {
    "ms-marco-MiniLM-L-6-v2": RerankerSpec(
        key="ms-marco-MiniLM-L-6-v2",
        repo="cross-encoder/ms-marco-MiniLM-L-6-v2",
        revision="233902d25c440f23af6f7d6e94d2946bac0bee0a",
        onnx_file="onnx/model.onnx",
        max_tokens=512,
        license="apache-2.0",
        weights_sha256="5d3e70fd0c9ff14b9b5169a51e957b7a9c74897afd0a35ce4bd318150c1d4d4a",
    ),
}
DEFAULT_RERANKER = "ms-marco-MiniLM-L-6-v2"


class OnnxCrossEncoder:
    def __init__(self, spec, threads=4):
        import onnxruntime as ort
        from tokenizers import Tokenizer

        self.spec, self.threads = spec, threads
        self.onnx_path = _fetch(spec.repo, spec.onnx_file, spec.revision)
        if (got := self.weights_sha256()) != spec.weights_sha256:  # refuse weights that are not the pinned ones
            raise ValueError(f"reranker weights {self.onnx_path} have SHA-256 {got}, expected {spec.weights_sha256}")
        self.tokenizer = Tokenizer.from_file(_fetch(spec.repo, "tokenizer.json", spec.revision))
        self.tokenizer.enable_truncation(max_length=spec.max_tokens, strategy="only_second")
        self.tokenizer.no_padding()
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = threads
        opts.inter_op_num_threads = 1
        self.session = ort.InferenceSession(self.onnx_path, opts, providers=["CPUExecutionProvider"])
        self.input_names = {i.name for i in self.session.get_inputs()}

    def score(self, query, texts):
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be a non-empty string")
        scores = []
        for text in texts:
            enc = self.tokenizer.encode(query, text)
            feed = {"input_ids": np.array([enc.ids], dtype=np.int64),
                    "attention_mask": np.array([enc.attention_mask], dtype=np.int64),
                    "token_type_ids": np.array([enc.type_ids], dtype=np.int64)}
            logits = self.session.run(None, {k: v for k, v in feed.items() if k in self.input_names})[0]
            scores.append(float(logits.reshape(-1)[0]))
        return scores

    def weights_sha256(self):
        h = hashlib.sha256()
        with open(self.onnx_path, "rb") as f:
            for block in iter(lambda: f.read(1 << 20), b""):
                h.update(block)
        return h.hexdigest()

    def config(self):
        return {"model": self.spec.key, "repo": self.spec.repo, "revision": self.spec.revision,
                "max_tokens": self.spec.max_tokens, "license": self.spec.license, "provider": "CPUExecutionProvider",
                "intra_op_threads": self.threads}


def load_reranker(key=DEFAULT_RERANKER, **kwargs):
    if key not in RERANKERS:
        raise ValueError(f"unknown reranker {key!r}; available: {sorted(RERANKERS)}")
    return OnnxCrossEncoder(RERANKERS[key], **kwargs)
