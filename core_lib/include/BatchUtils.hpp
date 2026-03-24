#pragma once
#include <vector>

struct BatchResult {
    std::vector<bool> entries;
    std::vector<bool> exits;
    std::vector<bool> short_entries;
    std::vector<bool> short_exits;
    std::vector<double> exit_prices;
    std::vector<double> stop_lines;
};

struct MarketDataBatch {
    const std::vector<double>& opens;
    const std::vector<double>& highs;
    const std::vector<double>& lows;
    const std::vector<double>& closes;
    const std::vector<double>& volumes;
};
