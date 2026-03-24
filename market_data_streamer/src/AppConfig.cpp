#include "../include/AppConfig.hpp"

#include <algorithm>
#include <cstdlib>
#include <fstream>
#include <iostream>

namespace {
std::string trim(std::string_view s) {
    auto first = s.find_first_not_of(" \t\r\n");
    if (std::string_view::npos == first) return "";
    auto last = s.find_last_not_of(" \t\r\n");
    return std::string(s.substr(first, (last - first + 1)));
}
}  // namespace

void AppConfig::load_env(std::string_view filename) {
    std::ifstream file;
    std::string fname(filename);
    std::string search_paths[] = {fname, "../" + fname, "../../" + fname};

    bool found = false;
    for (const auto& path : search_paths) {
        file.open(path);
        if (file.is_open()) {
            found = true;
            break;
        }
    }

    if (!found) {
        std::cerr << "[WARNING] Configuration file '" << filename
                  << "' not found. Falling back to system environment variables." << std::endl;
        return;
    }

    std::string line;
    int line_count = 0;
    while (std::getline(file, line)) {
        line_count++;
        // Skip comments and empty lines
        if (line.empty() || line[0] == '#') continue;

        auto equal_pos = line.find('=');
        if (equal_pos == std::string::npos) continue;

        std::string key = trim(line.substr(0, equal_pos));
        std::string value = trim(line.substr(equal_pos + 1));

        if (key.empty()) continue;

        // Set environment variable if not already present
        if (std::getenv(key.c_str()) == nullptr) {
#ifdef _WIN32
            _putenv_s(key.c_str(), value.c_str());
#else
            setenv(key.c_str(), value.c_str(), 1);
#endif
        }
    }
    std::cout << "[SUCCESS] Successfully loaded environment from '" << filename << "'" << std::endl;
}

std::string AppConfig::get_redis_host() {
    return get_env("REDIS_HOST", "127.0.0.1");
}

std::string AppConfig::get_redis_port() {
    return get_env("REDIS_PORT", "6379");
}

std::string AppConfig::get_redis_password() {
    return get_env("REDIS_PASSWORD", "");
}

std::string AppConfig::get_env(std::string_view key, std::string_view default_val) {
    const char* env = std::getenv(std::string(key).c_str());
    return env ? std::string(env) : std::string(default_val);
}
