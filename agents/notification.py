from llm_main import llm
import json
from datetime import datetime

def notfn_creater(msg, status_msg, saving_context):
    prompt = f"""
You are a notification-generation assistant.

Context from financial analysis:
{status_msg}

User-specific saving context:
"{saving_context}"

User request:
"{msg}"

Task:
Create a warm, simple, helpful notification message (3–4 lines only),
guiding the user on festival spending based on their financial condition.
Include a specific recommended savings figure.

Do NOT explain. ONLY output the final notification text.
    """
    return llm.invoke(prompt).content.strip()


def planner(msg, user):
    # Prepare financial analysis based on context
    prompt = f"""
You are a financial analysis assistant.

User monthly & spending context:
"{user['saving_context']}"
"{user['current_financial_context']}"

Task:
Create a 3–5 line bullet summary analyzing:
- spending level (high/moderate/low)
- income stability
- savings capability
- risk of festival overspending

Do not create the notification here. Only provide analysis context.
    """

    analysis = llm.invoke(prompt).content.strip()

    # Create final notification
    notification = notfn_creater(
        msg,
        analysis,
        user["saving_context"]
    )

    # Build MongoDB query
    mongo_query = {
        "update_query": f"""db.users.updateOne(
    {{ user_id: {user['user_id']} }},
    {{
        $push: {{
            notifications: {{
                msg: "{notification}"
            }}
        }}
    }}
)"""
    }

    return mongo_query



if __name__ == "__main__":

    users = [
        {
            "user_id": 101,
            "saving_context": "Your income is steady, but work-related expenses are high. Set a small weekly savings target to stay consistent.",
            "current_financial_context": "Frequent spending on fuel and food along with moderate earnings from deliveries. Bonuses help but are irregular."
        },
        {
            "user_id": 102,
            "saving_context": "Reduce discretionary expenses this month to improve your savings buffer before upcoming festivals.",
            "current_financial_context": "Mixed income from rides and freelance tasks. Spending mostly on general purchases and subscriptions."
        },
        {
            "user_id": 103,
            "saving_context": "Plan for a 10% monthly savings goal. Avoid unnecessary travel and control food expenses.",
            "current_financial_context": "Earnings mostly from delivery work. High transport and food expenses affecting savings potential."
        },
        {
            "user_id": 104,
            "saving_context": "Maintain your current pace and build an emergency fund. Limit non-essential purchases for better savings.",
            "current_financial_context": "Stable income from service gigs. Occasional medical and maintenance expenses reducing cash flow stability."
        },
        {
            "user_id": 105,
            "saving_context": "Your income pattern is strong. Redirect a portion of bonus earnings into short-term savings.",
            "current_financial_context": "Good monthly earnings driven by product sales and incentives. Spending moderate with few recurring costs."
        }
    ]

    msg = "Make a user notification for how much he should spend this upcoming Diwali according to his current spendings."

    final_queries = []

    for user in users:
        mongo_query = planner(msg, user)
        final_queries.append(mongo_query)
    print(final_queries)
