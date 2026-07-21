using System;
using System.Runtime.InteropServices;
using UnityEngine;

namespace Ironwall
{
    /// <summary>
    /// P/Invoke bindings for libironwall.so / .dll / .dylib
    /// </summary>
    public static class IronwallNative
    {
#if UNITY_EDITOR_LINUX || UNITY_STANDALONE_LINUX
        const string Lib = "ironwall";
#elif UNITY_EDITOR_OSX || UNITY_STANDALONE_OSX
        const string Lib = "ironwall";
#elif UNITY_EDITOR_WIN || UNITY_STANDALONE_WIN
        const string Lib = "ironwall";
#else
        const string Lib = "ironwall";
#endif

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern IntPtr ironwall_version();

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern IntPtr ironwall_client_create(
            [MarshalAs(UnmanagedType.LPStr)] string playerId,
            float maxSpeed);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern void ironwall_client_destroy(IntPtr client);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int ironwall_client_attest(
            IntPtr client,
            [MarshalAs(UnmanagedType.LPStr)] System.Text.StringBuilder outQuoteHash,
            UIntPtr outLen);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int ironwall_client_prove_movement(
            IntPtr client,
            float fromX, float fromY, float fromZ,
            float toX, float toY, float toZ,
            uint deltaTms,
            [MarshalAs(UnmanagedType.LPStr)] System.Text.StringBuilder outProofId,
            UIntPtr proofIdLen,
            [MarshalAs(UnmanagedType.LPStr)] System.Text.StringBuilder outCombinedHash,
            UIntPtr hashLen);

        [DllImport(Lib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int ironwall_client_respond_challenge(
            IntPtr client,
            [MarshalAs(UnmanagedType.LPStr)] string challengeId,
            [MarshalAs(UnmanagedType.LPStr)] System.Text.StringBuilder outResponseId,
            UIntPtr outLen);

        public static string GetVersion()
        {
            try
            {
                var ptr = ironwall_version();
                return ptr != IntPtr.Zero ? Marshal.PtrToStringAnsi(ptr) : "unknown";
            }
            catch (DllNotFoundException)
            {
                return "0.1.0-stub (native lib not loaded)";
            }
        }
    }
}
