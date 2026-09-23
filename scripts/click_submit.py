"""Click the Submit link for assignment #7 and observe what happens."""
from pathlib import Path
from core.auth import ensure_authenticated
from core.browser import browser_session
from core.utils import logger, ensure_dirs


def main():
    ensure_dirs()

    with browser_session(use_auth=True, headless=False) as page:
        # 1. Login + bridge to LMS
        ensure_authenticated(page)
        page.goto("https://cms.bahria.edu.pk/Sys/Common/GoToLMS.aspx",
                  wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(5000)

        # 2. Navigate to the assignments page for AI Lab
        url = (
            "https://lms.bahria.edu.pk/Student/Assignments.php"
            "?s=MjAyNjM%3D&oc=MTUxNTI3"
        )
        print(f"\nNavigating to: {url}")
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2500)
        print(f"Current URL: {page.url}")
        print(f"Page title: {page.title()}")

        # 3. Find the "Uninformed Search" row
        print("\nLooking for the Uninformed Search row...")
        rows = page.locator("tr").all()
        target_row = None
        for r in rows:
            try:
                t = r.inner_text()
                if "Uninformed Search" in t:
                    target_row = r
                    break
            except Exception:
                continue

        if not target_row:
            print("❌ Could not find Uninformed Search row")
            return

        print("✓ Found row:")
        print(target_row.inner_text()[:500])

        # 4. Find the Submit link in that row
        links = target_row.locator("a").all()
        submit_link = None
        for l in links:
            try:
                if (l.inner_text() or "").strip().lower() == "submit":
                    submit_link = l
                    break
            except Exception:
                continue

        if not submit_link:
            print("❌ No Submit link found")
            return

        # Print what we know about the link
        print(f"\nSubmit link found:")
        print(f"  href   = {submit_link.get_attribute('href')!r}")
        print(f"  onclick = {submit_link.get_attribute('onclick')!r}")
        print(f"  class   = {submit_link.get_attribute('class')!r}")

        # 5. Click it
        print(f"\nClicking Submit...")
        submit_link.click()
        page.wait_for_timeout(5000)

        # 6. Report what happened
        print(f"\n=== AFTER CLICK ===")
        print(f"URL now: {page.url}")
        print(f"Title now: {page.title()}")

        # File inputs
        file_inputs = page.locator("input[type=file]").all()
        print(f"\nFile inputs visible: {len(file_inputs)}")
        for i, inp in enumerate(file_inputs):
            try:
                print(f"  [{i}] name={inp.get_attribute('name')!r} "
                      f"id={inp.get_attribute('id')!r} "
                      f"visible={inp.is_visible()}")
            except Exception:
                pass

        # Modals
        modals = page.locator(".modal, [role=dialog], .ui-dialog, .modal-dialog").all()
        print(f"\nModal-like elements: {len(modals)}")

        # Any new buttons/links with 'upload' or 'submit' in them
        print(f"\nButtons/links with 'upload'/'submit':")
        for el in page.locator(
            "button:has-text('Upload'), button:has-text('Submit'), "
            "input[type=submit], a:has-text('Upload')"
        ).all():
            try:
                t = (el.inner_text() or el.get_attribute('value') or "")[:50]
                print(f"  - {t!r}  (visible={el.is_visible()})")
            except Exception:
                pass

        # 7. Save the resulting HTML for offline inspection
        out = Path("data/snapshots")
        out.mkdir(parents=True, exist_ok=True)
        f = out / "after_submit_click.html"
        f.write_text(page.content(), encoding="utf-8")
        print(f"\nSaved HTML to: {f}")

        print("\nBrowser stays open. Close it manually when done.")
        # Keep browser open by waiting for input
        input("\nPress Enter in the terminal to close the browser... ")


if __name__ == "__main__":
    main()
