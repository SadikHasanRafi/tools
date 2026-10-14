"""
earki.co -> kazim-rouge dashboard auto-poster (Selenium)

Install:  pip install selenium
Run:      python scraper.py
(Selenium 4.6+ downloads the matching chromedriver automatically.)
"""

import random
import time

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

# ------------------------------------------------------------------ CONFIG
START_URL = (
    "https://www.earki.co/jokes/joke/12176/%E0%A6%AA%E0%A6%BE%E0%A6%81%E0%A6%9A-%E0%A6%B9%E0%A6%BE%E0%A6%9C%E0%A6%BE%E0%A6%B0-%E0%A6%9F%E0%A6%BE%E0%A6%95%E0%A6%BE-%E0%A6%AE%E0%A6%BE%E0%A6%A8%E0%A7%87-%E0%A6%A4%E0%A7%8B-%E0%A6%AA%E0%A6%BE%E0%A6%81%E0%A6%9A-%E0%A6%B9%E0%A6%BE%E0%A6%9C%E0%A6%BE%E0%A6%B0-%E0%A6%9F%E0%A6%BE%E0%A6%95%E0%A6%BE%E0%A6%87"
)
LOGIN_URL = "https://kazim-rouge.vercel.app/dashboard/login"
NEW_POST_URL = "https://kazim-rouge.vercel.app/dashboard/new"
PASSWORD = "01533"
TOTAL_POSTS = 50
MIN_WAIT = 0.4   # seconds, for "click" type actions
MAX_WAIT = 0.8
TAG_POOL = ["news", "story", "bangladesh", "trending", "update", "latest", "feature", "read"]

# --- source site selectors
SRC_IMG = "#widget_339 > div > article > div > p:nth-child(2) > a > img"
SRC_TITLE = "#widget_339 > div > h2 > span"
SRC_AUTHOR = "#widget_339 > div > div.author_info > a > span > span.author_name"
SRC_BODY = "#widget_339 > div > article > div"
SRC_NEXT_LINKS = (
    "#articles_853 > div > div > div > "
    "div.left_image_right_content.oh.mb10 > div.right_content_holder > h2 > a"
)

# --- dashboard selectors
LOGIN_PASS = "body > main > form > input"
LOGIN_BTN = "body > main > form > button"
IMG_TAB_BTN = (
    "body > div.min-h-screen > main > div > div > form > div:nth-child(1) > "
    "div.mb-4.flex.gap-1.overflow-x-auto.border-b.border-zinc-200.sm\\:gap-2 > "
    "button.whitespace-nowrap.px-3.py-2\\.5.text-xs.font-medium.transition-all."
    "duration-200.sm\\:px-4.sm\\:text-sm.text-zinc-600.hover\\:text-zinc-800"
)
IMG_INPUT = (
    "body > div.min-h-screen > main > div > div > form > div:nth-child(1) > "
    "div.mb-4.flex.flex-col.gap-4.sm\\:flex-row.sm\\:items-start > "
    "div.flex-1.space-y-2 > div > div > input"
)
# Source URL input: your exact XPath first, then the id as a fallback
SOURCE_URL_XPATHS = [
    "//input[contains(@placeholder,'where this meme came from')]",
    "/html/body/div[2]/main/div/div/form/div[8]/input",
    '//*[@id="sourceUrl"]',
]
# The real submit is the only form button without type="button" ("📤 Upload meme").
# Matching just 'upload' would hit the "📤 Upload" image tab instead.
SUBMIT_BTN_ABS_XPATH = "//form/div/button[not(@type='button')]"
SUBMIT_BTN_CSS = "form button:not([type='button'])"
SUBMIT_BTN_XPATH = (
    "//form//button[contains(translate(normalize-space(.),"
    "'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'upload meme')]"
)


# ------------------------------------------------------------------ HELPERS
def human_wait():
    """Random pause (>= 3.5s) used before click-type actions."""
    time.sleep(random.uniform(MIN_WAIT, MAX_WAIT))


def locator(selector):
    """Accepts either a CSS selector or an XPath (starts with '/' or '(')."""
    if selector.startswith("/") or selector.startswith("("):
        return (By.XPATH, selector)
    return (By.CSS_SELECTOR, selector)


def css(driver, selector, timeout=10):
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located(locator(selector))
    )


def clickable(driver, selector, timeout=20):
    return WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable(locator(selector))
    )


def wait_page_loaded(driver, timeout=30):
    WebDriverWait(driver, timeout).until(
        lambda d: d.execute_script("return document.readyState") in ("interactive", "complete")
    )


def text_of(element):
    return (element.get_attribute("textContent") or "").strip()


def js_set_value(driver, element, value):
    """Instant 'paste' that also works with React/Next controlled inputs."""
    driver.execute_script(
        """
        const el = arguments[0], val = arguments[1];
        const proto = el.tagName === 'TEXTAREA'
            ? window.HTMLTextAreaElement.prototype
            : window.HTMLInputElement.prototype;
        Object.getOwnPropertyDescriptor(proto, 'value').set.call(el, val);
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
        """,
        element,
        value,
    )


def fill(driver, selector, value, name=""):
    """Paste instantly via JS, verify it stuck, otherwise fall back to typing."""
    el = css(driver, selector)
    js_set_value(driver, el, value)
    time.sleep(0.2)
    current = el.get_attribute("value") or ""
    if current.strip() != value.strip():
        print(f"  [{name or selector}] JS paste didn't stick, typing it instead...")
        el.clear()
        el.send_keys(value)
        time.sleep(0.2)
        current = el.get_attribute("value") or ""
    ok = current.strip() == value.strip()
    print(f"  [{name or selector}] {'OK' if ok else 'MISMATCH'}")
    return ok


def find_source_url_input(driver):
    """Scan real <input>/<textarea> fields and pick the 'source url' one by
    placeholder / id / name / label text. Returns the element or None."""
    keywords = ("came from", "source", "http", "url", "link")
    best, best_score = None, 0
    img_inputs = driver.find_elements(By.CSS_SELECTOR, IMG_INPUT)
    for el in driver.find_elements(By.CSS_SELECTOR, "form input, form textarea"):
        if not el.is_displayed():
            continue
        if (el.get_attribute("type") or "text").lower() in (
            "file", "hidden", "checkbox", "radio", "password", "submit",
        ):
            continue
        if el.get_attribute("id") in ("title", "description", "author", "body", "tags"):
            continue
        # the image-url box also says "url" -> skip it
        if el in img_inputs:
            continue
        label = driver.execute_script(
            "const l = arguments[0].labels && arguments[0].labels[0];"
            "const p = arguments[0].closest('div');"
            "return (l ? l.textContent : (p ? p.textContent : ''));",
            el,
        ) or ""
        hay = " ".join([
            el.get_attribute("placeholder") or "",
            el.get_attribute("id") or "",
            el.get_attribute("name") or "",
            label,
        ]).lower()
        score = sum(2 if k in ("came from", "source") else 1 for k in keywords if k in hay)
        if el.get_attribute("id") == "sourceUrl":
            score += 10
        if score > best_score:
            best, best_score = el, score
    return best


def fill_source_url(driver, value):
    """Fill the source-url input; JS paste first, real typing as fallback."""
    el = None
    for _ in range(10):  # form may still be rendering
        el = find_source_url_input(driver)
        if el is not None:
            break
        time.sleep(0.5)
    if el is None:
        print("  [sourceUrl] FIELD NOT FOUND! Inputs on page:")
        for i in driver.find_elements(By.CSS_SELECTOR, "form input, form textarea"):
            print("    ", i.tag_name, i.get_attribute("id"), repr(i.get_attribute("placeholder")))
        return False

    print(f"  [sourceUrl] using <{el.tag_name}> id={el.get_attribute('id')!r} "
          f"placeholder={el.get_attribute('placeholder')!r}")
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
    time.sleep(0.3)
    js_set_value(driver, el, value)
    time.sleep(0.2)
    if (el.get_attribute("value") or "").strip() != value.strip():
        try:
            el.click()
            el.send_keys(Keys.CONTROL, "a")
            el.send_keys(Keys.DELETE)
            el.send_keys(value)
        except Exception:
            driver.execute_script("arguments[0].focus();", el)
            el.send_keys(value)
        time.sleep(0.2)
    ok = (el.get_attribute("value") or "").strip() == value.strip()
    print(f"  [sourceUrl] {'OK' if ok else 'MISMATCH'}")
    return ok


def fill_first(driver, selectors, value, name=""):
    """Try each selector/XPath in order until one exists, then fill it."""
    for sel in selectors:
        try:
            css(driver, sel, timeout=8)
        except TimeoutException:
            print(f"  [{name}] not found with {sel}, trying next...")
            continue
        el = css(driver, sel)
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
        return fill(driver, sel, value, name)
    print(f"  [{name}] FIELD NOT FOUND with any selector!")
    return False


# ------------------------------------------------------------------ SCRAPE
def find_article_image(driver):
    """Image position varies per article: exact selector, any article img, then og:image."""
    for sel in (SRC_IMG, "#widget_339 article img"):
        for img in driver.find_elements(By.CSS_SELECTOR, sel):
            src = img.get_attribute("src")
            if src:
                return src
    for meta in driver.find_elements(By.CSS_SELECTOR, "meta[property='og:image']"):
        src = meta.get_attribute("content") or ""
        if src:
            return "https:" + src if src.startswith("//") else src
    return ""


def scrape_article(driver):
    wait_page_loaded(driver)
    # grab + store the post URL first, straight from the browser
    post_url = driver.execute_script("return window.location.href;") or driver.current_url
    title = text_of(css(driver, SRC_TITLE))  # waits for the article to render
    img_url = find_article_image(driver)
    author = text_of(css(driver, SRC_AUTHOR))

    body = css(driver, SRC_BODY)
    paragraphs = [
        text_of(p) for p in body.find_elements(By.TAG_NAME, "p") if text_of(p)
    ]
    article = "\n\n".join(paragraphs)
    description = paragraphs[0] if paragraphs else ""

    return {
        "img_url": img_url,
        "title": title,
        "author": author,
        "article": article,
        "description": description,
        "url": post_url,  # real URL of the post we just scraped
    }


# ------------------------------------------------------------------ DASHBOARD
def login(driver):
    driver.get(LOGIN_URL)
    wait_page_loaded(driver)
    css(driver, LOGIN_PASS)
    fill(driver, LOGIN_PASS, PASSWORD, "password")
    human_wait()
    clickable(driver, LOGIN_BTN).click()
    # wait until loading is completed (we leave the login page)
    try:
        WebDriverWait(driver, 30).until(lambda d: "login" not in d.current_url)
    except TimeoutException:
        print("Login URL did not change; continuing anyway.")
    wait_page_loaded(driver)
    time.sleep(0.5)


def pick_random_category(driver):
    el = css(driver, "#category")

    if el.tag_name.lower() == "select":
        # wait until the options are actually loaded (more than just a placeholder)
        def options_ready(d):
            opts = Select(d.find_element(By.CSS_SELECTOR, "#category")).options
            return len([o for o in opts if (o.get_attribute("value") or "").strip()]) >= 1

        try:
            WebDriverWait(driver, 15).until(options_ready)
        except TimeoutException:
            print("  [category] no options with a value found!")
            return False

        # open the dropdown, wait 0.4s, then select a random one
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
        el.click()
        time.sleep(0.2)

        # options have no value="" attribute, so pick by index (select_by_value crashes)
        sel = Select(el)
        idx = random.randrange(len(sel.options))
        choice = sel.options[idx]
        value = choice.text.strip()
        sel.select_by_index(idx)
        # make sure React sees the change
        driver.execute_script(
            "arguments[0].dispatchEvent(new Event('change', {bubbles:true}));", el
        )
        # close the dropdown (Escape closes the native popup, blur drops focus)
        try:
            el.send_keys(Keys.ESCAPE)
        except Exception:
            pass
        driver.execute_script("arguments[0].blur();", el)
        time.sleep(0.1)
        print(f"  [category] selected: {choice.text.strip()!r} ({value})")
        return True

    # ---- custom dropdown fallback (button / div based)
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
    el.click()
    time.sleep(0.2)
    opts = driver.find_elements(
        By.CSS_SELECTOR, "[role='option'], [role='menuitem'], [role='listbox'] li, ul[role] li"
    )
    opts = [o for o in opts if o.is_displayed() and text_of(o)]
    if not opts:
        print("  [category] custom dropdown opened but no options found!")
        return False
    choice = random.choice(opts)
    print(f"  [category] selected: {text_of(choice)!r}")
    choice.click()
    time.sleep(0.3)
    # close the dropdown if it's still open
    if any(o.is_displayed() for o in driver.find_elements(
            By.CSS_SELECTOR, "[role='option'], [role='menuitem'], [role='listbox'] li")):
        el.send_keys(Keys.ESCAPE)
    driver.execute_script("arguments[0].blur();", el)
    return True

# //todo
def find_submit_button(driver, timeout=20):
    """Find the submit button: your exact XPath first, then text match, then CSS path."""
    def finder(d):
        for by, sel in (
            (By.XPATH, SUBMIT_BTN_ABS_XPATH),
            (By.XPATH, SUBMIT_BTN_XPATH),
            (By.CSS_SELECTOR, SUBMIT_BTN_CSS),
        ):
            for b in d.find_elements(by, sel):
                if b.is_displayed():
                    return b
        return False

    return WebDriverWait(driver, timeout).until(finder)

# //todo
def click_submit(driver):
    btn = find_submit_button(driver)
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
    time.sleep(0.2)
    print(f"  [submit] clicking button: {text_of(btn)!r}")
    try:
        WebDriverWait(driver, 10).until(lambda d: btn.is_enabled())
        btn.click()
    except Exception as e:  # intercepted / stale / disabled -> JS click
        print(f"  [submit] normal click failed ({type(e).__name__}), using JS click")
        driver.execute_script("arguments[0].click();", btn)
    return btn


def wait_submit_finished(driver, before_url):
    """Wait until the upload is really done, not just 'button is enabled'."""
    time.sleep(0.8)  # let the request start / button switch to loading state
    deadline = time.time() + 45
    while time.time() < deadline:
        if driver.current_url != before_url:
            return True
        try:
            btn = find_submit_button(driver, timeout=2)
            if btn.is_enabled():
                # form still here and enabled again -> request finished
                time.sleep(0.3)
                return True
        except TimeoutException:
            # button vanished (page changed / success screen)
            return True
        except Exception:
            return True
        time.sleep(0.3)
    print("  [submit] wait timed out, moving on.")
    return False


def post_to_dashboard(driver, data):
    driver.get(NEW_POST_URL)
    wait_page_loaded(driver)
    css(driver, "#title")  # form is ready

    human_wait()
    clickable(driver, IMG_TAB_BTN).click()

    fill(driver, IMG_INPUT, data["img_url"], "image url")
    fill(driver, "#title", data["title"], "title")
    fill(driver, "#description", data["description"], "description")
    fill(driver, "#author", data["author"], "author")
    fill(driver, "#body", data["article"], "body")

    human_wait()
    pick_random_category(driver)

    tags = ", ".join(random.sample(TAG_POOL, k=random.randint(2, 4)))
    fill(driver, "#tags", tags, "tags")
    print(f"  source url -> {data['url']}")
    css(driver, "#sourceUrl")  # wait for the field
    driver.execute_script(
        "arguments[0].scrollIntoView({block:'center'});", css(driver, "#sourceUrl")
    )
    if not fill(driver, "#sourceUrl", data["url"], "sourceUrl"):
        fill_source_url(driver, data["url"])  # fallback scan

    human_wait()
    before = driver.current_url
    click_submit(driver)
    wait_submit_finished(driver, before)


# ------------------------------------------------------------------ NAVIGATION
ANY_ARTICLE_LINKS = "a[href*='/story/article/']"


def collect_links(driver, queue, visited):
    """Add every unseen article link on the current page to the queue."""
    for sel in (SRC_NEXT_LINKS, ANY_ARTICLE_LINKS):
        for a in driver.find_elements(By.CSS_SELECTOR, sel):
            href = (a.get_attribute("href") or "").split("#")[0]
            if href and href not in visited and href not in queue:
                queue.append(href)


def go_to_next_article(driver, queue, visited):
    """Open the next unvisited article from the queue. Returns False if none left."""
    collect_links(driver, queue, visited)
    while queue:
        href = queue.pop(0)
        if href in visited:
            continue
        driver.get(href)
        wait_page_loaded(driver)
        return True
    return False


# ------------------------------------------------------------------ MAIN
def main():
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.page_load_strategy = "eager"  # don't wait for every ad/image to finish
    driver = webdriver.Chrome(options=options)

    try:
        # tab 1 = source site, tab 2 = dashboard
        driver.get(START_URL)
        wait_page_loaded(driver)
        src_tab = driver.current_window_handle
        driver.switch_to.new_window("tab")
        dash_tab = driver.current_window_handle
        login(driver)

        visited, queue = set(), []
        posted, attempts = 0, 0
        while posted < TOTAL_POSTS and attempts < TOTAL_POSTS * 3:
            attempts += 1
            print(f"\n=== Post {posted + 1}/{TOTAL_POSTS} ===")
            try:
                driver.switch_to.window(src_tab)
                visited.add(driver.current_url.split("#")[0])
                data = scrape_article(driver)
                visited.add(data["url"])
                print("Scraped:", data["title"])
                print("URL    :", data["url"])

                driver.switch_to.window(dash_tab)
                post_to_dashboard(driver, data)
                posted += 1
                print(f"Posted. ({posted}/{TOTAL_POSTS})")
            except Exception as e:
                print(f"  !! skipped this article: {type(e).__name__}: {e}".splitlines()[0])

            if posted < TOTAL_POSTS:
                driver.switch_to.window(src_tab)
                if not go_to_next_article(driver, queue, visited):
                    print("No more unvisited articles. Stopping.")
                    break

        print(f"\nDone. Posted {posted}/{TOTAL_POSTS}.")
    finally:
        input("Press Enter to close the browser...")
        driver.quit()


if __name__ == "__main__":
    main()