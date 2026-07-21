# Unreal Sample

1. Copy `unreal/Ironwall` to your UE project `Plugins/`
2. Enable plugin
3. Add `UIronwallClient` to GameInstance or PlayerController
4. Call `StartSession` on login, `SubmitMovement` each tick, `StopSession` on disconnect.

See `IronwallClient.h/cpp` for native calls.
