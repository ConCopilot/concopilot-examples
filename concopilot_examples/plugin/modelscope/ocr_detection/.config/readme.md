# ocr_detection

This is a plugin for ModelScope `ocr_detection` pipeline.

## Config

A ModelScope pipeline model should be added to the plugin's `resources` list.
See the Usage section below for details.

## Usage

Add the plugin config to the `plugin_manager`'s `plugins` list to the `config.yaml` file for a specific Copilot/Agent like below:

```yaml
config:
  plugin_manager:
    config:
      plugins:
        -
          group_id: org.concopilot.example.modelscope.plugin
          artifact_id: ocr_detection
          version: <version>
          config:
            resources:
              -
                type: model
                name: ocr_detection # make sure identical to the model name in the resource list
```

Then, add the ModelScope pipeline model to the `resource_manager`'s `resources` list to the `config.yaml` file for the Copilot/Agent like below:

```yaml
config:
  resource_manager:
    config:
      resources:
        -
          group_id: org.concopilot.example.modelscope.model
          artifact_id: pipeline
          version: <version>
          config:
            name: ocr_detection # make sure identical to the name of the resource referenced by the plugin
            pipeline_params:
              task: ocr_detection
              model: damo/cv_resnet18_ocr-detection-db-line-level_damo
```

Please make sure the `name` of the resource is the same as the resource `name` referenced by the plugin.
