"""Run with: python -m unittest -v test_app"""
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import app


class FakeModel:
    tokenizer = SimpleNamespace(encode=lambda *args, **kwargs: list(range(100)))
    model = SimpleNamespace(config=SimpleNamespace(max_position_embeddings=1024, _commit_hash="mock"))

    def __call__(self, text, **kwargs):
        self.kwargs = kwargs
        return [{"summary_text": "Water evaporates, condenses into clouds, and returns as precipitation."}]


class CoreTests(unittest.TestCase):
    def test_word_count(self):
        self.assertEqual(app.count_words("Artificial intelligence is useful."), 4)
        self.assertEqual(app.count_words("The Earth's water-cycle matters."), 4)
        self.assertEqual(app.count_words(""), 0)

    def test_reduction(self):
        self.assertEqual(app.reduction(100, 40), 60.0)
        self.assertEqual(app.reduction(10, 12), -20.0)
        with self.assertRaises(ValueError):
            app.reduction(0, 0)

    def test_validation(self):
        for text in ("", "Too short.", None, "word " * 3000):
            with self.assertRaises(ValueError):
                app.validate(text)
        for text in app.EXAMPLES.values():
            app.validate(text)

    def test_key_points(self):
        original = "Water flows. Water evaporates. Clouds form."
        points = app.key_points(original, 2)
        self.assertEqual(len(points), 2)
        self.assertTrue(all(point in original for point in points))
        self.assertLess(original.index(points[0]), original.index(points[1]))
        self.assertEqual(app.key_points(original, 0), [])

    @patch("app.version", return_value="test-version")
    def test_generation_contract(self, _):
        model = FakeModel()
        result = app.generate(app.EXAMPLES["Water Cycle"], model)
        self.assertTrue(result["summary"])
        self.assertEqual(result["summary_words"], app.count_words(result["summary"]))
        self.assertFalse(model.kwargs["do_sample"])
        self.assertFalse(model.kwargs["truncation"])
        self.assertIn(result["summary"], app.markdown(result))

    def test_long_token_input_rejected(self):
        model = FakeModel()
        model.tokenizer = SimpleNamespace(encode=lambda *args, **kwargs: list(range(901)))
        with self.assertRaisesRegex(ValueError, "Nothing was truncated"):
            app.generate(app.EXAMPLES["Water Cycle"], model)

    def test_invalid_model_response(self):
        class EmptyModel(FakeModel):
            def __call__(self, *args, **kwargs):
                return []
        with self.assertRaises(RuntimeError):
            app.generate(app.EXAMPLES["Water Cycle"], EmptyModel())

    def test_csv_formula_escaping(self):
        report = app.csv_report([{"text": "=1+1", "words": 3}])
        self.assertIn("'=1+1", report)


class InterfaceTests(unittest.TestCase):
    def test_interface_load_and_clear(self):
        from streamlit.testing.v1 import AppTest
        page = AppTest.from_file("app.py").run(timeout=30)
        self.assertEqual(len(page.exception), 0)
        next(button for button in page.button if button.label == "Load example").click().run()
        self.assertEqual(page.text_area(key="paragraph").value, app.EXAMPLES["Artificial Intelligence"])
        next(button for button in page.button if button.label == "Clear input and result").click().run()
        self.assertEqual(page.text_area(key="paragraph").value, "")
        self.assertEqual(len(page.exception), 0)


if __name__ == "__main__":
    unittest.main()
