# simple-web-chat-user-interface

This is a web based `UserInterface` for a simple chat copilot.

It backed on a local HTTP service to host a page for the chatting,
and using WebSocket to transmit messages between the web server and other parts of the copilot.

## Config

1. `websocket_host` and `websocket_port`:
    The WebSocket server host and port to connect for messages transmissions.
2. `dist_path`:
    The chat server local path.
    This interface will unzip the web server dist.zip to this folder for serving.
    It will be defaulted to the component "config/dist" folder if specified to `null`.
3. `user_name`: The user name to be displayed. Default to `null`.
4. `slider_params`:
    A mapping for slider bar parameters.
    Each key in the mapping is the slider bar title,
    and each value in the mapping is a dict contains the `min`, `max`, initial `value`, and `step` of the slider.
5. `role_mapping`:
    Mapping component roles to names, and with an optional avatar url.
    If the component has been specified a name, the name in this mapping will be ignored.
6. `resources`:
    A `websocket_client` is needed for message transmission between this component and the backed web server.

## Usage

Adding the configs below to the `config.yaml` file for a specific Copilot:

```yaml
user_interface:
  group_id: org.concopilot.example.interface.chat
  artifact_id: simple-web-chat-user-interface
  version: <version>
```

### Resources

Two resources should be added to the copilot resource manager.
One is the `websocket_client` mentioned above,
another is a `http_server` for hosting the chatting page.
A `websocket_server` may also needed if you are not able to access a third-party one.
Below is an example:

```yaml
config:
  resource_manager:
    group_id: org.concopilot.basic.resource.manager
    artifact_id: basic-resource-manager
    version: <version>
    config:
      resources:
        -
          # ...
        -
          group_id: org.concopilot.example.resource.websocket.server
          artifact_id: simple-websocket-server
          version: <version>
          config:
            host: <websocket_host>
            port: <websocket_port>
        -
          group_id: org.concopilot.example.resource.websocket.client
          artifact_id: simple-websocket-client
          version: <version>
          config:
            host: <websocket_host>
            port: <websocket_port>
        -
          group_id: org.concopilot.example.resource.http.server
          artifact_id: simple-http-server
          version: <version>
          config:
            host: <chat_server_host>
            port: <chat_server_port>
            directory: <dist_path>
        -
          # ...
```

Please make sure that:
1. Make sure to connect to the same WebSocket server.
    That is, the server `host` and `port` of the WebSocket client must be the same to the ones of this user interface,
    as well as the ones of the WebSocket server if needed.
2. Make sure the HTTP server will be started at the same directory of this component's `dist_path` where the `dist.zip` being unzipped to.
3. Put the `websocket_server` resource before the client, so that the server will be initialized first.
