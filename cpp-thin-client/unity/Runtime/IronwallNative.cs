using System;
using System.Runtime.InteropServices;
using UnityEngine;

namespace Ironwall
{
    /// <summary>
    /// P/Invoke surface for libironwall (fill in once .so/.dll/.dylib is built).
    /// </summary>
    public static class IronwallNative
    {
        const string Lib = "ironwall";

        // [DllImport(Lib)] public static extern int ironwall_version();
        // [DllImport(Lib)] public static extern IntPtr ironwall_tee_generate();
        // etc.

        public static string Version => "0.1.0-stub";
    }
}
