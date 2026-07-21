#include "IronwallClient.h"

// C ABI from libironwall
extern "C" {
    struct ironwall_client;
    ironwall_client* ironwall_client_create(const char* player_id, float max_speed);
    void ironwall_client_destroy(ironwall_client* c);
    int ironwall_client_attest(ironwall_client* c, char* out_quote_hash, size_t out_len);
    int ironwall_client_prove_movement(
        ironwall_client* c,
        float from_x, float from_y, float from_z,
        float to_x, float to_y, float to_z,
        uint32_t delta_t_ms,
        char* out_proof_id, size_t proof_id_len,
        char* out_combined_hash, size_t hash_len);
    const char* ironwall_version(void);
}

UIronwallClient::UIronwallClient() {}

void UIronwallClient::BeginDestroy()
{
    StopSession();
    Super::BeginDestroy();
}

void UIronwallClient::StartSession(const FString& PlayerId)
{
    StopSession();

    NativeClient = ironwall_client_create(TCHAR_TO_UTF8(*PlayerId), MaxSpeed);
    if (!NativeClient)
    {
        UE_LOG(LogTemp, Error, TEXT("Ironwall: failed to create native client (is libironwall linked?)"));
        SessionId = FGuid::NewGuid().ToString();
        return;
    }

    char quote[128] = {};
    int rc = ironwall_client_attest(static_cast<ironwall_client*>(NativeClient), quote, sizeof(quote));
    if (rc != 0)
    {
        UE_LOG(LogTemp, Error, TEXT("Ironwall: attest failed rc=%d"), rc);
        return;
    }

    LastQuoteHash = UTF8_TO_TCHAR(quote);
    SessionId = FGuid::NewGuid().ToString();
    UE_LOG(LogTemp, Log, TEXT("Ironwall: session started quote=%s"), *LastQuoteHash);
}

void UIronwallClient::SubmitMovement(FVector From, FVector To, float DeltaSeconds)
{
    if (!NativeClient)
    {
        LastProofId = FGuid::NewGuid().ToString();
        return;
    }

    uint32_t dtMs = (uint32_t)FMath::Max(1, FMath::RoundToInt(DeltaSeconds * 1000.f));
    char proofId[80] = {};
    char hash[80] = {};

    int rc = ironwall_client_prove_movement(
        static_cast<ironwall_client*>(NativeClient),
        From.X, From.Y, From.Z,
        To.X, To.Y, To.Z,
        dtMs,
        proofId, sizeof(proofId),
        hash, sizeof(hash));

    if (rc == -3)
    {
        UE_LOG(LogTemp, Warning, TEXT("Ironwall: movement REJECTED (speedhack?)"));
        return;
    }
    if (rc != 0)
    {
        UE_LOG(LogTemp, Error, TEXT("Ironwall: prove failed rc=%d"), rc);
        return;
    }

    LastProofId = UTF8_TO_TCHAR(proofId);
    LastCombinedHash = UTF8_TO_TCHAR(hash);
    UE_LOG(LogTemp, Verbose, TEXT("Ironwall: proof=%s anchor=%s"), *LastProofId, *LastCombinedHash);
}

void UIronwallClient::StopSession()
{
    if (NativeClient)
    {
        ironwall_client_destroy(static_cast<ironwall_client*>(NativeClient));
        NativeClient = nullptr;
    }
    UE_LOG(LogTemp, Log, TEXT("Ironwall: session %s stopped"), *SessionId);
    SessionId.Empty();
}
