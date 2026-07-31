#include "IronwallClient.h"

extern "C" {
	void* ironwall_create(const char* player_id);
	int   ironwall_attest(void* handle, char* out_quote_hex, int out_len);
	int   ironwall_prove_movement(void* handle, float x0, float y0, float z0,
	                              float x1, float y1, float z1, float dt,
	                              char* out_proof_id, int out_len);
	void  ironwall_destroy(void* handle);
}

UIronwallClient::UIronwallClient()
{
	PrimaryComponentTick.bCanEverTick = false;
}

void UIronwallClient::BeginPlay()
{
	Super::BeginPlay();
}

void UIronwallClient::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	StopSession();
	Super::EndPlay(EndPlayReason);
}

bool UIronwallClient::StartSession(const FString& PlayerId)
{
	StopSession();
	FTCHARToUTF8 Utf8(*PlayerId);
	NativeHandle = ironwall_create(Utf8.Get());
	if (!NativeHandle)
	{
		UE_LOG(LogTemp, Error, TEXT("Ironwall: create failed"));
		return false;
	}
	char Quote[128] = {};
	if (ironwall_attest(NativeHandle, Quote, sizeof(Quote)) != 0)
	{
		UE_LOG(LogTemp, Warning, TEXT("Ironwall: attest soft-fail"));
	}
	else
	{
		UE_LOG(LogTemp, Log, TEXT("Ironwall: attest %s"), UTF8_TO_TCHAR(Quote));
	}
	return true;
}

bool UIronwallClient::SubmitMovement(FVector From, FVector To, float DeltaSeconds)
{
	if (!NativeHandle) return false;
	char ProofId[128] = {};
	const int Rc = ironwall_prove_movement(
		NativeHandle,
		From.X, From.Y, From.Z,
		To.X, To.Y, To.Z,
		DeltaSeconds,
		ProofId, sizeof(ProofId));
	if (Rc != 0)
	{
		UE_LOG(LogTemp, Warning, TEXT("Ironwall: prove_movement rejected rc=%d"), Rc);
		return false;
	}
	LastProofId = UTF8_TO_TCHAR(ProofId);
	UE_LOG(LogTemp, Log, TEXT("Ironwall: proof %s"), *LastProofId);
	return true;
}

void UIronwallClient::StopSession()
{
	if (NativeHandle)
	{
		ironwall_destroy(NativeHandle);
		NativeHandle = nullptr;
	}
}
