# basic-chat-copilot

This is a copilot/agent for a simple LLM chatting.

It uses the [basic-copilot](https://concopilot.org/component/org.concopilot.basic.copilot/basic-copilot) as the backed framework,
and the [chat-interactor](https://concopilot.org/component/org.concopilot.example/chat-interactor) for the main loop.

Some parameters of the components used in this chatting copilot are exposed in the "config.yaml" files for convenience.

## Config

As it uses the standard general [basic-copilot](https://concopilot.org/component/org.concopilot.basic.copilot/basic-copilot) framework,
people can refer to the basic-copilot [config detail](https://concopilot.org/component/org.concopilot.basic.copilot/basic-copilot/0.0.0) for how it works.
It is also recommended to check the differences between the config Yaml files of this component and the basic-copilot [one](https://concopilot.org/component/org.concopilot.basic.copilot/basic-copilot/0.0.0) to learn how to build a copilot/agent by just changing or adding components.

We provided several slightly different config Yaml files to show the advantages of ConCopilot component reusability and replaceability.
People can try to run them respectively to learn their detailed differences apart from the main chatting functionality.
Below are the instructions:

1. config.yaml

    The default config file, use OpenAI model and chatting in the command line interface.

2. config_glm.yaml

    Use ChatGLM model and chatting in the command line interface.

3. config_rwkv.yaml

    Use RWKV model and chatting in the command line interface.

4. config_web.yaml

    Use OpenAI model and the "[simple-web-chat-user-interface](https://concopilot.org/component/org.concopilot.example.interface.chat/simple-web-chat-user-interface/0.0.0)" so that user can chat to the LLM on a web page with a browser.

5. config_web_glm.yaml

    Use ChatGLM model and the "[simple-web-chat-user-interface](https://concopilot.org/component/org.concopilot.example.interface.chat/simple-web-chat-user-interface/0.0.0)" so that user can chat to the LLM on a web page with a browser.

6. config_web_rwkv.yaml

    Use RWKV model and the "[simple-web-chat-user-interface](https://concopilot.org/component/org.concopilot.example.interface.chat/simple-web-chat-user-interface/0.0.0)" so that user can chat to the LLM on a web page with a browser.

The configs for all the three models can be changed, feel free to try different model scales or versions for any of the OpenAI, ChatGLM, and RWKV if you like.

It is also possible to replace the backed LLM to any other models you like,
as long as you or anyone else has build those models into ConCopilot components.
Refer to the source code of the three models above and our [docs](https://concopilot.readthedocs.io/) for how to build and deploy ConCopilot components,
then you will find things very easy.
See [this](https://concopilot.readthedocs.io/en/latest/how_to/find_component_source_code/) to learn how to find a component's source code, 

## Usage

Run below command in any CLI to start the agent by using the default "config.yaml" configuration:

```shell
conpack run --group-id=org.concopilot.example.copilot --artifact-id=basic-chat-copilot --version=<version>
```

Replace the `<version>` to the specified version you like.
The lowest version provides all the config files above is "0.0.1".

Do forget to modify you OpenAI settings in you ".runtime" folder under your working directory.
Find the "config.yaml" according to the `group_id`, `artifact_id`, and `version` in the ".runtime" folder after the execution of the command.

You may also like to run this command first if you want to just download the components and modify settings first.

```shell
conpack build --group-id=org.concopilot.example.copilot --artifact-id=basic-chat-copilot --version=<version>
```

Run below command to start the agent with other config files:

```shell
conpack run --group-id=org.concopilot.example.copilot --artifact-id=basic-chat-copilot --version=<version> --config-file=<config_file>
```

Replace the `<config_file>` to any config files mentioned above.

### Note of Cuda, GPU and PyTorch

You must install Cuda yourself if you want to run either the ChatGLM or RWKV,
or even other LLMs locally on GPUs.
ConCopilot does NOT handle environment issues out of python.

ConCopilot can install PyTorch for you theoretically.
But you may also need to install it manually if the default `pip install torch` does not compatible to your environment.
