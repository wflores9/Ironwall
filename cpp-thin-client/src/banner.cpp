#include <iostream>
#include <fstream>
#include <string>

namespace ironwall {
void print_banner() {
    std::ifstream in("../assets/banner.txt");
    if (!in) in.open("../../assets/banner.txt");
    if (!in) in.open("assets/banner.txt");
    if (in) {
        std::string line;
        while (std::getline(in, line)) std::cout << line << "\n";
    } else {
        std::cout << "=== IRONWALL Anti-Cheat ===\n";
    }
    std::cout << std::endl;
}
}
