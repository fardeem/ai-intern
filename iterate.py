import os
import pathlib
import sys

import modal

script_path = pathlib.Path(os.path.realpath(__file__)).parent
sys.path.append(str(script_path))

from utils import walk_directory

stub = modal.Stub("ai-intern")
openai_image = modal.Image.debian_slim().pip_install("openai")


DEFAULT_DIR = "generated"

SYSTEM_PROMPT = """
You are an AI debugger who is trying to debug a program for a user based on their file system. The user has provided you with the following files and their contents, finally folllowed by the error message or issue they are facing.
"""

def USER_PROMPT(context: str, prompt: str): return f"""
My files are as follows:
{context}

My issue is as follows: 
{prompt}

Give me ideas for what could be wrong and what fixes to do in which files.
"""


@stub.function(
    image=openai_image,
    secret=modal.Secret.from_dotenv(
        os.path.join(os.path.dirname(os.path.realpath(__file__)), ".env")
    ),
    retries=modal.Retries(
        max_retries=3,
        backoff_coefficient=2.0,
        initial_delay=1.0,
    ),
    concurrency_limit=5,
    timeout=120,
)
def generate_response(system_prompt, user_prompt, model="gpt-4", *args):
    import openai

    # print(os.environ["OPENAI_API_KEY"])
    # Set up your OpenAI API credentials
    openai.api_key = os.environ["OPENAI_API_KEY"]

    messages = []
    messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})

    role = "assistant"
    for value in args:
        messages.append({"role": role, "content": value})
        role = "user" if role == "assistant" else "assistant"

    params = {
        'model': model,
        "messages": messages,
        "max_tokens": 1500,
        "temperature": 0,
    }

    # Send the API request
    response = openai.ChatCompletion.create(**params)

    # Get the reply from the API response
    reply = response.choices[0]["message"]["content"] # type: ignore 
    return reply




@stub.local_entrypoint()
def main(prompt, directory=DEFAULT_DIR):
  print('== ai-intern ==')
  
  code_contents = walk_directory(directory)


  context = "\n".join(f"{path}:\n{contents}" for path, contents in code_contents.items())

  user_prompt = USER_PROMPT(
    context=context,
    prompt=prompt,
  )
  
  res = generate_response.call(SYSTEM_PROMPT, user_prompt)
  
  print("\033[96m" + res + "\033[0m")


