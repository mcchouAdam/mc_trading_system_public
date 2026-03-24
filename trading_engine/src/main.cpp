#include <iostream>

#include "EngineCore.hpp"

int main() {
    std::cout << "--- Starting C++ Trading Engine ---" << std::endl;
    try {
        EngineCore engine;
        engine.run();
    } catch (const std::exception& e) {
        std::cerr << "[CRITICAL] Engine failed: " << e.what() << std::endl;
        return 1;
    }
    return 0;
}
