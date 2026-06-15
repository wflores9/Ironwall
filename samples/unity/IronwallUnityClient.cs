using System;
using System.Collections;
using System.Text;
using UnityEngine;
using UnityEngine.Networking;

public sealed class IronwallUnityClient : MonoBehaviour
{
    [SerializeField] private string BridgeUrl = "http://127.0.0.1:8767/input";
    [SerializeField] private string PlayerId = "unity-player";

    private ulong sequence;
    private string sessionToken;

    private void Awake()
    {
        sessionToken = Environment.GetEnvironmentVariable("IRONWALL_SESSION_TOKEN") ?? "";
    }

    private void Update()
    {
        var payload = JsonUtility.ToJson(new IronwallInputPayload
        {
            engine = "unity",
            player_id = PlayerId,
            sequence = sequence++,
            timestamp_ns = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds() * 1000000,
            actions = new IronwallActions
            {
                move_x = Input.GetAxisRaw("Horizontal"),
                move_y = Input.GetAxisRaw("Vertical"),
                look_x = Input.GetAxisRaw("Mouse X"),
                look_y = Input.GetAxisRaw("Mouse Y"),
                fire = Input.GetButton("Fire1"),
                jump = Input.GetButton("Jump")
            }
        });

        StartCoroutine(PostInput(payload));
    }

    private IEnumerator PostInput(string payload)
    {
        using var request = new UnityWebRequest(BridgeUrl, "POST");
        byte[] body = Encoding.UTF8.GetBytes(payload);
        request.uploadHandler = new UploadHandlerRaw(body);
        request.downloadHandler = new DownloadHandlerBuffer();
        request.SetRequestHeader("Content-Type", "application/json");
        request.SetRequestHeader("Authorization", "Bearer " + sessionToken);
        yield return request.SendWebRequest();
    }
}

[Serializable]
public sealed class IronwallInputPayload
{
    public string engine;
    public string player_id;
    public ulong sequence;
    public long timestamp_ns;
    public IronwallActions actions;
}

[Serializable]
public sealed class IronwallActions
{
    public float move_x;
    public float move_y;
    public float look_x;
    public float look_y;
    public bool fire;
    public bool jump;
}
