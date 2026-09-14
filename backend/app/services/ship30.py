import re
import logging
from typing import Dict, Any, List, Optional
from backend.app.config import settings
from backend.app.services.llm import (
    call_ollama,
    call_openai,
    call_anthropic,
    call_groq,
    ProviderError
)

logger = logging.getLogger(__name__)

SHIP30_SYSTEM_RUBRIC = """You are an elite ghostwriter and product strategist specialized in the Ship 30 for 30 framework (by Dickie Bush & Nicolas Cole).

Your mission is to transform grounded insights from Lenny's Podcast into a high-impact, publication-ready ~1,000 to 1,250-word atomic essay for product managers and tech operators.

STRICT SHIP 30 FOR 30 RUBRIC:
1. THE HOOK (First 2 sentences):
   - Open with an intriguing, counter-intuitive truth or urgent PM failure mode.
   - Promise a clear transformation: "Here is why [intuitive tactic] kills growth, and the exact framework to fix it."
2. ONE CORE IDEA:
   - Focus obsessively on one high-leverage growth or product concept. No tangents.
3. RHYTHM & FORMATTING ARCHITECTURE:
   - Clear, descriptive H2 and H3 subheadings that tell the story even if someone only skims.
   - Strategic **bolding** of key realizations on every section.
   - High rate of revelation: short punchy paragraphs (1-3 sentences max).
   - Bullet points for lists of 3-5 items to maximize clarity.
4. SOURCE TRACEABILITY:
   - Every single framework or tactic MUST explicitly cite the Lenny's Podcast guest, episode, and timestamp (e.g., "[Elena Verna, 00:00:45]").
5. THE ACTIONABLE TAKEAWAY (The "Tomorrow at 9 AM" Protocol):
   - Conclude with a concrete, step-by-step checklist the reader can run with their product team immediately.
6. LENGTH:
   - Must be comprehensive and detailed, targeting approximately 1,000 to 1,250 words.
"""

def generate_mock_ship30_essay(grounded_answer: str, sources: List[Dict[str, Any]], topic: Optional[str] = None) -> Dict[str, Any]:
    """
    Deterministic Ship 30 for 30 generator for offline/local evaluations.
    Produces a structured ~1,100 word essay adhering strictly to the rubric.
    """
    primary = sources[0] if sources else {
        "guest": "Elena Verna",
        "episode_title": "10 growth tactics that never work",
        "timestamp_range": "00:00:26 - 00:05:23",
        "timestamped_url": "https://www.youtube.com/watch?v=IHwS2By9UKM&t=26s"
    }

    guest = primary.get("guest", "Industry Expert")
    title_ep = primary.get("episode_title", "Lenny's Podcast")
    ts = primary.get("timestamp_range", "00:00:26")
    topic_clean = topic or f"Lessons from {guest} on Sustainable Growth"

    essay_md = f"""# The Antidote to Feature Factories: {topic_clean}

Most product teams think growth is a tactical problem solved by running more A/B tests and shipping more features. 

**They are completely wrong.**

In a standout discussion on *Lenny's Podcast* (*{title_ep}*, [{guest}, {ts}]), {guest} dismantled this misconception: true growth is never an afterthought you can outsource or sprint your way into—it must be engineered into the foundational loops of your product.

Here is the exact playbook to stop wasting engineering cycles and build a defensible growth engine.

---

## 1. The Trap: Mistaking Motion for Momentum

Every quarter, executive teams make the same fatal mistake:
- They see user acquisition flattening.
- They hire an agency or spin up an isolated "growth squad."
- They demand a high-tempo testing schedule of button colors and onboarding tooltips.

**Why this fails:** As {guest} highlights ({ts}), growth is not a marketing layer pasted on top of a product. If the core user journey doesn't naturally create retention and referral loops, tweaking conversion funnels is like rearranging deck chairs on the Titanic.

> **"To figure out your product-market fit and how to distribute it is not something you can outsource to somebody."**  
> — *{guest} on Lenny's Podcast*

When teams decouple product development from growth mechanics, they generate noise instead of compound interest.

---

## 2. The Core Framework: Closed Loops vs. Linear Leaks

Sustainable product-led companies do not rely on traditional linear sales funnels. They build self-reinforcing systems.

Consider the contrast between linear and looped product systems:

1. **The Linear Funnel (Fragile):**
   - Spend dollars or effort on top-of-funnel acquisition.
   - Force users through a rigid signup flow.
   - Hope a small percentage retain after 30 days.
   - *Result:* When spend stops, growth instantly flatlines.

2. **The Compounding Loop (Resilient):**
   - A new user experiences core value within their first session.
   - Their everyday product usage naturally generates public artifacts or collaborative invitations.
   - These artifacts attract the next cohort of qualified users at zero marginal acquisition cost.
   - *Result:* Growth accelerates with scale instead of becoming more expensive.

As documented in the transcript ({ts}), high-performing product leaders obsess over the **time-to-value (TTV)** and the friction points that prevent users from entering the compounding loop.

---

## 3. Three Common Anti-Patterns That Drain Engineering Bandwidth

During the episode, {guest} pointed out three specific initiatives that frequently consume months of engineering roadmap with near-zero lasting impact:

### Anti-Pattern A: The Vanity Redesign
A new executive or design lead arrives and promises that a complete visual overhaul of the marketing site will unlock hockey-stick growth. In practice, redesigns frequently tank search rankings and confuse existing workflows without addressing the underlying value proposition.

### Anti-Pattern B: The "Experimentation as an Excuse" Syndrome
Treating every minor decision as an A/B test paralyzes teams. When PMs require statistical significance for obvious UX fixes, velocity drops to zero. High-agency product teams reserve formal split testing for high-ambiguity, high-volume inflection points.

### Anti-Pattern C: Premature Monetization Gates
Slapping paywalls on arbitrary features before understanding user willingness-to-pay throttles activation. If users haven't formed a recurring habit around your core utility, pricing friction destroys retention before monetization can even begin.

---

## 4. The 4-Step "Tomorrow at 9 AM" Protocol

If you are a Product Manager leading a team tomorrow morning, here is how to apply this framework immediately:

1. **Audit Your Roadmap Against Retention:** Categorize every item on your current sprint into (a) Leverage, (b) Neutral, or (c) Overhead. Kill at least one project that fails to directly support user activation or recurring habit formation.
2. **Map the Natural Growth Loop:** Interview 5 power users. Ask: *"What is the exact moment someone else sees or benefits from what you created here?"* That interaction is the seed of your viral or content loop.
3. **Establish Guardrail Metrics:** Alongside your primary North Star Metric, define an anti-metric (such as Day-30 churn or customer support ticket volume) to ensure short-term gains aren't compromising brand equity.
4. **Align Engineering Directly to User Outcomes:** Stop rewarding feature output. Celebrate the metric moved and the friction removed.

---

## Conclusion & Grounded Sources

Building great software is hard; building software that distributes itself is an order of magnitude harder. The lesson from *{title_ep}* is unmistakable: real growth is structural, not superficial.

### Verified Citations
- **Primary Source:** {guest}, *{title_ep}*
- **Timestamp Window:** {ts}
- **Podcast:** Lenny's Podcast (Curated Archive)
"""
    # Count words
    word_count = len(re.findall(r'\b\w+\b', essay_md))
    
    # Generate clean, styled HTML version
    essay_html = convert_markdown_to_styled_html(essay_md, title_clean=topic_clean)

    return {
        "title": topic_clean,
        "essay_markdown": essay_md,
        "essay_html": essay_html,
        "word_count": word_count,
        "core_takeaway": f"Focus on structural compounding loops over linear hacks as explained by {guest} ({ts}).",
        "sources": sources,
        "provider_used": "mock (Ship 30 for 30 Skill Engine)"
    }

def convert_markdown_to_styled_html(md_text: str, title_clean: str) -> str:
    """
    Renders styled HTML for the Sandboxed Artifact Viewer.
    Strictly CSS and semantic markup; no JavaScript or inline scripts.
    """
    # Simple semantic HTML conversion for sandbox
    html_lines = []
    in_list = False

    for line in md_text.splitlines():
        line_str = line.strip()
        if not line_str:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            continue

        if line_str.startswith("# "):
            if in_list: html_lines.append("</ul>"); in_list = False
            html_lines.append(f"<h1>{line_str[2:]}</h1>")
        elif line_str.startswith("## "):
            if in_list: html_lines.append("</ul>"); in_list = False
            html_lines.append(f"<h2>{line_str[3:]}</h2>")
        elif line_str.startswith("### "):
            if in_list: html_lines.append("</ul>"); in_list = False
            html_lines.append(f"<h3>{line_str[4:]}</h3>")
        elif line_str.startswith("> "):
            if in_list: html_lines.append("</ul>"); in_list = False
            html_lines.append(f"<blockquote>{line_str[2:]}</blockquote>")
        elif line_str.startswith("- ") or line_str.startswith("* "):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            # Replace bold
            content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', line_str[2:])
            html_lines.append(f"<li>{content}</li>")
        elif re.match(r'^\d+\.\s', line_str):
            if in_list: html_lines.append("</ul>"); in_list = False
            content = re.sub(r'^\d+\.\s', '', line_str)
            content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)
            html_lines.append(f"<div class='numbered-item'><strong>Step</strong>: {content}</div>")
        elif line_str == "---":
            if in_list: html_lines.append("</ul>"); in_list = False
            html_lines.append("<hr />")
        else:
            if in_list: html_lines.append("</ul>"); in_list = False
            content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', line_str)
            content = re.sub(r'\*(.+?)\*', r'<em>\1</em>', content)
            html_lines.append(f"<p>{content}</p>")

    if in_list:
        html_lines.append("</ul>")

    body_content = "\n".join(html_lines)

    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title_clean}</title>
<style>
  :root {{
    --bg: #ffffff;
    --text: #1a202c;
    --primary: #4f46e5;
    --accent: #f43f5e;
    --border: #e2e8f0;
    --quote-bg: #f8fafc;
    --font-serif: "Merriweather", Georgia, serif;
    --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  }}
  body {{
    font-family: var(--font-serif);
    line-height: 1.8;
    color: var(--text);
    background: var(--bg);
    margin: 0;
    padding: 2.5rem;
    max-width: 760px;
    margin-left: auto;
    margin-right: auto;
  }}
  h1 {{
    font-family: var(--font-sans);
    font-size: 2.2rem;
    font-weight: 800;
    letter-spacing: -0.02em;
    line-height: 1.25;
    color: #0f172a;
    margin-bottom: 1.5rem;
    border-bottom: 2px solid var(--border);
    padding-bottom: 1rem;
  }}
  h2 {{
    font-family: var(--font-sans);
    font-size: 1.5rem;
    font-weight: 700;
    color: #1e293b;
    margin-top: 2.5rem;
    margin-bottom: 1rem;
    border-left: 4px solid var(--primary);
    padding-left: 0.75rem;
  }}
  h3 {{
    font-family: var(--font-sans);
    font-size: 1.2rem;
    font-weight: 600;
    color: #334155;
    margin-top: 1.75rem;
  }}
  p {{
    font-size: 1.08rem;
    margin-bottom: 1.25rem;
  }}
  strong {{
    font-weight: 700;
    color: #0f172a;
  }}
  blockquote {{
    background: var(--quote-bg);
    border-left: 4px solid var(--primary);
    margin: 1.5rem 0;
    padding: 1rem 1.5rem;
    font-style: italic;
    color: #334155;
    border-radius: 0 8px 8px 0;
  }}
  ul {{
    padding-left: 1.5rem;
    margin-bottom: 1.5rem;
  }}
  li {{
    font-size: 1.05rem;
    margin-bottom: 0.5rem;
  }}
  .numbered-item {{
    background: #f1f5f9;
    padding: 0.75rem 1rem;
    margin-bottom: 0.75rem;
    border-radius: 6px;
    font-family: var(--font-sans);
    font-size: 1rem;
  }}
  hr {{
    border: none;
    border-top: 1px solid var(--border);
    margin: 2.5rem 0;
  }}
  .badge {{
    display: inline-block;
    background: #ede9fe;
    color: #5b21b6;
    font-family: var(--font-sans);
    font-size: 0.75rem;
    font-weight: 600;
    padding: 0.25rem 0.6rem;
    border-radius: 9999px;
    margin-bottom: 1rem;
  }}
</style>
</head>
<body>
  <div class="badge">Ship 30 for 30 Atomic Essay</div>
  {body_content}
</body>
</html>"""
    return full_html

def execute_ship30_skill(
    grounded_answer: str,
    sources: List[Dict[str, Any]],
    topic: Optional[str] = None,
    provider: Optional[str] = None
) -> Dict[str, Any]:
    """
    Executes the Ship 30 for 30 essay generation skill.
    """
    active_provider = (provider or settings.LLM_PROVIDER).lower()

    if active_provider == "mock":
        return generate_mock_ship30_essay(grounded_answer, sources, topic)

    # Prepare prompt for LLM provider
    source_summaries = []
    for s in sources:
        source_summaries.append(f"- {s.get('speaker')} in {s.get('episode_title')} (timestamp: {s.get('timestamp_range')})")
    sources_text = "\n".join(source_summaries) if source_summaries else "Lenny's Podcast Episodes"

    user_instruction = (
        f"Rewrite this grounded advice from Lenny's Podcast into a ~1,100-word Ship 30 for 30 atomic essay.\n\n"
        f"TOPIC/QUESTION: {topic or 'Growth and Product Strategy'}\n\n"
        f"GROUNDED CONVERSATION SUMMARY:\n{grounded_answer}\n\n"
        f"VERIFIED PODCAST SOURCES TO CITE:\n{sources_text}\n\n"
        f"Ensure you strictly follow the Hook, Rhythm, One Core Idea, Bolding, and Tomorrow at 9 AM Takeaway."
    )

    try:
        if active_provider == "ollama":
            content = call_ollama(user_instruction, SHIP30_SYSTEM_RUBRIC)
            used = f"ollama ({settings.OLLAMA_MODEL})"
        elif active_provider == "openai":
            content = call_openai(user_instruction, SHIP30_SYSTEM_RUBRIC)
            used = f"openai ({settings.OPENAI_MODEL})"
        elif active_provider == "anthropic":
            content = call_anthropic(user_instruction, SHIP30_SYSTEM_RUBRIC)
            used = f"anthropic ({settings.ANTHROPIC_MODEL})"
        elif active_provider == "groq":
            content = call_groq(user_instruction, SHIP30_SYSTEM_RUBRIC)
            used = f"groq ({settings.GROQ_MODEL})"
        else:
            return generate_mock_ship30_essay(grounded_answer, sources, topic)

        title_match = re.search(r'^#\s*(.+)$', content, re.MULTILINE)
        essay_title = title_match.group(1).strip() if title_match else (topic or "Atomic Essay")
        word_count = len(re.findall(r'\b\w+\b', content))
        essay_html = convert_markdown_to_styled_html(content, essay_title)

        return {
            "title": essay_title,
            "essay_markdown": content,
            "essay_html": essay_html,
            "word_count": word_count,
            "core_takeaway": "Actionable synthesis adhering to Ship 30 for 30 protocol.",
            "sources": sources,
            "provider_used": used
        }
    except ProviderError:
        # Graceful fallback to mock essay if remote provider is unreachable or key missing
        logger.warning("Provider '%s' unavailable during Ship30 skill execution. Falling back to mock.", active_provider)
        return generate_mock_ship30_essay(grounded_answer, sources, topic)
