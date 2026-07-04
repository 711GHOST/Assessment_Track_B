"""Unit tests for the RAG building blocks (no HTTP layer)."""
from app.rag.chunking import chunk_text
from app.rag.embeddings import HashingEmbedder
from app.rag.reranker import LexicalReranker
from app.rag.vectorstore import ChunkHit, InMemoryVectorStore


def test_chunk_short_text_single_chunk():
    chunks = chunk_text("One sentence only.", chunk_size=200, overlap=40)
    assert chunks == ["One sentence only."]


def test_chunk_long_text_has_overlap():
    sentences = " ".join(f"Sentence number {i} talks about topic {i}." for i in range(120))
    chunks = chunk_text(sentences, chunk_size=60, overlap=15)
    assert len(chunks) > 1
    # Consecutive chunks share trailing/leading words (the overlap seed).
    first_words = set(chunks[0].split())
    second_words = set(chunks[1].split())
    assert first_words & second_words


def test_chunk_empty_text():
    assert chunk_text("   ") == []


def test_hashing_embedder_is_deterministic_and_normalized():
    embedder = HashingEmbedder()
    first, second = embedder.embed(["hello world", "hello world"])
    assert first == second
    assert len(first) == embedder.dim
    norm = sum(v * v for v in first) ** 0.5
    assert abs(norm - 1.0) < 1e-6


def test_vector_search_ranks_similar_text_higher():
    embedder = HashingEmbedder()
    store = InMemoryVectorStore()
    chunks = [
        "Cats and dogs are common household pets that people love.",
        "Quantum entanglement describes correlations between particles.",
    ]
    store.upsert("user1", "doc1", "Mixed", chunks, embedder.embed(chunks))

    query_vec = embedder.embed(["Which animals are popular pets like cats and dogs?"])[0]
    hits = store.search("user1", query_vec, top_k=2)
    assert hits[0].text.startswith("Cats and dogs")


def test_vector_store_isolates_users():
    embedder = HashingEmbedder()
    store = InMemoryVectorStore()
    chunks = ["Secret financial report about quarterly revenue."]
    store.upsert("owner", "doc1", "Secret", chunks, embedder.embed(chunks))

    query_vec = embedder.embed(["quarterly revenue"])[0]
    assert store.search("intruder", query_vec, top_k=5) == []
    assert len(store.search("owner", query_vec, top_k=5)) == 1


def test_lexical_reranker_prefers_keyword_overlap():
    hits = [
        ChunkHit(text="The weather in Paris is mild in spring.", score=0.5,
                 document_id="d1", chunk_index=0, document_title="Weather"),
        ChunkHit(text="LangChain provides chains, agents, and memory.", score=0.5,
                 document_id="d2", chunk_index=0, document_title="LangChain"),
    ]
    ranked = LexicalReranker().rerank("What does LangChain provide?", hits)
    assert ranked[0].document_id == "d2"
