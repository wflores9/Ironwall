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
        PublicAdditionalLibraries.Add(Path.Combine(IronwallRoot, "build", "libironwall.a"));
    }
}
