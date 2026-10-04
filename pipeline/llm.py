"""Optional LLM commentary via Groq's free tier."""

import time

from groq import APIConnectionError, APIStatusError, RateLimitError

from config import GROQ_API_KEY, GROQ_MODEL


RULES = (
    "Rules: use only the numbers and headlines given, exactly as written. "
    "'1-year' means the trailing 12 months, not year-to-date. "
    "Only say one number is higher or lower than another if it really is. "
    "Keep the sign: a number starting with - is a fall, + is a rise. "
    "No buy/sell advice."
)


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
                extra = {}
                if "gpt-oss" in self.model:
                    # reasoning models can spend the whole reply "thinking" and return no text
                    extra = {"reasoning_effort": "low", "include_reasoning": False}
                r = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    **extra,
                )
                time.sleep(2)  # stay under free-tier rate limits
                text = (r.choices[0].message.content or "").strip()
                if text:
                    return text
                print("   LLM returned an empty reply, retrying...")
            except (RateLimitError, APIConnectionError) as e:  # temporary - worth retrying
                print(f"   LLM busy ({e.__class__.__name__}), retrying...")
                time.sleep(5 * (attempt + 1))
            except APIStatusError as e:  # bad model name, bad key, etc. - retrying won't help
                print(f"   LLM error: {e.message}")
                return None
        return None

    def company_note(self, name, stats_line, index_line, headlines):
        return self.ask(
            f"You are a careful equity research writer. Write 3-4 sentences on {name} "
            f"for a weekly NIFTY IT review. Readers already see a table with every number, so "
            f"use at most 3 numbers and focus on how it compares with the index and what the news says.\n\n"
            f"Numbers (already computed, use exactly):\n{stats_line}\n"
            f"NIFTY IT index for comparison: {index_line}\n\n"
            f"Recent headlines (dates in brackets):\n{headlines or 'none'}\n\n"
            f"{RULES} If no headline clearly explains the move, say so. "
            "Point out when a headline is old."
        )

    def sector_summary(self, facts):
        return self.ask(
            "Write a 4-5 sentence sector summary for a NIFTY IT weekly review. Readers already "
            "see a table with every number, so do not list them: give the story - the overall "
            "trend, who stood out and why, and what the news suggests. Use at most 4 numbers.\n\n"
            f"{facts}\n\n{RULES}"
        )
