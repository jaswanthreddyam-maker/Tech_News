import asyncio
import random
import os
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, text
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.source import Source
from app.models.article import Category, RawArticle, ProcessedArticle, ArticleReadModel
from app.models.tnt_knowledge import ArticleEntityLink, EntityNode, ArticleTopicLink, TopicNode
from app.core.events.models import EventOutbox

async def seed_data():
    if settings.APP_ENV != "development" or os.environ.get("ALLOW_DEMO_DATA", "false").lower() != "true":
        raise RuntimeError("Seed script aborted. Must run with APP_ENV=development and ALLOW_DEMO_DATA=true to prevent accidental data corruption.")

    print("==================================================")
    print("SEEDING HOMEPAGE WITH REALISTIC ARTICLES & HTML")
    print("==================================================")

    async with AsyncSessionLocal() as session:
        # Clear existing non-test data to start fresh
        await session.execute(text("DELETE FROM tnt_article_topics;"))
        await session.execute(text("DELETE FROM tnt_article_entities;"))
        await session.execute(text("DELETE FROM articles;"))
        await session.execute(text("DELETE FROM processed_articles;"))
        await session.execute(text("DELETE FROM raw_articles;"))
        await session.execute(text("DELETE FROM tnt_editorial_decision_logs;"))
        await session.commit()
    print("[OK] Existing articles cleared.")

    # 1. Setup Categories and Sources
    async with AsyncSessionLocal() as session:
        categories = {
            "artificial-intelligence": "Artificial Intelligence",
            "security": "Security",
            "semiconductors": "Semiconductors",
            "robotics": "Robotics",
            "startups": "Startups",
            "general": "General",
        }
        category_objects = {}
        for slug, name in categories.items():
            cat = (await session.execute(select(Category).where(Category.slug == slug))).scalars().first()
            if not cat:
                cat = Category(name=name, slug=slug)
                session.add(cat)
                await session.flush()
            category_objects[slug] = cat

        sources = {
            "NVIDIA AI Blog": "https://blogs.nvidia.com/feed/",
            "Google Blog": "https://blog.google",
            "OpenAI Blog": "https://openai.com/news/rss.xml",
            "TechCrunch": "https://techcrunch.com/feed/",
            "The Verge": "https://www.theverge.com/rss/index.xml",
            "Ars Technica": "https://feeds.arstechnica.com/arstechnica/index",
        }
        source_objects = {}
        for name, url in sources.items():
            src = (await session.execute(select(Source).where(Source.name == name))).scalars().first()
            if not src:
                src = Source(name=name, url=url, category="technology", method="rss", credibility_score=90, crawl_interval=3600, enabled=True, health_state="healthy", reliability_score=100.0)
                session.add(src)
                await session.flush()
            source_objects[name] = src

        # Ensure topics nodes exist
        for tname in ["Artificial Intelligence", "Security", "Semiconductors", "Robotics", "Startups", "General"]:
            topic_node = await session.get(TopicNode, tname)
            if not topic_node:
                topic_node = TopicNode(name=tname, taxonomy_category="technology")
                session.add(topic_node)
        
        # Ensure entity nodes exist
        entities = {
            "entity_google": ("Google", "organization"),
            "entity_openai": ("OpenAI", "organization"),
            "entity_nvidia": ("NVIDIA", "organization"),
            "entity_microsoft": ("Microsoft", "organization"),
            "entity_apple": ("Apple", "organization"),
        }
        for eid, (ename, etype) in entities.items():
            entity_node = await session.get(EntityNode, eid)
            if not entity_node:
                entity_node = EntityNode(id=eid, canonical_name=ename, entity_type=etype, aliases=[ename])
                session.add(entity_node)

        await session.commit()
        print("[OK] Categories, sources, topic and entity nodes verified.")

    # 2. Rich articles to seed
    seed_articles = [
        {
            "title": "NVIDIA Blackwell GPUs Enter Full Production for Enterprise AI Workloads",
            "source": "NVIDIA AI Blog",
            "category": "semiconductors",
            "summary": "NVIDIA CEO Jensen Huang announced that the highly anticipated Blackwell architecture GPUs have entered full mass production, with shipping slated for major cloud service providers early next quarter.",
            "clean_html": """
            <h2>The Next Generation of AI Supercomputing</h2>
            <p>NVIDIA has officially entered full mass production for its next-generation Blackwell architecture GPUs. Designed to handle the massive compute demands of trillion-parameter large language models, Blackwell represents a significant leap forward in density and efficiency.</p>
            <blockquote>
              "Blackwell is the engine to power this new industrial revolution. We are working with every major cloud provider to bring these systems to enterprise customers as fast as possible."
              <cite>— Jensen Huang, CEO of NVIDIA</cite>
            </blockquote>
            <h3>Architecture and Heat Management</h3>
            <p>The Blackwell GPU features 208 billion transistors manufactured on a custom TSMC 4NP process. A key innovation is the transition to liquid-cooled server architectures, allowing for much higher rack densities.</p>
            <table>
              <thead>
                <tr>
                  <th>Feature</th>
                  <th>Hopper (H100)</th>
                  <th>Blackwell (B200)</th>
                  <th>Improvement</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>Transistors</td>
                  <td>80 Billion</td>
                  <td>208 Billion</td>
                  <td>2.6x Increase</td>
                </tr>
                <tr>
                  <td>FP8 Compute</td>
                  <td>4 PFLOPS</td>
                  <td>20 PFLOPS</td>
                  <td>5x Boost</td>
                </tr>
                <tr>
                  <td>Interconnect Bandwidth</td>
                  <td>900 GB/s</td>
                  <td>1.8 TB/s</td>
                  <td>2x Increase</td>
                </tr>
              </tbody>
            </table>
            <h3>High-Density Liquid Cooling Racks</h3>
            <p>Hyperscalers are redesigning their data centers to accommodate the high power requirements of Blackwell racks, which can draw up to 120kW per rack. Key features include:</p>
            <ul>
              <li><strong>Direct-to-Chip Liquid Cooling</strong>: Circulating coolant directly over the silicon die to maintain optimal operating temperatures.</li>
              <li><strong>NVLink 5 Interconnect</strong>: Connecting up to 576 GPUs in a single high-speed cluster domain.</li>
              <li><strong>Energy Efficiency</strong>: Delivering up to 25x less energy consumption for LLM inference workloads compared to Hopper.</li>
            </ul>
            <p>Major cloud providers including Google Cloud, Microsoft Azure, and Amazon Web Services have already placed massive orders and are preparing to receive their first shipments by late Q3.</p>
            """,
            "key_takeaways": [
                {"title": "Full Mass Production", "description": "NVIDIA Blackwell GPUs are in mass production, shipping to top-tier cloud partners in early Q3.", "priority": 1},
                {"title": "Liquid Cooling Standards", "description": "Blackwell racks draw up to 120kW, driving data centers to adopt direct-to-chip liquid cooling systems.", "priority": 2},
                {"title": "5x Compute Boost", "description": "B200 provides 20 PFLOPS of FP8 compute, representing a massive 5x upgrade over Hopper.", "priority": 3}
            ],
            "images_metadata": [
                {
                    "url": "/api/v1/uploads/thumbnails/8252e3d1ce6d654d.webp",
                    "alt": "NVIDIA Blackwell GPU silicon chips and boards.",
                    "caption": "A close-up view of the NVIDIA Blackwell B200 accelerator board.",
                    "credit": "NVIDIA Newsroom"
                }
            ],
            "entities": ["entity_nvidia", "entity_google", "entity_microsoft"],
            "topics": ["Semiconductors", "Artificial Intelligence"],
            "impact_score": 95.0,
            "thumbnail": "8252e3d1ce6d654d.webp"
        },
        {
            "title": "OpenAI Unveils GPT-5: A Leap Towards General Reasoning and Advanced Agents",
            "source": "OpenAI Blog",
            "category": "artificial-intelligence",
            "summary": "OpenAI officially introduced GPT-5, highlighting its capability for complex multi-step reasoning, tool integration, and autonomous agent orchestration across dynamic tasks.",
            "clean_html": """
            <h2>A New Frontier in Machine Intelligence</h2>
            <p>Today, OpenAI officially announced the release of GPT-5, the latest iteration of its flagship large language model. This release marks a significant departure from previous architectures, focusing heavily on systematic multi-step reasoning, dynamic tool usage, and native agent integration.</p>
            <blockquote>
              "We've designed GPT-5 from the ground up to think before it speaks. It is not just predicting the next token; it is planning its approach."
              <cite>— Sam Altman, CEO of OpenAI</cite>
            </blockquote>
            <h3>Key Capabilities & Benchmarks</h3>
            <p>According to OpenAI's technical report, GPT-5 achieves state-of-the-art performance across several critical reasoning benchmarks:</p>
            <table>
              <thead>
                <tr>
                  <th>Benchmark</th>
                  <th>GPT-4o</th>
                  <th>GPT-5</th>
                  <th>Improvement</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>MATH (Advanced)</td>
                  <td>76.4%</td>
                  <td>94.2%</td>
                  <td>+17.8%</td>
                </tr>
                <tr>
                  <td>GPQA (Graduate-Level Science)</td>
                  <td>53.2%</td>
                  <td>78.9%</td>
                  <td>+25.7%</td>
                </tr>
                <tr>
                  <td>HumanEval (Coding)</td>
                  <td>88.1%</td>
                  <td>96.5%</td>
                  <td>+8.4%</td>
                </tr>
              </tbody>
            </table>
            <h3>How Developers Can Build with Agents</h3>
            <p>The new model introduces a native <code>AgentLoop</code> API that handles state management, scratchpad thinking, and tool calls automatically. Here is a basic code example:</p>
            <pre><code>import openai

client = openai.OpenAI()
agent = client.agents.create(
    model="gpt-5-preview",
    tools=["web_search", "code_interpreter"],
    instructions="Research and compile a daily summary of quantum computing breakthroughs."
)
response = agent.run(prompt="Analyze today's news.")
print(response.output)</code></pre>
            <ul>
              <li><strong>Systematic Planning</strong>: GPT-5 executes a reasoning trace before calling any tools.</li>
              <li><strong>Parallel Tool Calls</strong>: The model can execute up to 10 tool calls simultaneously.</li>
              <li><strong>Long-Context State</strong>: Features a 256k token context window with perfect recall.</li>
            </ul>
            <p>The release is rolling out gradually to API developers and Plus users starting this morning.</p>
            """,
            "key_takeaways": [
                {"title": "Systematic Reasoning", "description": "GPT-5 incorporates pre-response planning traces, leading to a massive score of 94.2% on advanced MATH benchmarks.", "priority": 1},
                {"title": "Native Agent API", "description": "The new AgentLoop API enables developers to build multi-agent applications with less boilerplate code.", "priority": 2},
                {"title": "Expanded Context", "description": "Context window has been expanded to 256k tokens, allowing complete codebases to be analyzed.", "priority": 3}
            ],
            "images_metadata": [
                {
                    "url": "/api/v1/uploads/thumbnails/8621798166c17bfe.webp",
                    "alt": "Visual representation of OpenAI's GPT-5 reasoning graph.",
                    "caption": "A conceptual graph showcasing multi-step planning loops in GPT-5.",
                    "credit": "OpenAI Media"
                }
            ],
            "entities": ["entity_openai", "entity_microsoft"],
            "topics": ["Artificial Intelligence"],
            "impact_score": 98.0,
            "thumbnail": "8621798166c17bfe.webp"
        },
        {
            "title": "Google DeepMind Releases AlphaFold 3 Source Code to Global Scientific Community",
            "source": "Google Blog",
            "category": "artificial-intelligence",
            "summary": "Google DeepMind has released the full source code and weights of AlphaFold 3, enabling researchers worldwide to model interactions between proteins, DNA, RNA, and chemical compounds.",
            "clean_html": """
            <h2>Unlocking Molecular Biology for Everyone</h2>
            <p>Google DeepMind today fulfilled its promise to the scientific community by open-sourcing the code and weights for AlphaFold 3. The tool enables researchers to predict structure and interactions across a wide variety of bio-molecular complexes.</p>
            <h3>Expanding Beyond Protein Folding</h3>
            <p>While AlphaFold 1 and 2 focused primarily on predicting the structures of single proteins, AlphaFold 3 expands this capability to complex assemblies. It predicts interactions between proteins, DNA double helices, single-stranded RNA, and small organic molecules (ligands).</p>
            <ul>
              <li><strong>Drug Discovery Acceleration</strong>: Modellers can test candidate drug molecules against target enzymes in minutes.</li>
              <li><strong>Genomic Engineering</strong>: Understanding how proteins bind to DNA helps design better gene-editing tools.</li>
              <li><strong>Academic Collaboration</strong>: The model is free for academic research, under a non-commercial open science license.</li>
            </ul>
            <p>DeepMind continues to collaborate with scientific institutes to build accessible web portals for labs without high-performance GPU hardware.</p>
            """,
            "key_takeaways": [
                {"title": "Open Source Code & Weights", "description": "AlphaFold 3 is now fully open-sourced, enabling offline execution and custom training.", "priority": 1},
                {"title": "Multi-Molecule Modeling", "description": "Predicts interactions between proteins, DNA, RNA, and ligands with high accuracy.", "priority": 2}
            ],
            "images_metadata": [
                {
                    "url": "/api/v1/uploads/thumbnails/86b5794ac6b5394a.webp",
                    "alt": "A detailed 3D render of a protein-DNA molecular structure.",
                    "caption": "AlphaFold 3 prediction showcasing a transcription factor binding to DNA.",
                    "credit": "Google DeepMind"
                }
            ],
            "entities": ["entity_google"],
            "topics": ["Artificial Intelligence"],
            "impact_score": 90.0,
            "thumbnail": "86b5794ac6b5394a.webp"
        },
        {
            "title": "Critical Zero-Day Vulnerability Discovered in Core Linux Kernel Network Stack",
            "source": "Ars Technica",
            "category": "security",
            "summary": "Security researchers have disclosed a critical remote code execution zero-day vulnerability in the Linux kernel netfilter subcomponent, urging immediate patching.",
            "clean_html": """
            <h2>Urgent Network Stack Patching Required</h2>
            <p>A severe remote code execution (RCE) vulnerability has been uncovered in the netfilter component of the Linux kernel. Rated 9.8 on the CVSS scale, this vulnerability allows unauthenticated remote attackers to trigger kernel panic or execute arbitrary code at system level.</p>
            <h3>Technical Root Cause</h3>
            <p>The flaw resides in the handling of certain malformed IPv6 packets. An integer overflow in the packet fragmentation reassembly code leads to a heap buffer overflow in kernel memory space.</p>
            <pre><code>// Vulnerable netfilter code snippet
struct sk_buff *reasm_pkt = reassemble_ipv6(fragments);
if (reasm_pkt->len > max_limit) {
    // Missing check leads to buffer overflow
    memcpy(kernel_buffer, reasm_pkt->data, reasm_pkt->len);
}</code></pre>
            <p>Mainstream enterprise Linux distributions (Red Hat, Ubuntu, Debian, and SUSE) have already released emergency kernel patches. Infrastructure managers are urged to apply these updates immediately and reboot affected systems.</p>
            """,
            "key_takeaways": [
                {"title": "Critical Netfilter Bug", "description": "A remote code execution vulnerability rated 9.8 CVSS was found in the Linux netfilter stack.", "priority": 1},
                {"title": "Integer Overflow Cause", "description": "The bug is caused by an integer overflow in IPv6 packet fragmentation reassembly.", "priority": 2},
                {"title": "Patches Released", "description": "All major Linux distros have released patches. Immediate reboots are required.", "priority": 3}
            ],
            "images_metadata": [
                {
                    "url": "/api/v1/uploads/thumbnails/8c965e9c87cf4968.webp",
                    "alt": "Abstract cybersecurity digital network matrix.",
                    "caption": "The Linux netfilter stack vulnerability exposes enterprise infrastructure.",
                    "credit": "Ars Technica Media"
                }
            ],
            "entities": [],
            "topics": ["Security"],
            "impact_score": 88.0,
            "thumbnail": "8c965e9c87cf4968.webp"
        },
        {
            "title": "Silicon Valley Quantum Computing Startup Raises $150M Series B at $1.2B Valuation",
            "source": "TechCrunch",
            "category": "startups",
            "summary": "A quantum computing compiler software startup closed a massive funding round, aiming to solve error-correction scalability on noisy intermediate-scale quantum devices.",
            "clean_html": """
            <h2>Commercializing Quantum Software Layers</h2>
            <p>Quantum compile tech startup Q-Logic has closed a $150M Series B investment round, pushing its post-money valuation to $1.2 billion. The round was led by major venture capital players from Silicon Valley and Europe.</p>
            <h3>Addressing Quantum Decoy and Errors</h3>
            <p>Q-Logic does not build quantum computers. Instead, it develops compiler software that sits between high-level algorithms and physical quantum hardware. Their compiler mitigates gate errors dynamically, improving logical qubit fidelity on noisy intermediate-scale quantum (NISQ) devices.</p>
            <ul>
              <li><strong>Hardware Agnostic</strong>: Compiles algorithms for superconducting, trapped ion, and photonic systems.</li>
              <li><strong>Fidelity Boost</strong>: Demonstrates up to 10x error reduction on current 100-qubit hardware.</li>
              <li><strong>Expansion Goals</strong>: Funding will be used to double the research team and build global enterprise consulting practices.</li>
            </ul>
            """,
            "key_takeaways": [
                {"title": "New Unicorn Minted", "description": "Quantum software startup Q-Logic hits $1.2B valuation following a $150M Series B round.", "priority": 1},
                {"title": "Error Mitigation Tech", "description": "The startup's compiler reduces physical gate errors on NISQ devices by up to 10x.", "priority": 2}
            ],
            "images_metadata": [
                {
                    "url": "/api/v1/uploads/thumbnails/901f3fd0e03f1ee0.webp",
                    "alt": "Venture capital meeting and quantum processor chips.",
                    "caption": "A silicon quantum processor chip loaded into a dilution refrigerator.",
                    "credit": "TechCrunch Media"
                }
            ],
            "entities": [],
            "topics": ["Startups"],
            "impact_score": 82.0,
            "thumbnail": "901f3fd0e03f1ee0.webp"
        },
        {
            "title": "Apple Intelligence Integrates On-Device LLMs Directly Into Apple Silicon Systems",
            "source": "The Verge",
            "category": "artificial-intelligence",
            "summary": "Apple announced the deep integration of private on-device foundation models running directly on Apple M-series and A-series silicon chips, prioritizing user privacy.",
            "clean_html": """
            <h2>Local Foundation Models Redefine Privacy</h2>
            <p>Apple has unveiled Apple Intelligence, a suite of foundation models embedded directly into iOS and macOS. Operating systems can now execute generative text, image generation, and workflow orchestration locally on-device, bypassing third-party cloud transfers.</p>
            <h3>Private Cloud Compute Architecture</h3>
            <p>For complex requests exceeding local hardware capability, Apple introduces Private Cloud Compute. Requests are sent to custom servers powered by Apple Silicon chips in secure enclaves.</p>
            <blockquote>
              "Your data is never stored on our servers. It is processed in transient memory and immediately destroyed. Independent cryptographers can inspect our server logs to verify this."
              <cite>— Craig Federighi, VP of Software Engineering at Apple</cite>
            </blockquote>
            <p>Supported hardware includes Apple A17 Pro chips and all M-series processors, which contain upgraded Neural Engine accelerators.</p>
            """,
            "key_takeaways": [
                {"title": "Private Cloud Compute", "description": "Apple routes larger AI jobs to custom silicon servers in secure, inspectable enclaves.", "priority": 1},
                {"title": "On-Device Processing", "description": "Smaller models run locally on M-series and A17+ processors, ensuring absolute user privacy.", "priority": 2}
            ],
            "images_metadata": [
                {
                    "url": "/api/v1/uploads/thumbnails/916872ad4fd22d9a.webp",
                    "alt": "Apple Silicon processor layout illustration.",
                    "caption": "The Neural Engine layout inside the Apple M-series system-on-chip.",
                    "credit": "Apple Media Relations"
                }
            ],
            "entities": ["entity_apple"],
            "topics": ["Artificial Intelligence", "Semiconductors"],
            "impact_score": 85.0,
            "thumbnail": "916872ad4fd22d9a.webp"
        },
        {
            "title": "Humanoid Robotics Startup Partners with Major Logistics Firm for Warehouse Trials",
            "source": "The Verge",
            "category": "robotics",
            "summary": "Robotics developer announced pilot deployments of its autonomous bipedal humanoid robots in commercial shipping centers, aiming to automate parcel sorting tasks.",
            "clean_html": """
            <h2>Humanoid Automation in Logistics</h2>
            <p>Robotics startup Dexterity Labs has formed a partnership with logistics giant FedShip to run active pilot testing of humanoid bipedal robots. The robots will perform packing, sorting, and palletizing work alongside human employees.</p>
            <h3>Engineering Specifications</h3>
            <p>The robot stands 5'9" tall, weighs 160 lbs, and features 44 degrees of freedom. Utilizing high-torque electric actuators, it can lift up to 45 lbs safely.</p>
            <ul>
              <li><strong>Vision Processing</strong>: Onboard stereoscopic depth cameras feed a localized transformer model for spatial planning.</li>
              <li><strong>Battery Life</strong>: Runs for up to 6 hours on a single hot-swappable battery pack.</li>
              <li><strong>Safety Protocols</strong>: Instantly halts movement if a human worker enters its immediate active work envelope.</li>
            </ul>
            <p>The pilot program will begin in three fulfillment centers starting next month, with a goal of evaluating speed, durability, and coordination.</p>
            """,
            "key_takeaways": [
                {"title": "Fulfillment Center Pilots", "description": "Dexterity Labs is deploying bipedal humanoid robots into FedShip sorting facilities next month.", "priority": 1},
                {"title": "6-Hour Hot-Swap Battery", "description": "Robots are powered by hot-swappable batteries, minimizing offline charging time in 24/7 warehouses.", "priority": 2}
            ],
            "images_metadata": [
                {
                    "url": "/api/v1/uploads/thumbnails/926cd0936438fb9b.webp",
                    "alt": "Humanoid robot carrying a package in a warehouse corridor.",
                    "caption": "Dexterity Labs' Apollo humanoid robot navigating a shipping lane.",
                    "credit": "Dexterity Labs PR"
                }
            ],
            "entities": [],
            "topics": ["Robotics"],
            "impact_score": 80.0,
            "thumbnail": "926cd0936438fb9b.webp"
        },
        {
            "title": "Microsoft Announces Sentinel AI: Autonomous Threat Remediation Platform",
            "source": "TechCrunch",
            "category": "security",
            "summary": "Microsoft is launching Sentinel AI, a cybersecurity agent tool that autonomously isolates infected network nodes and patches security group rules in real-time.",
            "clean_html": """
            <h2>Next-Gen Autonomous Cyber Defense</h2>
            <p>Microsoft today announced the general availability of Sentinel AI, an autonomous cybersecurity remediation platform built on top of Azure. Sentinel AI acts as an active copilot that monitors system logs and takes containment action within seconds of discovering an attack.</p>
            <h3>Agentic Response Loops</h3>
            <p>Standard security information and event management (SIEM) tools alert human operators. Sentinel AI, however, is authorized to perform network isolation and firewall adjustments automatically.</p>
            <ul>
              <li><strong>Immediate Isolation</strong>: If ransomware behavior is detected on a server, Sentinel AI quarantines the node instantly.</li>
              <li><strong>Dynamic Patching</strong>: Scans incoming attack vectors and updates network security rules across Azure virtual networks.</li>
              <li><strong>Audit Verification</strong>: Log traces show exactly why the AI isolated a node, maintaining regulatory compliance.</li>
            </ul>
            <p>Microsoft plans to roll out Sentinel AI integration to all Microsoft 365 Defender customers by the end of Q3.</p>
            """,
            "key_takeaways": [
                {"title": "Active Containment", "description": "Sentinel AI autonomously quarantines compromised network hosts within seconds, rather than alerting and waiting.", "priority": 1},
                {"title": "Defender Integration", "description": "The tool will be integrated into the Microsoft 365 Defender dashboard by late Q3.", "priority": 2}
            ],
            "images_metadata": [
                {
                    "url": "/api/v1/uploads/thumbnails/926f70936c26398f.webp",
                    "alt": "Cyber security operations center dashboard layout.",
                    "caption": "Sentinel AI threat analysis screen displaying quarantined assets.",
                    "credit": "Microsoft Press"
                }
            ],
            "entities": ["entity_microsoft"],
            "topics": ["Security", "Artificial Intelligence"],
            "impact_score": 84.0,
            "thumbnail": "926f70936c26398f.webp"
        }
    ]

    async with AsyncSessionLocal() as session:
        now = datetime.now(timezone.utc)

        for idx, item in enumerate(seed_articles):
            src_obj = source_objects[item["source"]]
            cat_obj = category_objects[item["category"]]
            
            # 1. Raw Article
            raw = RawArticle(
                title=item["title"],
                url=f"https://example.com/story-seed-{idx}",
                url_hash=f"seed_hash_url_{idx}",
                title_hash=f"seed_hash_title_{idx}",
                status="processed",
                is_test_data=False,
                scraped_at=now - timedelta(minutes=idx * 20)
            )
            session.add(raw)
            await session.flush()

            # 2. Processed Article
            processed = ProcessedArticle(
                raw_article_id=raw.id,
                source_id=src_obj.id,
                category_id=cat_obj.id,
                title=item["title"],
                slug=f"seed-article-slug-{idx}",
                summary=item["summary"],
                content=item["summary"],  # plain content
                clean_html=item["clean_html"],
                key_takeaways=item["key_takeaways"],
                source=src_obj.name,
                source_name=src_obj.name,
                source_url=raw.url,
                thumbnail_status="success",
                thumbnail_url=f"/api/v1/uploads/thumbnails/{item['thumbnail']}",
                thumbnail_local=f"/app/uploads/thumbnails/{item['thumbnail']}",
                thumbnail_quality_score=95,
                thumbnail_source="og:image",
                thumbnail_hash=f"hash_{idx}",
                enrichment_status="completed",
                completed_enrichment_stages=["thumbnail", "knowledge"],
                final_score=item["impact_score"],
                editorial_version="v1:2026-06-21-v1",
                is_test_data=False,
                published_status="published",
                published_at=now - timedelta(minutes=idx * 20)
            )
            session.add(processed)
            await session.flush()
            art_id = processed.id

            # 3. Read Model
            rm = ArticleReadModel(
                id=str(art_id),
                url=processed.slug,
                title=item["title"],
                content=item["clean_html"],  # Make content the rich HTML for rendering fallback compatibility
                summary=item["summary"],
                source=src_obj.name,
                hash=f"read_hash_{idx}",
                thumbnail_url=processed.thumbnail_url,
                thumbnail_local=processed.thumbnail_local,
                key_takeaways=item["key_takeaways"],
                images=item["images_metadata"],
                published_at=processed.published_at,
                is_test_data=False,
                final_score=processed.final_score
            )
            session.add(rm)
            await session.flush()

            # 4. Link topics and entities
            for tname in item["topics"]:
                link = ArticleTopicLink(article_id=str(art_id), topic_name=tname, confidence=1.0)
                session.add(link)

            for eid in item["entities"]:
                link = ArticleEntityLink(article_id=str(art_id), entity_id=eid, confidence=1.0)
                session.add(link)

        await session.commit()
        print(f"[OK] Successfully seeded {len(seed_articles)} rich articles with HTML & takeaways.")

if __name__ == "__main__":
    asyncio.run(seed_data())
