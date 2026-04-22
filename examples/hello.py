"""Hello world for research-swarm.

Prove the install works. Ask one simple question, print the answer.

Run:
    python examples/hello.py
"""

from datetime import date

from research_agent.agent import build_agent, configure_lm


def main() -> None:
    configure_lm()
    agent = build_agent()
    result = agent(
        current_date=date.today().isoformat(),
        question="What is DSPy and who wrote it?",
    )
    print("─" * 72)
    print("SYNTHESIS")
    print("─" * 72)
    print(result.synthesis)
    print()
    print("SOURCES:")
    for s in result.sources:
        print(f"  · {s}")


if __name__ == "__main__":
    main()
