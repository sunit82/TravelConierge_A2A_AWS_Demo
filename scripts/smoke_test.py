from __future__ import annotations

import argparse

from scripts.invoke_main import invoke

DELEGATION_PROMPT = (
    "I am visiting Tokyo in April. What weather should I expect, and what should I pack?"
)
DIRECT_PROMPT = (
    "Explain the difference between a direct flight and a nonstop flight in two sentences."
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke test both travel agent routing paths")
    parser.add_argument("--runtime-arn", required=True)
    parser.add_argument("--role-arn", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    delegated, _ = invoke(args.runtime_arn, args.role_arn, DELEGATION_PROMPT)
    delegated_lower = delegated.casefold()
    if "demo" not in delegated_lower or "pack" not in delegated_lower:
        raise RuntimeError(
            "Delegation response did not preserve the demo-data disclosure and packing advice"
        )
    print("PASS: weather and packing delegation")
    print(delegated)

    direct, _ = invoke(args.runtime_arn, args.role_arn, DIRECT_PROMPT)
    direct_lower = direct.casefold()
    if "nonstop" not in direct_lower or "direct" not in direct_lower:
        raise RuntimeError("Direct response did not explain both flight terms")
    print("\nPASS: direct travel concierge answer")
    print(direct)


if __name__ == "__main__":
    main()

