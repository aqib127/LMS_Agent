"""
Authentication helpers for Bahria CMS (ASP.NET WebForms).
"""

from playwright.sync_api import Page, TimeoutError as PWTimeout, Locator
from loguru import logger
from config.settings import settings


class AuthError(Exception):
    """Raised when we can't authenticate and need human intervention."""


def _first_visible(page: Page, selectors: list[str], timeout_ms: int = 3000) -> Locator | None:
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            loc.wait_for(state="visible", timeout=timeout_ms)
            return loc
        except PWTimeout:
            continue
        except Exception as e:
            logger.debug(f"Selector {sel!r} failed: {e}")
            continue
    return None


def _has_password_field(page: Page) -> bool:
    try:
        return page.locator('input[type="password"]').first.is_visible(timeout=800)
    except Exception:
        return False


def _is_logged_in(page: Page) -> bool:
    if _has_password_field(page):
        return False
    url = page.url.lower().rstrip("/")
    if url in ("https://cms.bahria.edu.pk", "https://lms.bahria.edu.pk"):
        return False
    for marker in ("/login", "/signin", "login.aspx", "account/login"):
        if marker in url:
            return False
    if settings.lms_login_url.rstrip("/").lower() == url:
        return False
    return True


def _wait_for_options(page: Page, loc: Locator, timeout_ms: int = 5000) -> int:
    """Wait until the <select> has more than 1 option (i.e., populated). Returns count."""
    try:
        page.wait_for_function(
            """(el) => el && el.options && el.options.length > 1""",
            arg=loc.element_handle(),
            timeout=timeout_ms,
        )
    except Exception:
        pass
    try:
        count = loc.evaluate("el => el.options.length")
        logger.debug(f"Dropdown option count: {count}")
        return count
    except Exception:
        return 0


def _select_dropdown(page: Page, loc: Locator, desired: str, name: str) -> bool:
    """Robust selection with label, value, exact-text, then substring fallback."""
    desired_l = desired.strip().lower()

    # 0. Wait for options to load
    _wait_for_options(page, loc)

    # 1. label
    try:
        loc.select_option(label=desired, timeout=2500)
        logger.debug(f"[{name}] selected by label: {desired}")
        return True
    except Exception:
        pass

    # 2. value
    try:
        loc.select_option(value=desired, timeout=1500)
        logger.debug(f"[{name}] selected by value: {desired}")
        return True
    except Exception:
        pass

    # 3 & 4. JS: case-insensitive exact then partial
    try:
        result = loc.evaluate(
            """(el, desired) => {
                const d = desired.toLowerCase();
                for (const opt of el.options) {
                    if ((opt.textContent || '').trim().toLowerCase() === d) {
                        el.value = opt.value;
                        el.dispatchEvent(new Event('change', { bubbles: true }));
                        return { ok: true, how: 'exact', chosen: opt.textContent.trim(), value: opt.value };
                    }
                }
                for (const opt of el.options) {
                    if ((opt.textContent || '').trim().toLowerCase().includes(d)) {
                        el.value = opt.value;
                        el.dispatchEvent(new Event('change', { bubbles: true }));
                        return { ok: true, how: 'partial', chosen: opt.textContent.trim(), value: opt.value };
                    }
                }
                return { ok: false, options: [...el.options].map(o => o.textContent.trim()) };
            }""",
            desired,
        )
        if result.get("ok"):
            logger.debug(f"[{name}] JS-selected ({result['how']}): {result['chosen']} (value={result.get('value')})")
            return True
        logger.warning(f"[{name}] no option matched '{desired}'. Options: {result.get('options')}")
    except Exception as e:
        logger.warning(f"[{name}] JS selection failed: {e}")

    return False


def ensure_authenticated(page: Page, max_attempts: int = 2) -> None:
    for attempt in range(1, max_attempts + 1):
        logger.info(f"Auth check (attempt {attempt}/{max_attempts})")
        page.goto(settings.lms_login_url, wait_until="domcontentloaded", timeout=30000)

        # ASP.NET: options populate after postback; wait a bit longer
        page.wait_for_timeout(3000)

        if _is_logged_in(page):
            logger.info(f"Already authenticated. URL: {page.url}")
            return

        logger.info(f"Not logged in (URL: {page.url}) — attempting auto-login...")
        try:
            _do_login(page)
        except AuthError:
            raise
        except Exception as e:
            logger.error(f"Auto-login failed on attempt {attempt}: {e}")

        # ASP.NET postback reloads the same URL then redirects
        try:
            page.wait_for_url(
                lambda url: "login.aspx" not in url.lower()
                            and "cms.bahria.edu.pk" in url.lower(),
                timeout=20000,
            )
        except PWTimeout:
            logger.debug("No URL change after login — checking page state")

        page.wait_for_timeout(2500)

        if _is_logged_in(page):
            logger.info(f"Login successful. URL: {page.url}")
            return

        logger.warning(f"Still looks logged out. URL: {page.url}")

    raise AuthError(
        "Could not authenticate after multiple attempts. "
        "Run `python -m scripts.first_login` to log in manually and refresh the session."
    )


def _do_login(page: Page) -> None:
    """Fill the login form and submit."""

    # --- Enrollment ---
    user_field = _first_visible(page, settings.user_selectors())
    if not user_field:
        raise AuthError(f"Enrollment input not found. Tried: {settings.user_selectors()}")
    user_field.click()
    user_field.fill("")
    user_field.type(settings.lms_enrollment_no, delay=30)
    logger.debug(f"Filled enrollment: {settings.lms_enrollment_no}")

    # --- Password ---
    pass_field = _first_visible(page, settings.pass_selectors())
    if not pass_field:
        raise AuthError(f"Password input not found. Tried: {settings.pass_selectors()}")
    pass_field.click()
    pass_field.fill("")
    pass_field.type(settings.lms_password, delay=30)
    logger.debug("Filled password")

    # --- Institute ---
    inst_field = _first_visible(page, settings.institute_selectors(), timeout_ms=3000)
    if inst_field:
        ok = _select_dropdown(page, inst_field, settings.lms_institute, "Institute")
        if not ok:
            logger.warning(f"Could not select institute '{settings.lms_institute}'. Proceeding.")
    else:
        logger.warning("Institute dropdown not found")

    # --- Role ---
    role_field = _first_visible(page, settings.role_selectors(), timeout_ms=2000)
    if role_field:
        ok = _select_dropdown(page, role_field, settings.lms_role, "Role")
        if not ok:
            logger.warning(f"Could not select role '{settings.lms_role}'. Proceeding.")
    else:
        logger.warning("Role dropdown not found")

    # --- Submit (it's an <a> with JS onclick) ---
    submit = _first_visible(page, settings.submit_selectors())
    if not submit:
        raise AuthError(f"Sign In button not found. Tried: {settings.submit_selectors()}")

    # Best-effort: click and wait for the ASP.NET postback
    try:
        with page.expect_navigation(timeout=15000):
            submit.click()
        logger.info("Submitted login form (navigation detected)")
    except PWTimeout:
        # Postback may not trigger a normal navigation — fall back to wait
        logger.info("Submitted login form (no navigation event; waiting)")
        page.wait_for_timeout(3000)
