"""
Question Data Extractor Tool
Formats problem/question data for LLM analysis
"""
from typing import Dict, Any
from langchain.tools import tool


@tool
def extract_question_requirements(problem_data: dict) -> str:
    """
    Extract and format question requirements for LLM analysis.
    
    Formats: title, description, requirements, constraints, hints
    
    Args:
        problem_data: Problem/question data from database
        
    Returns:
        Formatted string with question details
    """
    if not problem_data or not isinstance(problem_data, dict):
        return "No question data provided"
    
    output_lines = []
    
    # Title
    output_lines.append("=== QUESTION ===")
    output_lines.append(f"Title: {problem_data.get('title', 'Unknown')}")
    output_lines.append(f"Difficulty: {problem_data.get('difficulty', 'Unknown').upper()}")
    output_lines.append("")
    
    # Description
    description = problem_data.get('description', '')
    if description:
        output_lines.append("=== DESCRIPTION ===")
        output_lines.append(description)
        output_lines.append("")
    
    # Requirements
    requirements = problem_data.get('requirements', [])
    if requirements:
        output_lines.append("=== REQUIRED COMPONENTS ===")
        for idx, req in enumerate(requirements, 1):
            output_lines.append(f"{idx}. {req}")
        output_lines.append("")
    
    # Constraints
    constraints = problem_data.get('constraints', [])
    if constraints:
        output_lines.append("=== CONSTRAINTS & ASSUMPTIONS ===")
        for idx, constraint in enumerate(constraints, 1):
            output_lines.append(f"{idx}. {constraint}")
        output_lines.append("")
    
    # Hints (optional, can help LLM understand context)
    hints = problem_data.get('hints', [])
    if hints:
        output_lines.append("=== HINTS (for context) ===")
        for idx, hint in enumerate(hints, 1):
            output_lines.append(f"{idx}. {hint}")
        output_lines.append("")
    
    # Categories
    categories = problem_data.get('categories', [])
    if categories:
        output_lines.append(f"Categories: {', '.join(categories)}")
        output_lines.append("")
    
    return "\n".join(output_lines)
