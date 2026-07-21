#include "IronwallModule.h"
#include "Modules/ModuleManager.h"

#define LOCTEXT_NAMESPACE "FIronwallModule"

void FIronwallModule::StartupModule()
{
    UE_LOG(LogTemp, Log, TEXT("Ironwall anti-cheat module started"));
}

void FIronwallModule::ShutdownModule()
{
    UE_LOG(LogTemp, Log, TEXT("Ironwall anti-cheat module shut down"));
}

#undef LOCTEXT_NAMESPACE

IMPLEMENT_MODULE(FIronwallModule, Ironwall)
