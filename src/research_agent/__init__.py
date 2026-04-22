"""research-swarm — a DSPy ReAct agent that researches questions, cites
its sources, grows a local archive from every fetch, and self-critiques
its answers.

See README.md for the tour.
"""
from dotenv import load_dotenv

# Load .env on package import so tools/agent modules see the keys.
load_dotenv()

__version__ = "0.1.0"
