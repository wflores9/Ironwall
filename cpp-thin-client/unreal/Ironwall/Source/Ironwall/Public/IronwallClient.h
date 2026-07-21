#pragma once
#include "CoreMinimal.h"
#include "UObject/NoExportTypes.h"
#include "IronwallClient.generated.h"

UCLASS(BlueprintType)
class IRONWALL_API UIronwallClient : public UObject
{
    GENERATED_BODY()
public:
    UIronwallClient();
    virtual void BeginDestroy() override;

    UFUNCTION(BlueprintCallable, Category = "Ironwall")
    void StartSession(const FString& PlayerId);

    UFUNCTION(BlueprintCallable, Category = "Ironwall")
    void SubmitMovement(FVector From, FVector To, float DeltaSeconds);

    UFUNCTION(BlueprintCallable, Category = "Ironwall")
    void StopSession();

    UPROPERTY(BlueprintReadOnly, Category = "Ironwall")
    FString SessionId;

    UPROPERTY(BlueprintReadOnly, Category = "Ironwall")
    FString LastProofId;

    UPROPERTY(BlueprintReadOnly, Category = "Ironwall")
    FString LastQuoteHash;

    UPROPERTY(BlueprintReadOnly, Category = "Ironwall")
    FString LastCombinedHash;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Ironwall")
    float MaxSpeed = 10.f;

private:
    void* NativeClient = nullptr;
};
