"""Optional LLM commentary via Groq's free tier."""

import time

from config import GROQ_API_KEY, GROQ_MODEL


class Writer:
    def __init__(self):
        self.model = GROQ_MODEL if GROQ_API_KEY else None
        self.client = None
        if GROQ_API_KEY:
            from groq import Groq
            self.client = Groq(api_key=GROQ_API_KEY)

    @property
    def enabled(self):
        return self.client is not None

    def ask(self, prompt, retries=3):
        for attempt in range(retries):
            try:
                r = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                )
                time.sleep(2)  # stay under free-tier rate limits
                return r.choices[0].message.content.strip()
            except Exception as e:  # usually a rate limit on the free tier
                print(f"   LLM error ({e.__class__.__name__}: {e}), retrying...")
                time.sleep(5 * (attempt + 1))
        return None

    def company_note(self, name, stats_line, index_line, headlines):
        return self.ask(
            f"You are a careful equity research writer. Write 3-4 sentences on {name} "
            f"for a weekly NIFTY IT review.\n\n"
            f"Numbers (already computed, use exactly):\n{stats_line}\n"
            f"NIFTY IT index for comparison: {index_line}\n\n"
            f"Recent headlines (dates in brackets):\n{headlines or 'none'}\n\n"
            "Rules: only use the numbers and headlines given. If no headline clearly "
            "explains the move, say so. Point out when a headline is old. No buy/sell advice."
        )

    def sector_summary(self, facts):
        return self.ask(
            "Write a 5-sentence sector summary for a NIFTY IT weekly review.\n\n"
            f"{facts}\n\nUse only these facts. No buy/sell advice."
        )
