import os
import pathlib
import sys

import modal

script_path = pathlib.Path(os.path.realpath(__file__)).parent  # noqa
sys.path.append(str(script_path))  # noqa

from utils import print_wrapped, walk_directory

stub = modal.Stub("ai-intern")
openai_image = modal.Image.debian_slim().pip_install("openai")


DEFAULT_DIR = "generated"

ITERATE_SYSTEM_PROMPT = """
You are an AI debugger who is trying to debug a program for a user based on their file system. The user has provided you with the following files and their contents, finally folllowed by the error message or issue they are facing.
"""


def ITERATE_USER_PROMPT(context: str, prompt: str): return f"""
My files are as follows:
{context}

My issue is as follows: 
{prompt}

Give me ideas for what could be wrong and what fixes to do in which files.
"""


EXPLAIN_SYSTEM_PROMPT = """
You are an expert AI software engineer who is trying to answer questions about a codebase for a user based on their file system. The user has provided you with the following files and their contents, finally followed by the question they have.
"""


def EXPLAIN_USER_PROMPT(context: str, prompt: str): return f"""
My files are as follows:
{context}

My question is as follows:
{prompt}

Give me answers to my question.
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
def generate_response(system_prompt, user_prompt, model="gpt-3.5-turbo-16k", *args):
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
    reply = response.choices[0]["message"]["content"]  # type: ignore
    return reply


@stub.local_entrypoint()
def main(prompt, variation, directory=DEFAULT_DIR):
    print('== ai-intern ==')

    code_contents = walk_directory(directory)

    print(
        'Found the following files in the directory you specified: \n',
        '\n'.join(code_contents.keys()),
    )

    context = "\n".join(f"{path}:\n{contents}" for path,
                        contents in code_contents.items())

    user_prompt = ITERATE_USER_PROMPT(
        context=context,
        prompt=prompt,
    ) if variation == "iterate" else EXPLAIN_USER_PROMPT(
        context=context,
        prompt=prompt,
    )

    system_prompt = ITERATE_SYSTEM_PROMPT if variation == "iterate" else EXPLAIN_SYSTEM_PROMPT

    res = generate_response.call(system_prompt, user_prompt)

    print("\033[96m" + res + "\033[0m")
