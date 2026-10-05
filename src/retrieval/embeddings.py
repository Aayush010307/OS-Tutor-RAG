"""Embedding models behind one small interface.

Retrieval code only sees `EmbeddingModel.embed_documents` / `embed_query` / `dim`. Model-specific details
(weights, revision, prefixes, pooling, input limit) live in a `ModelSpec`; adding a model means adding a
spec to `MODELS` (and, for a non-ONNX backend, another `EmbeddingModel` subclass).
"""
import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ModelSpec:
    key: str
    repo: str
    revision: str  # pinned commit: weights and tokenizer cannot change underneath the index
    onnx_file: str
    dim: int
    max_tokens: int  # longest input embedded without truncation; longer inputs are refused
    document_prefix: str
    query_prefix: str
    license: str


MODELS = {
    "nomic-embed-text-v1.5": ModelSpec(
        key="nomic-embed-text-v1.5",
        repo="nomic-ai/nomic-embed-text-v1.5",
        revision="e9b6763023c676ca8431644204f50c2b100d9aab",
        onnx_file="onnx/model.onnx",  # fp32 export shipped in the official repo
        dim=768,
        # config.json: max_position_embeddings=2048 (trained context), rotary_scaling_factor unset.
        # n_positions=8192 needs rotary scaling this ONNX graph does not apply, so 2048 is the safe limit.
        max_tokens=2048,
        document_prefix="search_document: ",
        query_prefix="search_query: ",
        license="apache-2.0",
    ),
}
DEFAULT_MODEL = "nomic-embed-text-v1.5"


def _check(text):
    if not isinstance(text, str) or not text.strip():
        raise ValueError(f"embedding input must be a non-empty string, got {text!r:.40}")
    return text


class EmbeddingModel(ABC):
    spec: ModelSpec

    @property
    def dim(self):
        return self.spec.dim

    @abstractmethod
    def _embed(self, texts):
        """Embed already-prefixed texts; returns float32 array (n, dim), L2-normalised."""

    def embed_documents(self, texts):
        if isinstance(texts, str):
            raise ValueError("embed_documents expects a list of strings")
        texts = [self.spec.document_prefix + _check(t) for t in texts]
        return self._embed(texts) if texts else np.empty((0, self.dim), dtype=np.float32)

    def embed_query(self, text):
        return self._embed([self.spec.query_prefix + _check(text)])[0]


class OnnxEmbeddingModel(EmbeddingModel):
    """BERT-style encoder exported to ONNX: mean pooling over tokens, then L2 normalisation.

    Runs on the CPU provider, one text per call (no padding), with a fixed thread count, so a text's
    vector does not depend on what else is in the batch or on hardware-specific accelerator kernels.
    """

    def __init__(self, spec, threads=4):
        import onnxruntime as ort
        from tokenizers import Tokenizer

        self.spec = spec
        self.threads = threads
        self.onnx_path = _fetch(spec.repo, spec.onnx_file, spec.revision)
        self.tokenizer = Tokenizer.from_file(_fetch(spec.repo, "tokenizer.json", spec.revision))
        self.tokenizer.no_truncation()  # never cut content; overlong input is an error instead
        self.tokenizer.no_padding()
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = threads
        opts.inter_op_num_threads = 1
        self.session = ort.InferenceSession(self.onnx_path, opts, providers=["CPUExecutionProvider"])
        self.input_names = {i.name for i in self.session.get_inputs()}

    def token_count(self, text, document=True):
        prefix = self.spec.document_prefix if document else self.spec.query_prefix
        return len(self.tokenizer.encode(prefix + text).ids)

    def _embed(self, texts):
        out = np.empty((len(texts), self.dim), dtype=np.float32)
        for i, text in enumerate(texts):
            ids = self.tokenizer.encode(text).ids
            if len(ids) > self.spec.max_tokens:
                raise ValueError(f"input is {len(ids)} tokens, above the {self.spec.max_tokens}-token limit of "
                                 f"{self.spec.key}; refusing to truncate")
            feed = {"input_ids": np.array([ids], dtype=np.int64),
                    "attention_mask": np.ones((1, len(ids)), dtype=np.int64),
                    "token_type_ids": np.zeros((1, len(ids)), dtype=np.int64)}
            hidden = self.session.run(None, {k: v for k, v in feed.items() if k in self.input_names})[0][0]
            vec = hidden.mean(axis=0)  # every position is a real token (no padding), so a plain mean
            out[i] = vec / np.linalg.norm(vec)
        return out

    def weights_sha256(self):
        h = hashlib.sha256()
        with open(self.onnx_path, "rb") as f:
            for block in iter(lambda: f.read(1 << 20), b""):
                h.update(block)
        return h.hexdigest()


def _fetch(repo, filename, revision):
    """Use the local Hugging Face cache when the pinned revision is there; download it otherwise."""
    from huggingface_hub import hf_hub_download
    from huggingface_hub.errors import LocalEntryNotFoundError

    try:
        return hf_hub_download(repo, filename, revision=revision, local_files_only=True)
    except LocalEntryNotFoundError:
        return hf_hub_download(repo, filename, revision=revision)


def load_model(key=DEFAULT_MODEL, **kwargs):
    if key not in MODELS:
        raise ValueError(f"unknown embedding model {key!r}; available: {sorted(MODELS)}")
    return OnnxEmbeddingModel(MODELS[key], **kwargs)
