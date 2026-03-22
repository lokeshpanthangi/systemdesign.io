"""
Review Agent — CheckingAgent
Analyzes user's Excalidraw diagram against question requirements using LLM.
"""
import json
from typing import Dict, Any
from langchain_core.prompts import ChatPromptTemplate

from Agents.review_agent.tools.helpers import extract_question_data, extract_diagram_data
from Agents.prompts.checking_prompt import CHECKING_SYSTEM_PROMPT, CHECKING_USER_PROMPT_TEMPLATE

from core.llm_provider import get_llm


class CheckingAgent:
    """Agent for checking user's system design solutions"""
    
    def __init__(self):
        """Initialize the checking agent with LLM from centralized provider"""
        self.llm = get_llm(temperature=0.3)
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", CHECKING_SYSTEM_PROMPT),
            ("human", "{input}")
        ])
    
    async def check_solution(
        self,
        problem_data: Dict[str, Any],
        diagram_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Check user's solution and provide feedback.
        
        Args:
            problem_data: Question/problem data (title, description, requirements, etc.)
            diagram_data: User's Excalidraw diagram data
            
        Returns:
            Structured feedback dict with keys: implemented, missing, next_steps
        """
        try:
            question_str = extract_question_data(problem_data)
            diagram_str = extract_diagram_data(diagram_data)
            
            user_input = CHECKING_USER_PROMPT_TEMPLATE.format(
                question_data=question_str,
                diagram_data=diagram_str
            )
            
            chain = self.prompt | self.llm
            result = await chain.ainvoke({"input": user_input})
            
            try:
                feedback_json = json.loads(result.content)
                return feedback_json
            except json.JSONDecodeError:
                return {
                    "implemented": ["Unable to parse AI response"],
                    "missing": ["Please try again"],
                    "next_steps": ["Check your internet connection"]
                }
            
        except Exception as e:
            return {
                "implemented": [],
                "missing": [f"Error analyzing solution: {str(e)}"],
                "next_steps": ["Please try again later"]
            }
    
    def check_solution_sync(
        self,
        problem_data: Dict[str, Any],
        diagram_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Synchronous version of check_solution."""
        try:
            question_str = extract_question_data(problem_data)
            diagram_str = extract_diagram_data(diagram_data)
            
            user_input = CHECKING_USER_PROMPT_TEMPLATE.format(
                question_data=question_str,
                diagram_data=diagram_str
            )
            
            chain = self.prompt | self.llm
            result = chain.invoke({"input": user_input})
            
            try:
                feedback_json = json.loads(result.content)
                return feedback_json
            except json.JSONDecodeError:
                return {
                    "implemented": ["Unable to parse AI response"],
                    "missing": ["Please try again"],
                    "next_steps": ["Check your internet connection"]
                }
            
        except Exception as e:
            return {
                "implemented": [],
                "missing": [f"Error analyzing solution: {str(e)}"],
                "next_steps": ["Please try again later"]
            }


# Singleton instance
_checking_agent = None


def get_checking_agent() -> CheckingAgent:
    """Get or create the singleton checking agent instance"""
    global _checking_agent
    if _checking_agent is None:
        _checking_agent = CheckingAgent()
    return _checking_agent


async def analyze_user_solution(
    problem_data: Dict[str, Any],
    diagram_data: Dict[str, Any]
) -> str:
    """
    Convenience function to analyze user solution.
    
    Args:
        problem_data: Question/problem data
        diagram_data: User's Excalidraw diagram data
        
    Returns:
        Feedback string
    """
    agent = get_checking_agent()
    return await agent.check_solution(problem_data, diagram_data)
