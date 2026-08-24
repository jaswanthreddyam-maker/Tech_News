import html
from typing import List, Dict, Any

class DailyBriefingRenderer:
    """
    Renders responsive dark-mode HTML and Plain Text email templates for Daily Briefing.
    """

    @classmethod
    def render_email(
        cls,
        edition_date: str,
        items: List[Dict[str, Any]],
        subscriber_email: str,
        click_url_builder: Any,
        unsubscribe_url: str,
        settings_url: str = "/settings",
    ) -> Dict[str, str]:
        item_count = len(items)
        headline_title = f"{item_count} stories worth knowing today" if item_count != 5 else "5 stories worth knowing today"

        # Plain Text rendering
        text_lines = [
            "TECH NEWS TODAY — YOUR DAILY BRIEFING",
            f"Edition: {edition_date}",
            "=" * 45,
            f"Here are the {headline_title.lower()}.\n"
        ]

        for item in items:
            rank_str = f"{item['rank']:02d}"
            click_url = click_url_builder(item['article_id'], item['url'])
            text_lines.append(f"{rank_str} | {item['headline'].upper()}")
            text_lines.append(f"Category: {item['category']} • {item['read_time']} min read")
            text_lines.append("Why it matters:")
            text_lines.append(f"{item['why_it_matters']}")
            text_lines.append(f"Read story -> {click_url}\n")

        text_lines.append("=" * 45)
        text_lines.append(f"Unsubscribe from Daily Briefing: {unsubscribe_url}")
        plain_text = "\n".join(text_lines)

        # HTML rendering
        items_html = ""
        for item in items:
            rank_str = f"{item['rank']:02d}"
            click_url = click_url_builder(item['article_id'], item['url'])
            safe_title = html.escape(str(item.get('headline') or 'Technology Update'))
            safe_why = html.escape(str(item.get('why_it_matters') or ''))
            safe_cat = html.escape(str(item.get('category') or 'Technology'))
            safe_source = html.escape(str(item.get('source') or 'Tech News'))

            items_html += f"""
            <!-- Story Card -->
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin-bottom: 32px; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 16px; background-color: #12151e; padding: 24px; color: #f3f4f6;">
                <tr>
                    <td>
                        <div style="font-family: monospace; font-size: 14px; font-weight: bold; color: #3b82f6; letter-spacing: 0.1em; margin-bottom: 8px;">
                            {rank_str} &nbsp;•&nbsp; {safe_cat.upper()} &nbsp;•&nbsp; {item['read_time']} MIN READ
                        </div>
                        <h2 style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 20px; font-weight: 700; color: #ffffff; margin: 0 0 12px 0; line-height: 1.35;">
                            {safe_title}
                        </h2>
                        <div style="background-color: rgba(59, 130, 246, 0.08); border-left: 3px solid #3b82f6; padding: 12px 16px; border-radius: 6px; margin-bottom: 16px;">
                            <div style="font-family: monospace; font-size: 11px; text-transform: uppercase; color: #9ca3af; letter-spacing: 0.08em; margin-bottom: 4px;">Why it matters</div>
                            <p style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 14px; color: #d1d5db; margin: 0; line-height: 1.5;">
                                {safe_why}
                            </p>
                        </div>
                        <div style="font-family: monospace; font-size: 13px;">
                            <a href="{click_url}" target="_blank" style="color: #60a5fa; text-decoration: none; font-weight: 600;">
                                Read story on Tech News Today &rarr;
                            </a>
                            <span style="color: #6b7280; font-size: 12px; margin-left: 12px;">via {safe_source}</span>
                        </div>
                    </td>
                </tr>
            </table>
            """

        html_body = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tech News Today — Daily Briefing</title>
</head>
<body style="background-color: #0b0d14; color: #e5e7eb; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 0;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #0b0d14; padding: 40px 16px;">
        <tr>
            <td align="center">
                <table role="presentation" width="100%" style="max-width: 600px;" cellspacing="0" cellpadding="0">
                    <!-- Header -->
                    <tr>
                        <td style="padding-bottom: 24px; border-bottom: 1px solid rgba(255, 255, 255, 0.1);">
                            <div style="font-family: monospace; font-size: 12px; letter-spacing: 0.15em; color: #3b82f6; text-transform: uppercase;">
                                TECH NEWS TODAY &nbsp;•&nbsp; EDITORIAL BRIEFING
                            </div>
                            <h1 style="font-size: 26px; font-weight: 800; color: #ffffff; margin: 8px 0 4px 0; letter-spacing: -0.02em;">
                                Your Daily Briefing
                            </h1>
                            <div style="font-family: monospace; font-size: 13px; color: #9ca3af;">
                                {edition_date} &nbsp;|&nbsp; {headline_title}
                            </div>
                        </td>
                    </tr>

                    <!-- Intro -->
                    <tr>
                        <td style="padding: 24px 0 16px 0; font-size: 15px; color: #9ca3af; line-height: 1.5;">
                            Good morning. Here are today's top executive technology developments, curated from canonical editorial signals.
                        </td>
                    </tr>

                    <!-- Articles -->
                    <tr>
                        <td>
                            {items_html}
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="padding-top: 24px; border-top: 1px solid rgba(255, 255, 255, 0.1); font-family: monospace; font-size: 12px; color: #6b7280; text-align: center; line-height: 1.6;">
                            <div>Sent to {html.escape(subscriber_email)} via Tech News Today Notification Engine</div>
                            <div style="margin-top: 8px;">
                                <a href="{unsubscribe_url}" style="color: #9ca3af; text-decoration: underline;">Unsubscribe from Daily Briefing</a>
                                &nbsp;•&nbsp;
                                <a href="{settings_url}" style="color: #9ca3af; text-decoration: underline;">Notification Settings</a>
                            </div>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""

        return {
            "subject": f"Tech News Today: Your Daily Briefing ({edition_date})",
            "html": html_body,
            "text": plain_text
        }
