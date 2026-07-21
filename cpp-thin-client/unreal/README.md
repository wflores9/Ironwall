# Ironwall Unreal Engine Plugin

Minimal UE5 plugin skeleton wrapping the Ironwall C++ thin client.

## Setup
1. Build standalone lib:
       cd cpp-thin-client && mkdir build && cd build
       cmake .. -DCMAKE_BUILD_TYPE=Release && cmake --build . -j
2. Copy unreal/Ironwall into your project's Plugins/ folder
3. Enable plugin in editor
4. Use UIronwallClient from Blueprint or C++
