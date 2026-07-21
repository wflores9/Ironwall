using System;
using UnityEngine;

namespace Ironwall
{
    /// <summary>
    /// Drop on a GameObject (or use as singleton). Calls into native libironwall later.
    /// </summary>
    public class IronwallClient : MonoBehaviour
    {
        public string PlayerId = "player_001";
        public float MaxSpeed = 10f;

        public string SessionId { get; private set; }
        public string LastProofId { get; private set; }

        public void StartSession()
        {
            SessionId = Guid.NewGuid().ToString();
            Debug.Log($"[Ironwall] session started for {PlayerId} -> {SessionId}");
            // TODO: P/Invoke ironwall_tee_generate + session_create
        }

        public void SubmitMovement(Vector3 from, Vector3 to, float deltaSeconds)
        {
            LastProofId = Guid.NewGuid().ToString();
            Debug.Log($"[Ironwall] movement proof {LastProofId} delta={deltaSeconds:F3}");
            // TODO: P/Invoke zk_prove + dual_anchor
        }

        public void StopSession()
        {
            Debug.Log($"[Ironwall] session {SessionId} stopped");
            SessionId = null;
        }

        void OnDestroy() => StopSession();
    }
}
