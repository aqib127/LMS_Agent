"""Run the agent once — great for cron or manual testing."""
from core.agent import run_once


def main():
    result = run_once(notify=True)
    print(f"\nNew: {result['new']}   Changed: {result['changed']}")
    for kind, s in result["summary"].items():
        if "error" in s:
            print(f"  {kind:20s} ERROR: {s['error']}")
        else:
            print(f"  {kind:20s} total={s['total']:3d}  new={s['new']:3d}  changed={s['changed']:3d}")


if __name__ == "__main__":
    main()
