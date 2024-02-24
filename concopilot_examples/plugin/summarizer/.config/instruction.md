**Task:** Create a concise running summary of actions and information results in the provided text,
focusing on key and important information to remember.

**Instructions:**

1. Combine the current summary with the latest information or contents.
2. Extract key information and rewrite it into human-readable natural language.
3. Keep the summarization less than {max_tokens} tokens.

**Note:**

1. The {content} will always be provided in JSON format.
2. The summarization result should be in plain text or markdown.
3. The "cerebrum" in the message refers to yourself.

**Summary So Far:**

"""

{previous_summary}

"""

**Latest Information/Contents:**

"""

{content}

"""

**Begin summarization:**
