#include "RedisService.hpp"

#include "AppConfig.hpp"

RedisService::RedisService() {
    sw::redis::ConnectionOptions opts;
    opts.host = AppConfig::get_redis_host();
    opts.port = std::stoi(AppConfig::get_redis_port());

    std::string password = AppConfig::get_redis_password();
    if (!password.empty()) {
        opts.password = password;
    }

    redis_ = std::make_unique<sw::redis::Redis>(opts);
}

sw::redis::Redis& RedisService::client() {
    return *redis_;
}

sw::redis::OptionalString RedisService::fetch_value(const std::string& key) {
    if (!redis_) return {};
    return redis_->get(key);
}

void RedisService::set_last_seen(const std::string& key) {
    if (redis_) {
        redis_->set(key, std::to_string(std::time(nullptr)));
    }
}
