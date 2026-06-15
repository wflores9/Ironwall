#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "IronwallUnrealClient.generated.h"

UCLASS()
class AIronwallUnrealClient : public AActor
{
    GENERATED_BODY()

public:
    AIronwallUnrealClient();

protected:
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;

private:
    UPROPERTY(EditAnywhere, Category = "Ironwall")
    FString BridgeUrl = TEXT("http://127.0.0.1:8767/input");

    UPROPERTY(EditAnywhere, Category = "Ironwall")
    FString PlayerId = TEXT("unreal-player");

    uint64 Sequence = 0;
    FString SessionToken;

    void SendInputPayload(const FString& PayloadJson) const;
};
