"""Run with python -m unittest discover -s rag-service -p test_*.py."""
import unittest
from unittest.mock import patch
from langchain_core.documents import Document
import retrieval


def doc(key, text):
    return Document(id=key, page_content=text, metadata={'chunk_id': key})


class RetrievalTests(unittest.TestCase):
    def test_normalize_identifiers(self):
        text = retrieval.normalize('PaymentService HTTPClient idempotency_key')
        self.assertIn('PaymentService', text)
        self.assertIn('Payment Service HTTP Client idempotency key', text)

    def test_exact_identifier_beats_semantic_only(self):
        semantic = doc('semantic', 'payment processing')
        exact = doc('exact', 'class PaymentService {}')
        result = retrieval.fuse([semantic], [exact], 'Explain PaymentService', 5)
        self.assertEqual(result[0].id, 'exact')

    def test_identifier_boundaries(self):
        self.assertEqual(retrieval.literal_matches('PaymentServiceFactory', ['paymentservice']), 0)
        self.assertEqual(retrieval.literal_matches('PaymentService.Run()', ['paymentservice']), 1)

    def test_quoted_phrase(self):
        self.assertEqual(retrieval.exact_terms('explain "duplicate payment"'), ['duplicate payment'])

    def test_fusion_deduplicates_and_rewards_both(self):
        a, b, c = doc('a', 'one'), doc('b', 'two'), doc('c', 'three')
        result = retrieval.fuse([a, b], [c, b], 'payment rules', 5)
        self.assertEqual([d.id for d in result], ['b', 'a', 'c'])

    @patch.dict('os.environ', {'SEARCH_MODE': 'hybrid'})
    @patch('retrieval.vector_store', side_effect=RuntimeError('embedding offline'))
    @patch('retrieval.keyword_search')
    def test_keyword_fallback(self, keyword, vector):
        keyword.return_value = [doc('a', 'PaymentService')]
        with self.assertLogs('retrieval', level='WARNING'):
            self.assertEqual(retrieval.retrieve('PaymentService')[0].id, 'a')

    @patch.dict('os.environ', {'SEARCH_MODE': 'hybrid'})
    @patch('retrieval.vector_store')
    @patch('retrieval.keyword_search', side_effect=RuntimeError('database offline'))
    def test_vector_fallback(self, keyword, vector):
        vector.return_value.similarity_search.return_value = [doc('a', 'payment')]
        with self.assertLogs('retrieval', level='WARNING'):
            self.assertEqual(retrieval.retrieve('payment')[0].id, 'a')

    @patch.dict('os.environ', {'SEARCH_MODE': 'hybrid'})
    @patch('retrieval.vector_store')
    @patch('retrieval.keyword_search', return_value=[])
    def test_empty_index(self, keyword, vector):
        vector.return_value.similarity_search.return_value = []
        self.assertEqual(retrieval.retrieve('payment'), [])


if __name__ == '__main__':
    unittest.main()
