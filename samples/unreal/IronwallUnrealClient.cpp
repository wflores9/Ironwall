#include "IronwallUnrealClient.h"

#include "Dom/JsonObject.h"
#include "HttpModule.h"
#include "Interfaces/IHttpRequest.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"

AIronwallUnrealClient::AIronwallUnrealClient()
{
    PrimaryActorTick.bCanEverTick = true;
}

void AIronwallUnrealClient::BeginPlay()
{
    Super::BeginPlay();
    SessionToken = FPlatformMisc::GetEnvironmentVariable(TEXT("IRONWALL_SESSION_TOKEN"));
}

void AIronwallUnrealClient::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);

    TSharedRef<FJsonObject> Actions = MakeShared<FJsonObject>();
    Actions->SetNumberField(TEXT("move_x"), 0.0);
    Actions->SetNumberField(TEXT("move_y"), 0.0);
    Actions->SetNumberField(TEXT("look_x"), 0.0);
    Actions->SetNumberField(TEXT("look_y"), 0.0);

    if (const APlayerController* Controller = GetWorld()->GetFirstPlayerController())
    {
        Actions->SetBoolField(TEXT("fire"), Controller->IsInputKeyDown(EKeys::LeftMouseButton));
        Actions->SetBoolField(TEXT("jump"), Controller->IsInputKeyDown(EKeys::SpaceBar));
    }
    else
    {
        Actions->SetBoolField(TEXT("fire"), false);
        Actions->SetBoolField(TEXT("jump"), false);
    }

    TSharedRef<FJsonObject> Payload = MakeShared<FJsonObject>();
    Payload->SetStringField(TEXT("engine"), TEXT("unreal"));
    Payload->SetStringField(TEXT("player_id"), PlayerId);
    Payload->SetNumberField(TEXT("sequence"), static_cast<double>(Sequence++));
    Payload->SetNumberField(TEXT("timestamp_ns"), FDateTime::UtcNow().ToUnixTimestamp() * 1000000000.0);
    Payload->SetObjectField(TEXT("actions"), Actions);

    FString PayloadJson;
    TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&PayloadJson);
    FJsonSerializer::Serialize(Payload, Writer);
    SendInputPayload(PayloadJson);
}

void AIronwallUnrealClient::SendInputPayload(const FString& PayloadJson) const
{
    TSharedRef<IHttpRequest, ESPMode::ThreadSafe> Request = FHttpModule::Get().CreateRequest();
    Request->SetURL(BridgeUrl);
    Request->SetVerb(TEXT("POST"));
    Request->SetHeader(TEXT("Content-Type"), TEXT("application/json"));
    Request->SetHeader(TEXT("Authorization"), TEXT("Bearer ") + SessionToken);
    Request->SetContentAsString(PayloadJson);
    Request->ProcessRequest();
}
