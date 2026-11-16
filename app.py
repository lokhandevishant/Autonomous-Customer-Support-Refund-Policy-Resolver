import streamlit as st
import pandas as pd
import main  # Connects directly to your main.py backend

st.set_page_config(
    page_title="Autonomous Refund & Policy Resolver",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 Agentic AI: Autonomous Refund & Policy Resolver")
st.caption("Powered by Groq Tool Calling (`get_order_details` → `check_return_policy` → `process_refund_or_escalate`), Live CSV Persistence & Human-in-the-Loop Override")

# Initialize session state for ticket history (filtering out any None entries from older main.py runs)
if "history" not in st.session_state:
    st.session_state.history = []
else:
    st.session_state.history = [item for item in st.session_state.history if isinstance(item, dict)]

# =====================================================================
# SIDEBAR: Controls, Policies Reference & Reset Button
# =====================================================================
with st.sidebar:
    st.header("⚙️ Demo Controls")
    if st.button("🔄 Reset All 105 Orders to PENDING", width="stretch"):
        if hasattr(main, "reset_all_orders_to_pending"):
            main.reset_all_orders_to_pending()
        else:
            orders = main.load_orders_from_csv()
            for oid in orders:
                orders[oid]["resolution_action"] = "PENDING"
                orders[oid]["ticket_id"] = ""
                orders[oid]["resolution_reason"] = ""
            main.save_orders_to_csv(orders)
        st.session_state.history = []
        st.success("All 105 orders in `orders_data.csv` reset to PENDING!")
        st.rerun()

    st.divider()
    st.subheader("📜 Return Policy Rules")
    policy_rows = []
    for cat, rules in main.POLICIES_DB.items():
        policy_rows.append({
            "Category": cat,
            "Standard Days": rules["standard_return_window_days"],
            "Gold Days": rules["gold_tier_return_window_days"],
            "Auto-Cap ($)": f"${rules['max_auto_refund_amount']:.0f}"
        })
    st.dataframe(pd.DataFrame(policy_rows), hide_index=True, width="stretch")

    st.divider()
    st.markdown(
        "**Decision Logic:**\n"
        "- **APPROVE_REFUND**: Inside return window AND amount $\\le$ Auto-Cap\n"
        "- **ESCALATE_TO_HUMAN**: Inside return window BUT amount $>$ Auto-Cap\n"
        "- **REJECT_REFUND**: Outside allowed return window"
    )

# =====================================================================
# TOP METRICS BAR (Live counts from orders_data.csv)
# =====================================================================
df_orders = pd.read_csv(main.CSV_FILENAME)
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Orders (CSV)", len(df_orders))
col2.metric("⏳ Pending", int((df_orders["resolution_action"] == "PENDING").sum()))
col3.metric("✅ Approved", int((df_orders["resolution_action"] == "APPROVE_REFUND").sum()))
col4.metric("⚠️ Escalated (Needs Human)", int((df_orders["resolution_action"] == "ESCALATE_TO_HUMAN").sum()))
col5.metric("❌ Rejected", int((df_orders["resolution_action"] == "REJECT_REFUND").sum()))

st.divider()

# =====================================================================
# MAIN INTERFACE: Left = Agent Tester | Right = Live CSV & Override
# =====================================================================
left_col, right_col = st.columns([1.15, 1])

with left_col:
    st.subheader("🎯 1. One-Click Demo Scenarios")
    b1, b2, b3 = st.columns(3)
    prompt_to_run = None

    if b1.button("✅ Demo 1: Gold VIP (ORD-1001)", width="stretch", help="34 days old, Gold Tier (45d limit), $180 <= $250 -> Auto-Approve"):
        prompt_to_run = "Hi, I want to return my headphones from order ORD-1001 for a refund."
    if b2.button("⚠️ Demo 2: Over Cap (ORD-1002)", width="stretch", help="10 days old, $620 > $250 cap -> Escalate to Human"):
        prompt_to_run = "Please refund my monitor on order ORD-1002, it has a dead pixel."
    if b3.button("❌ Demo 3: Late Return (ORD-1003)", width="stretch", help="40 days old, Standard Tier (30d limit) -> Reject"):
        prompt_to_run = "Can I get a refund for my shoes in order ORD-1003? They don't fit."

    st.subheader("💬 2. Or Test Any Order (ORD-1001 to ORD-1105)")
    with st.form("custom_ticket_form", clear_on_submit=False):
        quick_order = st.selectbox(
            "Quick-select an Order ID from CSV to inspect:",
            options=df_orders["order_id"].tolist(),
            format_func=lambda oid: (
                f"{oid} | {df_orders.loc[df_orders['order_id']==oid, 'customer_name'].values[0]} "
                f"({df_orders.loc[df_orders['order_id']==oid, 'customer_tier'].values[0]}) - "
                f"{df_orders.loc[df_orders['order_id']==oid, 'item'].values[0]} "
                f"[${df_orders.loc[df_orders['order_id']==oid, 'amount'].values[0]:.0f}, "
                f"{df_orders.loc[df_orders['order_id']==oid, 'days_since_purchase'].values[0]}d ago] "
                f"→ Status: {df_orders.loc[df_orders['order_id']==oid, 'resolution_action'].values[0]}"
            )
        )
        custom_text = st.text_input(
            "Customer Support Message (leave blank to auto-fill with selected order above):",
            placeholder="e.g., Hi, please refund my order ORD-1042 because it arrived damaged."
        )
        submitted = st.form_submit_button("🚀 Run Autonomous Agent", type="primary", width="stretch")
        if submitted:
            prompt_to_run = custom_text.strip() if custom_text.strip() else f"Hi, I would like to request a full refund for my order {quick_order}."

    # Execute the agent if triggered
    if prompt_to_run:
        with st.spinner("🤖 Agent is reasoning and calling tools via Groq..."):
            result = main.run_support_agent(prompt_to_run)
            if not isinstance(result, dict):
                result = {
                    "customer_message": prompt_to_run,
                    "steps": [],
                    "final_response": "Ticket processed! (Update `main.py` to the latest version to see step-by-step tool cards in the UI, or check your terminal output)."
                }
            st.session_state.history.insert(0, result)
            st.rerun()

    # Display Latest Execution Trace
    if st.session_state.history:
        latest = st.session_state.history[0]
        st.markdown("### 🧠 Latest Agent Execution Trace")
        st.info(f"**Customer Ticket:** {latest.get('customer_message', '')}")

        for step_info in latest.get("steps", []):
            tool_name = step_info["tool_name"]
            badge = "🔍" if tool_name == "get_order_details" else ("📏" if tool_name == "check_return_policy" else "⚡")
            with st.expander(f"{badge} Step {step_info['step']}: `{tool_name}`", expanded=True):
                st.markdown("**Tool Arguments Passed by LLM:**")
                st.json(step_info["tool_args"])
                st.markdown("**Tool Output Returned to LLM:**")
                st.json(step_info["tool_output"])

        st.success(f"**💌 Final Response to Customer:**\n\n{latest.get('final_response', '')}")

with right_col:
    # =================================================================
    # HUMAN-IN-THE-LOOP SUPERVISOR OVERRIDE PANEL
    # =================================================================
    st.subheader("👨‍💼 Human Supervisor Override Panel")
    st.caption("Step in to resolve `ESCALATE_TO_HUMAN` tickets or manually override any AI decision.")

    with st.container(border=True):
        override_filter = st.checkbox(
            "Show only `ESCALATE_TO_HUMAN` orders needing review",
            value=False
        )

        if override_filter:
            eligible_df = df_orders[df_orders["resolution_action"] == "ESCALATE_TO_HUMAN"]
        else:
            eligible_df = df_orders

        if eligible_df.empty:
            st.info("No orders currently in `ESCALATE_TO_HUMAN` state. Run **Demo 2 (ORD-1002)** or uncheck the filter above to override any order.")
        else:
            with st.form("human_override_form", clear_on_submit=False):
                target_oid = st.selectbox(
                    "Select Order to Override:",
                    options=eligible_df["order_id"].tolist(),
                    format_func=lambda oid: (
                        f"{oid} | {eligible_df.loc[eligible_df['order_id']==oid, 'customer_name'].values[0]} - "
                        f"{eligible_df.loc[eligible_df['order_id']==oid, 'item'].values[0]} "
                        f"(${eligible_df.loc[eligible_df['order_id']==oid, 'amount'].values[0]:.0f}) "
                        f"[{eligible_df.loc[eligible_df['order_id']==oid, 'resolution_action'].values[0]}]"
                    )
                )

                new_decision = st.selectbox(
                    "Supervisor Final Decision:",
                    options=["APPROVE_REFUND", "REJECT_REFUND", "ESCALATE_TO_HUMAN", "PENDING"]
                )

                supervisor_note = st.text_input(
                    "Supervisor Audit Note / Reason:",
                    value="Supervisor manual override: verified item condition and approved exception."
                )

                override_submitted = st.form_submit_button("🛡️ Apply Human Supervisor Override", width="stretch")

                if override_submitted:
                    orders_dict = main.load_orders_from_csv()
                    if target_oid in orders_dict:
                        orders_dict[target_oid]["resolution_action"] = new_decision
                        existing_ticket = orders_dict[target_oid].get("ticket_id", "")
                        orders_dict[target_oid]["ticket_id"] = existing_ticket if existing_ticket else f"OVR-{target_oid.split('-')[1]}"
                        orders_dict[target_oid]["resolution_reason"] = f"[HUMAN OVERRIDE] {supervisor_note}"
                        main.save_orders_to_csv(orders_dict)
                        st.success(f"Order `{target_oid}` manually updated to `{new_decision}` by Human Supervisor!")
                        st.rerun()

    st.divider()

    # =================================================================
    # LIVE CSV DATABASE VIEWER
    # =================================================================
    st.subheader("📊 Live `orders_data.csv` Database")
    filter_status = st.radio(
        "Filter orders by status:",
        ["All (105)", "Processed Only", "Escalated Only", "Pending Only"],
        horizontal=True
    )

    df_display = pd.read_csv(main.CSV_FILENAME)
    if filter_status == "Processed Only":
        df_display = df_display[df_display["resolution_action"] != "PENDING"]
    elif filter_status == "Escalated Only":
        df_display = df_display[df_display["resolution_action"] == "ESCALATE_TO_HUMAN"]
    elif filter_status == "Pending Only":
        df_display = df_display[df_display["resolution_action"] == "PENDING"]

    st.dataframe(
        df_display,
        width="stretch",
        height=380,
        hide_index=True
    )