"""
FP-4.x: Deterministic Sorting Utilities
Provides shared deterministic sorting logic for DAP, INDEX, and AMU₀.
"""
from typing import Any, Callable, List, Tuple, Dict


def detsort_dict(d: Dict[str, Any]) -> List[Tuple[str, Any]]:
    """
    Convert a dictionary to a deterministically sorted list of tuples.
    
    Args:
        d: Dictionary to sort.
        
    Returns:
        List of (key, value) tuples sorted by key.
    """
    return sorted(d.items(), key=lambda x: x[0])


def detsort_list(xs: List[Any], key: Callable[[Any], Any] = None) -> List[Any]:
    """
    Deterministically sort a list.
    
    Args:
        xs: List to sort.
        key: Optional key function for sorting.
        
    Returns:
        Sorted list (new list, original unchanged).
    """
    if key is None:
        return sorted(xs)
    return sorted(xs, key=key)


def detsort_paths(paths: List[str]) -> List[str]:
    """
    Deterministically sort file paths.
    
    Normalizes path separators and sorts lexicographically.
    
    Args:
        paths: List of file paths.
        
    Returns:
        Sorted list of paths with normalized separators.
    """
    normalized = [p.replace('\\', '/') for p in paths]
    return sorted(normalized)


def detsort_set(s: set) -> List[Any]:
    """
    Convert a set to a deterministically sorted list.
    
    Args:
        s: Set to convert and sort.
        
    Returns:
        Sorted list of set elements.
    """
    return sorted(list(s))
