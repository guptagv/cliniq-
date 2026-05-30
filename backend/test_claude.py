import os
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()
client = Anthropic()

message = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    messages=[
        {"role": "user", "content": "What are the main phases of a clinical trial? Answer in 3 bullet points."}
       ]
   )

print(message.content[0].text)