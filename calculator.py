import math

def calculate_requirements(attended_hours: int, total_hours: int, target_percent: float = 75.0):
    """
    Calculates the attendance status and requirements.

    Args:
        attended_hours (int): Number of hours attended.
        total_hours (int): Total number of hours conducted.
        target_percent (float): Target attendance percentage (default 75.0).

    Returns:
        dict: A dictionary containing:
            - current_percent (float): Current attendance percentage.
            - status (str): 'Safe' or 'Needs Improvement'.
            - hours_needed (int): Hours needed to reach target (0 if safe).
            - next_percent_if_missed (float): Attendance % if next class is missed.
    """
    if total_hours == 0:
        return {
            "current_percent": 0.0,
            "status": "No Classes",
            "hours_needed": 0
        }

    current_percent = (attended_hours / total_hours) * 100
    
    if current_percent >= target_percent:
        return {
            "current_percent": round(current_percent, 2),
            "status": "Safe",
            "hours_needed": 0
        }
    
    # Formula: (attended + x) / (total + x) >= target/100
    # attended + x >= (target/100) * (total + x)
    # attended + x >= target_ratio * total + target_ratio * x
    # x - target_ratio * x >= target_ratio * total - attended
    # x (1 - target_ratio) >= target_ratio * total - attended
    # x >= (target_ratio * total - attended) / (1 - target_ratio)
    
    target_ratio = target_percent / 100.0
    numerator = (target_ratio * total_hours) - attended_hours
    denominator = 1 - target_ratio
    
    # If denominator is 0 (target is 100%), handle separately but usually 1-0.75 = 0.25
    if denominator <= 0:
        # Impossible to secure 100% if you missed any, 
        # but effectively means you need infinite classes if you missed one.
        # For simplicity in this common case (75%), denominator is > 0.
        hours_needed = float('inf')
    else:
        hours_needed = numerator / denominator
    
    hours_needed = math.ceil(hours_needed)
    
    # Double check to ensure it's non-negative (it should be if current < target)
    hours_needed = max(0, hours_needed)

    return {
        "current_percent": round(current_percent, 2),
        "status": "Short",
        "hours_needed": hours_needed
    }
