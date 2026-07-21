# Ironwall Unity Package

## Install
- Copy this folder into your Unity project's Packages/ or use OpenUPM later.
- Or drag the folder into Assets/.

## Usage
1. Add `IronwallClient` component to a GameObject.
2. Call `StartSession()`, then `SubmitMovement(from, to, dt)` on movement.
3. Call `StopSession()` on disconnect / quit.

Native lib linkage (libironwall) is stubbed — wire P/Invoke in IronwallNative.cs after building the C++ library for your target platform.
