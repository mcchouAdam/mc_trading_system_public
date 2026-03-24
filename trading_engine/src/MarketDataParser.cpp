#include "MarketDataParser.hpp"

#include <cstdio>
#include <ctime>

#include "EngineConstants.hpp"
#include "Position.hpp"

Bar MarketDataParser::parse_realtime_tick(const std::string& epic, const nlohmann::json& data) {
    Bar tick;
    tick.epic = epic;
    tick.resolution = EngineConstants::RESOLUTION_TICK;
    tick.close = data.value("bid", 0.0);
    tick.open = tick.close;
    tick.high = tick.close;
    tick.low = tick.close;
    tick.timestamp = data.value("timestamp", 0LL);
    return tick;
}

Bar MarketDataParser::parse_realtime_bar(const std::string& epic, const std::string& res, const nlohmann::json& data) {
    Bar bar;
    bar.epic = epic;
    bar.resolution = res;

    bar.open = data.contains("o") ? data["o"].get<double>() : data.value("open", 0.0);
    bar.high = data.contains("h") ? data["h"].get<double>() : data.value("high", 0.0);
    bar.low = data.contains("l") ? data["l"].get<double>() : data.value("low", 0.0);
    bar.close = data.contains("c") ? data["c"].get<double>() : data.value("close", 0.0);

    if (data.contains("t")) {
        bar.timestamp = data["t"].get<int64_t>() / 1000;
    } else {
        std::string st = data.value("snapshotTime", "");
        if (!st.empty()) {
            struct tm t = {0};
            if (sscanf(st.c_str(), EngineConstants::ISO_DATETIME_FORMAT, &t.tm_year, &t.tm_mon, &t.tm_mday, &t.tm_hour,
                       &t.tm_min, &t.tm_sec) == 6) {
                t.tm_year -= 1900;
                t.tm_mon -= 1;
                bar.timestamp = (int64_t)mktime(&t);
            }
        }
    }
    return bar;
}

Bar MarketDataParser::parse_history_bar(const std::string& epic, const std::string& res, const nlohmann::json& row) {
    Bar b;
    b.epic = epic;
    b.resolution = res;
    b.open = row.value("open_price", 0.0);
    b.high = row.value("high_price", 0.0);
    b.low = row.value("low_price", 0.0);
    b.close = row.value("close_price", 0.0);

    struct tm t = {0};
    if (sscanf(row.value("time", "").c_str(), EngineConstants::ISO_DATETIME_FORMAT, &t.tm_year, &t.tm_mon, &t.tm_mday,
               &t.tm_hour, &t.tm_min, &t.tm_sec) == 6) {
        t.tm_year -= 1900;
        t.tm_mon -= 1;
        b.timestamp = (int64_t)mktime(&t);
    }
    return b;
}

Position MarketDataParser::parse_position(const nlohmann::json& item) {
    Position p;
    p.deal_id = item.value("deal_id", "");
    p.epic = item.value("epic", "");
    p.direction = item.value("direction", PositionDirection::BUY);
    p.entry_price = item.value("entry_price", 0.0);
    p.current_stop = item.value("stop_level", 0.0);
    p.current_tp =
        (item.contains("profit_level") && !item["profit_level"].is_null()) ? item["profit_level"].get<double>() : 0.0;
    p.strategy_name = item.value("strategy", "");
    return p;
}

std::map<std::string, double> MarketDataParser::parse_parameters(const nlohmann::json& item) {
    std::map<std::string, double> params;
    if (item.contains("parameters") && item["parameters"].is_object()) {
        auto params_json = item["parameters"];
        for (auto it = params_json.begin(); it != params_json.end(); ++it) {
            params[it.key()] = (double)it.value();
        }
    }
    return params;
}

nlohmann::json MarketDataParser::serialize_position_update(const std::string& deal_id, const std::string& epic,
                                                           const Signal& sig, const std::string& strategy_name,
                                                           const std::string& source) {
    return {{"deal_id", deal_id},
            {"epic", epic},
            {"action", (sig.action == SignalAction::UPDATE_SL ? EngineConstants::SIGNAL_ACTION_UPDATE_SL
                                                              : EngineConstants::SIGNAL_ACTION_CLOSE)},
            {"stop_loss", sig.stop_loss},
            {"take_profit", sig.take_profit},
            {"strategy", strategy_name},
            {"source", source}};
}

nlohmann::json MarketDataParser::serialize_trade_signal(const Signal& sig, const StrategyInstance& s,
                                                        const std::string& resolution) {
    return {{"epic", sig.epic},
            {"action", (sig.action == SignalAction::BUY ? PositionDirection::BUY : PositionDirection::SELL)},
            {"price", sig.price},
            {"stop_loss", sig.stop_loss},
            {"take_profit", sig.take_profit},
            {"strategy", s.name},
            {"resolution", resolution},
            {"sizing_type", s.sizing_type},
            {"position_size", s.position_size},
            {"use_ml", s.use_ml}};
}
