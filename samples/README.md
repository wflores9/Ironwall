# Ironwall Engine Samples

These samples show the recommended engine integration shape:

1. Launch the game through `ironwall-launcher`.
2. Read `IRONWALL_SESSION_TOKEN` and player metadata from the environment.
3. Capture engine-native input events.
4. Send deterministic input JSON to an Ironwall bridge/sidecar.
5. Let the Ironwall thin-client layer handle HMAC signing, Merkle audit, and server transport.

The samples are intentionally small and dependency-light. They are designed to
be copied into an existing Unity or Unreal project as a first integration pass.

## Unity

Copy `unity/IronwallUnityClient.cs` into `Assets/Scripts/` and attach it to a
GameObject in the first loaded scene. Configure `BridgeUrl` if your local bridge
is not listening on `http://127.0.0.1:8767/input`.

## Unreal

Copy `unreal/IronwallUnrealClient.h` and `unreal/IronwallUnrealClient.cpp` into
an Unreal module, add `HTTP` and `Json` dependencies, then create the actor in
your player controller or game instance.
