import os
from typing import Protocol, List, Dict
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class BriefingGenerator(Protocol):
    """
    Interface for generating newsletter content.
    """
    async def generate_briefing(self) -> Dict[str, str]:
        """
        Returns a dict with 'title', 'content_html', and 'content_text'.
        """
        ...

class OpenAIBriefingGenerator:
    """
    Mock/AI implementation of the BriefingGenerator.
    """
    async def generate_briefing(self) -> Dict[str, str]:
        # In a real implementation, this would query the DB for the top 5 articles
        # and pass them to OpenAI to generate a summary.
        # For now, we mock the generated content.
        
        today = datetime.now().strftime("%Y-%m-%d")
        title = f"Tech News Today - Daily AI Briefing ({today})"
        
        content_text = f"Welcome to today's AI Briefing for {today}.\n\n"
        content_text += "1. Tech Giants Announce New AI Models\n"
        content_text += "2. The Future of Autonomous Agents\n"
        content_text += "3. Market Updates in Cloud Computing\n"
        
        content_html = f\"\"\"
        <html>
            <body style="font-family: sans-serif; line-height: 1.6; color: #333;">
                <h2>{title}</h2>
                <p>Here are the top stories curated for you today:</p>
                <ul>
                    <li><strong>Tech Giants Announce New AI Models</strong>: A summary of recent breakthroughs.</li>
                    <li><strong>The Future of Autonomous Agents</strong>: How agents are changing software development.</li>
                    <li><strong>Market Updates in Cloud Computing</strong>: Recent shifts in provider market share.</li>
                </ul>
                <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
                <p style="font-size: 12px; color: #999;">
                    You are receiving this because you subscribed to the Daily AI Briefing.<br>
                    <!-- Tracking Pixel and Unsubscribe links will be injected by the delivery task -->
                </p>
            </body>
        </html>
        \"\"\"
        
        logger.info(f"Generated briefing: {title}")
        return {
            "title": title,
            "content_html": content_html,
            "content_text": content_text
        }

def get_briefing_generator() -> BriefingGenerator:
    return OpenAIBriefingGenerator()
