import unittest
from calculator import calculate_requirements

class TestCalculator(unittest.TestCase):
    def test_safe_attendance(self):
        # 80/100 = 80% > 75%
        result = calculate_requirements(80, 100)
        self.assertEqual(result['status'], 'Safe')
        self.assertEqual(result['hours_needed'], 0)

    def test_short_attendance(self):
        # 60/100 = 60% < 75%
        # Needs to reach 75%.
        # (60+x)/(100+x) = 0.75 => 60+x = 75 + 0.75x => 0.25x = 15 => x = 60
        result = calculate_requirements(60, 100)
        self.assertEqual(result['status'], 'Short')
        self.assertEqual(result['hours_needed'], 60)
        
    def test_boundary_attendance(self):
        # 74/100 = 74%
        # (74+x)/(100+x) = 0.75 => 74+x = 75 + 0.75x => 0.25x = 1 => x = 4
        result = calculate_requirements(74, 100)
        self.assertEqual(result['hours_needed'], 4)

    def test_zero_classes(self):
        result = calculate_requirements(0, 0)
        self.assertEqual(result['status'], 'No Classes')

if __name__ == '__main__':
    unittest.main()
