import streamlit as st
import json
import os

SUGGESTED_QUESTIONS = [
    "Which stores will stock out this weekend?",
    "Why is Connaught Place flagged as high risk?",
    "Should I transfer or markdown the Sherwani Set?",
    "What's driving the velocity spike on Linen Kurta?",
    "Which SKUs should I pre-position before Diwali?",
    "Show me overstock items I can liquidate quickly",
]


def build_context(data):
    summary      = data["summary"]
    risk_df      = data["risk_df"]
    actions_df   = data["actions_df"]
    store_health = data["store_health"]
    events       = data["events"]
    today        = data["today"]

    # Top critical items
    critical = risk_df[risk_df["risk_severity"] == "critical"][
        ["sku_name", "size", "store_name", "risk_type", "doh", "daily_velocity_7d", "effective_stock"]
    ].head(15)

    # Top actions
    top_actions = actions_df[["sku_name", "size", "store_name", "risk_type", "recommended_action",
                               "transfer_qty", "from_location", "to_location", "prevented_loss",
                               "confidence", "priority_score"]].head(15) if actions_df is not None and not actions_df.empty else None

    # Store health
    store_h = store_health[["store_name", "city", "tier", "critical_count", "warning_count", "health_pct", "status"]]

    # Events
    ev_list = []
    for _, ev in events.iterrows():
        days_away = (ev["start_date"] - today).days
        ev_list.append(f"{ev['event_name']} in {days_away} days, affects {ev['affected_categories']}, {ev['expected_demand_multiplier']}x demand")

    context = f"""
TODAY: {today}
NETWORK SNAPSHOT:
- Total SKU-locations: {summary['total_sku_locations']}
- Critical stockouts: {summary['stockout_critical_count']}
- At-risk (warning): {summary['stockout_warning_count']}
- Overstock locations: {summary['overstock_count']}
- Overstock value: ₹{summary['overstock_value']:,}
- Network health: {summary['network_health_pct']}%
- Pending actions: {summary['pending_actions']}
- Velocity anomalies: {summary['anomaly_count']}
- Data gaps: {summary['data_gap_count']}
- Capital at risk (stockout): ₹{summary['capital_at_risk']:,}

UPCOMING EVENTS:
{chr(10).join(ev_list)}

STORE HEALTH:
{store_h.to_string(index=False)}

CRITICAL ITEMS (top 15):
{critical.to_string(index=False)}

TOP RECOMMENDED ACTIONS (top 15):
{top_actions.to_string(index=False) if top_actions is not None else "No actions available"}
"""
    return context


def call_groq(messages, context):
    try:
        from groq import Groq

        # Try Streamlit secrets first, then env var
        try:
            api_key = st.secrets["GROQ_API_KEY"]
        except Exception:
            api_key = os.environ.get("GROQ_API_KEY", "")

        if not api_key:
            return None, "no_key"

        client = Groq(api_key=api_key)

        system_prompt = f"""You are an expert inventory copilot for a multi-store Indian apparel retail ops manager.
You have real-time access to their network inventory data. Answer questions specifically using this data.
Be direct, specific, and operational. Reference actual SKU names, store names, and numbers.
Do NOT make up data not present in the context. Format responses clearly with bullet points where helpful.
Use ₹ for currency. Keep responses concise — this is an ops tool, not a report.

LIVE INVENTORY CONTEXT:
{context}"""

        api_messages = [{"role": "system", "content": system_prompt}]
        for msg in messages:
            api_messages.append({"role": msg["role"], "content": msg["content"]})

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=api_messages,
            max_tokens=800,
            temperature=0.3,
        )
        return response.choices[0].message.content, "ok"

    except ImportError:
        return None, "no_groq"
    except Exception as e:
        return None, str(e)


def render(data):
    st.markdown("""
    <div class="page-title">AI Inventory Copilot</div>
    <div class="page-subtitle">Ask anything about your inventory · Answers grounded in live network data</div>
    """, unsafe_allow_html=True)

    # ── API KEY CHECK ─────────────────────────────────────────────────────────
    has_key = False
    try:
        k = st.secrets.get("GROQ_API_KEY", "")
        has_key = bool(k)
    except Exception:
        has_key = bool(os.environ.get("GROQ_API_KEY", ""))

    if not has_key:
        st.markdown("""
        <div class="alert-banner">
            🔑 Add your Groq API key to enable the AI Copilot.<br>
            In Streamlit Cloud → App Settings → Secrets → add: <code>GROQ_API_KEY = "your-key"</code><br>
            Get a free key at <strong>console.groq.com</strong>
        </div>
        """, unsafe_allow_html=True)

        # Show demo mode
        st.markdown("""
        <div style="background:#0f1117;border:1px solid #1e2130;border-radius:12px;padding:20px 24px;margin-top:16px;">
            <div style="font-size:14px;font-weight:600;color:#f0f6fc;margin-bottom:12px;">💡 What you can ask the copilot:</div>
        </div>
        """, unsafe_allow_html=True)

        for q in SUGGESTED_QUESTIONS:
            st.markdown(f"""
            <div style="background:#0d1117;border:1px solid #1e2130;border-radius:8px;padding:10px 16px;margin-bottom:8px;font-size:13px;color:#c9d1d9;">
                💬 "{q}"
            </div>
            """, unsafe_allow_html=True)
        return

    # ── CONTEXT BUILDER ───────────────────────────────────────────────────────
    context = build_context(data)

    # ── CHAT UI ───────────────────────────────────────────────────────────────
    col_chat, col_suggest = st.columns([7, 3])

    with col_suggest:
        st.markdown("<div class='section-header'>Quick Questions</div>", unsafe_allow_html=True)
        for q in SUGGESTED_QUESTIONS:
            if st.button(q, key=f"sq_{q[:20]}", use_container_width=True):
                st.session_state.chat_history.append({"role": "user", "content": q})
                response, status = call_groq(st.session_state.chat_history, context)
                if response:
                    st.session_state.chat_history.append({"role": "assistant", "content": response})
                st.rerun()

    with col_chat:
        # Chat history
        chat_container = st.container()
        with chat_container:
            if not st.session_state.chat_history:
                st.markdown("""
                <div style="text-align:center;padding:48px 24px;color:#8b949e;">
                    <div style="font-size:32px;margin-bottom:12px;">🤖</div>
                    <div style="font-size:16px;font-weight:600;color:#f0f6fc;margin-bottom:8px;">Inventory Copilot Ready</div>
                    <div style="font-size:13px;">Ask me anything about your network — stockouts, transfers, markdowns, Diwali prep.</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                for msg in st.session_state.chat_history:
                    if msg["role"] == "user":
                        st.markdown(f"""
                        <div style="display:flex;justify-content:flex-end;margin-bottom:12px;">
                            <div style="background:#1c2433;border:1px solid #30363d;border-radius:12px 12px 2px 12px;padding:12px 16px;max-width:75%;font-size:13px;color:#f0f6fc;">
                                {msg['content']}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div style="display:flex;justify-content:flex-start;margin-bottom:12px;">
                            <div style="margin-right:8px;font-size:18px;margin-top:4px;">🤖</div>
                            <div style="background:#0f1117;border:1px solid #1e2130;border-radius:2px 12px 12px 12px;padding:12px 16px;max-width:85%;font-size:13px;color:#c9d1d9;line-height:1.6;">
                                {msg['content'].replace(chr(10), '<br>')}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

        # Input
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        user_input = st.chat_input("Ask about inventory, risks, transfers, or Diwali prep...")

        if user_input:
            st.session_state.chat_history.append({"role": "user", "content": user_input})

            with st.spinner("Analysing inventory data..."):
                response, status = call_groq(st.session_state.chat_history, context)

            if response:
                st.session_state.chat_history.append({"role": "assistant", "content": response})
            elif status == "no_key":
                st.error("API key not found. Check Streamlit secrets.")
            elif status == "no_groq":
                st.error("Groq library not installed. Add `groq>=0.4.0` to requirements.txt")
            else:
                st.error(f"API error: {status}")

            st.rerun()

        # Clear chat
        if st.session_state.chat_history:
            if st.button("🗑 Clear conversation", use_container_width=True):
                st.session_state.chat_history = []
                st.rerun()

    # ── CONTEXT PREVIEW ───────────────────────────────────────────────────────
    with st.expander("🔍 View data context sent to AI"):
        st.code(context, language="text")
