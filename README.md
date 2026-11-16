# Autonomous Customer Support Refund & Policy Resolver (Agentic AI)

## 📌 Project Overview

In modern e-commerce and retail operations, customer support teams spend thousands of hours manually cross-referencing refund requests against order history, product categories, customer loyalty tiers, and company return policies.

This project demonstrates a **modern Agentic AI workflow** powered by the **Groq API** that autonomously resolves customer refund tickets. Instead of merely generating conversational replies, the AI agent uses **3 deterministic function-calling tools** to inspect a local CSV database of 105 orders (`orders_data.csv`), evaluate dynamic policy constraints, execute a binding business decision (`APPROVE_REFUND`, `ESCALATE_TO_HUMAN`, or `REJECT_REFUND`), and write the audit trail directly back into the CSV file.

To ensure enterprise safety and full human control, the project includes an interactive **Streamlit Dashboard (`app.py`)** featuring a **Human-in-the-Loop (HITL) Supervisor Override Panel**.

---

## 🧠 How the Agentic Workflow Works (3-Tool Loop)

When a customer submits a natural-language refund request (e.g., *"Hi, I want to return my headphones from order ORD-1001"*), the LLM enters an autonomous **Reason + Act (ReAct)** loop:

1. **Tool 1: `get_order_details(order_id)`**
   * **Action:** Queries `orders_data.csv` for the given Order ID (`ORD-1001` to `ORD-1105`).
   * **Data Retrieved:** Customer name, loyalty tier (`Standard` vs. `Gold`), item name, product category, order dollar amount, and `days_since_purchase`.

2. **Tool 2: `check_return_policy(category, customer_tier)`**
   * **Action:** Looks up the company's return rules for that specific product category (`Electronics`, `Apparel`, `Home & Kitchen`, `Footwear`, `Gaming`) and customer loyalty tier.
   * **Data Retrieved:** `allowed_return_window_days` (e.g., 30 days for Standard vs. 45–60 days for Gold VIPs) and `max_auto_refund_amount` (dollar cap before supervisor approval is required).

3. **Tool 3: `process_refund_or_escalate(order_id, action, reason)`**
   * **Action:** After comparing the order age against the return window and the price against the auto-refund dollar cap, the agent executes one of three actions:
     * `APPROVE_REFUND`: Inside the return window **and** within the auto-approval dollar limit.
     * `ESCALATE_TO_HUMAN`: Inside the return window **but** exceeds the auto-approval dollar limit (e.g., a \$620 monitor when the cap is \$250).
     * `REJECT_REFUND`: Outside the eligible return window for that customer's tier.
   * **State Persistence:** Automatically updates `orders_data.csv` with the `ticket_id`, `resolution_action`, and `resolution_reason`.

---

## 🛡️ How We Maintain Control Over the System (Guardrails & Human Override)

Enterprise AI agents must never operate without boundaries. This system enforces control at two levels:

1. **Automated Policy & Financial Guardrails:**
   * **Hard Dollar Caps:** The AI is strictly forbidden from auto-approving refunds above the category's `max_auto_refund_amount` (\$150–\$300). High-value tickets are forced into `ESCALATE_TO_HUMAN`.
   * **Strict JSON Schema Enum:** The tool schema restricts the LLM's output action to `["APPROVE_REFUND", "ESCALATE_TO_HUMAN", "REJECT_REFUND"]`. It cannot invent unauthorized actions or alter product prices.
   * **Deterministic Execution (`temperature=0.0`):** Eliminates randomness so identical inputs always yield identical tool calls.

2. **Human-in-the-Loop (HITL) Supervisor Override Panel (`app.py`):**
   * Whenever the AI flags an order as `ESCALATE_TO_HUMAN` (such as `ORD-1002` for a \$620 monitor), a human manager can use the **Human Supervisor Override Panel** in the Streamlit UI to review the ticket, filter specifically for escalated orders, enter an audit note, and manually override the status to `APPROVE_REFUND` or `REJECT_REFUND`.
   * The override writes `[HUMAN OVERRIDE]` directly into `orders_data.csv` to maintain a clear audit trail.
   * A **1-Click Reset Button** (`🔄 Reset All 105 Orders to PENDING`) in the sidebar allows the operator to restore the entire database to its initial state at any time.

---

## 📂 Project Structure

```text
├── app.py                # Interactive Streamlit UI with Tool Trace Viewer & Human Override Panel
├── main.py               # Core Agentic AI loop, Groq API integration, and 3 Python tools
├── orders_data.csv       # Local database with 105 orders (ORD-1001 to ORD-1105)
├── .env                  # Environment file storing your GROQ_API_KEY
└── README.md             # Project documentation and setup guide
```

---

## 🚀 Step-by-Step Setup & Execution Guide

### 1. Prerequisites
* **Python 3.8+** installed on your system.
* A free **Groq API Key** from [console.groq.com](https://console.groq.com/).

### 2. Install Dependencies
Open your terminal or command prompt in the project folder and install the required packages:

```bash
pip install streamlit pandas groq python-dotenv
```

### 3. Configure the `.env` File
Create a file named `.env` in the root directory of the project and add your Groq API key:

```env
GROQ_API_KEY=gsk_your_actual_groq_api_key_here
```

---

## 🖥️ Option A: Running the Interactive Streamlit UI (Recommended for Live Demos)

Launch the web dashboard with:

```bash
streamlit run app.py
```

### How to Demo with the Streamlit UI:
1. **100% On-Demand Control:** When launched via Streamlit, the system waits for your command.
2. **One-Click Demo Scenarios:** Click **Demo 1 (`ORD-1001`)**, **Demo 2 (`ORD-1002`)**, or **Demo 3 (`ORD-1003`)** on the left panel to watch the agent execute its 3 tool calls and display the expandable JSON trace cards in real time.
3. **Demonstrate Human Supervisor Override:**
   * Click **⚠️ Demo 2: Over Cap (`ORD-1002`)**. The agent will see that \$620 exceeds the \$250 cap and set the status to `ESCALATE_TO_HUMAN`.
   * Go to the **👨‍💼 Human Supervisor Override Panel** on the right side, check *"Show only `ESCALATE_TO_HUMAN` orders needing review"*, select `ORD-1002`, and click **🛡️ Apply Human Supervisor Override** to approve it as a human manager!
4. **Test Any of the 105 Orders:** Select any order from `ORD-1001` to `ORD-1105` in the dropdown to test the agent live during Q&A.

---

## 💻 Option B: Running via Terminal CLI (`python3 main.py`)

If you run `main.py` directly in the terminal instead of Streamlit:

```bash
python3 main.py
```

> **⚡ Important Note on Terminal Startup Behavior:**
> When you run `python3 main.py`, **it automatically executes the 3 built-in demo test cases at the start** (`ORD-1001`, `ORD-1002`, and `ORD-1003`) to immediately showcase all three decision branches (`APPROVE_REFUND`, `ESCALATE_TO_HUMAN`, and `REJECT_REFUND`). **Right after these 3 automated runs finish**, the script unlocks the `INTERACTIVE DEMO MODE` prompt where you can type any order ID (`ORD-1001` to `ORD-1105`) or `exit` to quit.
