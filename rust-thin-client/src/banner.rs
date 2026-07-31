pub fn print_banner() {
    let candidates = [
        "assets/banner.txt",
        "../assets/banner.txt",
        "../../assets/banner.txt",
    ];
    for path in candidates {
        if let Ok(s) = std::fs::read_to_string(path) {
            println!("{s}");
            return;
        }
    }
    println!("=== IRONWALL Anti-Cheat ===\n");
}
