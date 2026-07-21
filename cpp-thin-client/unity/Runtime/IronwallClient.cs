using System;
using System.Runtime.InteropServices;
using System.Text;
using UnityEngine;

namespace Ironwall
{
    public class IronwallClient : MonoBehaviour
    {
        public string PlayerId = "player_001";
        public float MaxSpeed = 10f;

        public string SessionId { get; private set; }
        public string LastProofId { get; private set; }
        public string LastQuoteHash { get; private set; }
        public string LastCombinedHash { get; private set; }

        IntPtr _native;

        void Awake()
        {
            Debug.Log($"[Ironwall] native version: {IronwallNative.GetVersion()}");
        }

        public void StartSession()
        {
            if (_native != IntPtr.Zero)
                IronwallNative.ironwall_client_destroy(_native);

            _native = IronwallNative.ironwall_client_create(PlayerId, MaxSpeed);
            if (_native == IntPtr.Zero)
            {
                Debug.LogError("[Ironwall] failed to create native client (lib missing?)");
                SessionId = Guid.NewGuid().ToString(); // fallback stub
                return;
            }

            var quote = new StringBuilder(128);
            int rc = IronwallNative.ironwall_client_attest(_native, quote, (UIntPtr)quote.Capacity);
            if (rc != 0)
            {
                Debug.LogError($"[Ironwall] attest failed rc={rc}");
                return;
            }
            LastQuoteHash = quote.ToString();
            SessionId = Guid.NewGuid().ToString();
            Debug.Log($"[Ironwall] session started quote={LastQuoteHash}");
        }

        public void SubmitMovement(Vector3 from, Vector3 to, float deltaSeconds)
        {
            if (_native == IntPtr.Zero)
            {
                LastProofId = Guid.NewGuid().ToString();
                return;
            }

            uint dtMs = (uint)Mathf.Max(1, Mathf.RoundToInt(deltaSeconds * 1000f));
            var proofId = new StringBuilder(80);
            var hash = new StringBuilder(80);
            int rc = IronwallNative.ironwall_client_prove_movement(
                _native,
                from.x, from.y, from.z,
                to.x, to.y, to.z,
                dtMs,
                proofId, (UIntPtr)proofId.Capacity,
                hash, (UIntPtr)hash.Capacity);

            if (rc == -3)
            {
                Debug.LogWarning("[Ironwall] movement REJECTED (speedhack?)");
                return;
            }
            if (rc != 0)
            {
                Debug.LogError($"[Ironwall] prove failed rc={rc}");
                return;
            }

            LastProofId = proofId.ToString();
            LastCombinedHash = hash.ToString();
            Debug.Log($"[Ironwall] proof={LastProofId} anchor={LastCombinedHash}");
        }

        public void StopSession()
        {
            if (_native != IntPtr.Zero)
            {
                IronwallNative.ironwall_client_destroy(_native);
                _native = IntPtr.Zero;
            }
            Debug.Log($"[Ironwall] session {SessionId} stopped");
            SessionId = null;
        }

        void OnDestroy() => StopSession();
    }
}
