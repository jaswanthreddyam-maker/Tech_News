from app.services.ingestion.processor import clean_and_sanitize_html


def test_clean_and_sanitize_html_unsafe_tags():
    # Unsafe tags like script, style, iframe, form should be completely stripped
    html = """
    <div>
        <h1>Header Title</h1>
        <script>alert('XSS');</script>
        <style>body { background: red; }</style>
        <iframe></iframe>
        <form><input type="text"/></form>
        <p>This is safe content.</p>
    </div>
    """
    cleaned = clean_and_sanitize_html(html)
    assert "Header Title" in cleaned
    assert "This is safe content" in cleaned
    assert "alert" not in cleaned
    assert "background" not in cleaned
    assert "iframe" not in cleaned
    assert "form" not in cleaned


def test_clean_and_sanitize_html_attributes():
    # Unsafe attributes like onclick should be removed, while safe attributes like href and target should be cleaned if javascript:
    html = """
    <div>
        <a href="https://example.com" onclick="doEvil()" target="_blank">Valid Link</a>
        <a href="javascript:alert('XSS')">Bad Link</a>
    </div>
    """
    cleaned = clean_and_sanitize_html(html)
    assert 'href="https://example.com"' in cleaned
    assert 'target="_blank"' in cleaned
    assert "onclick" not in cleaned
    assert "javascript:" not in cleaned


def test_clean_and_sanitize_html_boilerplate():
    # Elements with class/id containing social/advertisement/comment/sidebar should be stripped
    html = """
    <div>
        <p>Main content of the technology news story.</p>
        <div class="social-share-widget">Share this page on Twitter</div>
        <div id="sidebar-menu">Sidebar details</div>
        <div class="comment-section">Awesome post!</div>
    </div>
    """
    cleaned = clean_and_sanitize_html(html)
    assert "Main content" in cleaned
    assert "Share this" not in cleaned
    assert "Sidebar details" not in cleaned
    assert "Awesome post" not in cleaned


def test_clean_and_sanitize_html_structures():
    # Allowed tags (p, ul, h1-6, pre, blockquote) should be formatted into clean blocks
    html = """
    <div>
        <h1>Core Heading</h1>
        <p>Some paragraph text.</p>
        <blockquote>Quotes are preserved.</blockquote>
        <pre><code>x = 1</code></pre>
        <ul>
            <li>Item 1</li>
            <li>Item 2</li>
        </ul>
    </div>
    """
    cleaned = clean_and_sanitize_html(html)
    assert "<h1" in cleaned
    assert "<p>Some paragraph text.</p>" in cleaned
    assert "<blockquote" in cleaned
    assert "<pre><code>x = 1</code></pre>" in cleaned
    assert "<ul" in cleaned
    assert "<li" in cleaned


def test_clean_and_sanitize_plain_text():
    # Plain text inputs (e.g. from RSS description or Reddit summaries) should be cleanly formatted
    plain = "This is paragraph one.\n\nThis is paragraph two."
    cleaned = clean_and_sanitize_html(plain)
    assert "<p>This is paragraph one.</p>" in cleaned
    assert "<p>This is paragraph two.</p>" in cleaned
