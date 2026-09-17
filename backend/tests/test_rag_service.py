import sys
import types
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, call, patch

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

# Keep these unit tests independent from optional runtime dependencies without
# leaking the stubs into other test modules.
sqlmodel = types.ModuleType("sqlmodel")
sqlmodel.Session = object
sqlmodel.select = lambda model: model

indexing_models = types.ModuleType("app.models.indexing")
indexing_models.IndexedDocument = type("IndexedDocument", (), {})

embedding_service = types.ModuleType("app.services.embedding_service")
embedding_service.embed_query = None

chroma_service = types.ModuleType("app.services.chroma_service")
chroma_service.query_collection = None

llm_service = types.ModuleType("app.services.llm_service")
config_service = types.ModuleType("app.services.config_service")
app_config = types.ModuleType("app.config")
app_config.settings = types.SimpleNamespace(rag_context_max_chars=12000)

with patch.dict(
    sys.modules,
    {
        "sqlmodel": sqlmodel,
        "app.models.indexing": indexing_models,
        "app.config": app_config,
        "app.services.embedding_service": embedding_service,
        "app.services.chroma_service": chroma_service,
        "app.services.llm_service": llm_service,
        "app.services.config_service": config_service,
    },
):
    from app.services import rag_service

sys.path.remove(str(BACKEND_DIR))


def make_chunk(document_id: int, title: str, text: str, distance: float = 0.1) -> dict:
    return {
        "id": f"{document_id}-0",
        "document_id": document_id,
        "document_title": title,
        "text": text,
        "distance": distance,
        "chunk_index": 0,
    }


def empty_session() -> Mock:
    session = Mock()
    session.exec.return_value.all.return_value = []
    return session


class PrepareContextTests(unittest.TestCase):
    def test_retrieval_default_matches_ten_chunk_context_budget(self):
        self.assertTrue(hasattr(rag_service, "DEFAULT_RAG_N_RESULTS"))
        self.assertEqual(rag_service.DEFAULT_RAG_N_RESULTS, 10)

    def test_context_budget_never_includes_a_partial_chunk(self):
        chunks = [
            make_chunk(1, "First", "complete first excerpt"),
            make_chunk(2, "Second", "second excerpt must not be cut"),
        ]
        first_context = rag_service._build_context(chunks[:1])

        self.assertTrue(hasattr(rag_service, "_prepare_context"))
        context, selected = rag_service._prepare_context(
            "question", chunks, max_context_chars=len(first_context) + 1
        )

        self.assertEqual(context, first_context)
        self.assertEqual(selected, chunks[:1])
        self.assertNotIn("second excerpt", context)

    def test_budget_drops_are_logged_without_sensitive_values(self):
        secret_query = "private query value"
        secret_text = "private document contents"
        chunks = [make_chunk(9, "Private title", secret_text)]

        with patch.object(rag_service.logger, "info") as info:
            context, selected = rag_service._prepare_context(
                secret_query, chunks, max_context_chars=1
            )

        self.assertEqual((context, selected), ("", []))
        info.assert_called_once_with(
            "RAG context budget excluded chunks",
            extra={
                "event": "rag_context_budget_exceeded",
                "retrieved_chunk_count": 1,
                "selected_chunk_count": 0,
                "dropped_chunk_count": 1,
                "context_budget_chars": 1,
            },
        )
        logged_values = repr(info.call_args)
        self.assertNotIn(secret_query, logged_values)
        self.assertNotIn(secret_text, logged_values)
        self.assertNotIn("Private title", logged_values)

    def test_exact_normalized_title_match_is_prioritized(self):
        chunks = [
            make_chunk(1, "Similar document", "semantic result"),
            make_chunk(2, "Annual   Report 2024.PDF", "explicit title result"),
        ]
        one_chunk_budget = max(
            len(rag_service._build_context([chunk])) for chunk in chunks
        )

        context, selected = rag_service._prepare_context(
            "Summarize annual report 2024.pdf please",
            chunks,
            max_context_chars=one_chunk_budget,
        )

        self.assertEqual(selected, [chunks[1]])
        self.assertIn("explicit title result", context)
        self.assertNotIn("semantic result", context)

    def test_longest_overlapping_title_match_is_prioritized(self):
        chunks = [
            make_chunk(1, "Annual Report", "short title result"),
            make_chunk(2, "Annual Report.pdf", "exact title result"),
        ]
        one_chunk_budget = max(
            len(rag_service._build_context([chunk])) for chunk in chunks
        )

        context, selected = rag_service._prepare_context(
            "Summarize Annual Report.pdf",
            chunks,
            max_context_chars=one_chunk_budget,
        )

        self.assertEqual(selected, [chunks[1]])
        self.assertIn("exact title result", context)
        self.assertNotIn("short title result", context)

    def test_exact_document_id_match_is_prioritized_without_partial_matches(self):
        chunks = [
            make_chunk(142, "Semantic winner", "wrong id result"),
            make_chunk(42, "Requested document", "exact id result"),
        ]
        one_chunk_budget = max(
            len(rag_service._build_context([chunk])) for chunk in chunks
        )

        context, selected = rag_service._prepare_context(
            "What does document ID 42 say?",
            chunks,
            max_context_chars=one_chunk_budget,
        )

        self.assertEqual(selected, [chunks[1]])
        self.assertIn("exact id result", context)
        self.assertNotIn("wrong id result", context)

    def test_colon_document_id_marker_is_recognized(self):
        self.assertTrue(rag_service._query_mentions_document_id("use id:42", 42))
        self.assertFalse(rag_service._query_mentions_document_id("use id:42", 142))

    def test_explicit_retrieval_keeps_first_chunk_when_semantic_results_duplicate_it(
        self,
    ):
        targeted = make_chunk(42, "Requested", "targeted contents", distance=0.2)
        semantic_duplicate = {
            **targeted,
            "text": "semantic duplicate",
            "distance": 0.1,
        }
        semantic_other = make_chunk(1, "Other", "other contents")
        session = Mock()
        session.exec.return_value.all.return_value = [
            types.SimpleNamespace(paperless_id=42, title="Requested")
        ]
        query = Mock(side_effect=[[targeted], [semantic_duplicate, semantic_other]])

        with patch.object(rag_service, "query_collection", query):
            chunks = rag_service._retrieve_chunks(
                "Use document ID 42", [0.1], session, n_results=10
            )

        self.assertEqual(chunks, [targeted, semantic_other])


class AnswerPathTests(unittest.IsolatedAsyncioTestCase):
    async def test_search_retrieves_exact_id_missing_from_semantic_results(self):
        semantic_chunk = make_chunk(1, "Semantic result", "unrelated")
        exact_chunk = make_chunk(42, "Requested document", "requested contents")
        indexed_documents = [
            types.SimpleNamespace(paperless_id=1, title="Semantic result"),
            types.SimpleNamespace(paperless_id=42, title="Requested document"),
        ]
        session = Mock()
        session.exec.return_value.all.return_value = indexed_documents
        config = {
            "provider": "test",
            "base_url": "",
            "api_key": "",
            "model": "configured",
        }

        def retrieve(_embedding, n_results, document_ids=None):
            return [exact_chunk] if document_ids == [42] else [semantic_chunk]

        complete = AsyncMock(return_value="answer")
        with (
            patch.object(rag_service, "_get_embedding_config", return_value=config),
            patch.object(rag_service, "_get_llm_config", return_value=config),
            patch.object(rag_service, "embed_query", AsyncMock(return_value=[0.1])),
            patch.object(
                rag_service, "query_collection", Mock(side_effect=retrieve)
            ) as query,
            patch.object(rag_service.llm_service, "complete", complete, create=True),
        ):
            result = await rag_service.search_and_answer(
                "What does document ID 42 say?", session
            )

        self.assertEqual(result["sources"][0]["document_id"], 42)
        self.assertIn("requested contents", complete.await_args.args[0])
        self.assertIn(
            call([0.1], n_results=10, document_ids=[42]),
            query.call_args_list,
        )

    async def test_stream_retrieves_exact_title_missing_from_semantic_results(self):
        semantic_chunk = make_chunk(1, "Semantic result", "unrelated")
        exact_chunk = make_chunk(42, "Annual   Report.PDF", "requested contents")
        indexed_documents = [
            types.SimpleNamespace(paperless_id=1, title="Semantic result"),
            types.SimpleNamespace(paperless_id=42, title="Annual   Report.PDF"),
        ]
        session = Mock()
        session.exec.return_value.all.return_value = indexed_documents
        config = {
            "provider": "test",
            "base_url": "",
            "api_key": "",
            "model": "configured",
        }

        def retrieve(_embedding, n_results, document_ids=None):
            return [exact_chunk] if document_ids == [42] else [semantic_chunk]

        prompts = []

        async def stream_complete(prompt, **_kwargs):
            prompts.append(prompt)
            yield "answer"

        with (
            patch.object(rag_service, "_get_embedding_config", return_value=config),
            patch.object(rag_service, "_get_llm_config", return_value=config),
            patch.object(rag_service, "embed_query", AsyncMock(return_value=[0.1])),
            patch.object(
                rag_service, "query_collection", Mock(side_effect=retrieve)
            ) as query,
            patch.object(
                rag_service.llm_service,
                "stream_complete",
                stream_complete,
                create=True,
            ),
        ):
            streamed = [
                token
                async for token in rag_service.stream_answer(
                    "Summarize annual report.pdf", session
                )
            ]

        self.assertEqual(streamed, ["answer"])
        self.assertIn("requested contents", prompts[0])
        self.assertIn(
            call([0.1], n_results=10, document_ids=[42]),
            query.call_args_list,
        )

    async def test_search_skips_llm_when_no_complete_chunk_fits(self):
        chunks = [make_chunk(1, "Document", "content")]
        config = {
            "provider": "test",
            "base_url": "",
            "api_key": "",
            "model": "configured",
        }
        complete = AsyncMock(return_value="must not be used")

        with (
            patch.object(rag_service, "_get_embedding_config", return_value=config),
            patch.object(rag_service, "_get_llm_config", return_value=config),
            patch.object(rag_service, "embed_query", AsyncMock(return_value=[0.1])),
            patch.object(rag_service, "query_collection", Mock(return_value=chunks)),
            patch.object(rag_service.llm_service, "complete", complete, create=True),
            patch.object(rag_service.settings, "rag_context_max_chars", 1),
        ):
            result = await rag_service.search_and_answer("question", empty_session())

        self.assertEqual(
            result,
            {
                "answer": "Relevant documents were found, but none fit within the configured context budget.",
                "sources": [],
                "query": "question",
            },
        )
        complete.assert_not_awaited()

    async def test_stream_skips_llm_when_no_complete_chunk_fits(self):
        chunks = [make_chunk(1, "Document", "content")]
        config = {
            "provider": "test",
            "base_url": "",
            "api_key": "",
            "model": "configured",
        }

        async def unused_stream(*args, **kwargs):
            yield "must not be used"

        stream_complete = Mock(side_effect=unused_stream)

        with (
            patch.object(rag_service, "_get_embedding_config", return_value=config),
            patch.object(rag_service, "_get_llm_config", return_value=config),
            patch.object(rag_service, "embed_query", AsyncMock(return_value=[0.1])),
            patch.object(rag_service, "query_collection", Mock(return_value=chunks)),
            patch.object(
                rag_service.llm_service,
                "stream_complete",
                stream_complete,
                create=True,
            ),
            patch.object(rag_service.settings, "rag_context_max_chars", 1),
        ):
            streamed = [
                token
                async for token in rag_service.stream_answer(
                    "question", empty_session()
                )
            ]

        self.assertEqual(
            streamed,
            [
                "Relevant documents were found, but none fit within the configured context budget."
            ],
        )
        stream_complete.assert_not_called()

    async def test_search_sources_only_include_chunks_used_in_context(self):
        chunks = [
            make_chunk(1, "Included", "fits"),
            make_chunk(2, "Excluded", "does not fit in the remaining budget"),
        ]
        budget = len(rag_service._build_context(chunks[:1]))
        complete = AsyncMock(return_value="answer")

        with (
            patch.object(
                rag_service,
                "_get_embedding_config",
                return_value={
                    "provider": "test",
                    "base_url": "",
                    "api_key": "",
                    "model": "embedding",
                },
            ),
            patch.object(
                rag_service,
                "_get_llm_config",
                return_value={
                    "provider": "test",
                    "base_url": "",
                    "api_key": "",
                    "model": "llm",
                },
            ),
            patch.object(rag_service, "embed_query", AsyncMock(return_value=[0.1])),
            patch.object(rag_service, "query_collection", Mock(return_value=chunks)),
            patch.object(rag_service.llm_service, "complete", complete, create=True),
            patch.object(rag_service.settings, "rag_context_max_chars", budget),
        ):
            result = await rag_service.search_and_answer("question", empty_session())

        self.assertEqual([source["document_id"] for source in result["sources"]], [1])
        prompt = complete.await_args.args[0]
        self.assertIn("fits", prompt)
        self.assertNotIn("does not fit", prompt)

    async def test_search_and_stream_use_the_same_context_preparation(self):
        chunks = [make_chunk(7, "Shared", "shared context")]
        config = {
            "provider": "test",
            "base_url": "",
            "api_key": "",
            "model": "configured",
        }
        prepare_context = Mock(return_value=("prepared context", chunks))

        async def stream_complete(*args, **kwargs):
            yield "token"

        with (
            patch.object(rag_service, "_get_embedding_config", return_value=config),
            patch.object(rag_service, "_get_llm_config", return_value=config),
            patch.object(rag_service, "embed_query", AsyncMock(return_value=[0.1])),
            patch.object(rag_service, "query_collection", Mock(return_value=chunks)),
            patch.object(rag_service, "_prepare_context", prepare_context),
            patch.object(
                rag_service.llm_service,
                "complete",
                AsyncMock(return_value="answer"),
                create=True,
            ),
            patch.object(
                rag_service.llm_service,
                "stream_complete",
                stream_complete,
                create=True,
            ),
        ):
            await rag_service.search_and_answer("same query", empty_session())
            streamed = [
                token
                async for token in rag_service.stream_answer(
                    "same query", empty_session()
                )
            ]

        self.assertEqual(streamed, ["token"])
        self.assertEqual(prepare_context.call_count, 2)
        self.assertEqual(
            prepare_context.call_args_list[0], prepare_context.call_args_list[1]
        )

    async def test_context_budget_comes_from_application_settings(self):
        self.assertTrue(hasattr(rag_service, "settings"))
        chunks = [make_chunk(1, "Document", "content")]
        config = {
            "provider": "test",
            "base_url": "",
            "api_key": "",
            "model": "configured",
        }
        prepare_context = Mock(return_value=("context", chunks))

        with (
            patch.object(rag_service.settings, "rag_context_max_chars", 4321),
            patch.object(rag_service, "_get_embedding_config", return_value=config),
            patch.object(rag_service, "_get_llm_config", return_value=config),
            patch.object(rag_service, "embed_query", AsyncMock(return_value=[0.1])),
            patch.object(rag_service, "query_collection", Mock(return_value=chunks)),
            patch.object(rag_service, "_prepare_context", prepare_context),
            patch.object(
                rag_service.llm_service,
                "complete",
                AsyncMock(return_value="answer"),
                create=True,
            ),
        ):
            await rag_service.search_and_answer("question", empty_session())

        prepare_context.assert_called_once_with(
            "question", chunks, max_context_chars=4321
        )

    async def test_search_logs_never_include_the_query(self):
        secret_query = "private query value"
        chunks = [make_chunk(1, "Document", "content")]
        config = {
            "provider": "test",
            "base_url": "",
            "api_key": "",
            "model": "configured",
        }

        with (
            patch.object(rag_service, "_get_embedding_config", return_value=config),
            patch.object(rag_service, "_get_llm_config", return_value=config),
            patch.object(rag_service, "embed_query", AsyncMock(return_value=[0.1])),
            patch.object(rag_service, "query_collection", Mock(return_value=chunks)),
            patch.object(
                rag_service.llm_service,
                "complete",
                AsyncMock(return_value="answer"),
                create=True,
            ),
            patch.object(rag_service.logger, "info") as info,
        ):
            await rag_service.search_and_answer(secret_query, empty_session())

        self.assertNotIn(secret_query, repr(info.call_args_list))


if __name__ == "__main__":
    unittest.main()
