import asyncio

from app.adapters.llm.embedder import Embedder
from app.adapters.llm.ollama_client import OllamaClient


def test_ollama_generate_uses_bounded_runtime_options() -> None:
    captured: dict[str, object] = {}
    client = OllamaClient(
        base_url="http://127.0.0.1:11434",
        keep_alive="30s",
        num_ctx=2048,
        num_predict=512,
        num_gpu=20,
        num_thread=6,
    )

    async def fake_post_json(path: str, payload: dict[str, object]) -> dict[str, object]:
        captured["path"] = path
        captured["payload"] = payload
        return {"response": "grounded answer"}

    client._post_json = fake_post_json  # type: ignore[method-assign]

    answer = asyncio.run(client.generate(prompt="Use citations.", model="phi3:mini", temperature=0.2))

    assert answer == "grounded answer"
    assert captured["path"] == "/api/generate"
    payload = captured["payload"]
    assert isinstance(payload, dict)
    assert payload["keep_alive"] == "30s"
    assert payload["model"] == "phi3:mini"
    options = payload["options"]
    assert isinstance(options, dict)
    assert options == {
        "temperature": 0.2,
        "num_ctx": 2048,
        "num_predict": 512,
        "num_gpu": 20,
        "num_thread": 6,
    }


def test_embedder_batches_ollama_embeddings_to_reduce_memory_pressure() -> None:
    class FakeOllama:
        def __init__(self) -> None:
            self.batches: list[list[str]] = []

        async def is_available(self) -> bool:
            return True

        async def embed(self, texts: list[str], model: str) -> list[list[float]]:
            self.batches.append(texts)
            return [[1.0, 0.0, 0.0] for _ in texts]

    fake = FakeOllama()
    embedder = Embedder(ollama_client=fake, use_ollama=True, batch_size=2)  # type: ignore[arg-type]

    vectors = asyncio.run(embedder.embed(["one", "two", "three", "four", "five"]))

    assert len(vectors) == 5
    assert [len(batch) for batch in fake.batches] == [2, 2, 1]
    assert embedder.last_backend == "ollama"
