import pytest
import httpx
import asyncio
from crew_agents import DocumentAnalysisCrew

@pytest.mark.asyncio
async def test_ollama_connection():
    """Test if Ollama server is running and accessible"""
    crew = DocumentAnalysisCrew()
    is_healthy = await crew.check_ollama_health()
    assert is_healthy, "Ollama server is not running or not accessible"

@pytest.mark.asyncio
async def test_model_availability():
    """Test if deepseek-r1:1.5b model is available in Ollama"""
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:11434/api/tags")
        assert response.status_code == 200, "Failed to get model list from Ollama"
        
        models = response.json()
        model_names = [model['name'] for model in models['models']]
        assert "deepseek-r1:1.5b" in model_names, "deepseek-r1:1.5b model is not available in Ollama"

@pytest.mark.asyncio
async def test_model_query():
    """Test if model can process a simple query"""
    crew = DocumentAnalysisCrew()
    try:
        response = await crew.llm.agenerate(["Hello, are you the deepseek-r1:1.5b model?"])
        assert response is not None, "Model failed to generate response"
        assert len(response.generations) > 0, "Model returned empty response"
    except Exception as e:
        pytest.fail(f"Model query failed: {str(e)}")

@pytest.mark.asyncio
async def test_agent_creation():
    """Test if agents can be created with the model"""
    crew = DocumentAnalysisCrew()
    try:
        analyzer, specialist = crew.create_agents()
        assert analyzer is not None, "Failed to create analyzer agent"
        assert specialist is not None, "Failed to create specialist agent"
        assert analyzer.llm.model == "deepseek-r1:1.5b", "Analyzer using wrong model"
        assert specialist.llm.model == "deepseek-r1:1.5b", "Specialist using wrong model"
    except Exception as e:
        pytest.fail(f"Agent creation failed: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_ollama_connection())
    asyncio.run(test_model_availability())
    asyncio.run(test_model_query())
    asyncio.run(test_agent_creation())
    print("All tests passed! System is ready for document upload.")
