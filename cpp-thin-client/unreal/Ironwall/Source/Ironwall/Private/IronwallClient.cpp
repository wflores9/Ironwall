#include "IronwallClient.h"

void UIronwallClient::StartSession(const FString& PlayerId)
{
    SessionId = FGuid::NewGuid().ToString();
    UE_LOG(LogTemp, Log, TEXT("Ironwall session started for %s -> %s"), *PlayerId, *SessionId);
}

void UIronwallClient::SubmitMovement(FVector From, FVector To, float DeltaSeconds)
{
    LastProofId = FGuid::NewGuid().ToString();
    UE_LOG(LogTemp, Verbose, TEXT("Ironwall movement proof %s (delta=%.3f)"), *LastProofId, DeltaSeconds);
}

void UIronwallClient::StopSession()
{
    UE_LOG(LogTemp, Log, TEXT("Ironwall session %s stopped"), *SessionId);
    SessionId.Empty();
}
