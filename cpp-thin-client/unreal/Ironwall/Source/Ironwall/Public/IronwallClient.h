#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "IronwallClient.generated.h"

UCLASS(ClassGroup=(Ironwall), meta=(BlueprintSpawnableComponent))
class IRONWALL_API UIronwallClient : public UActorComponent
{
	GENERATED_BODY()
public:
	UIronwallClient();

	UFUNCTION(BlueprintCallable, Category="Ironwall")
	bool StartSession(const FString& PlayerId);

	UFUNCTION(BlueprintCallable, Category="Ironwall")
	bool SubmitMovement(FVector From, FVector To, float DeltaSeconds);

	UFUNCTION(BlueprintCallable, Category="Ironwall")
	void StopSession();

	UFUNCTION(BlueprintCallable, Category="Ironwall")
	FString GetLastProofId() const { return LastProofId; }

protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

private:
	void* NativeHandle = nullptr;
	FString LastProofId;
};
