#include "IronwallClient.h"

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
	NativeHandle = ironwall_client_create(Utf8.Get(), 10.0f);
	if (!NativeHandle)
	{
		UE_LOG(LogTemp, Error, TEXT("Ironwall: create failed"));
		return false;
	}
	char Quote[128] = {};
	if (ironwall_client_attest(static_cast<ironwall_client*>(NativeHandle), Quote, sizeof(Quote)) != 0)
	{
		UE_LOG(LogTemp, Warning, TEXT("Ironwall: attest soft-fail"));
	}
	else
	{
		UE_LOG(LogTemp, Log, TEXT("Ironwall: attest %s"), UTF8_TO_TCHAR(Quote));
	}
	UE_LOG(LogTemp, Log, TEXT("Ironwall: version %s"), UTF8_TO_TCHAR(ironwall_version()));
	return true;
}

bool UIronwallClient::SubmitMovement(FVector From, FVector To, float DeltaSeconds)
{
	if (!NativeHandle) return false;
	char ProofId[128] = {};
	char Combined[128] = {};
	const uint32_t DtMs = static_cast<uint32_t>(FMath::Max(1.0f, DeltaSeconds * 1000.0f));
	const int Rc = ironwall_client_prove_movement(
		static_cast<ironwall_client*>(NativeHandle),
		From.X, From.Y, From.Z,
		To.X, To.Y, To.Z,
		DtMs,
		ProofId, sizeof(ProofId),
		Combined, sizeof(Combined));
	if (Rc != 0)
	{
		UE_LOG(LogTemp, Warning, TEXT("Ironwall: prove_movement rejected rc=%d"), Rc);
		return false;
	}
	LastProofId = UTF8_TO_TCHAR(ProofId);
	UE_LOG(LogTemp, Log, TEXT("Ironwall: proof %s hash %s"), *LastProofId, UTF8_TO_TCHAR(Combined));
	return true;
}

void UIronwallClient::StopSession()
{
	if (NativeHandle)
	{
		ironwall_client_destroy(static_cast<ironwall_client*>(NativeHandle));
		NativeHandle = nullptr;
	}
}
