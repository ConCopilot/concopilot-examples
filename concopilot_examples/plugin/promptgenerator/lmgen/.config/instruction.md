You will be provided a YAML configuration of a Plugin. 
Your task is to summarize the configuration as precise and concise as possible, better less than 200 words.

The summarization must include these information:

1. A precise and concise "Summary" that describe the function and purpose of the Plugin.
2. A list of API descriptions for APIs that the plugin provided, also including the function and purpose of each API.

The summarization you made will be provided to some other LLM like you to help that LLM understand all the APIs provided by the Plugin, and when and how to call each API.
The YAML configuration will also be provided to the LLM, so do not provide a too detailed summarization, just provide information that can help the LLM understand the YAML configuration. 
You must make sure if you are provided the summarization and YAML configuration, you can definitely understand when and how to use the plugin in any arbitrary task.

Below is an example of the YAML configuration format:

```yaml
id: <id> # The ID of the plugin
name: <name> # The name of the plugin

info: # The basic information of the plugin. This section must exist if `as_plugin` is `true`.
  title: <title> # The title of the plugin
  description: <description> # The description of the plugin
  description_for_human: <description_for_human> # Optional. Description for human readers
  description_for_model: <description_for_model> # Optional. Description for Large Language Models (LLMs) to read
  prompt: <optional_prompt> # If exists, this is the instruction to prompt LLMs
  prompt_file_name: <optional_prompt_file_name> # If exists, this is the name of the file located in the same folder as the "config.yaml" file that contains the instructions to prompt LLMs
  prompt_file_path: <optional_prompt_file_path> # If exists, this is the full file path that indicates the file contains the instructions to prompt LLMs
commands: # The list of APIs provided by the plugin. This section must exist if `as_plugin` is `true`.
  -
    command_name: <command_name_1> # The name of the first API
    description: <command_description_1> # The description of the API
    parameter: # The `parameter` required by the API
      type: # The type of the `parameter`, recommend to use a Python `Dict`
            # Use the YAML mapping/object syntax to describe the `Dict` items.
            # The YAML mapping/object syntax indicates that the type is a `Dict`,
            # and each item in the YAML mapping/object describes one key-value pair in the `Dict`.
            # The keys in the `Dict` are always string type, and their names are described as the YAML mapping/object keys.
            # The type of the value for each key is described under that key using the parameter type description syntax.
        <param_name_1>: # The name of the first parameter
          type: string # The type of the first parameter
          description: <description_1> # The description of this parameter
          enum: # Optional. The entire possible values of this parameter
            - <enum_1>
            - <enum_2>
          required: true # If true, the parameter must be provided when calling the API. If false, the parameter is optional. Defaults to true.
          asset_ref_acceptable: false # If true, an `AssetRef` object (or URL) representing an `Asset` field with the acceptable data type can be passed instead of the real parameter object.
                                      # The plugin will read the corresponding asset from the Copilot context in this case.
                                      # If false, only the real parameter object is acceptable. No `AssetRef` should be passed to this parameter.
                                      # This field defaults to false if not provided.
          example: <example> # Optional. An example of the parameter.
        <param_name_2>:
          type: List # Set the type to `List` if the parameter is a list type and the list elements are simple.
                     # It is better to attach the element type, e.g., `List[int]`.
          description: <description_2>
          required: true
          example: <example>
        <param_name_3>:
          type: # Use the YAML list syntax to describe the list element object when the list element type is complex.
                # The YAML list syntax indicates that the type is a `List`,
                # and each element in the YAML list describes the key name and value type of one field in the list element object using the parameter type description syntax.
                # Note the additional YAML `name` field that describes the key name.
            -
              name: <element_field_name1>
              type: int
              description: <element_field_description_1>
              required: true
              example: <example>
            -
              name: <element_field_name2>
              type: string
              description: <element_field_description_2>
              required: true
              example: <example>
          description: <description_3>
          required: true
          example: <example>
        <param_name_4>:
          type: Dict # Set the type to `Dict` or `Mapping` if the keys and values are simple.
                     # It is better to attach the key and value types, e.g., `Dict[str, int]`.
                     # Please note that the `Dict` keys should always be in string type.
          description: <description_4>
          required: true
          example: <example>
        <param_name_5>:
          type: # Use the YAML mapping/object syntax to describe the `Dict` items.
                # Just like the type description of the `parameter` field
            _type_ref: <type_ref_name> # Optional. A complex type can have a type reference that other parts of the YAML file can refer to for the entire type description.
            <key_name_1>:
              type: int
              description: <value_description_1>
              required: true
              example: <example>
            <key_name_2>:
              type: string
              description: <value_description_2>
              required: true
              example: <example>
          description: <description_5>
          required: true
          example: <example>
        <param_name_6>:
          type: <type_ref_name> # Use the value of the `_type_ref` defined above to indicate that this parameter has the same type as the above parameter
          description: <description_6>
          required: false
          example: <example>
      description: <description_1> # An optional description.
      required: true # An optional `required` field. Can be omitted because it defaults to true.
      asset_ref_acceptable: false # This field can also appear here to indicate that an asset reference can be passed to represent the entire input parameter dictionary.
    response: # The API response.
      type:
        <response_field_name_1>: # The name of the first response field
          type: string # The type of the first response field
          description: <response_field_description_1> # The description of the response field.
          optional: false # If false, this response field will always be included in the response. If true, this response field can be absent in the response. Defaults to false.
          example: <response_field_example_1> # Optional. An example of this response field.
        <response_field_name_2>:
          type: string
          description: <response_field_description_2>
          optional: false
          example: <response_field_example_2>
  -
    command_name: <command_name_2>
    description: <command_description_2>
    parameter:
      type: string # Can also be a simple type.
      # ...
    response:
      # ...
  # ...

config:
  id: <id> # Optional. The configured ID of the plugin
  name: <name> # Optional. The configured name of the plugin
```

Below is the YAML configuration that need you to summarize:
