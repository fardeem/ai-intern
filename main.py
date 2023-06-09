import ast
import os
import pathlib
import sys

import modal

script_path = pathlib.Path(os.path.realpath(__file__)).parent  # noqa
sys.path.append(str(script_path))  # noqa
from generate_prompts import (GENERATE_FILE_STRINGS_SYSTEM_PROMPT,
                              GENERATE_FILE_SYSTEM_PROMPT,
                              GENERATE_FILE_USER_PROMPT,
                              SHARED_DEPENDENCIES_SYSTEM_PROMPT)

stub = modal.Stub("ai-intern")
generatedDir = "generated"
openai_image = modal.Image.debian_slim().pip_install("openai", "tiktoken")
openai_model = "gpt-4"  # or 'gpt-3.5-turbo',
openai_model_max_tokens = 2000  # i wonder how to tweak this properly


def write_file(filename, filecode, directory):
    # Output the filename in blue color
    print("\033[94m" + f"writing: {filename}" + "\033[0m")

    file_path = directory + "/" + filename
    dir = os.path.dirname(file_path)
    os.makedirs(dir, exist_ok=True)

    # Open the file in write mode
    with open(file_path, "w") as file:
        # Write content to the file
        file.write(filecode)


def clean_dir(directory):
    print("Cleaning directory:", directory)

    extensions_to_skip = ['.png', '.jpg', '.jpeg',
                          '.gif', '.bmp', '.svg', '.ico', '.tif', '.tiff']

    if os.path.exists(directory):
        for root, dirs, files in os.walk(directory):
            for file in files:
                _, extension = os.path.splitext(file)
                if extension not in extensions_to_skip:
                    os.remove(os.path.join(root, file))

            for dir in dirs:
                clean_dir(os.path.join(root, dir))
                os.rmdir(os.path.join(root, dir))
    else:
        os.makedirs(directory, exist_ok=True)


def log(log_file_path: str, text: str, should_log: bool):
    if not should_log:
        return

    with open(log_file_path, "a") as log_file:
        log_file.write(text + "\n\n\n")


def calculate_cost(prompt, response):
    import tiktoken

    encoding = tiktoken.encoding_for_model(openai_model)

    prompt_token = len(encoding.encode(prompt))
    response_token = len(encoding.encode(response))

    prompt_cost_rate_per_1000 = 0.03
    response_cost_rate_per_1000 = 0.06

    prompt_cost = prompt_token / 1000 * prompt_cost_rate_per_1000
    response_cost = response_token / 1000 * response_cost_rate_per_1000
    total_cost = prompt_cost + response_cost

    return total_cost


def print_cost(reason: str, cost: str):
    print("\033[93m" + f"Cost of {reason}: {cost}" + "\033[0m")


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
    concurrency_limit=5
)
def generate_response(system_prompt, user_prompt, *args):
    import openai

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
        "model": openai_model,
        "messages": messages,
        "max_tokens": openai_model_max_tokens,
        "temperature": 0,
    }

    # Send the API request
    response = openai.ChatCompletion.create(**params)

    # Get the reply from the API response
    reply = response.choices[0]["message"]["content"]  # type: ignore

    total_cost = calculate_cost(system_prompt + user_prompt, reply)

    return reply, total_cost


@stub.function()
def generate_file(filename, filepaths_string=None, shared_dependencies=None, prompt=None):
    # call openai api with this prompt
    system_prompt = GENERATE_FILE_SYSTEM_PROMPT(
        prompt=prompt,
        filepaths_string=filepaths_string,
        shared_dependencies=shared_dependencies,
    )
    user_prompt = GENERATE_FILE_USER_PROMPT(
        filename=filename,
        prompt=prompt,
    )

    filecode, cost = generate_response.call(
        system_prompt,
        user_prompt
    )

    return filename, filecode, cost


@stub.function()
def generate(prompt: str, should_log: bool, directory: str = generatedDir):
    print("=== ai-intern ===")
    print("\033[92m" + prompt + "\033[0m")
    print('\n')

    total_cost = 0
    log_file_path = directory + "/logs.md"

    # Clean directory
    clean_dir(directory)

    # Generate filepaths
    print("Generating filepaths...")

    filepaths_string, cost = generate_response.call(
        GENERATE_FILE_STRINGS_SYSTEM_PROMPT,
        prompt,
    )

    total_cost += cost
    print(filepaths_string)
    print_cost("Generating filepaths", cost)
    log(
        log_file_path=log_file_path,
        text=f"**Generating filepaths:**\n{filepaths_string}\nCost: {cost}",
        should_log=should_log,
    )
    print("\n")

    # Parse filepaths
    list_actual = []
    try:
        list_actual = ast.literal_eval(filepaths_string)
    except ValueError:
        print("Failed to parse result: " + filepaths_string)
        return

    # if shared_dependencies.md is there, read it in, else set it to None
    shared_dependencies = None
    if os.path.exists("shared_dependencies.md"):
        with open("shared_dependencies.md", "r") as shared_dependencies_file:
            shared_dependencies = shared_dependencies_file.read()

    print('Figuring out shared dependencies...')
    system_prompt = SHARED_DEPENDENCIES_SYSTEM_PROMPT(
        prompt=prompt,
        filepaths_string=filepaths_string,
    )

    # understand shared dependencies
    shared_dependencies, cost = generate_response.call(
        system_prompt,
        prompt,
    )

    total_cost += cost
    print_cost("Shared dependencies cost", cost)
    write_file("shared_dependencies.md", shared_dependencies, directory)
    log(
        log_file_path=log_file_path,
        text=f"**Generating shared dependencies:**\n{shared_dependencies}",
        should_log=should_log,
    )
    print("\n")

    # Generating code
    print('Generating code for each file...')
    for filename, filecode, cost in generate_file.map(
        list_actual, order_outputs=False, kwargs=dict(filepaths_string=filepaths_string, shared_dependencies=shared_dependencies, prompt=prompt)
    ):
        total_cost += cost
        print_cost(f"Generating {filename}", cost)

        write_file(
            filename,
            filecode,
            directory,
        )

        log(
            log_file_path=log_file_path,
            text=f"**Generating code for filename:** {filename}\n\nCode:\n{filecode}\n\nCost: {cost}",
            should_log=should_log,
        )

        print("\n")

    print_cost("Total app", total_cost)
    log(
        log_file_path=log_file_path,
        text=f"**Total cost:** {total_cost}",
        should_log=should_log)


@stub.local_entrypoint()
def main(prompt, logging=False, directory=generatedDir):
    if prompt.endswith(".md"):
        with open(prompt, "r") as promptfile:
            prompt = promptfile.read()

    generate(prompt=prompt, directory=directory, should_log=logging)
