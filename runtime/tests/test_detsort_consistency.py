"""Tests for CND-6: Detsort Consistency"""
import unittest

from runtime.util.detsort import detsort_dict, detsort_list, detsort_paths, detsort_set


class TestDetsortConsistency(unittest.TestCase):
    """Test deterministic sorting utilities."""
    
    def test_detsort_dict_stable(self):
        """Dict sorting is stable across runs."""
        d = {"c": 3, "a": 1, "b": 2}
        
        result1 = detsort_dict(d)
        result2 = detsort_dict(d)
        
        self.assertEqual(result1, result2)
        self.assertEqual(result1[0][0], "a")
    
    def test_detsort_list_stable(self):
        """List sorting is stable."""
        xs = [3, 1, 2]
        
        result1 = detsort_list(xs)
        result2 = detsort_list(xs)
        
        self.assertEqual(result1, result2)
        self.assertEqual(result1, [1, 2, 3])
    
    def test_detsort_paths_normalizes(self):
        """Path sorting normalizes separators."""
        paths = ["b\\file.py", "a/file.py"]
        
        result = detsort_paths(paths)
        
        self.assertEqual(result[0], "a/file.py")
        self.assertEqual(result[1], "b/file.py")
    
    def test_detsort_set_deterministic(self):
        """Set to list conversion is deterministic."""
        s = {"c", "a", "b"}
        
        result1 = detsort_set(s)
        result2 = detsort_set(s)
        
        self.assertEqual(result1, result2)
        self.assertEqual(result1, ["a", "b", "c"])


if __name__ == '__main__':
    unittest.main()
