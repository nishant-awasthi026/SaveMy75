import unittest
from analyzer import AttendanceAnalyzer

class TestAnalyzerLogic(unittest.TestCase):
    def setUp(self):
        self.analyzer = AttendanceAnalyzer()
        # Mocking the predictor loading since we only test logic here
        self.analyzer.predictor = None 

    def test_parse_rows_with_percentage(self):
        # Flattened word structure from docTR: {'text': str, 'y': float, ...}
        # Simulating row: "Compiler Design 13 21 61.9%"
        
        mock_row = [
            {'text': "Compiler", 'y': 0.1, 'x': 0.1},
            {'text': "Design", 'y': 0.1, 'x': 0.2},
            {'text': "13", 'y': 0.1, 'x': 0.5},
            {'text': "21", 'y': 0.1, 'x': 0.6},
            {'text': "61.9%", 'y': 0.1, 'x': 0.8},
        ]
        
        # We test _parse_rows which expects a list of rows
        rows = [mock_row]
        data = self.analyzer._parse_rows(rows)
        
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['course'], "Compiler Design")
        self.assertEqual(data[0]['attended'], 13)
        self.assertEqual(data[0]['total'], 21)

    def test_parse_rows_integers_only(self):
        # Simulating row: "Math 40 50" (No percentage)
        # Should pick 40/50
        
        mock_row = [
            {'text': "Math", 'y': 0.2, 'x': 0.1},
            {'text': "50", 'y': 0.2, 'x': 0.5},
            {'text': "40", 'y': 0.2, 'x': 0.6},
        ]
        
        rows = [mock_row]
        data = self.analyzer._parse_rows(rows)
        
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['course'], "Math")
        self.assertEqual(data[0]['attended'], 40)
        self.assertEqual(data[0]['total'], 50)

if __name__ == '__main__':
    unittest.main()
