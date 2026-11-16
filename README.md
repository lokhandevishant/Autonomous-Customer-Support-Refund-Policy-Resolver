# Autonomous Customer Support Refund & Policy Resolver (Agentic AI)

## 📌 Project Overview

In modern e-commerce and retail operations, customer support teams spend thousands of hours manually cross-referencing refund requests against order history, product categories, customer loyalty tiers, and company return policies.

This project demonstrates a **modern Agentic AI workflow** powered by the **Groq API** that autonomously resolves customer refund tickets. Instead of merely generating conversational replies, the AI agent uses **3 deterministic function-calling tools** to inspect a local CSV database of 105 orders (`orders_data.csv`), evaluate dynamic policy constraints, execute a binding business decision (`APPROVE_REFUND`, `ESCALATE_TO_HUMAN`, or `REJECT_REFUND`), and write the audit trail directly back into the CSV file.

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

## 🛡️ Why This Architecture is 100% Demo-Proof

* **Zero External Database Flakiness:** Uses a local, deterministic 105-record CSV database (`orders_data.csv`) that can be inspected before and after the run in Microsoft Excel or VS Code.
* **Deterministic Reasoning (`temperature=0.0`):** Ensures the LLM makes consistent, repeatable tool calls every single time.
* **Built-In Financial Guardrails:** Demonstrates how enterprise AI agents safely escalate high-value transactions to human supervisors rather than blindly approving expensive refunds.

## 📂 Project Structure

```
├── main.py   # Main Python script containing the Agentic loop & 3 tools 
├── orders_data.csv       # Local database with 105 orders (ORD-1001 to ORD-1105)
├── .env                  # Environment file storing your GROQ_API_KEY
└── README.md             # Project documentation and setup guide
```

## 🚀 Step-by-Step Setup & Execution Guide

### 1. Prerequisites

* **Python 3.8+** installed on your system.
* A free **Groq API Key** from [console.groq.com](https://console.groq.com/).

### 2. Install Dependencies

Open your terminal or command prompt in the project folder and install the required packages:

```bash
pip install groq python-dotenv
```

### 3. Configure the `.env` File

Create a file named `.env` in the root directory of the project (in the exact same folder as your Python script and `orders_data.csv`) and add your Groq API key:

```env
GROQ_API_KEY=gsk_your_actual_groq_api_key_here
```

### 4. Run the Agent

Make sure `orders_data.csv` is **closed in Excel** (so your OS doesn't lock the file from being updated), then run:

```bash
python3 main.py
```

## 🎯 Execution Flow: Automated Startup Demo + Interactive User Mode

> **⚡ Important Note on Startup Behavior:**
> When you run the script, **it does not immediately ask for user input.** Instead, the system **automatically executes 3 built-in demo test cases at the start** (`ORD-1001`, `ORD-1002`, and `ORD-1003`) to immediately showcase all three decision branches (`APPROVE_REFUND`, `ESCALATE_TO_HUMAN`, and `REJECT_REFUND`) in your terminal. **Only after these 3 automated runs finish** does the system open the interactive prompt for you to type your own requests.

### Phase 1: Automatic Demo Execution (Runs Immediately on Startup)
As soon as you launch the script, you will see the agent autonomously process 3 pre-configured customer tickets step-by-step (`Step 1 -> Step 2 -> Step 3`):

1. **`ORD-1001` (Auto-Approve via VIP Exception):** Purchased 34 days ago (\$180). Exceeds the standard 30-day Electronics window, *but* the customer is a `Gold` member (45-day window). Result: **`APPROVE_REFUND`**.
2. **`ORD-1002` (Escalate due to Dollar Cap):** Purchased 10 days ago (\$620). Within the 30-day window, *but* exceeds the \$250 auto-refund cap. Result: **`ESCALATE_TO_HUMAN`**.
3. **`ORD-1003` (Reject due to Expired Window):** Purchased 40 days ago (\$95) by a `Standard` tier member (30-day limit). Result: **`REJECT_REFUND`**.

### Phase 2: Live Interactive User Mode (Starts After the Demo Finishes)
Once the 3 automatic demo tickets complete, the terminal displays:
```text
===========================================================================
INTERACTIVE DEMO MODE (Type any order ID from ORD-1001 to ORD-1105, or 'exit' to quit)
===========================================================================
Enter a customer request (e.g., 'Refund order ORD-1042') or 'exit':
```
Now you (or your professor) can type any natural-language refund request for **any order between `ORD-1001` and `ORD-1105`**, such as:
* `Refund order ORD-1042 please`
* `Hi, I want to return my item from order ORD-1005`
* `Can I get a refund on ORD-1088?`

Type `exit` or `q` and press **Enter** when you are ready to close the program.

### Phase 3: Verify the Output in Excel
Because the agent writes its decisions directly to disk during both Phase 1 and Phase 2, you can open `orders_data.csv` in Excel or VS Code after running the script to view the updated `resolution_action`, `ticket_id`, and `resolution_reason` columns. *(Note: If you run the script multiple times, `Step 1` will show the saved `resolution_action` from your previous run because the CSV file retains its updated state.)*