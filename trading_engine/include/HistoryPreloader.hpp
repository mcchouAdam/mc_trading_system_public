#pragma once

#include <sw/redis++/redis++.h>

#include <deque>
#include <functional>
#include <mutex>
#include <set>
#include <string>

#include "Bar.hpp"

class HistoryPreloader {
public:
    HistoryPreloader(sw::redis::Redis* redis);

    // preload_cb will be called if data is successfully loaded
    void preload(const std::string& epic, const std::string& resolution, std::function<bool()> check_if_empty,
                 std::function<void(const std::deque<Bar>&)> on_history_loaded);

private:
    sw::redis::Redis* redis_;
    std::set<std::string> preloading_tasks_;
    std::mutex preload_mutex_;
};
