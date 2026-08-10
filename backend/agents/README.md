# Tech News Today - Modular Multi-Agent System

This directory houses the autonomous agent codebase, divided by clear domain boundaries to prevent monolithic code files:

## Directory Structure

* `base/`: Baseline agent specifications (`BaseAgent` parent class).
* `scraper/`: Playwright scrapers with politer rates.
* `verifier/`: Content screening / validation agent.
* `summarizer/`: Prompt templates parsing news stories.
* `categorizer/`: Sorting stories by tech channels.
* `seo/`: Compiling custom metadata titles.
* `ranking/`: Weighting trending values.
* `shared/`: Shared tools (user-agents, proxies, rates).
* `orchestration/`: Running workflows asynchronously.
