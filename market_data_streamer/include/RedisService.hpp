#ifndef REDIS_SERVICE_HPP
#define REDIS_SERVICE_HPP

#include <sw/redis++/redis++.h>

#include <memory>
#include <string>

class RedisService {
public:
    RedisService();
    sw::redis::Redis& client();
    sw::redis::OptionalString fetch_value(const std::string& key);
    void set_last_seen(const std::string& key);

private:
    std::unique_ptr<sw::redis::Redis> redis_;
};

#endif  // REDIS_SERVICE_HPP
