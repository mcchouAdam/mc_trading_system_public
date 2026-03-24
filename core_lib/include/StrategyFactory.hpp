#pragma once

#include <memory>
#include <string>
#include <map>
#include <functional>
#include <unordered_map>

#include "IStrategy.hpp"
#include "strategies/MACD.hpp"
#include "strategies/PineL4.hpp"
#include "strategies/YuBrokenBottom.hpp"

class StrategyFactory {
public:
    using CreatorFunc = std::function<std::unique_ptr<IStrategy>(const std::map<std::string, double>&)>;

    static StrategyFactory& instance() {
        static StrategyFactory factory;
        return factory;
    }

    void register_strategy(const std::string& name, CreatorFunc creator) {
        creators_[name] = std::move(creator);
    }

    std::unique_ptr<IStrategy> create(const std::string& name, const std::map<std::string, double>& params) const {
        auto it = creators_.find(name);
        if (it != creators_.end()) {
            return it->second(params);
        }
        return nullptr;
    }

private:
    StrategyFactory() {
        register_strategy("MACD", [](const std::map<std::string, double>& p) { return std::make_unique<MACD>(p); });
        register_strategy("YuBrokenBottom", [](const std::map<std::string, double>& p) { return std::make_unique<YuBrokenBottom>(p); });
        register_strategy("PineL4", [](const std::map<std::string, double>& p) { return std::make_unique<PineL4>(p); });
    }

    std::unordered_map<std::string, CreatorFunc> creators_;
};
