from openai import OpenAI
import os 

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.environ["NVIDIA_API_KEY"],
)

response = client.chat.completions.create(
    model="nvidia/nemotron-3-ultra-550b-a55b",
    messages=[
        {"role": "user", "content": "Explain FastAPI streaming briefly."}
    ],
    max_tokens=2000,
    stream=True,
    extra_body={
        "chat_template_kwargs": {
            "enable_thinking": True
        }
    }
)

for chunk in response:
    if chunk.choices and chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")