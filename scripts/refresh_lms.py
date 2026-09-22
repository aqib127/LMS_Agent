"""Deep LMS refresh — run once a day. Also sends email digest if changed."""
from core.agent import run_lms_and_notify
from core.storage import stats


def main():
    print("=== Deep LMS scrape starting ===")
    result = run_lms_and_notify()
    print(f"\nNew: {result['new']}   Changed: {result['changed']}")
    for kind, s in result["summary"].items():
        print(f"  {kind:25s} total={s['total']:4d}  new={s['new']:3d}  changed={s['changed']:3d}")

    print("\n=== DB totals ===")
    for k, n in stats().items():
        print(f"  {k:25s} {n}")


if __name__ == "__main__":
    main()
