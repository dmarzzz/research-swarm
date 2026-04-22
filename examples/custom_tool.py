"""Add your own tool to the agent's toolbox.

The agent reads the tool's docstring to decide when to call it, so
write docstrings *for the agent*, not just for humans. The format
matters: be specific about WHEN to use the tool and WHAT the return
value looks like.

Run:
    python examples/custom_tool.py
"""

from datetime import date

import dspy

from research_agent.agent import ResearchTask, configure_lm
from research_agent.tools import (
    arxiv_search,
    fetch_url,
    local_search,
    web_search,
)


def hacker_news_front_page() -> str:
    """Fetch the current Hacker News front page.

    Use this when the user asks about "what's trending on HN" or wants
    a snapshot of what the HN community is discussing right now.

    Returns:
        Formatted list of ~20 stories with title, URL, points, and
        comment count.
    """
    import json
    import urllib.request

    # Algolia HN front-page API
    url = "https://hn.algolia.com/api/v1/search?tags=front_page"
    with urllib.request.urlopen(url, timeout=10) as resp:
        data = json.loads(resp.read())

    blocks = []
    for hit in data.get("hits", [])[:20]:
        title = hit.get("title") or hit.get("story_title") or "(no title)"
        url = hit.get("url") or hit.get("story_url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
        points = hit.get("points", 0)
        comments = hit.get("num_comments", 0)
        blocks.append(f"- {title}\n  {url}\n  {points} points · {comments} comments")
    return "\n\n".join(blocks) if blocks else "No stories found."


def main() -> None:
    configure_lm()

    # Build a ReAct module with the default tools PLUS our custom one.
    agent = dspy.ReAct(
        ResearchTask,
        tools=[
            local_search,
            web_search,
            arxiv_search,
            fetch_url,
            hacker_news_front_page,   # ← custom
        ],
        max_iters=10,
    )

    result = agent(
        current_date=date.today().isoformat(),
        question="What's trending on Hacker News right now, and how do those topics connect?",
    )
    print(result.synthesis)
    print()
    print("sources:")
    for s in result.sources:
        print(f"  · {s}")


if __name__ == "__main__":
    main()
