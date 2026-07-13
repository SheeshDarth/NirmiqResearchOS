import asyncio

from app.adapters.llm.embedder import Embedder
from app.adapters.llm.generator import Generator
from app.adapters.llm.ollama_client import OllamaClient
from scripts.runtime_benchmark import assess_runtime_budgets


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


def test_generator_uses_installed_instruct_model_when_default_is_missing() -> None:
    class FakeOllama:
        def __init__(self) -> None:
            self.generated_with: str | None = None

        async def is_available(self) -> bool:
            return True

        async def list_models(self) -> list[str]:
            return ["nomic-embed-text:latest", "qwen3.5:4b", "mistral:7b-instruct-q4_K_M"]

        async def generate(self, prompt: str, model: str, temperature: float = 0.0) -> str:
            self.generated_with = model
            return "Grounded answer. [1]"

    fake = FakeOllama()
    generator = Generator(ollama_client=fake, default_model="phi3:mini", use_ollama=True)  # type: ignore[arg-type]

    answer = asyncio.run(generator.answer(prompt="Answer with citations.", temperature=0.1))

    assert answer == "Grounded answer. [1]"
    assert fake.generated_with == "mistral:7b-instruct-q4_K_M"
    assert generator.last_backend == "ollama"
    assert generator.last_model_requested == "phi3:mini"
    assert generator.last_model_used == "mistral:7b-instruct-q4_K_M"
    assert generator.last_model_fallback is True


def test_generator_prefers_small_phi_model_before_installed_seven_b_model() -> None:
    class FakeOllama:
        def __init__(self) -> None:
            self.generated_with: str | None = None

        async def is_available(self) -> bool:
            return True

        async def list_models(self) -> list[str]:
            return ["mistral:7b-instruct-q4_K_M", "phi3:mini"]

        async def generate(self, prompt: str, model: str, temperature: float = 0.0) -> str:
            self.generated_with = model
            return "Grounded answer. [1]"

    fake = FakeOllama()
    generator = Generator(ollama_client=fake, default_model="missing:small", use_ollama=True)  # type: ignore[arg-type]

    answer = asyncio.run(generator.answer(prompt="Answer with citations.", temperature=0.1))

    assert answer == "Grounded answer. [1]"
    assert fake.generated_with == "phi3:mini"
    assert generator.last_model_used == "phi3:mini"
    assert generator.last_model_fallback is True


def test_ollama_client_serializes_generation_and_embedding_operations() -> None:
    client = OllamaClient(base_url="http://127.0.0.1:11434")
    active_operations = 0
    peak_operations = 0

    async def fake_post_json(path: str, payload: dict[str, object]) -> dict[str, object]:
        nonlocal active_operations, peak_operations
        active_operations += 1
        peak_operations = max(peak_operations, active_operations)
        await asyncio.sleep(0.01)
        active_operations -= 1
        if path == "/api/generate":
            return {"response": "grounded answer"}
        return {"embeddings": [[1.0, 0.0]]}

    client._post_json = fake_post_json  # type: ignore[method-assign]

    async def exercise_client() -> tuple[str, list[list[float]]]:
        generated, embeddings = await asyncio.gather(
            client.generate(prompt="Use evidence.", model="phi3:mini"),
            client.embed(texts=["source text"], model="nomic-embed-text"),
        )
        return generated, embeddings

    answer, vectors = asyncio.run(exercise_client())

    assert answer == "grounded answer"
    assert vectors == [[1.0, 0.0]]
    assert peak_operations == 1


def test_cancelled_ollama_waiter_does_not_leak_operation_capacity() -> None:
    client = OllamaClient(base_url="http://127.0.0.1:11434")
    first_started = asyncio.Event()
    release_first = asyncio.Event()

    async def fake_post_json(path: str, payload: dict[str, object]) -> dict[str, object]:
        if not first_started.is_set():
            first_started.set()
            await release_first.wait()
        return {"response": "grounded answer"}

    client._post_json = fake_post_json  # type: ignore[method-assign]

    async def exercise_cancellation() -> str:
        first = asyncio.create_task(client.generate(prompt="first", model="phi3:mini"))
        await first_started.wait()
        waiting = asyncio.create_task(client.generate(prompt="cancel me", model="phi3:mini"))
        await asyncio.sleep(0)
        waiting.cancel()
        try:
            await waiting
        except asyncio.CancelledError:
            pass
        release_first.set()
        await first
        return await client.generate(prompt="after cancellation", model="phi3:mini")

    answer = asyncio.run(exercise_cancellation())

    assert answer == "grounded answer"


def test_runtime_budget_assessment_passes_measured_balanced_values() -> None:
    assessment = assess_runtime_budgets(
        {
            "runtime": {"profile": "balanced"},
            "readiness_warm_latency": {"p95_ms": 26.72},
            "query_warm_latency": {"median_ms": 5_182.0},
            "api_rss_after_bytes": 147 * 1024**2,
            "gpu_after": [{"memory_used_mib": 2474}],
        }
    )

    assert assessment["status"] == "pass"
    assert assessment["enforcement"] == "advisory"
    assert all(check["passed"] for check in assessment["checks"])


def test_runtime_budget_assessment_warns_without_failing_execution() -> None:
    assessment = assess_runtime_budgets(
        {
            "runtime": {"profile": "low_memory"},
            "readiness_warm_latency": {"p95_ms": 900.0},
            "query_warm_latency": {"median_ms": 50_000.0},
            "api_rss_after_bytes": 1200 * 1024**2,
        }
    )

    assert assessment["status"] == "warn"
    assert assessment["enforcement"] == "advisory"
    assert any(not check["passed"] for check in assessment["checks"])
