# Ironwall Unreal Plugin

1. Build lib: cd cpp-thin-client && cmake -B build -DCMAKE_BUILD_TYPE=Release && cmake --build build -j
2. Copy unreal/Ironwall into UE project Plugins/Ironwall
3. Enable plugin, add UIronwallClient to Pawn/PlayerController
4. BeginPlay -> StartSession; movement -> SubmitMovement; EndPlay -> StopSession
