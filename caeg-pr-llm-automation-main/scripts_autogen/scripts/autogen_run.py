import logging
import autogen
from autogen import AssistantAgent, UserProxyAgent, ConversableAgent
from autogen.agentchat import GroupChat, GroupChatManager
import autogen.runtime_logging
import os
from typing import Annotated
import json
import importlib
import pprint

import get_diff


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

logger.info("Initiating logging")

logging_session_id = autogen.runtime_logging.start(
    config={"filename":"runtime.log"}
)

config_list = [
  {
    "model": "gpt-4o",
    "api_type": "azure",
    "api_key": '',
    "base_url": "",
    "api_version": "2024-02-01"
  }
]

llm_config = {
    # "request_timeout": 600,
    "seed":1,
    "config_list": config_list,
    "temperature": 0.2
}

logger.info("llm configured successfully")

# Agent messages
navigator_message = """
    You are FileNavigator. You can access your local repository and navigate to specific files.
    You'll open the requested file and show its content as a list of lines using see_file()
"""
analyzer_message = """
    You are an efficient Code Analyzer. You can analyze the code changes within a file based on the diff content provided. You do not have to analyze the whole code given to you. You have to analyze only the diff data provided to you. You can understand the context from the opened file.

    Provide a list of lines representing the diff content, and you'll check if high code quality is maintained in the code. Some of the good practices you'll analyze are:

    Proper Logging: Check if critical events and errors are logged clearly and informatively.
    Exception Handling: Verify if potential exceptions (such as division by zero, file not found, etc.) are handled gracefully using appropriate mechanisms like try-except blocks.
    Code Quality: Evaluate if the code is well-documented, follows consistent naming conventions, uses small functions (preferably less than 100 lines), and employs the RAII principle for resource management. Check if immutability is indicated using const where possible, smart pointers are used instead of raw pointers, range-based for loops are utilized, and operations that can lead to undefined behavior (like dereferencing null pointers) are avoided. You only have to mention ways to improve the code quality.
    Finally, you'll generate a patch including the relevant code needed to improve the code quality. You'll include only the relevant code and ensure the suggested patch is in unidiff format. You will ensure that you do this religiously. The patch MUST be in unified formatting.

    An example of the analysis of a cpp file names "my_function.cpp" is given below. I'll use the same format. This analysis will be my final message. Ensure that the patch you generate is in unified format. Also, ensure that the correct file name is provided in the analysis.
    {
    "file": "functions/my_function.cpp", 
    "proper logging": false, 
    "exception handling": false, 
    "code suggestions": "Add exception handling for division by zero and include logging for input and output values."
    "code quality":"
        1. The functions `add` and `divide` are small and well-defined.
        2. The code lacks comments and documentation.
    "patch":"    
    int my_function(int value) {
    -  int result = 1000 / value;
    -  return result;
    +    if (value == 0) {
    +        throw invalid_argument("Division by zero is not allowed.");
    +    }
    +    int result = 1000 / value;
    +    return result;
    }

    +    try {
    +        int result = my_function(input_value);
    +        cout << "Result: " << result << endl;
    +    } catch (const invalid_argument& e) {
    +        cerr << "Error: " << e.what() << endl;
    +    }"
"""
updater_message = """
    You are JsonUpdater.
    You will be provided with analysis data. You'll create a file named 'analysis.json' in the repo directory using create_json_file(), if it does not already exist. 
    To create the json file, the 'filename' argument for create_json_file() will be 'repo/analysis.json'. If it already exists, you'll update the JSON file with the analysis using create_json_file(). The data to be updated should be in dictionary format.
    An example of the dictionary that needs to be updated in the 'analysis.json' file looks like this:
    {
        "file": "function.cpp",
        "proper_logging": "The code does not include any logging mechanism. Critical events such as the input value and the result are printed to the console but not logged.",
        "exception_handling": "There is no exception handling for potential errors, such as division by zero, which can cause the program to crash.",
        "code_quality": "The function `my_function` is small and well-defined. The code lacks comments and documentation. The use of `using namespace std;` is generally discouraged in header files or global scope to avoid naming conflicts. The code does not handle potential exceptions, such as division by zero. The code does not use modern C++ features like smart pointers, range-based for loops, or RAII principles. The code does not follow consistent naming conventions for variables (e.g., `input_value` vs. `value`).",
        "suggested_improvements": 
            1. "Add Exception Handling: Handle division by zero in `my_function`. Use try-catch blocks in `main` to catch and handle exceptions gracefully.",
            2. "Add Logging: Include logging for input values and results.",
            3. "Improve Code Quality: Add comments and documentation. Avoid using `using namespace std;` in global scope."
        "patch": "#include <iostream>\n+#include <stdexcept>\n\n-using namespace std;\n+using std::cin;\n+using std::cout;\n+using std::cerr;\n+using std::endl;\n+using std::invalid_argument;\n\n int my_function(int value) {\n-  int result = 1000 / value;\n-  return result;\n+    if (value == 0) {\n+        throw invalid_argument(\"Division by zero is not allowed.\");\n+    }\n+    int result = 1000 / value;\n+    return result;\n }\n\n int main() {\n-  int input_value;\n+    int input_value;\n\n-  cout << \"Enter an integer value: \";\n-  cin >> input_value;\n+    cout << \"Enter an integer value: \";\n+    cin >> input_value;\n\n-  int result = my_function(input_value);\n+    try {\n+        int result = my_function(input_value);\n\n-  cout << \"Result: \" << result << endl;\n+        cout << \"Result: \" << result << endl;\n+    } catch (const invalid_argument& e) {\n+        cerr << \"Error: \" << e.what() << endl;\n+    }\n\n-  return 0;\n+    return 0;\n }"
    }
    Return TERMINATE once you have updated the 'analysis.json' file. Do not forget to return TERMINATE. Always do it after the data is appended successfully.
"""
executor_message = """
    You are Executor. You know very well when to execute a tool/function when an agent responds. You only execute tools.
    Return TERMINATE once you have updated the 'analysis.json' file. Do not forget to return TERMINATE. Output TERMINATE if the last message is empty. Always do it after the data is appended successfully.
"""

logger.info("Agent messages defined successfully")

# Agents
file_navigator = autogen.AssistantAgent(
    name="FileNavigator",
    description="An autonomous agent proficient in navigating through file structures and retrieving targeted data efficiently.",
    llm_config=llm_config,
    system_message=navigator_message,
)
analyzer = autogen.AssistantAgent(
    name="Analyzer",
    description="A specialized agent equipped with advanced analytical capabilities to process and interpret complex cpp code.",
    llm_config=llm_config,
    system_message=analyzer_message,
    # system_message="Give your analysis of the code."
)
json_updater = autogen.AssistantAgent(
    name="JsonUpdater",
    description="An automated agent designed to create and update JSON files with precision and accuracy based on specified criteria.",
    llm_config=llm_config,
    system_message=updater_message,
)
executor = autogen.ConversableAgent(
    name="Executor",
    human_input_mode="NEVER",
    description="An AI agent to execute functions.",
    system_message=executor_message,
    # is_termination_msg=lambda x: x.get("content", "").find("TERMINATE") >= 0,
)
user_proxy = autogen.UserProxyAgent(
    name="UserProxy",
    human_input_mode="NEVER",
    # code_execution_config=False,
    max_consecutive_auto_reply=0,
    is_termination_msg=lambda msg: msg.get("content") is not None and "TERMINATE" in msg["content"],
)

logger.info("Agents created successfully")

# Group Chat
group_msg = """You are the Orchestrator of the code-analysis process. You will follow the below workflow:
    1. First, use see_file() to navigate to the file location and output the contents of the file. This task is given to the Navigator agent.
    2. Second, send the diff data and the output of the Navigator agent to the Analyzer agent.
    3. Third, send the output of the Analyzer agent to the JsonUpdater agent.
    4. The process is completed.
    5. Return TERMINATE once the JsonUpdater agent updates the 'analysis'.json file. Do not forget. You should output/type 'TERMINATE'.
    6. If you recieve an empty message from the executor, terminate the group chat. Do not forget to return TERMINATE. Always do it after updating the 'analysis.json' file
    """
groupchat = autogen.GroupChat(
    agents=[file_navigator, analyzer, json_updater, executor],
    messages=[group_msg],
    max_round=10, # here will be at most 10 iteratiosn of selecting speaker, agent speaks and broadcasting message.
    speaker_selection_method="auto",
)
manager = autogen.GroupChatManager(
    groupchat=groupchat, 
    llm_config=llm_config,
    max_consecutive_auto_reply = 0,
    system_message=group_msg,
    is_termination_msg=lambda msg: msg.get("content") is not None and "TERMINATE" in msg["content"],
    )

# Tool definitions
default_path = "/app/"
@executor.register_for_execution()
@json_updater.register_for_llm(description="List files in choosen directory.")
@file_navigator.register_for_llm(description="List files in choosen directory.")
def list_dir(directory: Annotated[str, "Directory to check."]) -> str:
    files = os.listdir(default_path + directory)
    return f"These are the list of files in the {directory}: {files}."

@executor.register_for_execution()
@file_navigator.register_for_llm(description="Check the contents of a chosen file.")
def see_file(filename: Annotated[str, "Name and path of file to check."]) -> str:
    with open(default_path + filename, "r") as file:
        lines = file.readlines()
    formatted_lines = [f"{i+1}:{line}" for i, line in enumerate(lines)]
    file_contents = "".join(formatted_lines)
    final_msg = "These are the file contents" + file_contents
    return final_msg

@executor.register_for_execution()
@json_updater.register_for_llm(description="Create a new json file in the repository directory using the filename as argument.")
def create_json_file(filename: str) -> str:
  try:
    new_list = []
    with open(default_path + filename, 'w') as json_file:
      json.dump(new_list, json_file, indent=4)
    return f"JSON file created successfully at {filename}"
  except Exception as e:
    print(f"An error occurred while creating the JSON file: {e}")
    return str(e)

@executor.register_for_execution()
@json_updater.register_for_llm(description="Update JSON file by appending data to a list using the file name as argument.")
def update_json_file(filename: str, data: dict) -> str:
  try:
    with open(default_path + filename, 'r') as f:
      filedata = json.load(f)
    
    if not isinstance(filedata, list):
      return "Error: JSON data is not a list."
    filedata.append(data)
    
    with open(default_path + filename, 'w') as f:
      json.dump(filedata, f, indent=4)
   
    print("Data appended successfully.")
    return "TERMINATE"
  
  except Exception as e:
    print(f"An error occurred: {e}")
    return str(e)

logger.info("Functions defined successfully.")

# Get diff content
token = os.getenv("token")
pr_number = os.getenv("pr_number")
repo_owner = os.getenv("repo_owner")
importlib.reload(get_diff)
diff_content = get_diff.main(repo_owner, pr_number, token)

manager_msg ="""
You are to work with a directory named 'repo' in this current directory.
This is a diff file named {file_name} from a PR. 
{single_diff_file}
Send it to the manager. Navigate to the file and then analyse and then create/update the 'analysis.json' file.
"""

# Initiate chat
logger.info("Initiating chat")
cost_dict = {}
summary_dict = {}
for i, single_file in enumerate(diff_content):
    print(f"============================== NEW DIFF FILE : {single_file['filename']} ======================================")
    chat_result = user_proxy.initiate_chat(
        manager,
        message=manager_msg.format(file_name=single_file['filename'] , single_diff_file=diff_content[i]),
        max_turns=2,
        summary_method="reflection_with_llm",
        max_consecutive_auto_reply=1,
    )
    cost_dict[f"file {i+1}"] = chat_result.cost["usage_including_cached_inference"]["total_cost"]
    summary_dict[f"file {i+1}"] = chat_result.summary
    user_proxy.reset()
    manager.reset()
    analyzer.reset()
    file_navigator.reset()
    json_updater.reset()

total_cost = 0
for value in cost_dict.values():
    total_cost += value
print(f"Summary for each file chat: {summary_dict}")
print(f"Cost for each file: {cost_dict}")
print(f"Total Cost: {total_cost}")

logger.info("Chat terminated")
