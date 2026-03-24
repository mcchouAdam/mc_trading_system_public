#include <chrono>
#include <iostream>
#include <thread>

#include "AppConfig.hpp"
#include "CapitalWsClient.hpp"

int main() {
    AppConfig::load_env(".env");

    constexpr int ERROR_RETRY_DELAY_SECONDS = 5;

    while (true) {
        std::cout << "--- Starting Capital.com WS Client ---" << std::endl;
        bool normal_exit = false;
        try {
            CapitalWsClient client;
            client.run();
            normal_exit = true;
        } catch (const std::exception& e) {
            std::cerr << "[CRITICAL ERROR] " << e.what() << std::endl;
            normal_exit = false;
        }

        if (normal_exit) {
            std::cout << "[INFO] Restarting client immediately due to config update..." << std::endl;
            std::this_thread::sleep_for(std::chrono::milliseconds(AppConfig::RESTART_DELAY_MS));
        } else {
            std::cout << "[RECONNECT] Waiting " << ERROR_RETRY_DELAY_SECONDS << "s before retrying..." << std::endl;
            std::this_thread::sleep_for(std::chrono::seconds(ERROR_RETRY_DELAY_SECONDS));
        }
    }
    return 0;
}
