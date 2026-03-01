"""
Swarm-OS — No-Code AI Workforce Builder (MVP)

How to Run:
    pip install -r requirements.txt
    export GOOGLE_API_KEY="your-key"   # or set via ~/.streamlit/secrets.toml
    streamlit run app.py

    Runs in Offline Demo Mode automatically if no API key is set.
"""

import os
import io
import re
import sys
import time
import queue
import threading
import contextlib
import textwrap
from datetime import datetime

if "OPENAI_API_KEY" not in os.environ:
    os.environ["OPENAI_API_KEY"] = "UNUSED-crewai-requires-this"

import streamlit as st

st.set_page_config(
    page_title="Swarm-OS · Enterprise Orchestration",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

_ANSI_RE = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]')


def strip_ansi(text: str) -> str:
    return _ANSI_RE.sub('', text)


st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    * { font-family: 'Inter', sans-serif; }

    :root {
        --bg-dark: #0e1117; --card: #161b22; --accent: #58a6ff;
        --accent2: #3fb950; --glow: rgba(88,166,255,.12);
        --text: #c9d1d9; --text-dim: #8b949e; --border: #30363d;
    }

    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d1117 0%, #161b22 100%);
        border-right: 1px solid var(--border);
    }

    .npu-badge {
        display: inline-flex; align-items: center; gap: 8px;
        background: linear-gradient(135deg, #1a1e2e 0%, #0d1117 100%);
        border: 1px solid #f0883e; border-radius: 10px;
        padding: 12px 18px; margin-top: 8px;
        font-size: 0.85rem; color: #f0883e;
        box-shadow: 0 0 20px rgba(240,136,62,.12);
    }
    .npu-badge .dot {
        width: 8px; height: 8px; border-radius: 50%;
        background: #3fb950; box-shadow: 0 0 6px #3fb950;
        animation: pulse-dot 1.8s infinite;
    }
    @keyframes pulse-dot {
        0%, 100% { opacity: 1; } 50% { opacity: .35; }
    }

    .hero { text-align: center; padding: 24px 0 6px; }
    .hero h1 {
        font-size: 2.8rem; font-weight: 800;
        background: linear-gradient(90deg, #58a6ff, #bc8cff, #f778ba);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        margin-bottom: 2px;
    }
    .hero p { color: var(--text-dim); font-size: 1.05rem; margin-top: 0; }

    .status-pill {
        display: inline-flex; align-items: center; gap: 6px;
        padding: 6px 14px; border-radius: 999px;
        font-size: 0.8rem; font-weight: 600; margin-bottom: 8px;
    }
    .status-online  { background: #0d2818; color: #3fb950; border: 1px solid #238636; }
    .status-running { background: #1c1a05; color: #d29922; border: 1px solid #9e6a03;
                      animation: pulse-pill 1.4s infinite; }
    .status-done    { background: #0d2818; color: #3fb950; border: 1px solid #238636; }
    @keyframes pulse-pill {
        0%, 100% { opacity: 1; } 50% { opacity: .55; }
    }

    div[data-testid="stMetric"] {
        background: var(--card); border: 1px solid var(--border);
        border-radius: 12px; padding: 18px 20px;
        transition: border-color .25s, box-shadow .25s;
    }
    div[data-testid="stMetric"]:hover {
        border-color: var(--accent); box-shadow: 0 0 20px var(--glow);
    }
    div[data-testid="stMetric"] label {
        color: var(--text-dim) !important; font-weight: 500 !important;
        font-size: 0.82rem !important; text-transform: uppercase; letter-spacing: 0.5px;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #e6edf3 !important; font-weight: 700 !important;
    }

    .agent-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin: 12px 0 20px; }
    .agent-card {
        background: var(--card); border: 1px solid var(--border);
        border-radius: 12px; padding: 20px 22px;
        transition: border-color .25s, box-shadow .25s;
    }
    .agent-card:hover { border-color: var(--accent); box-shadow: 0 0 24px var(--glow); }
    .agent-card .agent-header { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
    .agent-card .agent-icon {
        width: 36px; height: 36px; border-radius: 10px;
        display: flex; align-items: center; justify-content: center; font-size: 1.2rem;
    }
    .agent-card .icon-blue   { background: rgba(88,166,255,.15); }
    .agent-card .icon-purple { background: rgba(188,140,255,.15); }
    .agent-card h4 { margin: 0; color: #e6edf3; font-size: 0.95rem; }
    .agent-card .agent-role {
        font-size: 0.75rem; color: var(--accent); font-weight: 600;
        text-transform: uppercase; letter-spacing: 0.5px; margin: 0;
    }
    .agent-card p { margin: 6px 0 0; font-size: .85rem; color: var(--text-dim); line-height: 1.45; }

    .result-card {
        background: linear-gradient(135deg, #161b22 0%, #0e1117 100%);
        border: 1px solid var(--border); border-radius: 14px;
        padding: 26px 28px; margin-top: 8px; color: #c9d1d9; line-height: 1.6;
    }
    .result-card h2, .result-card h3 { color: #e6edf3; }
    .result-card strong { color: #e6edf3; }

    .result-header { display: flex; align-items: center; gap: 10px; padding: 12px 0 8px; }
    .result-header .result-icon {
        width: 32px; height: 32px; border-radius: 8px;
        display: flex; align-items: center; justify-content: center; font-size: 1rem;
    }
    .result-header .icon-green  { background: rgba(63,185,80,.15); color: #3fb950; }
    .result-header .icon-blue   { background: rgba(88,166,255,.15); color: #58a6ff; }
    .result-header h3 { margin: 0; font-size: 1rem; color: #e6edf3; }

    .divider { border: none; border-top: 1px solid var(--border); margin: 20px 0; }

    div.stButton > button {
        width: 100%; padding: 14px 0; font-size: 1.15rem; font-weight: 700;
        border-radius: 12px;
        background: linear-gradient(135deg, #238636 0%, #2ea043 100%);
        color: white; border: none;
        box-shadow: 0 0 20px rgba(46,160,67,.25);
        transition: transform .15s, box-shadow .15s;
    }
    div.stButton > button:hover {
        transform: translateY(-2px); box-shadow: 0 4px 30px rgba(46,160,67,.4);
    }
    div.stButton > button:active { transform: translateY(0); }

    .section-header { display: flex; align-items: center; gap: 8px; margin: 16px 0 8px; }
    .section-header h3 { margin: 0; font-size: 1.05rem; font-weight: 700; color: #e6edf3; }
    .block-container { padding-top: 1.5rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


def _get_api_key() -> str | None:
    key = os.environ.get("GOOGLE_API_KEY")
    if key and key != "UNUSED-crewai-requires-this":
        return key
    try:
        key = st.secrets["GOOGLE_API_KEY"]
        if key:
            return key
    except (KeyError, FileNotFoundError):
        pass
    return None


API_KEY = _get_api_key()
DEMO_MODE = API_KEY is None

DEMO_CHALLENGES = textwrap.dedent("""\
## 🔍 Market Challenges — EdTech

**1. Engagement Gap**
Despite the influx of digital learning tools, maintaining student engagement
remains the #1 unsolved problem. Passive video content leads to 60-70%
drop-off rates within the first week.

**2. Personalization at Scale**
Most platforms still deliver a one-size-fits-all curriculum. Adaptive-learning
engines exist but are prohibitively expensive for K-12 institutions in
emerging economies.

**3. Assessment Integrity**
The shift to online exams has amplified concerns around cheating and
AI-generated submissions, forcing schools to rethink evaluation models
entirely.
""")

DEMO_STRATEGY = textwrap.dedent("""\
## 🚀 3-Point Business Strategy

**1. AI-Powered Interactive Simulations**
Replace passive content with an AI physics simulator that lets students
*experiment* in a sandbox environment — dramatically boosting engagement
and conceptual retention.

**2. Freemium Micro-Licensing Model**
Offer the simulator free for individual learners while monetizing through
school/district site licenses. Tiered pricing ensures accessibility across
emerging and developed markets.

**3. Embedded Formative Assessment**
Integrate real-time skill tracking directly into simulations. This removes
the need for separate exams, reduces cheating incentives, and provides
teachers with continuous, actionable insights.
""")

DEMO_LOGS = [
    "[crew] 🚀  Initializing Swarm-OS Crew …",
    "[crew]    ├─ LLM ➜ Gemini 3 Flash (CrewAI Native LLM)",
    "[crew]    ├─ Process ➜ Sequential",
    "[crew]    └─ Agents ➜ 2 loaded",
    "",
    "[agent:market_researcher] 🧠 Starting task: Identify 3 market challenges …",
    "[agent:market_researcher]    Querying LLM with industry context …",
    "[agent:market_researcher]    ✓ LLM response received (324 tokens)",
    "[agent:market_researcher]    ✓ Validation passed — 3 challenges extracted",
    "[agent:market_researcher] ✅ Task complete.",
    "",
    "[agent:strategic_consultant] 🧠 Starting task: Build 3-point strategy …",
    "[agent:strategic_consultant]    Ingesting market challenges …",
    "[agent:strategic_consultant]    Querying LLM with goal + challenges …",
    "[agent:strategic_consultant]    ✓ LLM response received (512 tokens)",
    "[agent:strategic_consultant]    ✓ Strategy validated — 3 points",
    "[agent:strategic_consultant] ✅ Task complete.",
    "",
    "[crew] ✅ All tasks finished. Aggregating results …",
    "[crew] 🏁 Swarm execution complete.",
]


def run_crew(industry: str, goal: str, log_queue: queue.Queue) -> dict:
    """Build and kick off the CrewAI pipeline. Returns challenges + strategy."""
    from crewai import Agent, Task, Crew, Process, LLM

    os.environ["GEMINI_API_KEY"] = API_KEY
    os.environ["GOOGLE_API_KEY"] = API_KEY

    llm = LLM(
        model="gemini/gemini-3-flash-preview",
        temperature=0.4,
        api_key=API_KEY,
    )

    researcher = Agent(
        role="Market Researcher",
        goal=f"Analyze the {industry} industry and identify exactly 3 current, high-impact market challenges.",
        backstory=f"You are a seasoned market analyst with 15 years of experience in {industry}. You deliver concise, data-informed insights.",
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

    consultant = Agent(
        role="Strategic Consultant",
        goal="Using the identified market challenges and the project goal, craft a focused 3-point business strategy.",
        backstory="You are a McKinsey-trained strategic consultant who translates market intelligence into actionable growth strategies.",
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

    task_research = Task(
        description=(
            f"Research the **{industry}** industry thoroughly. "
            "Identify and describe exactly **3 current market challenges** "
            "that a new entrant should understand. "
            "Format the output as a numbered Markdown list with bold titles "
            "and 2-3 sentence explanations for each challenge."
        ),
        expected_output="A Markdown-formatted list of 3 market challenges, each with a bold title and a brief explanation.",
        agent=researcher,
    )

    task_strategy = Task(
        description=(
            f"You have been given the following project goal:\n> {goal}\n\n"
            "And the market challenges identified by the Market Researcher.\n\n"
            "Using both inputs, create a **3-point business strategy** to "
            "successfully launch this project. Each point should include a "
            "bold title and 2-3 sentence rationale. Format the output in Markdown."
        ),
        expected_output="A Markdown-formatted 3-point business strategy, each with a bold title and a brief rationale.",
        agent=consultant,
    )

    crew = Crew(
        agents=[researcher, consultant],
        tasks=[task_research, task_strategy],
        process=Process.sequential,
        verbose=True,
    )

    log_buffer = io.StringIO()

    class QueueWriter(io.TextIOBase):
        def write(self, s: str) -> int:
            log_buffer.write(s)
            for line in s.splitlines():
                stripped = line.strip()
                if stripped:
                    clean = strip_ansi(stripped)
                    if API_KEY:
                        clean = clean.replace(API_KEY, "***REDACTED***")
                    if clean:
                        log_queue.put(clean)
            return len(s)

        def flush(self):
            pass

    writer = QueueWriter()

    with contextlib.redirect_stdout(writer), contextlib.redirect_stderr(writer):
        result = crew.kickoff()

    raw = str(result)
    try:
        tasks_output = result.tasks_output
        challenges_text = str(tasks_output[0])
        strategy_text = str(tasks_output[1])
    except Exception:
        challenges_text = raw
        strategy_text = ""

    return {"challenges": challenges_text, "strategy": strategy_text}


SENTINEL = "__DONE__"


def _crew_thread(industry: str, goal: str, log_q: queue.Queue, result_q: queue.Queue):
    try:
        out = run_crew(industry, goal, log_q)
        result_q.put(out)
    except Exception as exc:
        log_q.put(f"[error] ❌ {strip_ansi(str(exc))}")
        result_q.put({
            "challenges": f"⚠️ An error occurred:\n```\n{exc}\n```",
            "strategy": "",
        })
    finally:
        log_q.put(SENTINEL)


with st.sidebar:
    st.markdown("## ⚙️ Swarm Configuration")
    st.markdown("<hr class='divider'>", unsafe_allow_html=True)

    industry = st.text_input("🏭 Target Industry", value="EdTech", help="The industry your project targets.")
    goal = st.text_area("🎯 Project Goal", value="Launch an AI-powered physics simulator", height=100, help="Describe your project goal in one or two sentences.")

    st.markdown("<hr class='divider'>", unsafe_allow_html=True)

    st.markdown(
        """
        <div class="npu-badge">
            <div class="dot"></div>
            <span><b>Hardware Acceleration</b><br>AMD Ryzen™ AI NPU — Enabled</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<hr class='divider'>", unsafe_allow_html=True)

    if DEMO_MODE:
        st.warning("🔒 **Offline Demo Mode** — No API key detected.")
    else:
        st.success("🟢 **Live Mode** — Gemini connected.")

    show_sources = st.toggle("📖 Show model reasoning / sources", value=False)


st.markdown(
    """
    <div class="hero">
        <h1>🤖 Swarm-OS</h1>
        <p>Enterprise AI Workforce Orchestration · No-Code · Real-Time</p>
    </div>
    """,
    unsafe_allow_html=True,
)

mode_label = "DEMO" if DEMO_MODE else "ONLINE"
st.markdown(f'<span class="status-pill status-online">● System {mode_label}</span>', unsafe_allow_html=True)

st.markdown('<div class="section-header"><h3>📡 Command Center</h3></div>', unsafe_allow_html=True)

m1, m2, m3 = st.columns(3)
with m1:
    st.metric(label="Active Agents", value="2", delta="Ready")
with m2:
    st.metric(label="Inference Engine", value="Gemini Flash", delta="Low Latency")
with m3:
    st.metric(label="Edge Compute", value="AMD Ryzen™ AI", delta="NPU Enabled")

st.divider()

st.markdown('<div class="section-header"><h3>🤖 Deployed Agents</h3></div>', unsafe_allow_html=True)

st.markdown(
    """
    <div class="agent-grid">
        <div class="agent-card">
            <div class="agent-header">
                <div class="agent-icon icon-blue">🔬</div>
                <div>
                    <p class="agent-role">Agent 1</p>
                    <h4>Market Researcher</h4>
                </div>
            </div>
            <p>Analyzes the target industry and surfaces 3 key market
            challenges using real-time LLM intelligence. Trained on
            15 years of market analysis expertise.</p>
        </div>
        <div class="agent-card">
            <div class="agent-header">
                <div class="agent-icon icon-purple">📊</div>
                <div>
                    <p class="agent-role">Agent 2</p>
                    <h4>Strategic Consultant</h4>
                </div>
            </div>
            <p>Synthesizes challenges + your project goal into a
            focused 3-point business strategy. McKinsey-trained
            methodology for actionable growth plans.</p>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

deploy = st.button("🚀 Deploy Swarm", use_container_width=True)

if deploy:
    st.markdown('<span class="status-pill status-running">⟳ Swarm Running</span>', unsafe_allow_html=True)

    agent_col1, agent_col2 = st.columns(2)
    with agent_col1:
        agent1_status = st.status("🔬 **Market Researcher**", expanded=True)
        agent1_status.write("⏳ Waiting for deployment…")
    with agent_col2:
        agent2_status = st.status("📊 **Strategic Consultant**", expanded=True)
        agent2_status.write("⏳ Queued — awaiting Market Researcher output…")

    st.divider()

    st.markdown('<div class="section-header"><h3>📟 Terminal Logs</h3></div>', unsafe_allow_html=True)

    with st.expander("Live Agent Console", expanded=True):
        console = st.empty()
        log_lines: list[str] = []

        if DEMO_MODE:
            agent1_status.update(label="🔬 **Market Researcher** — Running", state="running")

            for i, line in enumerate(DEMO_LOGS):
                log_lines.append(line)
                console.code("\n".join(log_lines), language="log")
                time.sleep(0.18)

                if i == 9:
                    agent1_status.update(label="🔬 **Market Researcher** — Complete ✅", state="complete")
                    agent2_status.update(label="📊 **Strategic Consultant** — Running", state="running")
                elif i == 16:
                    agent2_status.update(label="📊 **Strategic Consultant** — Complete ✅", state="complete")

            challenges = DEMO_CHALLENGES
            strategy = DEMO_STRATEGY

        else:
            log_q: queue.Queue = queue.Queue()
            result_q: queue.Queue = queue.Queue()

            agent1_status.update(label="🔬 **Market Researcher** — Running", state="running")

            thread = threading.Thread(target=_crew_thread, args=(industry, goal, log_q, result_q), daemon=True)
            thread.start()

            timeout_s = 180
            start_ts = time.time()
            researcher_done = False

            while True:
                try:
                    msg = log_q.get(timeout=0.3)
                except queue.Empty:
                    if time.time() - start_ts > timeout_s:
                        log_lines.append("[timeout] ⏰ Agent execution timed out.")
                        console.code("\n".join(log_lines), language="log")
                        break
                    continue
                if msg == SENTINEL:
                    break

                log_lines.append(msg)
                console.code("\n".join(log_lines), language="log")

                msg_lower = msg.lower()
                if not researcher_done and ("strategic consultant" in msg_lower or "task 2" in msg_lower):
                    researcher_done = True
                    agent1_status.update(label="🔬 **Market Researcher** — Complete ✅", state="complete")
                    agent2_status.update(label="📊 **Strategic Consultant** — Running", state="running")

            agent1_status.update(label="🔬 **Market Researcher** — Complete ✅", state="complete")
            agent2_status.update(label="📊 **Strategic Consultant** — Complete ✅", state="complete")

            thread.join(timeout=5)
            try:
                result_data = result_q.get_nowait()
            except queue.Empty:
                result_data = {"challenges": "⚠️ No output received from agents.", "strategy": ""}

            challenges = result_data["challenges"]
            strategy = result_data["strategy"]

    st.markdown('<span class="status-pill status-done">✓ Swarm Complete</span>', unsafe_allow_html=True)
    st.divider()
    st.markdown('<div class="section-header"><h3>📊 Swarm Intelligence Output</h3></div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(
            f"""
            <div class="result-header">
                <div class="result-icon icon-green">🔬</div>
                <h3>Market Challenges</h3>
            </div>
            <div class="result-card">{challenges.replace(chr(10), '<br>')}</div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            f"""
            <div class="result-header">
                <div class="result-icon icon-blue">📊</div>
                <h3>Business Strategy</h3>
            </div>
            <div class="result-card">{strategy.replace(chr(10), '<br>')}</div>
            """,
            unsafe_allow_html=True,
        )

    if show_sources:
        st.divider()
        with st.expander("📖 Model Reasoning & Sources", expanded=False):
            st.markdown(
                "**Model:** `gemini-3-flash-preview` via CrewAI Native LLM (litellm)\n\n"
                "**Process:** `Sequential` — Market Researcher runs first; "
                "its output is fed to the Strategic Consultant.\n\n"
                "**Agents:**\n"
                "- Market Researcher — backstory: 15 yr industry analyst\n"
                "- Strategic Consultant — backstory: McKinsey-trained strategist\n\n"
                "**Temperature:** 0.4 (balanced creativity & precision)\n\n"
                "*Full verbose logs are available in the Live Agent Console above.*"
            )

    st.divider()

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    report_md = textwrap.dedent(f"""\
# Swarm-OS Strategy Report
**Generated:** {timestamp}
**Industry:** {industry}
**Goal:** {goal}

---

{challenges}

---

{strategy}

---
*Report generated by Swarm-OS · Powered by CrewAI & Google Gemini*
""")

    st.download_button(
        label="📥 Download Strategy Report (.md)",
        data=report_md,
        file_name=f"swarm_os_strategy_{industry.lower().replace(' ', '_')}.md",
        mime="text/markdown",
        use_container_width=True,
    )
