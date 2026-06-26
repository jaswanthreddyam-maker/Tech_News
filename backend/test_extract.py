import asyncio
import re

import httpx
from bs4 import BeautifulSoup


def clean_html_debug(raw_html: str) -> dict:
    soup = BeautifulSoup(raw_html, "html.parser")
    title_tag = soup.find("title")
    title = title_tag.get_text().strip() if title_tag else ""

    boilerplate_tags = [
        "script", "style", "noscript", "iframe", "header", "footer", "nav", 
        "aside", "form", "svg", "button", "canvas", "video", "audio", "input",
        "select", "textarea", "modal", "dialog"
    ]
    for tag in soup.find_all(boilerplate_tags):
        tag.decompose()

    noise_words = {
        "comment", "share", "social", "advertisement", "sidebar", "menu", "footer", "header", "nav", 
        "widget", "banner", "promo", "popup", "cookie"
    }

    for element in list(soup.find_all()):
        if not getattr(element, "attrs", None):
            continue
        if element.name in ("article", "main", "body", "html"):
            continue

        classes = element.get("class", [])
        if isinstance(classes, str):
            classes = [classes]

        is_noise = False
        for cls in classes:
            for word in noise_words:
                if word in cls.lower():
                    # Exclude layout wrappers
                    if "with-" in cls.lower() or "has-" in cls.lower() or "container" in cls.lower() or "wrapper" in cls.lower() or "layout" in cls.lower():
                        continue
                    is_noise = True
                    break
            if is_noise:
                break

        elem_id = element.get("id", "")
        if elem_id and not is_noise:
            for word in noise_words:
                if word in elem_id.lower():
                    if "with-" in elem_id.lower() or "has-" in elem_id.lower() or "container" in elem_id.lower() or "wrapper" in elem_id.lower() or "layout" in elem_id.lower():
                        continue
                    is_noise = True
                    break

        if is_noise:
            element.decompose()

    body_container = None
    semantic_selectors = [
        "article", "main", "[itemprop='articleBody']", 
        ".article-content", ".post-content", ".entry-content", ".story-content",
        "#article-body", "#story-body", ".main-content"
    ]

    for selector in semantic_selectors:
        if selector.startswith("."):
            found = soup.find(class_=selector[1:])
        elif selector.startswith("#"):
            found = soup.find(id=selector[1:])
        elif selector.startswith("["):
            attr_name, attr_val = selector[1:-1].split("=")
            attr_val = attr_val.strip("'\"")
            found = soup.find(attrs={attr_name: attr_val})
        else:
            found = soup.find(selector)

        if found and len(found.get_text(strip=True)) > 200:
            body_container = found
            break

    if not body_container:
        body_container = soup.body if soup.body else soup

    content_elements = body_container.find_all(["p", "li", "h1", "h2", "h3", "h4", "h5", "h6"])
    if content_elements:
        cleaned_text = "\n\n".join(elem.get_text().strip() for elem in content_elements if elem.get_text().strip())
    else:
        cleaned_text = body_container.get_text(separator="\n\n", strip=True)

    cleaned_text = re.sub(r'\n{3,}', '\n\n', cleaned_text)
    cleaned_text = re.sub(r' +', ' ', cleaned_text)

    return {
        "title": title,
        "clean_text": cleaned_text,
        "word_count": len(cleaned_text.split())
    }

async def run():
    url = "https://blogs.nvidia.com/blog/hpe-ai-factory-agentic-enterprise"
    async with httpx.AsyncClient(follow_redirects=True) as client:
        r = await client.get(url)

    res = clean_html_debug(r.text)
    print("Title:", res["title"])
    print("Word Count:", res["word_count"])
    print("Sample content:")
    print(res["clean_text"][:500])

asyncio.run(run())
