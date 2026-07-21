using UnrealBuildTool;
using System.IO;

public class Ironwall : ModuleRules
{
    public Ironwall(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

        PublicDependencyModuleNames.AddRange(new string[] {
            "Core", "CoreUObject", "Engine"
        });

        string IronwallRoot = Path.GetFullPath(Path.Combine(ModuleDirectory, "../../.."));
        PublicIncludePaths.Add(Path.Combine(IronwallRoot, "include"));

        // Link static lib (preferred for UE) or shared
        string LibPath = Path.Combine(IronwallRoot, "build", "libironwall.a");
        if (File.Exists(LibPath))
        {
            PublicAdditionalLibraries.Add(LibPath);
        }
        else
        {
            // fallback name without path for system install
            PublicAdditionalLibraries.Add("ironwall");
        }
    }
}
