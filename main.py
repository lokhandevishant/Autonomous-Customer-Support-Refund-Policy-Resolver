import os
import sys
import csv
import json
from dotenv import load_dotenv
from groq import Groq

# Load environment variables from the .env file in the same directory
load_dotenv()

api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    print("ERROR: GROQ_API_KEY not found! Please create a .env file with GROQ_API_KEY=gsk_your_key_here")
    sys.exit(1)

# Initialize Groq client using the key loaded from .env
client = Groq(api_key=api_key)
MODEL = "openai/gpt-oss-120b"  # Or "llama-3.3-70b-versatile"

CSV_FILENAME = "orders_data.csv"

# =====================================================================
# 1. RETURN POLICIES DATABASE (5 Product Categories)
# =====================================================================
POLICIES_DB = {
    "Electronics": {
        "standard_return_window_days": 30,
        "gold_tier_return_window_days": 45,
        "max_auto_refund_amount": 250.00,
        "notes": "Electronics over $250 require supervisor inspection before refund."
    },
    "Apparel": {
        "standard_return_window_days": 30,
        "gold_tier_return_window_days": 60,
        "max_auto_refund_amount": 250.00,
        "notes": "Original tags must be attached and item unworn."
    },
    "Home & Kitchen": {
        "standard_return_window_days": 45,
        "gold_tier_return_window_days": 60,
        "max_auto_refund_amount": 300.00,
        "notes": "Appliances over $300 require technician verification."
    },
    "Footwear": {
        "standard_return_window_days": 30,
        "gold_tier_return_window_days": 45,
        "max_auto_refund_amount": 200.00,
        "notes": "Soles must show zero outdoor wear."
    },
    "Gaming": {
        "standard_return_window_days": 15,
        "gold_tier_return_window_days": 30,
        "max_auto_refund_amount": 150.00,
        "notes": "Strict 15-day window for standard members; consoles over $150 require escalation."
    }
}

# =====================================================================
# 2. CSV HELPER FUNCTIONS (Read, Write & Reset Directly to orders_data.csv)
# =====================================================================
def load_orders_from_csv(filename: str = CSV_FILENAME) -> dict:
    """Load all rows from orders_data.csv into a dictionary keyed by order_id."""
    orders = {}
    with open(filename, mode="r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["amount"] = float(row["amount"])
            row["days_since_purchase"] = int(row["days_since_purchase"])
            orders[row["order_id"].upper()] = row
    return orders


def save_orders_to_csv(orders: dict, filename: str = CSV_FILENAME):
    """Write updated order statuses back to orders_data.csv so changes show in UI/Excel."""
    fieldnames = [
        "order_id", "customer_name", "customer_tier", "item", "category",
        "amount", "days_since_purchase", "status",
        "resolution_action", "ticket_id", "resolution_reason"
    ]
    with open(filename, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for order in orders.values():
            writer.writerow(order)


def reset_all_orders_to_pending(filename: str = CSV_FILENAME):
    """Reset all 105 orders back to PENDING for a clean demo slate."""
    global ORDERS_DB, ACTION_LOG
    ORDERS_DB = load_orders_from_csv(filename)
    for oid in ORDERS_DB:
        ORDERS_DB[oid]["resolution_action"] = "PENDING"
        ORDERS_DB[oid]["ticket_id"] = ""
        ORDERS_DB[oid]["resolution_reason"] = ""
    save_orders_to_csv(ORDERS_DB, filename)
    ACTION_LOG.clear()


# Load the 105 orders from CSV at startup
ORDERS_DB = load_orders_from_csv()
ACTION_LOG = []


# =====================================================================
# 3. DEFINE THE 3 PYTHON TOOLS
# =====================================================================
def get_order_details(order_id: str) -> str:
    """Tool 1: Fetch order details from the CSV database by order_id."""
    global ORDERS_DB
    ORDERS_DB = load_orders_from_csv()  # Ensure fresh state
    order = ORDERS_DB.get(order_id.strip().upper())
    if not order:
        return json.dumps({
            "error": f"Order '{order_id}' not found in {CSV_FILENAME}. Valid IDs are ORD-1001 to ORD-1105."
        }, ensure_ascii=False)
    return json.dumps(order, ensure_ascii=False)


def check_return_policy(category: str, customer_tier: str) -> str:
    """Tool 2: Retrieve return window rules and auto-refund dollar caps for a category and tier."""
    matched_policy = None
    matched_cat_name = category
    for cat_name, policy_data in POLICIES_DB.items():
        if cat_name.lower() == category.strip().lower():
            matched_policy = policy_data
            matched_cat_name = cat_name
            break

    if not matched_policy:
        return json.dumps({
            "error": f"No policy found for category '{category}'. Valid categories: {list(POLICIES_DB.keys())}"
        }, ensure_ascii=False)

    allowed_days = (
        matched_policy["gold_tier_return_window_days"]
        if customer_tier.strip().lower() == "gold"
        else matched_policy["standard_return_window_days"]
    )
    return json.dumps({
        "category": matched_cat_name,
        "customer_tier": customer_tier,
        "allowed_return_window_days": allowed_days,
        "max_auto_refund_amount": matched_policy["max_auto_refund_amount"],
        "policy_notes": matched_policy["notes"]
    }, ensure_ascii=False)


def process_refund_or_escalate(order_id: str, action: str, reason: str) -> str:
    """
    Tool 3: Execute the final decision and persist it directly back to orders_data.csv.
    action must be one of: 'APPROVE_REFUND', 'ESCALATE_TO_HUMAN', or 'REJECT_REFUND'.
    """
    global ORDERS_DB
    ORDERS_DB = load_orders_from_csv()
    oid = order_id.strip().upper()
    ticket_id = f"TCK-{len(ACTION_LOG) + 5001}"

    record = {
        "ticket_id": ticket_id,
        "order_id": oid,
        "action_taken": action,
        "reason": reason
    }
    ACTION_LOG.append(record)

    # Update the row in memory and write back to orders_data.csv
    if oid in ORDERS_DB:
        ORDERS_DB[oid]["resolution_action"] = action
        ORDERS_DB[oid]["ticket_id"] = ticket_id
        ORDERS_DB[oid]["resolution_reason"] = reason
        save_orders_to_csv(ORDERS_DB)

    return json.dumps({
        "status": "SUCCESS_SAVED_TO_CSV",
        "csv_file_updated": CSV_FILENAME,
        "record": record
    }, ensure_ascii=False)


AVAILABLE_FUNCTIONS = {
    "get_order_details": get_order_details,
    "check_return_policy": check_return_policy,
    "process_refund_or_escalate": process_refund_or_escalate,
}

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "get_order_details",
            "description": "Fetch order details (amount, purchase age in days, category, customer tier) from orders_data.csv by order ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "The order ID, e.g., ORD-1001"}
                },
                "required": ["order_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_return_policy",
            "description": "Check the return window days and maximum auto-refund limit for a category and customer tier.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Product category: Electronics, Apparel, Home & Kitchen, Footwear, or Gaming"
                    },
                    "customer_tier": {
                        "type": "string",
                        "description": "Customer loyalty tier: Standard or Gold"
                    }
                },
                "required": ["category", "customer_tier"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "process_refund_or_escalate",
            "description": "Finalize the support ticket and update orders_data.csv by approving the refund, rejecting it, or escalating to a human supervisor.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "The order ID being processed"},
                    "action": {
                        "type": "string",
                        "enum": ["APPROVE_REFUND", "ESCALATE_TO_HUMAN", "REJECT_REFUND"],
                        "description": "The final resolution decision"
                    },
                    "reason": {"type": "string", "description": "Clear explanation citing policy numbers, dollar caps, and days"}
                },
                "required": ["order_id", "action", "reason"]
            }
        }
    }
]


# =====================================================================
# 4. THE AGENTIC REASONING LOOP (Returns structured steps for Streamlit + CLI)
# =====================================================================
def run_support_agent(customer_message: str) -> dict:
    """
    Runs the agentic loop and returns a dictionary containing:
      - 'customer_message': original input prompt
      - 'steps': list of tool call traces (step, tool_name, tool_args, tool_output)
      - 'final_response': the final natural-language answer from the LLM
    """
    print("\n" + "=" * 75)
    print(f"CUSTOMER TICKET: {customer_message}")
    print("=" * 75)

    messages = [
        {
            "role": "system",
            "content": (
                "You are an Autonomous Customer Support Refund Resolver. "
                "Follow these steps strictly:\n"
                "1. Call get_order_details first to inspect the order from the CSV database.\n"
                "2. Call check_return_policy using the order's exact category and customer_tier.\n"
                "3. Compare days_since_purchase against allowed_return_window_days, AND compare "
                "order amount against max_auto_refund_amount.\n"
                "   - If days_since_purchase > allowed_return_window_days -> call process_refund_or_escalate with REJECT_REFUND.\n"
                "   - If days_since_purchase <= allowed_return_window_days BUT amount > max_auto_refund_amount -> call process_refund_or_escalate with ESCALATE_TO_HUMAN.\n"
                "   - If days_since_purchase <= allowed_return_window_days AND amount <= max_auto_refund_amount -> call process_refund_or_escalate with APPROVE_REFUND.\n"
                "4. Finally, write a concise, polite response to the customer explaining the decision."
            )
        },
        {"role": "user", "content": customer_message}
    ]

    step = 1
    executed_steps = []
    final_response = ""

    while True:
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS_SCHEMA,
            tool_choice="auto",
            temperature=0.0
        )

        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls

        if not tool_calls:
            final_response = response_message.content or ""
            print(f"\n[AGENT FINAL RESPONSE]:\n{final_response}")
            break

        messages.append(response_message)

        for tool_call in tool_calls:
            func_name = tool_call.function.name
            func_args = json.loads(tool_call.function.arguments)

            print(f"  -> Step {step} | Tool Call: {func_name}({func_args})")

            function_to_call = AVAILABLE_FUNCTIONS[func_name]
            tool_output = function_to_call(**func_args)
            print(f"     <- Tool Output: {tool_output}")

            executed_steps.append({
                "step": step,
                "tool_name": func_name,
                "tool_args": func_args,
                "tool_output": json.loads(tool_output)
            })
            step += 1

            messages.append({
                "tool_call_id": tool_call.id,
                "role": "tool",
                "name": func_name,
                "content": tool_output,
            })

    return {
        "customer_message": customer_message,
        "steps": executed_steps,
        "final_response": final_response
    }


# =====================================================================
# 5. TERMINAL DEMO RUNNER (Only runs if you execute `python3 main.py`)
# =====================================================================
if __name__ == "__main__":
    print(f"Loaded {len(ORDERS_DB)} orders from '{CSV_FILENAME}' (ORD-1001 to ORD-1105).")

    # Run 3 automated demo cases showing all 3 outcomes (Approve, Escalate, Reject)
    run_support_agent("Hi, I want to return my headphones from order ORD-1001 for a refund.")
    run_support_agent("Please refund my monitor on order ORD-1002, it has a dead pixel.")
    run_support_agent("Can I get a refund for my shoes in order ORD-1003? They don't fit.")

    # Interactive mode: Let your professor pick ANY order from ORD-1001 to ORD-1105 live!
    print("\n" + "=" * 75)
    print("INTERACTIVE DEMO MODE (Type any order ID from ORD-1001 to ORD-1105, or 'exit' to quit)")
    print("=" * 75)
    while True:
        user_input = input("\nEnter a customer request (e.g., 'Refund order ORD-1042') or 'exit': ").strip()
        if user_input.lower() in ("exit", "quit", "q", ""):
            break
        run_support_agent(user_input)

    print("\n" + "=" * 75)
    print(f"DONE! Open '{CSV_FILENAME}' in Excel to view the updated resolution columns.")
